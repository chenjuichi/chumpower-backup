import math

import json

from datetime import datetime

from flask import Blueprint, jsonify, request

#from database.tables import default_process_steps
from database.tables import Session
from database.p_tables import P_Material, P_Assemble, P_Process, P_Product, P_Part

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect
#from werkzeug.security import generate_password_hash
from sqlalchemy import func, or_

from datetime import datetime, timezone

#import pymysql
#from sqlalchemy import exc
#from sqlalchemy import func

createTableP = Blueprint('createTableP', __name__)


from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


def _int_or_error(value, name):
  try:
    iv = int(value)
    if iv < 0:
      raise ValueError
    return iv
  except Exception:
    raise ValueError(f"{name} 必須是非負整數")


def _normalize_int(value, default=0):
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def read_all_p_part_process_code_p():

    # 從 p_part 資料表讀取所有製程資料，組出：
    #
    #     code_to_assembleStep = { '100-01': step_code, '100-02': step_code, ... }
    #
    # 規則：
    #   - 使用 P_Part.part_code 當 key 的來源，例如 'B100-01'
    #   - 若 part_code 以 'B' 開頭，就去掉 'B'，變成 '100-01' 當 dict 的 key
    #   - value 直接使用 P_Part.process_step_code

    session = Session()
    code_to_assembleStep = {}

    try:
        parts = session.query(P_Part).order_by(P_Part.id).all()
        print(f"read_all_p_part_process_code_p(): 從 p_part 讀到 {len(parts)} 筆資料")

        for part in parts:
            raw_code = (part.part_code or "").strip()
            if not raw_code:
                continue

            # 去掉開頭 'B'，跟原本 Excel 版的行為一致
            if raw_code.startswith("B"):
                key = raw_code[1:]   # 'B100-01' -> '100-01'
            else:
                key = raw_code

            step = part.process_step_code or 0
            if not step:
                # 若 process_step_code 為 0 或 None，就略過（必要時可以改成保留）
                continue

            # 若同一個 key 被多筆覆蓋，印出提示（最後一筆會生效）
            if key in code_to_assembleStep and code_to_assembleStep[key] != step:
                print(
                    f"  ⚠️ key={key} 已有 step={code_to_assembleStep[key]}，"
                    f"這筆 part_code={raw_code} 的 step={step} 會覆蓋前一筆"
                )

            code_to_assembleStep[key] = step

    finally:
        session.close()

    print("read_all_p_part_process_code_p(), 從 p_part 組完，總筆數:", len(code_to_assembleStep))
    return code_to_assembleStep


# ------------------------------------------------------------------


@createTableP.route("/createProcessP", methods=['POST'])
def create_process_p():
  print("createProcessP....")

  request_data = request.get_json()

  _begin_time = request_data.get('begin_time')
  _end_time = request_data.get('end_time')
  _period_time = request_data.get('periodTime')
  _period_time2 = request_data.get('periodTime2')
  _process_work_time_qty = request_data.get('process_work_time_qty')

  _normal_work_time = request_data.get('normal_work_time')
  _assemble_id = request_data.get('assemble_id')
  _has_started = bool(request_data.get('has_started'))

  _user_id = request_data['user_id']
  _material_id = request_data['id']
  _process_type= request_data['process_type']

  print("process_type:", _process_type)
  print("id:", _material_id)
  print("assemble_id:", _assemble_id)
  print("has_started:", _has_started)
  print("begin_time:", _begin_time)
  print("end_time:", _end_time)

  s = Session()

  material = s.query(P_Material).filter_by(id = _material_id).first()

  print("material:", material)
  if not material:
    print("error, order_num 不存在!")
    return jsonify({"error": "order_num 不存在"}), 400  # 找不到對應的 Material 記錄
  print("step1...", material.id)

  if _process_type != 6 and _process_type != 5:
    # 計算期間時間
    if _period_time2:
      period_time = _period_time2
    else:
      time_diff = datetime.strptime(_end_time, "%Y-%m-%d %H:%M:%S") - datetime.strptime(_begin_time, "%Y-%m-%d %H:%M:%S")
      period_time = str(time_diff).split('.')[0]  # 去除微秒，格式為 'HH:MM:SS'
    print("step2-1...", period_time)

  # 3️⃣ 直接新增 P_Process 記錄（無論是否已存在）
  new_process = P_Process(
    material_id = _material_id,
    assemble_id = _assemble_id,
    has_started = _has_started,
    user_id = _user_id,
    process_type = _process_type,
    normal_work_time = _normal_work_time,

    begin_time = _begin_time if _process_type != 6 and _process_type != 5 else '',
    end_time = _end_time if _process_type != 6 and _process_type != 5 else '',
    period_time = period_time if _process_type != 6 and _process_type != 5 else '',
    process_work_time_qty = _process_work_time_qty if _process_type != 6 and _process_type != 5 else 0,
  )
  print("step3...")

  s.add(new_process)

  s.flush()  # ← 立刻送出 INSERT 並回填自增 id（未提交交易）

  new_process_id = new_process.id  # ← 這裡就拿得到主鍵 id
  print("new_process_id:", new_process_id)

  s.commit()

  s.close()

  return jsonify({
    'status': True,
    'process_id': new_process_id
  })


@createTableP.route("/copyAssembleForDifferenceP", methods=['POST'])
def copy_assemble_for_difference_p():
  print("copyAssembleForDifferenceP....")

  request_data = request.get_json()

  _copy_id = request_data['copy_id']
  _must_qty = request_data.get('must_receive_qty')
  _pre_must_qty = request_data.get('pre_must_receive_qty')

  #print("_copy_id, _must_qty", _copy_id, _must_qty)

  return_value = True
  s = Session()

  # 根據 copy_id 尋找現有的 Material 資料
  #exist = s.query(Assemble).filter_by(id = _copy_id).first()

  # 1. 取得原始 assemble 記錄
  source_assemble = s.query(P_Assemble).get(_copy_id)

  """
  # 2. 找出符合複製條件的所有 assemble 記錄
  matching_assembles = s.query(Assemble).filter(
      Assemble.material_id == source_assemble.material_id,
      Assemble.must_receive_qty == source_assemble.must_receive_qty,
      #Assemble.process_step_code <= source_assemble.process_step_code
  ).all()
  """
  k = _copy_id
  h = k + 1
  m = k + 2  # 若之後也要用，可以一起放進 IN

  ids = [k, h]            # 只要 k、h
  matching_assembles = (
    s.query(P_Assemble)
     .filter(
        P_Assemble.material_id == source_assemble.material_id,
        P_Assemble.update_time == source_assemble.update_time,
        P_Assemble.id.in_(ids)          # 「包含 k 或 h」
     )
     .order_by(P_Assemble.id.asc())
     .all()
  )
  print("matching_assembles:",matching_assembles)

  # 2-1. 先更新這些舊紀錄的 must_receive_end_qty = pre_must_receive_qty
  #      （如果 pre_must_receive_qty 有帶進來）
  if _pre_must_qty is not None:
    try:
      pre_must_val = int(_pre_must_qty)
    except (TypeError, ValueError):
      pre_must_val = 0

    for rec in matching_assembles:
      print(f"update old rec(id={rec.id}) must_receive_end_qty ->", pre_must_val)
      rec.must_receive_end_qty = pre_must_val

  # 3. 複製這些記錄（排除 id）並新增到 DB
  print("len(matching_assembles):", len(matching_assembles))
  new_ids = []
  for record in matching_assembles:
    #abnormal_field=False
    """
    if record.work_num == 'B109':
      process_step_code =3
      ok2=3
      ok3=3
    if record.work_num == 'B110':
      process_step_code =2
      ok2=5
      ok3=5
    if record.work_num == 'B106':
      process_step_code =1
      ok2=7
      ok3=7
    else:
      # 如果不是這三種工作中心，就略過，不新增
      print("skip record.id =", record.id, "work_num =", record.work_num)
      continue
    """
    #code_to_assembleStep = read_all_p_part_process_code_p()
    #process_step_code = code_to_assembleStep
    process_step_code = record.process_step_code
    ok2 = 0
    ok3 = 0

    """
    if record.work_num == 'B109':
        process_step_code = 3
        ok2 = 3
        ok3 = 3
    elif record.work_num == 'B110':
        process_step_code = 2
        ok2 = 5
        ok3 = 5
    elif record.work_num == 'B106':
        process_step_code = 1
        ok2 = 7
        ok3 = 7
    else:
        # 如果不是這三種工作中心，就略過，不新增
        print("skip record.id =", record.id, "work_num =", record.work_num)
        continue
    """
    abnormal_field=False

    new_record = P_Assemble(
      material_id=record.material_id,
      material_num=record.material_num,
      material_comment=record.material_comment,
      seq_num=record.seq_num,
      work_num=record.work_num,
      process_step_code=process_step_code,
      must_receive_qty = _must_qty,     #應領取數量
      must_receive_end_qty=_must_qty,
      input_disable =False,
      input_end_disable =False,
      input_abnormal_disable = abnormal_field,
      completed_qty = 0,                    #完成數量
      total_completed_qty = 0,
      ask_qty=0,
      update_time= datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      is_copied_from_id=record.id,
      show2_ok=ok2,
      show3_ok=ok3,

      isShowBomGif=record.isShowBomGif,
      isStockIn = record.isStockIn,
      isSimultaneously = record.isSimultaneously,
    )
    s.add(new_record)
    s.flush()  # 先 flush 以取得新 ID
    print("new_record.id:", new_record.id)
    new_ids.append(new_record.id)
  # end for loop

  try:
    s.commit()
    print("Process data create successfully.")
  except Exception as e:
    s.rollback()
    print("Error:", str(e))
    return_message = '錯誤! 資料新增複製沒有成功...'
    return_value = False

  s.close()

  return jsonify({
    'assemble_data': new_ids,
  })


@createTableP.route("/copyNewAssembleP", methods=['POST'])
def copy_new_assemble_p():
  print("copyNewAssembleP....")

  request_data = request.get_json()
  print("request_data:", request_data)

  _copy_id = request_data['copy_id']
  _must_qty = request_data.get('must_receive_qty')

  print("_copy_id, _must_qty", _copy_id, _must_qty)

  return_value = True
  s = Session()

  # 根據 copy_id 尋找現有的 Material 資料
  #exist = s.query(Assemble).filter_by(id = _copy_id).first()

  # 1. 取得原始 assemble 記錄
  source_assemble = s.query(P_Assemble).get(_copy_id)

  matching_assembles = []
  """
  bb = source_assemble
  while True:
      aa = s.get(Assemble, bb.id + 1)  # 下一筆（相鄰 id）
      if not aa:
          break
      if (aa.material_id == source_assemble.material_id) and (aa.update_time == source_assemble.update_time):
        matching_assembles.append(aa)
        bb = aa   # 往下一筆繼續找
      else:
        break
  """

  """
    # 2. 找出符合複製條件的所有 assemble 記錄
    matching_assembles = s.query(Assemble).filter(
        Assemble.material_id == source_assemble.material_id,
        Assemble.must_receive_qty == source_assemble.must_receive_qty,
        #Assemble.process_step_code <= source_assemble.process_step_code
    ).all()
  """


  k = _copy_id
  h = k - 1
  m = k + 1  # 若之後也要用，可以一起放進 IN

  ids = [k, h, m]            # 只要 k、h
  matching_assembles = (
    s.query(P_Assemble)
     .filter(
        P_Assemble.material_id == source_assemble.material_id,
        #Assemble.is_copied_from_id == source_assemble.update_time,
        P_Assemble.id.in_(ids)          # 「包含 k 或 h」
     )
     #.order_by(Assemble.id.asc())
     .all()
  )

  print("matching_assembles:",matching_assembles)

  # 3. 複製這些記錄（排除 id）並新增到 DB
  new_ids = []
  for record in matching_assembles:
    abnormal_field=False
    #code_to_assembleStep = read_all_p_part_process_code_p()
    #process_step_code = code_to_assembleStep
    process_step_code = record.process_step_code
    ok2 = 0
    ok3 = 0

    """
    if record.work_num == 'B109':
      process_step_code =3
    if record.work_num == 'B110':
      process_step_code =2
    if record.work_num == 'B106':
      process_step_code =1
    """

    new_record = P_Assemble(
      material_id=record.material_id,
      material_num=record.material_num,
      material_comment=record.material_comment,
      seq_num=record.seq_num,
      work_num=record.work_num,
      process_step_code=process_step_code,
      isAssembleStationShow=False,
      must_receive_qty = _must_qty,         #應領取數量
      must_receive_end_qty = _must_qty,     #應完成數量
      input_disable =False,
      input_end_disable =False,

      alarm_enable=False,
      isAssembleFirstAlarm=False,

      input_abnormal_disable = abnormal_field,
      completed_qty = 0,                    #完成數量
      total_completed_qty = 0,
      ask_qty=0,
      update_time= datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      is_copied_from_id=record.id,
      #show2_ok=3 if (record.work_num=='109') else (5 if (record.work_num=='110') else 7),
      #show3_ok=3 if (record.work_num=='109') else (5 if (record.work_num=='110') else 7),
      show2_ok=ok2,
      show3_ok=ok3,

      isShowBomGif=record.isShowBomGif,
      isStockIn = record.isStockIn,
      isSimultaneously = record.isSimultaneously,
    )
    s.add(new_record)
    s.flush()  # 先 flush 以取得新 ID
    new_ids.append(new_record.id)
  # end for loop

  try:
    s.commit()
    print("Process data create successfully.")
  except Exception as e:
    s.rollback()
    print("Error:", str(e))
    return_message = '錯誤! 資料新增複製沒有成功...'
    return_value = False

  s.close()

  return jsonify({
    'assemble_data': new_ids,
  })


@createTableP.route("/createProductP", methods=["POST"])
def create_product_p():

    # 加工線入庫：
    # 1. 支援單筆或批次
    # 2. allOk_qty 必須 > 0
    # 3. 若 assemble 已入庫，禁止重複入庫
    # 4. 若沒送 process_id，會自動補一筆 P_Process(process_type=31)
    # 5. 建立 P_Product
    # 6. 回寫 P_Material / P_Assemble 狀態

    s = Session()
    try:
        payload = request.get_json() or {}

        raw_items = payload.get("items", None)
        if raw_items is None:
            raw_items = [payload]

        if not isinstance(raw_items, list) or len(raw_items) == 0:
            return jsonify({
                "status": False,
                "error": "payload 應為物件或 {items: [...]}，且不可為空"
            }), 400

        # ---------- 先驗證 material_id ----------
        material_ids = [it.get("material_id") for it in raw_items]
        try:
            material_ids_int = [int(mid) for mid in material_ids]
        except (TypeError, ValueError):
            return jsonify({"status": False, "error": "material_id 必須是整數"}), 400

        exist_mid_set = set(
            [m.id for m in s.query(P_Material.id).filter(P_Material.id.in_(material_ids_int)).all()]
        )

        errors = []
        for idx, it in enumerate(raw_items):
            mid = it.get("material_id")
            if mid is None:
                errors.append({"index": idx, "error": "material_id 為必填"})
                continue
            if int(mid) not in exist_mid_set:
                errors.append({"index": idx, "error": f"material_id {mid} 不存在"})

        if errors:
            return jsonify({"status": False, "errors": errors}), 400

        created_rows = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for idx, it in enumerate(raw_items):
            mid = _normalize_int(it.get("material_id"), 0)
            if mid <= 0:
                continue

            add_qty = _normalize_int(it.get("allOk_qty"), 0)
            if add_qty <= 0:
                return jsonify({
                    "status": False,
                    "error": f"第 {idx + 1} 筆入庫數量必須大於 0"
                }), 400

            user_id = (it.get("user_id") or "").strip() or "system"

            delivery_qty = _normalize_int(it.get("delivery_qty"), 0)
            assemble_qty = _normalize_int(it.get("assemble_qty"), 0)
            good_qty = _normalize_int(it.get("good_qty"), add_qty)
            non_good_qty = _normalize_int(it.get("non_good_qty"), 0)
            line_diff = _normalize_int(it.get("line_difference"), 1)

            # assemble_id：優先用前端送的，否則抓該 material 最新一筆
            assemble_id = _normalize_int(it.get("assemble_id"), 0)
            if assemble_id <= 0:
                latest_a = (
                    s.query(P_Assemble)
                    .filter(P_Assemble.material_id == mid)
                    .order_by(P_Assemble.id.desc())
                    .first()
                )
                assemble_id = latest_a.id if latest_a else 0

            # 先抓 assemble，後面要做防重複與回寫
            a = None
            if assemble_id > 0:
                a = (
                    s.query(P_Assemble)
                    .filter(P_Assemble.id == assemble_id, P_Assemble.material_id == mid)
                    .one_or_none()
                )

            # 已入庫就禁止重複入庫
            #if a and bool(getattr(a, "isStockIn", False)):
            #    return jsonify({
            #        "status": False,
            #        "error": f"material_id={mid}, assemble_id={assemble_id} 已入庫，禁止重複入庫"
            #    }), 400

            process_id_to_use = _normalize_int(it.get("process_id"), 0)

            # 若沒送 process_id，就自動補一筆入庫 P_Process(31)
            if process_id_to_use <= 0:
                exist_proc = None
                if assemble_id > 0:
                    exist_proc = (
                        s.query(P_Process)
                        .filter(P_Process.material_id == mid)
                        .filter(P_Process.assemble_id == assemble_id)
                        .filter(P_Process.process_type == 31)
                        .filter(P_Process.process_work_time_qty == add_qty)
                        .order_by(P_Process.id.desc())
                        .first()
                    )

                if exist_proc:
                    process_id_to_use = exist_proc.id
                else:
                    m_for_must = s.query(P_Material).filter(P_Material.id == mid).one_or_none()
                    must_qty = _normalize_int(getattr(m_for_must, "must_allOk_qty", 0), 0) if m_for_must else 0

                    stockin_proc = P_Process(
                        material_id=mid,
                        assemble_id=assemble_id,
                        has_started=True,
                        user_id=user_id,
                        begin_time=now_str,
                        end_time=now_str,
                        period_time="00:00:00",
                        pause_time=0,
                        elapsedActive_time=0,
                        str_elapsedActive_time="00:00:00",
                        is_pause=True,
                        process_type=31,
                        process_work_time_qty=add_qty,
                        must_allOk_qty=must_qty,
                        allOk_qty=add_qty,
                        isAllOk=True,
                        normal_work_time=0,
                    )
                    s.add(stockin_proc)
                    s.flush()
                    process_id_to_use = stockin_proc.id

            # 建立 P_Product
            p = P_Product(
                material_id=mid,
                process_id=(process_id_to_use or None),
                line_difference=line_diff,
                delivery_qty=delivery_qty,
                assemble_qty=assemble_qty,
                allOk_qty=add_qty,
                good_qty=good_qty,
                non_good_qty=non_good_qty,
                reason=(it.get("reason") or None),
                confirm_comment=(it.get("confirm_comment") or None),
            )
            s.add(p)
            s.flush()
            created_rows.append(p)

            # 回寫 P_Material
            m = s.query(P_Material).filter(P_Material.id == mid).one_or_none()
            if m is not None:
                old_total = _normalize_int(getattr(m, "total_allOk_qty", 0), 0)
                new_total = old_total + add_qty

                m.allOk_qty = add_qty
                m.total_allOk_qty = new_total

                must_qty2 = _normalize_int(getattr(m, "must_allOk_qty", 0), 0)
                #if must_qty2 > 0 and new_total >= must_qty2:
                if new_total >= must_qty2:
                    m.isAllOk = True
                    m.show2_ok = 8

            # 回寫 P_Assemble：已入庫後不要再顯示於待入庫清單
            if a:
                a.allOk_qty = add_qty
                a.isStockIn = True
                #a.isWarehouseStationShow = False
                a.isWarehouseStationShow = True
                a.update_time = now_str

        s.commit()

        items = []
        for p in created_rows:
            items.append({
                "id": p.id,
                "material_id": p.material_id,
                "process_id": p.process_id,
                "delivery_qty": p.delivery_qty,
                "assemble_qty": p.assemble_qty,
                "allOk_qty": p.allOk_qty,
                "good_qty": p.good_qty,
                "non_good_qty": p.non_good_qty,
                "reason": p.reason,
                "confirm_comment": p.confirm_comment,
                "create_at": getattr(p, "create_at", None).isoformat() if getattr(p, "create_at", None) else None,
            })

        return jsonify({
            "status": True,
            "created": len(items),
            "items": items
        })

    except SQLAlchemyError as e:
        s.rollback()
        return jsonify({"status": False, "error": str(e)}), 500
    except Exception as e:
        s.rollback()
        return jsonify({"status": False, "error": str(e)}), 500
    finally:
        s.close()

