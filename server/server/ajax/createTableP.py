#import math

import json

import traceback

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

#from database.tables import default_process_steps
from database.tables import Session
from database.p_tables import P_Material, P_Assemble, P_Process, P_Product, P_Part

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect

from sqlalchemy import func, or_

from datetime import datetime, timezone

createTableP = Blueprint('createTableP', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


"""
def _int_or_error(value, name):
  try:
    iv = int(value)
    if iv < 0:
      raise ValueError
    return iv
  except Exception:
    raise ValueError(f"{name} 必須是非負整數")
"""


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


"""
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
"""

# 20260813版
# ...
# 20260804版
# createProcessP：
# 1. 使用 P_Material row lock，避免多人同時新增
# 2. type=2/5/19：30 秒內相同搬運防重複
# 3. type=3：同 material 只建立一次
# 4. type=6：空白搬運通知防重複
# 5. type=21/22/23：相同員工、工序的 active process 防重複
# 6. type=5 保留 begin_time / end_time / period_time
@createTableP.route("/createProcessP", methods=["POST"])
def create_process_p():
    print("createProcessP....")

    request_data = request.get_json(silent=True) or {}

    begin_time = request_data.get("begin_time")
    end_time = request_data.get("end_time")
    period_time1 = request_data.get("periodTime")
    period_time2 = request_data.get("periodTime2")

    normal_work_time = request_data.get("normal_work_time")
    process_work_time_qty = request_data.get(
        "process_work_time_qty",
        0
    )

    assemble_id_raw = request_data.get("assemble_id")
    has_started = bool(request_data.get("has_started"))

    user_id = str(request_data.get("user_id") or "").strip()
    material_id_raw = request_data.get("id")
    process_type_raw = request_data.get("process_type")

    # ------------------------------------------------------------
    # 參數檢查
    # ------------------------------------------------------------
    if (
        not user_id
        or material_id_raw is None
        or process_type_raw is None
    ):
        return jsonify({
            "status": False,
            "message":
                "missing params: user_id / id / process_type"
        }), 400

    try:
        material_id = int(material_id_raw)
        process_type = int(process_type_raw)
        assemble_id = int(assemble_id_raw or 0)
        work_qty = int(process_work_time_qty or 0)
    except (TypeError, ValueError):
        return jsonify({
            "status": False,
            "message":
                "invalid params: id / process_type / "
                "assemble_id / process_work_time_qty"
        }), 400

    def parse_datetime(value):
        if value in (None, "", "None"):
            return None

        if isinstance(value, datetime):
            return value

        text = str(value).strip()

        if text.endswith("Z"):
            text = text[:-1]

        text = text.replace("T", " ")

        try:
            return datetime.fromisoformat(text)
        except (TypeError, ValueError):
            pass

        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
        ):
            try:
                return datetime.strptime(text, fmt)
            except (TypeError, ValueError):
                continue

        return None

    session = Session()

    try:
        # --------------------------------------------------------
        # 鎖定加工線 material
        # --------------------------------------------------------
        material = (
            session.query(P_Material)
            .filter(P_Material.id == material_id)
            .with_for_update()
            .one_or_none()
        )

        if not material:
            session.rollback()

            return jsonify({
                "status": False,
                "message":
                    f"p_material id={material_id} 不存在"
            }), 400

        print(
            "[createProcessP] material locked:",
            material.id
        )

        # --------------------------------------------------------
        # type=2 / 5 / 19：
        # 同 material、type、user，30 秒內視為重送
        # --------------------------------------------------------
        if process_type in {2, 5, 19}:
            incoming_begin_dt = parse_datetime(begin_time)

            latest_transport = (
                session.query(P_Process)
                .filter(
                    P_Process.material_id == material_id,
                    P_Process.process_type == process_type,
                    P_Process.user_id == user_id,
                )
                .order_by(
                    P_Process.id.desc()
                )
                .first()
            )

            if latest_transport and incoming_begin_dt:
                latest_begin_dt = parse_datetime(
                    latest_transport.begin_time
                )

                if latest_begin_dt:
                    diff_seconds = abs(
                        (
                            incoming_begin_dt
                            - latest_begin_dt
                        ).total_seconds()
                    )

                    if diff_seconds <= 30:
                        session.commit()

                        print(
                            "[createProcessP] duplicate "
                            "transport skipped:",
                            {
                                "material_id": material_id,
                                "process_type": process_type,
                                "existing_process_id":
                                    latest_transport.id,
                                "diff_seconds":
                                    diff_seconds,
                            }
                        )

                        return jsonify({
                            "status": True,
                            "created": False,
                            "process_id":
                                latest_transport.id,
                            "skipped": True,
                            "duplicate": True,
                            "message":
                                "短時間內已有相同搬運紀錄，"
                                "本次重複呼叫已忽略",
                        }), 200

        # --------------------------------------------------------
        # type=3：
        # AGV 加工區 -> 成品區，同 material 防重複
        # --------------------------------------------------------
        if process_type == 3:
            existed_type3 = (
                session.query(P_Process)
                .filter(
                    P_Process.material_id == material_id,
                    P_Process.process_type == 3,
                )
                .order_by(P_Process.id.asc())
                .first()
            )

            if existed_type3:
                session.commit()

                return jsonify({
                    "status": True,
                    "created": False,
                    "process_id": existed_type3.id,
                    "skipped": True,
                    "duplicate": True,
                    "message":
                        "此加工工單已有 AGV 搬運紀錄，"
                        "不重複新增",
                }), 200

        '''
        # --------------------------------------------------------
        # type=6：
        # 空白堆高機通知防重複
        # --------------------------------------------------------
        if process_type == 6:
            existed_type6 = (
                session.query(P_Process)
                .filter(
                    P_Process.material_id == material_id,
                    P_Process.process_type == 6,
                    or_(
                        P_Process.begin_time.is_(None),
                        P_Process.begin_time == "",
                    ),
                    or_(
                        P_Process.end_time.is_(None),
                        P_Process.end_time == "",
                    ),
                    func.coalesce(
                        P_Process.elapsedActive_time,
                        0
                    ) == 0,
                    or_(
                        P_Process.has_started.is_(False),
                        P_Process.has_started.is_(None),
                    ),
                )
                .order_by(P_Process.id.asc())
                .first()
            )

            if existed_type6:
                session.commit()

                return jsonify({
                    "status": True,
                    "created": False,
                    "process_id": existed_type6.id,
                    "skipped": True,
                    "duplicate": True,
                    "message":
                        "已有未執行的堆高機搬運紀錄，"
                        "不重複新增",
                }), 200
        '''
        # 20260813版
        # ------------------------------------------------------------
        # type=6：
        # 堆高機 加工區 -> 成品區
        #
        # 同一個「送出批次 assemble_id」只建立一次。
        #
        # 不可只用 material_id 防重複，
        # 因為一張加工工單可以分批送出多次。
        # ------------------------------------------------------------
        if process_type == 6:

            existed_type6 = (
                session.query(P_Process)
                .filter(
                    P_Process.material_id ==
                    material_id
                )
                .filter(
                    P_Process.assemble_id ==
                    assemble_id
                )
                .filter(
                    P_Process.process_type == 6
                )
                .order_by(
                    P_Process.id.asc()
                )
                .first()
            )

            if existed_type6:
                session.commit()

                return jsonify({
                    "status": True,
                    "created": False,

                    "process_id":
                        existed_type6.id,

                    "skipped": True,
                    "duplicate": True,

                    "message":
                        "此批次已有堆高機搬運紀錄，"
                        "不重複新增",
                }), 200
        #

        # --------------------------------------------------------
        # type=21 / 22 / 23：
        # 同員工、同 assemble、同製程 active 防重複
        # --------------------------------------------------------
        if (
            process_type in {21, 22, 23}
            and has_started
        ):
            existed_active = (
                session.query(P_Process)
                .filter(
                    P_Process.material_id == material_id,
                    P_Process.assemble_id == assemble_id,
                    P_Process.process_type == process_type,
                    P_Process.user_id == user_id,
                    P_Process.has_started.is_(True),
                    or_(
                        P_Process.end_time.is_(None),
                        P_Process.end_time == "",
                    ),
                )
                .order_by(P_Process.id.asc())
                .first()
            )

            if existed_active:
                session.commit()

                return jsonify({
                    "status": True,
                    "created": False,
                    "process_id": existed_active.id,
                    "skipped": True,
                    "duplicate": True,
                    "message":
                        "此員工此加工工序已開始，"
                        "不重複新增",
                }), 200

        # --------------------------------------------------------
        # 計算 period_time
        # type=6 為空白通知，不計算
        # type=5 現在保留搬運時間
        # --------------------------------------------------------
        period_time = ""

        if process_type != 6:
            if period_time2:
                period_time = str(period_time2)

            elif period_time1:
                period_time = str(period_time1)

            elif begin_time and end_time:
                begin_dt = parse_datetime(begin_time)
                end_dt = parse_datetime(end_time)

                if begin_dt and end_dt:
                    period_time = str(
                        end_dt - begin_dt
                    ).split(".")[0]

        # --------------------------------------------------------
        # 新增 P_Process
        # --------------------------------------------------------
        completed_transport = (
            process_type in {2, 3, 5}
            and bool(end_time)
        )

        new_process = P_Process(
            material_id=material_id,
            assemble_id=assemble_id,

            has_started=(
                False
                if completed_transport
                else has_started
            ),

            user_id=user_id,
            process_type=process_type,
            normal_work_time=normal_work_time,

            begin_time=(
                begin_time
                if process_type != 6
                else None
            ),

            end_time=(
                end_time
                if process_type != 6
                else None
            ),

            period_time=(
                period_time
                if process_type != 6
                else ""
            ),

            process_work_time_qty=(
                work_qty
                if process_type != 6
                else 0
            ),

            is_pause=(
                True
                if completed_transport
                else False
            ),

            pause_started_at=None,
        )

        session.add(new_process)
        session.flush()

        new_process_id = new_process.id

        session.commit()

        print(
            "[createProcessP] created:",
            {
                "process_id": new_process_id,
                "material_id": material_id,
                "assemble_id": assemble_id,
                "process_type": process_type,
            }
        )

        return jsonify({
            "status": True,
            "created": True,
            "process_id": new_process_id,
            "skipped": False,
            "duplicate": False,
        }), 200

    except Exception as exc:
        session.rollback()

        print(
            "createProcessP ERROR:",
            repr(exc)
        )

        return jsonify({
            "status": False,
            "message": str(exc),
        }), 500

    finally:
        session.close()


"""
# 20260827版
# 20260813版
@createTableP.route("/copyAssembleForDifferenceP", methods=['POST'])
def copy_assemble_for_difference_p():
  print("copyAssembleForDifferenceP....")

  request_data = request.get_json()

  _copy_id = request_data['copy_id']
  _must_qty = request_data.get('must_receive_qty')
  _pre_must_qty = request_data.get('pre_must_receive_qty')

  #
  # ============================================================
  # 20260827
  # 以「訂單 + 加工工序」計算真正剩餘量
  #
  # 同一 order_num 可能有多個 P_Material，
  # 但 Excel MEINH 是這張訂單這道工序的總加工需求，
  # 不可以每一個 material 都重新從 MEINH 開始扣。
  # ============================================================

  return_value = True
  s = Session()

  # ============================================================
  # 1. 先取得目前實際結束的 P_Assemble
  # ============================================================
  source_assemble = (
      s.query(P_Assemble)
      .filter(
          P_Assemble.id == _copy_id
      )
      .one_or_none()
  )

  if source_assemble is None:
      s.close()

      return jsonify({
          'status': False,
          'message':
              f'找不到 P_Assemble id={_copy_id}',
          'assemble_data': [],
          'remaining_qty': 0,
      }), 404

  # ============================================================
  # 2. 取得 P_Material
  # ============================================================
  material_record = (
      s.query(P_Material)
      .filter(
          P_Material.id ==
          source_assemble.material_id
      )
      .one_or_none()
  )

  if material_record is None:
      s.close()

      return jsonify({
          'status': False,
          'message':
              f'找不到 P_Material id='
              f'{source_assemble.material_id}',
          'assemble_data': [],
          'remaining_qty': 0,
      }), 404


  # ============================================================
  # 3. 再取得訂單 / 工序
  # ============================================================
  order_num = str(
      material_record.order_num or ''
  ).strip()

  work_num = str(
      source_assemble.work_num or ''
  ).strip()

  seq_num = str(
      source_assemble.seq_num or ''
  ).strip()

  # ------------------------------------------------------------
  # 1. 找這張訂單、同一道工序的原始需求量
  #
  # 只看 root row：
  # is_copied_from_id IS NULL
  #
  # 多個 material 可能各自都有 181，
  # 所以不能 SUM，要取 MAX。
  # ------------------------------------------------------------
  target_qty = (
      s.query(
          func.max(
              func.coalesce(
                  P_Assemble.original_must_receive_end_qty,
                  P_Assemble.must_receive_end_qty,
                  0
              )
          )
      )
      .join(
          P_Material,
          P_Material.id ==
          P_Assemble.material_id
      )
      .filter(
          P_Material.order_num == order_num,
          P_Assemble.work_num == work_num,
          P_Assemble.is_copied_from_id.is_(None),
      )
      .scalar()
  )

  target_qty = int(
      target_qty or 0
  )

  # 舊資料 original_must_receive_end_qty 可能沒有值
  if target_qty <= 0:
      target_qty = int(
          source_assemble
          .original_must_receive_end_qty
          or source_assemble
          .must_receive_end_qty
          or source_assemble
          .must_receive_qty
          or 0
      )

  # ------------------------------------------------------------
  # 2. 同訂單 + 同工序，累計真正已完成量
  #
  # 只能 SUM completed_qty，
  # 不可 SUM total_completed_qty，
  # 因為 total_completed_qty 是累計欄位，
  # 再加會重複計算。
  # ------------------------------------------------------------
  total_completed = (
      s.query(
          func.coalesce(
              func.sum(
                  P_Assemble.completed_qty
              ),
              0
          )
      )
      .join(
          P_Material,
          P_Material.id ==
          P_Assemble.material_id
      )
      .filter(
          P_Material.order_num == order_num,
          P_Assemble.work_num == work_num,
      )
      .scalar()
  )

  total_completed = int(
      total_completed or 0
  )

  # ------------------------------------------------------------
  # 3. 同訂單同工序累計廢料
  # ------------------------------------------------------------
  total_abnormal = (
      s.query(
          func.coalesce(
              func.sum(
                  P_Assemble.abnormal_qty
              ),
              0
          )
      )
      .join(
          P_Material,
          P_Material.id ==
          P_Assemble.material_id
      )
      .filter(
          P_Material.order_num == order_num,
          P_Assemble.work_num == work_num,
      )
      .scalar()
  )

  total_abnormal = int(
      total_abnormal or 0
  )

  # ------------------------------------------------------------
  # 4. 真正剩餘量
  # ------------------------------------------------------------
  remaining_qty = max(
      target_qty
      - total_completed
      - total_abnormal,
      0
  )

  print(
      "[copyAssembleForDifferenceP remaining]",
      {
          "order_num": order_num,
          "work_num": work_num,
          "target_qty": target_qty,
          "total_completed": total_completed,
          "total_abnormal": total_abnormal,
          "frontend_difference": _must_qty,
          "remaining_qty": remaining_qty,
      }
  )
  #

  # 根據 copy_id 尋找現有的 Material 資料
  #exist = s.query(Assemble).filter_by(id = _copy_id).first()

  # 1. 取得原始 assemble 記錄
  source_assemble = s.query(P_Assemble).get(_copy_id)

  #
  if source_assemble is None:
    s.close()

    return jsonify({
        'status': False,
        'message':
            f'找不到 P_Assemble id={_copy_id}',
        'assemble_data': [],
    }), 404

  # ------------------------------------------------------------
  # 剩餘列的「領取數量」必須維持整張工單原始領取量。
  #
  # 例如：
  # 原始領取 120
  # 完成 38、剩餘 82
  #
  # 新列：
  #   ask_qty = 120
  #   must_receive_end_qty = 82
  #   total_completed_qty = 38
  # ------------------------------------------------------------
  material_record = (
      s.query(P_Material)
      .filter(
          P_Material.id ==
          source_assemble.material_id
      )
      .first()
  )

  original_ask_qty = max(
      int(
          source_assemble.ask_qty
          or 0
      ),
      int(
          source_assemble.total_ask_qty
          or 0
      ),
      int(
          getattr(
              material_record,
              'material_qty',
              0
          )
          or 0
      ),
  )
  #

  '''
  # 2. 找出符合複製條件的所有 assemble 記錄
  matching_assembles = s.query(Assemble).filter(
      Assemble.material_id == source_assemble.material_id,
      Assemble.must_receive_qty == source_assemble.must_receive_qty,
      #Assemble.process_step_code <= source_assemble.process_step_code
  ).all()
  '''

  '''
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
  '''
  # 20260827版
  # ------------------------------------------------------------
  # 部分完成時，只複製目前實際結束的 P_Assemble。
  #
  # 不可以用 copy_id + 1 判斷另一道工序，
  # 因為資料表 id 只是流水號，不能代表工序關係。
  # ------------------------------------------------------------
  matching_assembles = [
      source_assemble
  ]

  print(
      "matching_assembles:",
      [
          (
              r.id,
              r.work_num,
              r.process_step_code,
              r.must_receive_qty,
              r.must_receive_end_qty,
              r.completed_qty,
          )
          for r in matching_assembles
      ]
  )
  #

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
    '''
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
    '''
    #code_to_assembleStep = read_all_p_part_process_code_p()
    #process_step_code = code_to_assembleStep
    process_step_code = record.process_step_code
    ok2 = 0
    ok3 = 0

    '''
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
    '''
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
      #total_completed_qty = 0,
      # 20260813版
      # 整張工單累計完成量沿用
      total_completed_qty=int(
          _pre_must_qty or 0
      ),

      total_ask_qty_end=int(
          _pre_must_qty or 0
      ),
      #
      #ask_qty=0,
      # 20260813版
      ask_qty=original_ask_qty,
      total_ask_qty=original_ask_qty,
      #
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
"""


"""
# 20260827版
@createTableP.route(
    "/copyAssembleForDifferenceP",
    methods=['POST']
)
def copy_assemble_for_difference_p():

    print("copyAssembleForDifferenceP....")

    request_data = (
        request.get_json(silent=True)
        or {}
    )

    # ============================================================
    # 0. Request
    # ============================================================

    try:
        _copy_id = int(
            request_data.get(
                'copy_id'
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        _copy_id = 0

    # ------------------------------------------------------------
    # 舊前端仍可能傳這些欄位。
    #
    # frontend_difference：
    #   只留作 debug，不再當真正剩餘量。
    #
    # pre_must_receive_qty：
    #   目前前端代表「本次完成數量」。
    # ------------------------------------------------------------

    _frontend_difference = (
        request_data.get(
            'frontend_difference'
        )
    )

    # 相容目前舊版前端
    if _frontend_difference is None:
        _frontend_difference = (
            request_data.get(
                'must_receive_qty'
            )
        )

    _pre_must_qty = (
        request_data.get(
            'pre_must_receive_qty'
        )
    )

    _completed_qty_from_front = (
        request_data.get(
            'completed_qty'
        )
    )

    _abnormal_qty_from_front = (
        request_data.get(
            'abnormal_qty'
        )
    )

    if _copy_id <= 0:
        return jsonify({
            'status': False,
            'message':
                'copy_id 不正確',
            'assemble_data': [],
            'remaining_qty': 0,
        }), 400

    s = Session()

    try:

        # ========================================================
        # 1. 取得目前 P_Assemble
        # ========================================================

        source_assemble = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.id
                ==
                _copy_id
            )
            .with_for_update()
            .one_or_none()
        )

        if source_assemble is None:

            s.rollback()

            return jsonify({
                'status': False,
                'message':
                    f'找不到 P_Assemble '
                    f'id={_copy_id}',
                'assemble_data': [],
                'remaining_qty': 0,
            }), 404

        # ========================================================
        # 2. 取得目前 P_Material
        # ========================================================

        material_record = (
            s.query(P_Material)
            .filter(
                P_Material.id
                ==
                source_assemble.material_id
            )
            .one_or_none()
        )

        if material_record is None:

            s.rollback()

            return jsonify({
                'status': False,
                'message':
                    '找不到 P_Material '
                    f'id={source_assemble.material_id}',
                'assemble_data': [],
                'remaining_qty': 0,
            }), 404

        order_num = str(
            material_record.order_num
            or ''
        ).strip()

        work_num = str(
            source_assemble.work_num
            or ''
        ).strip()

        seq_num = str(
            source_assemble.seq_num
            or ''
        ).strip()

        # ========================================================
        # 3. 本次完成量
        #
        # 優先：
        #   completed_qty_from_front
        #   pre_must_receive_qty
        #   source.completed_qty
        #
        # 只用於：
        #   將完成的舊 row
        #   must_receive_end_qty 改成本批實際完成量。
        #
        # 真正跨批累計仍以 DB SUM(completed_qty) 為準。
        # ========================================================

        try:
            current_completed_qty = int(
                _completed_qty_from_front
                if _completed_qty_from_front
                is not None
                else (
                    _pre_must_qty
                    if _pre_must_qty
                    is not None
                    else (
                        source_assemble
                        .completed_qty
                        or 0
                    )
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            current_completed_qty = int(
                source_assemble
                .completed_qty
                or 0
            )

        current_completed_qty = max(
            current_completed_qty,
            0
        )

        # ========================================================
        # 4. 找這張訂單、同一道工序的 Excel 原始需求量
        #
        # 例如：
        #
        # 121200006710
        # B103-01
        # Excel MEINH = 181
        #
        # 同 order_num 可能有多個 P_Material，
        # 所以不能 SUM 原始需求量。
        #
        # 使用 MAX。
        # ========================================================

        target_qty = (
            s.query(
                func.max(
                    func.coalesce(
                        P_Assemble
                        .original_must_receive_end_qty,

                        P_Assemble
                        .must_receive_end_qty,

                        0
                    )
                )
            )
            .join(
                P_Material,
                P_Material.id
                ==
                P_Assemble.material_id
            )
            .filter(
                P_Material.order_num
                ==
                order_num,

                P_Assemble.work_num
                ==
                work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,

                # 原始 row 優先作為
                # Excel MEINH 的來源
                P_Assemble
                .is_copied_from_id
                .is_(None),
            )
            .scalar()
        )

        target_qty = int(
            target_qty
            or 0
        )

        # --------------------------------------------------------
        # 舊資料 fallback
        # --------------------------------------------------------

        if target_qty <= 0:

            target_qty = int(
                source_assemble
                .original_must_receive_end_qty
                or
                source_assemble
                .must_receive_end_qty
                or
                source_assemble
                .must_receive_qty
                or 0
            )

        if target_qty <= 0:

            s.rollback()

            return jsonify({
                'status': False,
                'message':
                    f'工單 {order_num} '
                    f'工序 {work_num} '
                    '找不到有效應完成數量',
                'assemble_data': [],
                'remaining_qty': 0,
            }), 400

        # ========================================================
        # 5. 同訂單 + 同工序累計完成數量
        #
        # ★ 只能 SUM completed_qty
        #
        # 不可 SUM total_completed_qty，
        # 因為 total_completed_qty 本身就是累計，
        # 再 SUM 會重複。
        # ========================================================

        total_completed = (
            s.query(
                func.coalesce(
                    func.sum(
                        P_Assemble
                        .completed_qty
                    ),
                    0
                )
            )
            .join(
                P_Material,
                P_Material.id
                ==
                P_Assemble.material_id
            )
            .filter(
                P_Material.order_num
                ==
                order_num,

                P_Assemble.work_num
                ==
                work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,
            )
            .scalar()
        )

        total_completed = int(
            total_completed
            or 0
        )

        # ========================================================
        # 6. 同訂單 + 同工序累計廢料
        # ========================================================

        total_abnormal = (
            s.query(
                func.coalesce(
                    func.sum(
                        P_Assemble
                        .abnormal_qty
                    ),
                    0
                )
            )
            .join(
                P_Material,
                P_Material.id
                ==
                P_Assemble.material_id
            )
            .filter(
                P_Material.order_num
                ==
                order_num,

                P_Assemble.work_num
                ==
                work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,
            )
            .scalar()
        )

        total_abnormal = int(
            total_abnormal
            or 0
        )

        # ========================================================
        # 7. 真正剩餘數量
        #
        # Excel MEINH
        # - 同訂單同工序累計完成
        # - 同訂單同工序累計廢料
        # ========================================================

        remaining_qty = max(
            target_qty
            -
            total_completed
            -
            total_abnormal,
            0
        )

        print(
            "[copyAssembleForDifferenceP remaining]",
            {
                'copy_id':
                    _copy_id,

                'material_id':
                    source_assemble.material_id,

                'order_num':
                    order_num,

                'work_num':
                    work_num,

                'seq_num':
                    seq_num,

                'target_qty':
                    target_qty,

                'current_completed_qty':
                    current_completed_qty,

                'total_completed':
                    total_completed,

                'total_abnormal':
                    total_abnormal,

                'frontend_difference':
                    _frontend_difference,

                'remaining_qty':
                    remaining_qty,
            }
        )

        # ========================================================
        # 8. 已完成的 source row：
        #
        # must_receive_end_qty
        # 改成本批實際完成數量。
        #
        # original_must_receive_end_qty
        # 永遠保留 Excel MEINH。
        # ========================================================

        if current_completed_qty > 0:

            source_assemble.must_receive_end_qty = (
                current_completed_qty
            )

        # 舊資料 original 可能為 0
        if int(
            source_assemble
            .original_must_receive_end_qty
            or 0
        ) <= 0:

            source_assemble.original_must_receive_end_qty = (
                target_qty
            )

        # ========================================================
        # 9. 同訂單同工序已全部完成
        #
        # ★ 不可以再建立 child P_Assemble
        # ========================================================

        if remaining_qty <= 0:

            print(
                "[copyAssembleForDifferenceP]",
                {
                    'order_num':
                        order_num,

                    'work_num':
                        work_num,

                    'target_qty':
                        target_qty,

                    'total_completed':
                        total_completed,

                    'total_abnormal':
                        total_abnormal,

                    'remaining_qty':
                        remaining_qty,

                    'action':
                        'NO COPY',
                }
            )

            s.commit()

            return jsonify({
                'status': True,

                'assemble_data': [],

                'remaining_qty':
                    0,

                'all_completed':
                    True,

                'target_qty':
                    target_qty,

                'total_completed_qty':
                    total_completed,

                'total_abnormal_qty':
                    total_abnormal,
            })

        # ========================================================
        # 10. 防止重複建立同一剩餘 child
        #
        # 使用：
        # parent id
        # + 同工序
        # + completed_qty=0
        # + 尚未送 Warehouse
        #
        # 若前端重複送出，不再建立第二筆。
        # ========================================================

        existing_child = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.material_id
                ==
                source_assemble.material_id,

                P_Assemble.is_copied_from_id
                ==
                source_assemble.id,

                P_Assemble.work_num
                ==
                source_assemble.work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,

                P_Assemble.process_step_code
                >
                0,

                func.coalesce(
                    P_Assemble.completed_qty,
                    0
                )
                ==
                0,

                or_(
                    P_Assemble
                    .isWarehouseStationShow
                    .is_(False),

                    P_Assemble
                    .isWarehouseStationShow
                    .is_(None),
                ),
            )
            .order_by(
                P_Assemble.id.desc()
            )
            .first()
        )

        if existing_child is not None:

            # ----------------------------------------------------
            # 若已存在 child，
            # 同步成目前最新 remaining_qty。
            # ----------------------------------------------------

            existing_child.must_receive_qty = (
                remaining_qty
            )

            existing_child.must_receive_end_qty = (
                remaining_qty
            )

            existing_child.original_must_receive_end_qty = (
                target_qty
            )

            existing_child.total_completed_qty = (
                total_completed
            )

            existing_child.total_ask_qty_end = (
                total_completed
            )

            s.commit()

            print(
                "[copyAssembleForDifferenceP]",
                "reuse existing child:",
                existing_child.id
            )

            return jsonify({
                'status': True,

                'assemble_data': [
                    int(
                        existing_child.id
                    )
                ],

                'remaining_qty':
                    remaining_qty,

                'all_completed':
                    False,

                'reused':
                    True,

                'target_qty':
                    target_qty,

                'total_completed_qty':
                    total_completed,

                'total_abnormal_qty':
                    total_abnormal,
            })

        # ========================================================
        # 11. 領取數量
        #
        # 畫面上的領取量沿用原始加工單。
        # ========================================================

        original_ask_qty = max(
            int(
                source_assemble.ask_qty
                or 0
            ),

            int(
                source_assemble.total_ask_qty
                or 0
            ),

            int(
                getattr(
                    material_record,
                    'material_qty',
                    0
                )
                or 0
            ),
        )

        # ========================================================
        # 12. 只複製目前這一筆
        #
        # ★ 不可以再使用：
        #
        # copy_id + 1
        #
        # DB id 是流水號，
        # 不代表下一道工序。
        # ========================================================

        record = source_assemble

        process_step_code = int(
            record.process_step_code
            or 0
        )

        # --------------------------------------------------------
        # 如果前面已經有人先把 source step 改成 0，
        # 可從 P_Part 重新取得加工 step。
        # --------------------------------------------------------

        if process_step_code <= 0:

            part_record = (
                s.query(P_Part)
                .filter(
                    P_Part.part_code
                    ==
                    record.work_num
                )
                .first()
            )

            if part_record is not None:

                process_step_code = int(
                    part_record
                    .process_step_code
                    or 0
                )

        if process_step_code <= 0:

            s.rollback()

            return jsonify({
                'status': False,
                'message':
                    f'工序 {work_num} '
                    '找不到有效 process_step_code',
                'assemble_data': [],
                'remaining_qty':
                    remaining_qty,
            }), 400

        # ========================================================
        # 13. 建立真正剩餘 row
        # ========================================================

        new_record = P_Assemble(

            material_id=
                record.material_id,

            material_num=
                record.material_num,

            material_comment=
                record.material_comment,

            seq_num=
                record.seq_num,

            work_num=
                record.work_num,

            process_step_code=
                process_step_code,

            # ----------------------------------------------------
            # ★ 真正剩餘數量
            # ----------------------------------------------------

            must_receive_qty=
                remaining_qty,

            must_receive_end_qty=
                remaining_qty,

            # Excel 原始工序 MEINH
            original_must_receive_end_qty=
                target_qty,

            input_disable=
                False,

            input_end_disable=
                False,

            input_abnormal_disable=
                False,

            completed_qty=
                0,

            # ----------------------------------------------------
            # ★ 正式跨批累計完成量
            # ----------------------------------------------------

            total_completed_qty=
                total_completed,

            total_ask_qty_end=
                total_completed,

            # ----------------------------------------------------
            # 領取數量維持原工單
            # ----------------------------------------------------

            ask_qty=
                original_ask_qty,

            total_ask_qty=
                original_ask_qty,

            update_time=
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            is_copied_from_id=
                record.id,

            show2_ok=
                0,

            show3_ok=
                0,

            isShowBomGif=
                record.isShowBomGif,

            # ----------------------------------------------------
            # ★ 必須沿用來源工序
            #
            # 如果來源 B103-01 是最後需入庫工序，
            # 剩餘 child 做完也必須可送 Warehouse。
            # ----------------------------------------------------

            isStockIn=
                record.isStockIn,

            isSimultaneously=
                record.isSimultaneously,
        )

        s.add(
            new_record
        )

        s.flush()

        new_id = int(
            new_record.id
        )

        print(
            "[copyAssembleForDifferenceP]",
            {
                'new_id':
                    new_id,

                'parent_id':
                    record.id,

                'remaining_qty':
                    remaining_qty,

                'target_qty':
                    target_qty,

                'total_completed':
                    total_completed,

                'isStockIn':
                    bool(
                        new_record.isStockIn
                    ),
            }
        )

        s.commit()

        # ========================================================
        # 14. Return
        # ========================================================

        return jsonify({
            'status': True,

            'assemble_data': [
                new_id
            ],

            'remaining_qty':
                remaining_qty,

            'all_completed':
                False,

            'reused':
                False,

            'target_qty':
                target_qty,

            'total_completed_qty':
                total_completed,

            'total_abnormal_qty':
                total_abnormal,
        })

    except Exception as e:

        s.rollback()

        print(
            "copyAssembleForDifferenceP Error:",
            repr(e)
        )

        traceback.print_exc()

        return jsonify({
            'status': False,

            'message':
                str(e),

            'assemble_data':
                [],

            'remaining_qty':
                0,
        }), 500

    finally:

        s.close()
    #
"""


"""
# 20260909版
@createTableP.route(
    "/copyAssembleForDifferenceP",
    methods=['POST']
)
def copy_assemble_for_difference_p():

    print("copyAssembleForDifferenceP....")

    request_data = (
        request.get_json(silent=True)
        or {}
    )

    # ============================================================
    # 0. Request
    # ============================================================

    try:
        _copy_id = int(
            request_data.get(
                'copy_id'
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        _copy_id = 0


    # ------------------------------------------------------------
    # frontend_difference：
    # 只作 debug，不作為真正 remaining_qty。
    # ------------------------------------------------------------

    _frontend_difference = (
        request_data.get(
            'frontend_difference'
        )
    )

    if _frontend_difference is None:
        _frontend_difference = (
            request_data.get(
                'must_receive_qty'
            )
        )


    # 舊版前端相容
    _pre_must_qty = (
        request_data.get(
            'pre_must_receive_qty'
        )
    )


    _completed_qty_from_front = (
        request_data.get(
            'completed_qty'
        )
    )


    _abnormal_qty_from_front = (
        request_data.get(
            'abnormal_qty'
        )
    )


    if _copy_id <= 0:
        return jsonify({
            'status': False,
            'message':
                'copy_id 不正確',
            'assemble_data': [],
            'remaining_qty': 0,
        }), 400


    s = Session()

    try:

        # ========================================================
        # 1. 取得目前 P_Assemble
        # ========================================================

        source_assemble = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.id
                ==
                _copy_id
            )
            .with_for_update()
            .one_or_none()
        )


        if source_assemble is None:

            s.rollback()

            return jsonify({
                'status': False,
                'message':
                    f'找不到 P_Assemble id={_copy_id}',
                'assemble_data': [],
                'remaining_qty': 0,
            }), 404


        # ========================================================
        # 2. 取得目前 P_Material
        # ========================================================

        material_record = (
            s.query(P_Material)
            .filter(
                P_Material.id
                ==
                source_assemble.material_id
            )
            .with_for_update()
            .one_or_none()
        )


        if material_record is None:

            s.rollback()

            return jsonify({
                'status': False,
                'message':
                    f'找不到 P_Material '
                    f'id={source_assemble.material_id}',
                'assemble_data': [],
                'remaining_qty': 0,
            }), 404


        order_num = str(
            material_record.order_num
            or ''
        ).strip()


        work_num = str(
            source_assemble.work_num
            or ''
        ).strip()


        seq_num = str(
            source_assemble.seq_num
            or ''
        ).strip()


        # ========================================================
        # 3. 本次完成量
        # ========================================================

        try:

            current_completed_qty = int(
                _completed_qty_from_front
                if _completed_qty_from_front
                is not None
                else (
                    _pre_must_qty
                    if _pre_must_qty
                    is not None
                    else (
                        source_assemble.completed_qty
                        or 0
                    )
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            current_completed_qty = int(
                source_assemble.completed_qty
                or 0
            )


        current_completed_qty = max(
            current_completed_qty,
            0
        )


        # ========================================================
        # 4. 找 Excel 原始應完成量
        #
        # 例如：
        #
        # 999900006179
        #
        # material_qty = 400
        # Excel 廢品 = 1
        #
        # original_must_receive_end_qty = 399
        #
        # target_qty 必須取得 399
        # ========================================================

        target_qty = (
            s.query(
                func.max(
                    func.coalesce(
                        P_Assemble
                        .original_must_receive_end_qty,

                        P_Assemble
                        .must_receive_end_qty,

                        0
                    )
                )
            )
            .join(
                P_Material,
                P_Material.id
                ==
                P_Assemble.material_id
            )
            .filter(
                P_Material.order_num
                ==
                order_num,

                P_Assemble.work_num
                ==
                work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,

                P_Assemble
                .is_copied_from_id
                .is_(None),
            )
            .scalar()
        )


        target_qty = int(
            target_qty
            or 0
        )


        # 舊資料 fallback
        if target_qty <= 0:

            target_qty = int(
                source_assemble
                .original_must_receive_end_qty
                or
                source_assemble
                .must_receive_end_qty
                or
                source_assemble
                .must_receive_qty
                or 0
            )


        if target_qty <= 0:

            s.rollback()

            return jsonify({
                'status': False,
                'message':
                    f'工單 {order_num} '
                    f'工序 {work_num} '
                    '找不到有效應完成數量',
                'assemble_data': [],
                'remaining_qty': 0,
            }), 400


        # ========================================================
        # 5. 同訂單 + 同工序累計完成數量
        #
        # ★ 只能 SUM completed_qty
        # ========================================================

        total_completed = (
            s.query(
                func.coalesce(
                    func.sum(
                        P_Assemble.completed_qty
                    ),
                    0
                )
            )
            .join(
                P_Material,
                P_Material.id
                ==
                P_Assemble.material_id
            )
            .filter(
                P_Material.order_num
                ==
                order_num,

                P_Assemble.work_num
                ==
                work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,
            )
            .scalar()
        )


        total_completed = int(
            total_completed
            or 0
        )


        # ========================================================
        # 6. 同訂單 + 同工序累計廢料
        #
        # 注意：
        # Excel 原始廢品已經反映在 target_qty=399。
        #
        # 此處只累計 PEnd 後續人工新增的 abnormal_qty。
        # ========================================================

        total_abnormal = (
            s.query(
                func.coalesce(
                    func.sum(
                        P_Assemble.abnormal_qty
                    ),
                    0
                )
            )
            .join(
                P_Material,
                P_Material.id
                ==
                P_Assemble.material_id
            )
            .filter(
                P_Material.order_num
                ==
                order_num,

                P_Assemble.work_num
                ==
                work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,
            )
            .scalar()
        )


        total_abnormal = int(
            total_abnormal
            or 0
        )


        # ========================================================
        # 7. 真正剩餘數量
        #
        # 999900006179：
        #
        # target_qty = 399
        # total_completed = 100
        # total_abnormal = 0
        #
        # remaining_qty = 299
        # ========================================================

        remaining_qty = max(
            target_qty
            -
            total_completed
            -
            total_abnormal,
            0
        )


        print(
            "[copyAssembleForDifferenceP remaining]",
            {
                'copy_id':
                    _copy_id,

                'material_id':
                    source_assemble.material_id,

                'order_num':
                    order_num,

                'work_num':
                    work_num,

                'seq_num':
                    seq_num,

                'target_qty':
                    target_qty,

                'current_completed_qty':
                    current_completed_qty,

                'total_completed':
                    total_completed,

                'total_abnormal':
                    total_abnormal,

                'frontend_difference':
                    _frontend_difference,

                'remaining_qty':
                    remaining_qty,
            }
        )


        # ========================================================
        # 8. 已完成 source row
        #
        # 本批完成 100：
        #
        # source.must_receive_end_qty = 100
        #
        # original_must_receive_end_qty 保留 399
        # ========================================================

        if current_completed_qty > 0:

            source_assemble.must_receive_end_qty = (
                current_completed_qty
            )


        if int(
            source_assemble
            .original_must_receive_end_qty
            or 0
        ) <= 0:

            source_assemble.original_must_receive_end_qty = (
                target_qty
            )


        # ========================================================
        # 9. 已經全部完成
        # ========================================================

        if remaining_qty <= 0:

            print(
                "[copyAssembleForDifferenceP]",
                {
                    'order_num':
                        order_num,

                    'work_num':
                        work_num,

                    'target_qty':
                        target_qty,

                    'total_completed':
                        total_completed,

                    'total_abnormal':
                        total_abnormal,

                    'remaining_qty':
                        remaining_qty,

                    'action':
                        'NO COPY',
                }
            )


            s.commit()


            return jsonify({
                'status':
                    True,

                'assemble_data':
                    [],

                'remaining_qty':
                    0,

                'all_completed':
                    True,

                'target_qty':
                    target_qty,

                'total_completed_qty':
                    total_completed,

                'total_abnormal_qty':
                    total_abnormal,
            })


        # ========================================================
        # 10. 防止重複建立剩餘 child
        # ========================================================

        existing_child = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.material_id
                ==
                source_assemble.material_id,

                P_Assemble.is_copied_from_id
                ==
                source_assemble.id,

                P_Assemble.work_num
                ==
                source_assemble.work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,

                P_Assemble.process_step_code
                >
                0,

                func.coalesce(
                    P_Assemble.completed_qty,
                    0
                )
                ==
                0,

                or_(
                    P_Assemble
                    .isWarehouseStationShow
                    .is_(False),

                    P_Assemble
                    .isWarehouseStationShow
                    .is_(None),
                ),
            )
            .order_by(
                P_Assemble.id.desc()
            )
            .first()
        )


        # ========================================================
        # 10-1. child 已存在
        # ========================================================

        if existing_child is not None:

            existing_child.must_receive_qty = (
                remaining_qty
            )

            existing_child.must_receive_end_qty = (
                remaining_qty
            )

            existing_child.original_must_receive_end_qty = (
                target_qty
            )

            existing_child.completed_qty = 0

            existing_child.total_completed_qty = (
                total_completed
            )

            existing_child.total_ask_qty_end = (
                total_completed
            )


            # ----------------------------------------------------
            # ★ 20260909
            # child 必須重新成為 PBegin row
            # ----------------------------------------------------

            existing_child.show2_ok = 3

            existing_child.show3_ok = 0

            existing_child.isAssembleStationShow = False

            existing_child.isWarehouseStationShow = False

            existing_child.input_disable = False

            existing_child.input_end_disable = False

            existing_child.input_abnormal_disable = False


            # child 本身尚未產生新廢料
            existing_child.abnormal_qty = 0


            # ----------------------------------------------------
            # Material 回到等待加工狀態
            # ----------------------------------------------------

            material_record.show2_ok = 3

            material_record.hasStarted = False

            material_record.isOpen = False

            material_record.isOpenEmpId = ''


            s.commit()


            print(
                "[copyAssembleForDifferenceP REUSE CHILD]",
                {
                    'order_num':
                        order_num,

                    'parent_id':
                        source_assemble.id,

                    'child_id':
                        existing_child.id,

                    'remaining_qty':
                        remaining_qty,

                    'target_qty':
                        target_qty,

                    'total_completed':
                        total_completed,
                }
            )


            return jsonify({
                'status':
                    True,

                'assemble_data': [
                    int(
                        existing_child.id
                    )
                ],

                'remaining_qty':
                    remaining_qty,

                'all_completed':
                    False,

                'reused':
                    True,

                'target_qty':
                    target_qty,

                'total_completed_qty':
                    total_completed,

                'total_abnormal_qty':
                    total_abnormal,
            })


        # ========================================================
        # 11. 領取數量
        # ========================================================

        original_ask_qty = max(
            int(
                source_assemble.ask_qty
                or 0
            ),

            int(
                source_assemble.total_ask_qty
                or 0
            ),

            int(
                getattr(
                    material_record,
                    'material_qty',
                    0
                )
                or 0
            ),
        )


        # ========================================================
        # 12. 找回原加工 process_step_code
        #
        # copy API 被呼叫時，parent 通常還沒改成 0。
        #
        # 但為避免呼叫順序改變，step=0 時從 P_Part 還原。
        # ========================================================

        process_step_code = int(
            source_assemble.process_step_code
            or 0
        )


        if process_step_code <= 0:

            part_record = (
                s.query(P_Part)
                .filter(
                    P_Part.part_code
                    ==
                    source_assemble.work_num
                )
                .first()
            )


            if part_record is not None:

                process_step_code = int(
                    part_record.process_step_code
                    or 0
                )


        if process_step_code <= 0:

            s.rollback()

            return jsonify({
                'status':
                    False,

                'message':
                    f'工序 {work_num} '
                    '找不到有效 process_step_code',

                'assemble_data':
                    [],

                'remaining_qty':
                    remaining_qty,
            }), 400


        # ========================================================
        # 13. 建立真正剩餘 child row
        #
        # 999900006179：
        #
        # parent：
        #   completed_qty = 100
        #
        # child：
        #   must_receive_qty = 299
        #   must_receive_end_qty = 299
        #   completed_qty = 0
        # ========================================================

        new_record = P_Assemble(

            material_id=
                source_assemble.material_id,

            material_num=
                source_assemble.material_num,

            material_comment=
                source_assemble.material_comment,

            seq_num=
                source_assemble.seq_num,

            work_num=
                source_assemble.work_num,

            process_step_code=
                process_step_code,


            # ★ 真正剩餘量
            must_receive_qty=
                remaining_qty,

            must_receive_end_qty=
                remaining_qty,


            # Excel 原始需求量
            original_must_receive_end_qty=
                target_qty,


            completed_qty=
                0,


            # 歷史累計完成量
            total_completed_qty=
                total_completed,

            total_ask_qty_end=
                total_completed,


            # 領取數量保持原工單
            ask_qty=
                original_ask_qty,

            total_ask_qty=
                original_ask_qty,


            # ----------------------------------------------------
            # ★ child 尚未新增人工廢料
            # ----------------------------------------------------

            abnormal_qty=
                0,


            # ----------------------------------------------------
            # ★ PBegin 操作欄位
            # ----------------------------------------------------

            input_disable=
                False,

            input_end_disable=
                False,

            input_abnormal_disable=
                False,


            # ----------------------------------------------------
            # ★ 直接設成 PBegin 等待加工
            # ----------------------------------------------------

            show2_ok=
                3,

            show3_ok=
                0,

            isAssembleStationShow=
                False,

            isWarehouseStationShow=
                False,


            update_time=
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),


            is_copied_from_id=
                source_assemble.id,


            isShowBomGif=
                source_assemble.isShowBomGif,


            # 必須沿用來源工序
            isStockIn=
                source_assemble.isStockIn,

            isSimultaneously=
                source_assemble.isSimultaneously,
        )


        s.add(
            new_record
        )

        s.flush()


        new_id = int(
            new_record.id
        )


        # ========================================================
        # 14. Material 回到 PBegin 等待加工
        # ========================================================

        material_record.show2_ok = 3

        material_record.hasStarted = False

        material_record.isOpen = False

        material_record.isOpenEmpId = ''


        print(
            "[copyAssembleForDifferenceP CHILD CREATED]",
            {
                'order_num':
                    order_num,

                'parent_id':
                    source_assemble.id,

                'child_id':
                    new_id,

                'target_qty':
                    target_qty,

                'total_completed':
                    total_completed,

                'total_abnormal':
                    total_abnormal,

                'remaining_qty':
                    remaining_qty,

                'process_step_code':
                    process_step_code,

                'child_show2_ok':
                    new_record.show2_ok,

                'child_isAssembleStationShow':
                    new_record.isAssembleStationShow,

                'child_isWarehouseStationShow':
                    new_record.isWarehouseStationShow,
            }
        )


        s.commit()


        # ========================================================
        # 15. Return
        # ========================================================

        return jsonify({
            'status':
                True,

            'assemble_data': [
                new_id
            ],

            'remaining_qty':
                remaining_qty,

            'all_completed':
                False,

            'reused':
                False,

            'target_qty':
                target_qty,

            'total_completed_qty':
                total_completed,

            'total_abnormal_qty':
                total_abnormal,
        })


    except Exception as e:

        s.rollback()

        print(
            "copyAssembleForDifferenceP Error:",
            repr(e)
        )

        traceback.print_exc()

        return jsonify({
            'status':
                False,

            'message':
                str(e),

            'assemble_data':
                [],

            'remaining_qty':
                0,
        }), 500


    finally:

        s.close()
"""


# 20260909版
@createTableP.route(
    "/copyAssembleForDifferenceP",
    methods=['POST']
)
def copy_assemble_for_difference_p():

    print("copyAssembleForDifferenceP....")

    request_data = (
        request.get_json(silent=True)
        or {}
    )

    # ============================================================
    # 0. Request
    # ============================================================

    try:
        _copy_id = int(
            request_data.get(
                'copy_id'
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        _copy_id = 0


    # ------------------------------------------------------------
    # frontend_difference：
    # 只作 debug，不作為真正 remaining_qty。
    # ------------------------------------------------------------

    _frontend_difference = (
        request_data.get(
            'frontend_difference'
        )
    )

    if _frontend_difference is None:
        _frontend_difference = (
            request_data.get(
                'must_receive_qty'
            )
        )


    # 舊版前端相容
    _pre_must_qty = (
        request_data.get(
            'pre_must_receive_qty'
        )
    )


    _completed_qty_from_front = (
        request_data.get(
            'completed_qty'
        )
    )


    _abnormal_qty_from_front = (
        request_data.get(
            'abnormal_qty'
        )
    )


    if _copy_id <= 0:
        return jsonify({
            'status': False,
            'message':
                'copy_id 不正確',
            'assemble_data': [],
            'remaining_qty': 0,
        }), 400


    s = Session()

    try:

        # ========================================================
        # 1. 取得目前 P_Assemble
        # ========================================================

        source_assemble = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.id
                ==
                _copy_id
            )
            .with_for_update()
            .one_or_none()
        )


        if source_assemble is None:

            s.rollback()

            return jsonify({
                'status': False,
                'message':
                    f'找不到 P_Assemble id={_copy_id}',
                'assemble_data': [],
                'remaining_qty': 0,
            }), 404


        # ========================================================
        # 2. 取得目前 P_Material
        # ========================================================

        material_record = (
            s.query(P_Material)
            .filter(
                P_Material.id
                ==
                source_assemble.material_id
            )
            .with_for_update()
            .one_or_none()
        )


        if material_record is None:

            s.rollback()

            return jsonify({
                'status': False,
                'message':
                    f'找不到 P_Material '
                    f'id={source_assemble.material_id}',
                'assemble_data': [],
                'remaining_qty': 0,
            }), 404


        order_num = str(
            material_record.order_num
            or ''
        ).strip()


        work_num = str(
            source_assemble.work_num
            or ''
        ).strip()


        seq_num = str(
            source_assemble.seq_num
            or ''
        ).strip()


        material_id = int(
            source_assemble.material_id
            or 0
        )


        # ========================================================
        # 3. 本次完成量
        # ========================================================

        try:

            current_completed_qty = int(
                _completed_qty_from_front
                if _completed_qty_from_front
                is not None
                else (
                    _pre_must_qty
                    if _pre_must_qty
                    is not None
                    else (
                        source_assemble.completed_qty
                        or 0
                    )
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            current_completed_qty = int(
                source_assemble.completed_qty
                or 0
            )


        current_completed_qty = max(
            current_completed_qty,
            0
        )


        # ========================================================
        # 4. 找 Excel 原始應完成量
        #
        # ★ 20260909 修正：
        #
        # 只能找「目前 material_id」的資料。
        #
        # 不能再使用：
        #
        # order_num + work_num + seq_num
        #
        # 去跨 material_id 找資料。
        #
        # 例如：
        #
        # order_num = 999900006179
        #
        # 舊資料：
        # material_id = 172
        # assemble 196 / 203
        #
        # 本次資料：
        # material_id = 186
        # assemble 219
        #
        # 兩者不可混算。
        #
        # material_qty = 400
        # Excel 廢品 = 1
        #
        # original_must_receive_end_qty = 399
        #
        # target_qty 必須取得 399
        # ========================================================

        target_qty = (
            s.query(
                func.max(
                    func.coalesce(
                        P_Assemble
                        .original_must_receive_end_qty,

                        P_Assemble
                        .must_receive_end_qty,

                        0
                    )
                )
            )
            .filter(

                # ★ 20260909
                # 僅目前 material_id
                P_Assemble.material_id
                ==
                source_assemble.material_id,

                P_Assemble.work_num
                ==
                source_assemble.work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,

                # root row
                P_Assemble
                .is_copied_from_id
                .is_(None),
            )
            .scalar()
        )


        target_qty = int(
            target_qty
            or 0
        )


        # 舊資料 fallback
        if target_qty <= 0:

            target_qty = int(
                source_assemble
                .original_must_receive_end_qty
                or
                source_assemble
                .must_receive_end_qty
                or
                source_assemble
                .must_receive_qty
                or 0
            )


        if target_qty <= 0:

            s.rollback()

            return jsonify({
                'status': False,
                'message':
                    f'工單 {order_num} '
                    f'工序 {work_num} '
                    '找不到有效應完成數量',
                'assemble_data': [],
                'remaining_qty': 0,
            }), 400


        # ========================================================
        # 5. 目前 material_id + 同工序累計完成數量
        #
        # ★ 20260909 修正
        #
        # 只能 SUM completed_qty：
        #
        # material_id
        # + work_num
        # + seq_num
        #
        # 不可以再使用 order_num 跨 material_id 累計。
        #
        # 999900006179：
        #
        # material_id=172：
        #   196 = 300
        #   203 = 98
        #
        # material_id=186：
        #   219 = 100
        #
        # 當正在處理 material_id=186 時：
        #
        # total_completed 必須 = 100
        #
        # 不能變成：
        #
        # 300 + 98 + 100 = 498
        # ========================================================

        total_completed = (
            s.query(
                func.coalesce(
                    func.sum(
                        P_Assemble.completed_qty
                    ),
                    0
                )
            )
            .filter(

                # ★ 20260909
                P_Assemble.material_id
                ==
                source_assemble.material_id,

                P_Assemble.work_num
                ==
                source_assemble.work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,
            )
            .scalar()
        )


        total_completed = int(
            total_completed
            or 0
        )


        # ========================================================
        # 6. 目前 material_id + 同工序累計廢料
        #
        # ★ 20260909 修正
        #
        # Excel 原始廢品已經反映在：
        #
        # original_must_receive_end_qty
        #
        # 例如：
        #
        # 400 - Excel 廢品1 = 399
        #
        # 所以此處只累計：
        #
        # 目前 material_id
        # 後續 PEnd 人工新增的 abnormal_qty
        #
        # 不可以把舊 material_id 的 abnormal_qty 算進來。
        # ========================================================

        total_abnormal = (
            s.query(
                func.coalesce(
                    func.sum(
                        P_Assemble.abnormal_qty
                    ),
                    0
                )
            )
            .filter(

                # ★ 20260909
                P_Assemble.material_id
                ==
                source_assemble.material_id,

                P_Assemble.work_num
                ==
                source_assemble.work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,
            )
            .scalar()
        )


        total_abnormal = int(
            total_abnormal
            or 0
        )


        # ========================================================
        # 7. 真正剩餘數量
        #
        # 999900006179：
        #
        # material_id = 186
        #
        # target_qty = 399
        #
        # 第一次：
        #
        # completed = 100
        # abnormal = 0
        #
        # remaining =
        #
        # 399 - 100 - 0
        # = 299
        # ========================================================

        remaining_qty = max(
            target_qty
            -
            total_completed
            -
            total_abnormal,
            0
        )


        print(
            "[copyAssembleForDifferenceP remaining]",
            {
                'copy_id':
                    _copy_id,

                'material_id':
                    material_id,

                'order_num':
                    order_num,

                'work_num':
                    work_num,

                'seq_num':
                    seq_num,

                'target_qty':
                    target_qty,

                'current_completed_qty':
                    current_completed_qty,

                'total_completed':
                    total_completed,

                'total_abnormal':
                    total_abnormal,

                'frontend_difference':
                    _frontend_difference,

                'remaining_qty':
                    remaining_qty,
            }
        )


        # ========================================================
        # 8. 已完成 source row
        #
        # 本批完成 100：
        #
        # source.must_receive_end_qty = 100
        #
        # original_must_receive_end_qty 保留 399
        # ========================================================

        if current_completed_qty > 0:

            source_assemble.must_receive_end_qty = (
                current_completed_qty
            )


        if int(
            source_assemble
            .original_must_receive_end_qty
            or 0
        ) <= 0:

            source_assemble.original_must_receive_end_qty = (
                target_qty
            )


        # ========================================================
        # 9. 已經全部完成
        # ========================================================

        if remaining_qty <= 0:

            print(
                "[copyAssembleForDifferenceP]",
                {
                    'material_id':
                        material_id,

                    'order_num':
                        order_num,

                    'work_num':
                        work_num,

                    'target_qty':
                        target_qty,

                    'total_completed':
                        total_completed,

                    'total_abnormal':
                        total_abnormal,

                    'remaining_qty':
                        remaining_qty,

                    'action':
                        'NO COPY',
                }
            )


            s.commit()


            return jsonify({
                'status':
                    True,

                'assemble_data':
                    [],

                'remaining_qty':
                    0,

                'all_completed':
                    True,

                'target_qty':
                    target_qty,

                'total_completed_qty':
                    total_completed,

                'total_abnormal_qty':
                    total_abnormal,
            })


        # ========================================================
        # 10. 防止重複建立剩餘 child
        #
        # 這裡原本就已經限制 material_id，
        # 維持不變。
        # ========================================================

        existing_child = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.material_id
                ==
                source_assemble.material_id,

                P_Assemble.is_copied_from_id
                ==
                source_assemble.id,

                P_Assemble.work_num
                ==
                source_assemble.work_num,

                P_Assemble.seq_num
                ==
                source_assemble.seq_num,

                P_Assemble.process_step_code
                >
                0,

                func.coalesce(
                    P_Assemble.completed_qty,
                    0
                )
                ==
                0,

                or_(
                    P_Assemble
                    .isWarehouseStationShow
                    .is_(False),

                    P_Assemble
                    .isWarehouseStationShow
                    .is_(None),
                ),
            )
            .order_by(
                P_Assemble.id.desc()
            )
            .first()
        )


        # ========================================================
        # 10-1. child 已存在
        # ========================================================

        if existing_child is not None:

            existing_child.must_receive_qty = (
                remaining_qty
            )

            existing_child.must_receive_end_qty = (
                remaining_qty
            )

            existing_child.original_must_receive_end_qty = (
                target_qty
            )

            existing_child.completed_qty = 0

            existing_child.total_completed_qty = (
                total_completed
            )

            existing_child.total_ask_qty_end = (
                total_completed
            )


            # ----------------------------------------------------
            # child 必須重新成為 PBegin row
            # ----------------------------------------------------

            existing_child.show2_ok = 3

            existing_child.show3_ok = 0

            existing_child.isAssembleStationShow = False

            existing_child.isWarehouseStationShow = False

            existing_child.input_disable = False

            existing_child.input_end_disable = False

            existing_child.input_abnormal_disable = False


            # child 本身尚未產生新廢料
            existing_child.abnormal_qty = 0


            # ----------------------------------------------------
            # Material 回到等待加工狀態
            # ----------------------------------------------------

            material_record.show2_ok = 3

            material_record.hasStarted = False

            material_record.isOpen = False

            material_record.isOpenEmpId = ''


            s.commit()


            print(
                "[copyAssembleForDifferenceP REUSE CHILD]",
                {
                    'material_id':
                        material_id,

                    'order_num':
                        order_num,

                    'parent_id':
                        source_assemble.id,

                    'child_id':
                        existing_child.id,

                    'remaining_qty':
                        remaining_qty,

                    'target_qty':
                        target_qty,

                    'total_completed':
                        total_completed,

                    'total_abnormal':
                        total_abnormal,
                }
            )


            return jsonify({
                'status':
                    True,

                'assemble_data': [
                    int(
                        existing_child.id
                    )
                ],

                'remaining_qty':
                    remaining_qty,

                'all_completed':
                    False,

                'reused':
                    True,

                'target_qty':
                    target_qty,

                'total_completed_qty':
                    total_completed,

                'total_abnormal_qty':
                    total_abnormal,
            })


        # ========================================================
        # 11. 領取數量
        # ========================================================

        original_ask_qty = max(
            int(
                source_assemble.ask_qty
                or 0
            ),

            int(
                source_assemble.total_ask_qty
                or 0
            ),

            int(
                getattr(
                    material_record,
                    'material_qty',
                    0
                )
                or 0
            ),
        )


        # ========================================================
        # 12. 找回原加工 process_step_code
        #
        # copy API 被呼叫時，
        # parent 通常還沒改成 0。
        #
        # 但為避免呼叫順序改變，
        # step=0 時從 P_Part 還原。
        # ========================================================

        process_step_code = int(
            source_assemble.process_step_code
            or 0
        )


        if process_step_code <= 0:

            part_record = (
                s.query(P_Part)
                .filter(
                    P_Part.part_code
                    ==
                    source_assemble.work_num
                )
                .first()
            )


            if part_record is not None:

                process_step_code = int(
                    part_record.process_step_code
                    or 0
                )


        if process_step_code <= 0:

            s.rollback()

            return jsonify({
                'status':
                    False,

                'message':
                    f'工序 {work_num} '
                    '找不到有效 process_step_code',

                'assemble_data':
                    [],

                'remaining_qty':
                    remaining_qty,
            }), 400


        # ========================================================
        # 13. 建立真正剩餘 child row
        #
        # 999900006179：
        #
        # parent：
        #
        # completed_qty = 100
        #
        # child：
        #
        # must_receive_qty = 299
        # must_receive_end_qty = 299
        # completed_qty = 0
        #
        # total_completed_qty = 100
        # total_ask_qty_end = 100
        #
        # process_step_code > 0
        #
        # → 回到 PBegin
        # ========================================================

        new_record = P_Assemble(

            material_id=
                source_assemble.material_id,

            material_num=
                source_assemble.material_num,

            material_comment=
                source_assemble.material_comment,

            seq_num=
                source_assemble.seq_num,

            work_num=
                source_assemble.work_num,

            process_step_code=
                process_step_code,


            # ★ 真正剩餘量
            must_receive_qty=
                remaining_qty,

            must_receive_end_qty=
                remaining_qty,


            # Excel 原始需求量
            original_must_receive_end_qty=
                target_qty,


            completed_qty=
                0,


            # 歷史累計完成量
            total_completed_qty=
                total_completed,

            total_ask_qty_end=
                total_completed,


            # 領取數量保持原工單
            ask_qty=
                original_ask_qty,

            total_ask_qty=
                original_ask_qty,


            # child 尚未新增人工廢料
            abnormal_qty=
                0,


            # PBegin 操作欄位
            input_disable=
                False,

            input_end_disable=
                False,

            input_abnormal_disable=
                False,


            # PBegin 等待加工
            show2_ok=
                3,

            show3_ok=
                0,

            isAssembleStationShow=
                False,

            isWarehouseStationShow=
                False,


            update_time=
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),


            is_copied_from_id=
                source_assemble.id,


            isShowBomGif=
                source_assemble.isShowBomGif,


            isStockIn=
                source_assemble.isStockIn,

            isSimultaneously=
                source_assemble.isSimultaneously,
        )


        s.add(
            new_record
        )

        s.flush()


        new_id = int(
            new_record.id
        )


        # ========================================================
        # 14. Material 回到 PBegin 等待加工
        # ========================================================

        material_record.show2_ok = 3

        material_record.hasStarted = False

        material_record.isOpen = False

        material_record.isOpenEmpId = ''


        print(
            "[copyAssembleForDifferenceP CHILD CREATED]",
            {
                'material_id':
                    material_id,

                'order_num':
                    order_num,

                'parent_id':
                    source_assemble.id,

                'child_id':
                    new_id,

                'target_qty':
                    target_qty,

                'total_completed':
                    total_completed,

                'total_abnormal':
                    total_abnormal,

                'remaining_qty':
                    remaining_qty,

                'process_step_code':
                    process_step_code,

                'child_show2_ok':
                    new_record.show2_ok,

                'child_isAssembleStationShow':
                    new_record.isAssembleStationShow,

                'child_isWarehouseStationShow':
                    new_record.isWarehouseStationShow,
            }
        )


        s.commit()


        # ========================================================
        # 15. Return
        # ========================================================

        return jsonify({
            'status':
                True,

            'assemble_data': [
                new_id
            ],

            'remaining_qty':
                remaining_qty,

            'all_completed':
                False,

            'reused':
                False,

            'target_qty':
                target_qty,

            'total_completed_qty':
                total_completed,

            'total_abnormal_qty':
                total_abnormal,
        })


    except Exception as e:

        s.rollback()

        print(
            "copyAssembleForDifferenceP Error:",
            repr(e)
        )

        traceback.print_exc()

        return jsonify({
            'status':
                False,

            'message':
                str(e),

            'assemble_data':
                [],

            'remaining_qty':
                0,
        }), 500


    finally:

        s.close()


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


"""
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
"""


@createTableP.route(
    "/createProductP",
    methods=["POST"]
)
def create_product_p():

    # ============================================================
    # 加工線入庫
    #
    # 1. 支援單筆或批次
    # 2. allOk_qty 必須 > 0
    # 3. 建立 P_Product
    # 4. 若沒送 process_id：
    #
    #    一般情況：
    #        建立 P_Process(process_type=31)
    #
    #    加工線 line_difference == 1：
    #        同 material_id
    #        同 user_id
    #        5 秒內連續呼叫
    #
    #        視為「同一次按入庫」
    #
    #        P_Product 仍逐筆建立，
    #        但 P_Process(type=31) 只建立一筆，
    #        後續數量累加。
    #
    # 5. 回寫 P_Material / P_Assemble
    # ============================================================

    s = Session()

    try:
        payload = (
            request.get_json(
                silent=True
            )
            or {}
        )

        raw_items = payload.get(
            "items",
            None
        )

        if raw_items is None:
            raw_items = [payload]

        if (
            not isinstance(
                raw_items,
                list
            )
            or
            len(raw_items) == 0
        ):
            return jsonify({
                "status": False,
                "error":
                    "payload 應為物件或 "
                    "{items: [...]}，且不可為空"
            }), 400


        # ========================================================
        # 1. 先驗證 material_id
        # ========================================================
        material_ids = [
            it.get("material_id")
            for it in raw_items
        ]

        try:
            material_ids_int = [
                int(mid)
                for mid in material_ids
            ]

        except (
            TypeError,
            ValueError
        ):
            return jsonify({
                "status": False,
                "error":
                    "material_id 必須是整數"
            }), 400


        exist_mid_set = set(
            mid
            for (mid,) in (
                s.query(
                    P_Material.id
                )
                .filter(
                    P_Material.id.in_(
                        material_ids_int
                    )
                )
                .all()
            )
        )


        errors = []

        for idx, it in enumerate(
            raw_items
        ):
            mid = it.get(
                "material_id"
            )

            if mid is None:
                errors.append({
                    "index": idx,
                    "error":
                        "material_id 為必填"
                })
                continue

            try:
                mid_int = int(mid)
            except (
                TypeError,
                ValueError
            ):
                errors.append({
                    "index": idx,
                    "error":
                        "material_id 必須為整數"
                })
                continue

            if (
                mid_int
                not in exist_mid_set
            ):
                errors.append({
                    "index": idx,
                    "error":
                        f"material_id "
                        f"{mid_int} 不存在"
                })


        if errors:
            return jsonify({
                "status": False,
                "errors": errors
            }), 400


        created_rows = []


        # ========================================================
        # 2. 逐筆處理
        # ========================================================
        for idx, it in enumerate(
            raw_items
        ):

            now_dt = datetime.now()

            now_str = (
                now_dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )


            # ----------------------------------------------------
            # Material
            # ----------------------------------------------------
            mid = _normalize_int(
                it.get(
                    "material_id"
                ),
                0
            )

            if mid <= 0:
                continue


            # ----------------------------------------------------
            # 本次入庫量
            # ----------------------------------------------------
            add_qty = _normalize_int(
                it.get(
                    "allOk_qty"
                ),
                0
            )

            if add_qty <= 0:
                return jsonify({
                    "status": False,
                    "error":
                        f"第 {idx + 1} 筆"
                        "入庫數量必須大於 0"
                }), 400


            user_id = str(
                it.get("user_id")
                or ""
            ).strip()

            if not user_id:
                user_id = "system"


            delivery_qty = (
                _normalize_int(
                    it.get(
                        "delivery_qty"
                    ),
                    0
                )
            )

            assemble_qty = (
                _normalize_int(
                    it.get(
                        "assemble_qty"
                    ),
                    0
                )
            )

            good_qty = (
                _normalize_int(
                    it.get(
                        "good_qty"
                    ),
                    add_qty
                )
            )

            non_good_qty = (
                _normalize_int(
                    it.get(
                        "non_good_qty"
                    ),
                    0
                )
            )

            line_diff = (
                _normalize_int(
                    it.get(
                        "line_difference"
                    ),
                    1
                )
            )


            # ====================================================
            # 3. 鎖定 Material
            # ====================================================
            m = (
                s.query(P_Material)
                .filter(
                    P_Material.id ==
                    mid
                )
                .with_for_update()
                .one_or_none()
            )

            if m is None:
                return jsonify({
                    "status": False,
                    "error":
                        f"material_id={mid} "
                        "不存在"
                }), 400


            # ====================================================
            # 4. Assemble
            #
            # 優先使用前端送入的 assemble_id。
            # 沒有才抓 material 最新一筆。
            # ====================================================
            assemble_id = (
                _normalize_int(
                    it.get(
                        "assemble_id"
                    ),
                    0
                )
            )

            if assemble_id <= 0:
                latest_a = (
                    s.query(P_Assemble)
                    .filter(
                        P_Assemble
                        .material_id ==
                        mid
                    )
                    .order_by(
                        P_Assemble
                        .id
                        .desc()
                    )
                    .first()
                )

                assemble_id = (
                    latest_a.id
                    if latest_a
                    else 0
                )


            a = None

            if assemble_id > 0:
                a = (
                    s.query(P_Assemble)
                    .filter(
                        P_Assemble.id ==
                        assemble_id
                    )
                    .filter(
                        P_Assemble
                        .material_id ==
                        mid
                    )
                    .with_for_update()
                    .one_or_none()
                )


            # ====================================================
            # 5. Process 31
            # ====================================================
            process_id_to_use = (
                _normalize_int(
                    it.get(
                        "process_id"
                    ),
                    0
                )
            )


            if process_id_to_use <= 0:

                # =================================================
                # A. 加工線
                #
                # line_difference == 1
                #
                # Warehouse 前端會因多筆勾選：
                #
                #   createProductP(38)
                #   createProductP(50)
                #   createProductP(32)
                #
                # 三個 request 在極短時間內依序到達。
                #
                # 同 material + 同 user + 5 秒內，
                # 視為同一次「按入庫」。
                # =================================================
                if line_diff == 1:

                    merge_since = (
                        now_dt
                        - timedelta(
                            seconds=5
                        )
                    )

                    existing_stockin_proc = (
                        s.query(P_Process)
                        .filter(
                            P_Process
                            .material_id ==
                            mid
                        )
                        .filter(
                            P_Process
                            .process_type ==
                            31
                        )
                        .filter(
                            P_Process
                            .user_id ==
                            user_id
                        )
                        .filter(
                            P_Process
                            .create_at >=
                            merge_since
                        )
                        .order_by(
                            P_Process
                            .id
                            .desc()
                        )
                        .with_for_update()
                        .first()
                    )


                    # ---------------------------------------------
                    # 已經有本次入庫 Process 31
                    #
                    # 不再新增，
                    # 只累加數量。
                    # ---------------------------------------------
                    if existing_stockin_proc:

                        old_qty = (
                            _normalize_int(
                                existing_stockin_proc
                                .process_work_time_qty,
                                0
                            )
                        )

                        merged_qty = (
                            old_qty
                            + add_qty
                        )


                        existing_stockin_proc\
                            .process_work_time_qty = (
                                merged_qty
                            )

                        existing_stockin_proc\
                            .allOk_qty = (
                                merged_qty
                            )


                        # must_allOk_qty：
                        # 優先保留整張 Material
                        # 應入庫總量。
                        material_must_qty = (
                            _normalize_int(
                                getattr(
                                    m,
                                    "must_allOk_qty",
                                    0
                                ),
                                0
                            )
                        )

                        if material_must_qty > 0:
                            existing_stockin_proc\
                                .must_allOk_qty = (
                                    material_must_qty
                                )


                        existing_stockin_proc\
                            .isAllOk = (
                                merged_qty
                                >= material_must_qty
                                if material_must_qty > 0
                                else True
                            )


                        # 第一筆 begin_time 保留，
                        # end_time 更新為本批最後一筆時間。
                        existing_stockin_proc\
                            .end_time = (
                                now_str
                            )


                        process_id_to_use = (
                            existing_stockin_proc.id
                        )


                        print(
                            "[createProductP] "
                            "merge process31:",
                            {
                                "process_id":
                                    process_id_to_use,

                                "material_id":
                                    mid,

                                "first_assemble_id":
                                    existing_stockin_proc
                                    .assemble_id,

                                "current_assemble_id":
                                    assemble_id,

                                "user_id":
                                    user_id,

                                "old_qty":
                                    old_qty,

                                "add_qty":
                                    add_qty,

                                "merged_qty":
                                    merged_qty,

                                "must_qty":
                                    material_must_qty,
                            }
                        )


                    # ---------------------------------------------
                    # 本次入庫第一筆
                    #
                    # 建立新的 Process 31。
                    # ---------------------------------------------
                    else:

                        must_qty = (
                            _normalize_int(
                                getattr(
                                    m,
                                    "must_allOk_qty",
                                    0
                                ),
                                0
                            )
                        )


                        stockin_proc = (
                            P_Process(
                                material_id=
                                    mid,

                                # 第一批 assemble 留下即可
                                assemble_id=
                                    assemble_id,

                                has_started=
                                    False,

                                user_id=
                                    user_id,

                                begin_time=
                                    now_str,

                                end_time=
                                    now_str,

                                period_time=
                                    "00:00:00",

                                pause_time=
                                    0,

                                elapsedActive_time=
                                    0,

                                str_elapsedActive_time=
                                    "00:00:00",

                                is_pause=
                                    True,

                                process_type=
                                    31,

                                process_work_time_qty=
                                    add_qty,

                                must_allOk_qty=
                                    must_qty,

                                allOk_qty=
                                    add_qty,

                                isAllOk=(
                                    add_qty >= must_qty
                                    if must_qty > 0
                                    else True
                                ),

                                normal_work_time=
                                    0,
                            )
                        )


                        s.add(
                            stockin_proc
                        )

                        s.flush()


                        process_id_to_use = (
                            stockin_proc.id
                        )


                        print(
                            "[createProductP] "
                            "create process31:",
                            {
                                "process_id":
                                    process_id_to_use,

                                "material_id":
                                    mid,

                                "assemble_id":
                                    assemble_id,

                                "user_id":
                                    user_id,

                                "qty":
                                    add_qty,

                                "must_qty":
                                    must_qty,
                            }
                        )


                # =================================================
                # B. 非加工線
                #
                # 保留原本行為：
                # 依 material + assemble + qty
                # 找既有 type=31，
                # 找不到才新增。
                #
                # 雖然 createProductP 正常主要是加工線使用，
                # 這段保留可避免影響既有相容邏輯。
                # =================================================
                else:

                    exist_proc = None

                    if assemble_id > 0:
                        exist_proc = (
                            s.query(P_Process)
                            .filter(
                                P_Process
                                .material_id ==
                                mid
                            )
                            .filter(
                                P_Process
                                .assemble_id ==
                                assemble_id
                            )
                            .filter(
                                P_Process
                                .process_type ==
                                31
                            )
                            .filter(
                                P_Process
                                .process_work_time_qty ==
                                add_qty
                            )
                            .order_by(
                                P_Process
                                .id
                                .desc()
                            )
                            .first()
                        )


                    if exist_proc:

                        process_id_to_use = (
                            exist_proc.id
                        )

                    else:

                        must_qty = (
                            _normalize_int(
                                getattr(
                                    m,
                                    "must_allOk_qty",
                                    0
                                ),
                                0
                            )
                        )


                        stockin_proc = (
                            P_Process(
                                material_id=
                                    mid,

                                assemble_id=
                                    assemble_id,

                                has_started=
                                    False,

                                user_id=
                                    user_id,

                                begin_time=
                                    now_str,

                                end_time=
                                    now_str,

                                period_time=
                                    "00:00:00",

                                pause_time=
                                    0,

                                elapsedActive_time=
                                    0,

                                str_elapsedActive_time=
                                    "00:00:00",

                                is_pause=
                                    True,

                                process_type=
                                    31,

                                process_work_time_qty=
                                    add_qty,

                                must_allOk_qty=
                                    must_qty,

                                allOk_qty=
                                    add_qty,

                                isAllOk=
                                    True,

                                normal_work_time=
                                    0,
                            )
                        )


                        s.add(
                            stockin_proc
                        )

                        s.flush()

                        process_id_to_use = (
                            stockin_proc.id
                        )


            # ====================================================
            # 6. 建立 P_Product
            #
            # 即使 Process 31 被合併，
            # Product 還是每一個 assemble 建自己的明細。
            #
            # 例如：
            #
            # P_Product:
            #   assemble68 -> 38
            #   assemble70 -> 50
            #   assemble71 -> 32
            #
            # 但 process_id 全部指向同一筆 type=31。
            # ====================================================
            p = P_Product(
                material_id=
                    mid,

                process_id=(
                    process_id_to_use
                    or None
                ),

                line_difference=
                    line_diff,

                # 20260816版 add
                # 真正執行入庫的人員
                user_id=user_id,

                delivery_qty=
                    delivery_qty,

                assemble_qty=
                    assemble_qty,

                allOk_qty=
                    add_qty,

                good_qty=
                    good_qty,

                non_good_qty=
                    non_good_qty,

                reason=(
                    it.get("reason")
                    or None
                ),

                confirm_comment=(
                    it.get(
                        "confirm_comment"
                    )
                    or None
                ),
            )


            s.add(p)

            s.flush()

            created_rows.append(p)


            # ====================================================
            # 7. 回寫 P_Material
            # ====================================================
            old_total = (
                _normalize_int(
                    getattr(
                        m,
                        "total_allOk_qty",
                        0
                    ),
                    0
                )
            )

            new_total = (
                old_total
                + add_qty
            )


            m.allOk_qty = (
                add_qty
            )

            m.total_allOk_qty = (
                new_total
            )


            must_qty2 = (
                _normalize_int(
                    getattr(
                        m,
                        "must_allOk_qty",
                        0
                    ),
                    0
                )
            )


            if (
                must_qty2 <= 0
                or
                new_total >= must_qty2
            ):
                m.isAllOk = True
                m.show2_ok = 8


            # ====================================================
            # 8. 回寫 P_Assemble
            # ====================================================
            if a:

                a.allOk_qty = (
                    add_qty
                )

                a.isStockIn = (
                    True
                )

                # 延續你目前既有邏輯：
                # createProductP 先設 True，
                # Warehouse 前端完成後會再依流程更新。
                a.isWarehouseStationShow = (
                    True
                )

                a.update_time = (
                    now_str
                )


        # ========================================================
        # 9. Commit
        # ========================================================
        s.commit()


        # ========================================================
        # 10. Response
        # ========================================================
        items = []

        for p in created_rows:

            items.append({
                "id":
                    p.id,

                "material_id":
                    p.material_id,

                "process_id":
                    p.process_id,

                "delivery_qty":
                    p.delivery_qty,

                "assemble_qty":
                    p.assemble_qty,

                "allOk_qty":
                    p.allOk_qty,

                "good_qty":
                    p.good_qty,

                "non_good_qty":
                    p.non_good_qty,

                "reason":
                    p.reason,

                "confirm_comment":
                    p.confirm_comment,

                "create_at":
                    (
                        getattr(
                            p,
                            "create_at",
                            None
                        ).isoformat()
                        if getattr(
                            p,
                            "create_at",
                            None
                        )
                        else None
                    ),
            })


        return jsonify({
            "status": True,
            "created": len(items),
            "items": items
        }), 200


    except SQLAlchemyError as e:

        s.rollback()

        traceback.print_exc()

        return jsonify({
            "status": False,
            "error": str(e)
        }), 500


    except Exception as e:

        s.rollback()

        traceback.print_exc()

        return jsonify({
            "status": False,
            "error": str(e)
        }), 500


    finally:

        s.close()

