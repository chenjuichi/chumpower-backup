import os
import datetime
from datetime import datetime as dt
from datetime import datetime as DateTime

from flask import Blueprint, jsonify, request, current_app

import traceback

from sqlalchemy import inspect, or_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError

#from database.tables import User, UserDelegate, Permission, Setting, Bom, Material, Assemble, AbnormalCause, Process, Product, Agv, Session

from database.p_tables import P_Material, P_Assemble,  P_Process

from werkzeug.security import generate_password_hash


from .assemble_update_utils import (
    ALLOWED_FIELDS, FIELD_SCHEMAS,
    coerce_by_schema, serialize_assemble, now_str
)

from .helper import (
    release_b109_batch_to_b110,
    release_b109_to_b110_batch,
    normalize_create_at,
    sync_assemble_schedule_rows,

    to_int,
    mark_assemble_finished,
    count_running_process,
    mark_waiting_send,
    mark_finished_hidden,

    move_assemble_to_warehouse,
)

from database.tables import (
    User,
    UserDelegate,
    Permission,
    Setting,
    Bom,
    Material,
    Assemble,
    AbnormalCause,
    Process,
    Product,
    Agv,
    Session,
    default_process_steps,
)

updateTable = Blueprint('updateTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


def format_period_time(start_dt, end_dt):
    # 回傳類似 '0:00:04' 的 period_time
    try:
        seconds = int((end_dt - start_dt).total_seconds())
    except Exception:
        seconds = 1

    seconds = max(seconds, 1)

    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    return f"{h}:{m:02d}:{s:02d}"


def ensure_process_log(
    session,
    material_id,
    process_type,
    user_id,
    begin_time=None,
    end_time=None,
    assemble_id=0
):
    #確保 Information 有指定 process_type 紀錄。
    #已存在就不重複新增。
    #
    #process_type:
    #  29 = 等待AGV，組裝區 -> 成品區
    #  3  = AGV運行，組裝區 -> 成品區

    exists = (
        session.query(Process)
        .filter(Process.material_id == material_id)
        .filter(Process.process_type == process_type)
        .first()
    )

    if exists:
        return exists

    now = dt.now()

    if begin_time is None:
        begin_time = now

    if end_time is None:
        end_time = begin_time + datetime.timedelta(seconds=1)

    row = Process(
        material_id=material_id,
        assemble_id=assemble_id or 0,
        has_started=False,
        user_id=user_id,
        user_delegate_id='',

        begin_time=begin_time,
        end_time=end_time,
        period_time=format_period_time(begin_time, end_time),

        pause_time=0,
        pause_started_at=None,
        elapsedActive_time=0,
        str_elapsedActive_time=None,
        is_pause=True,

        process_type=process_type,
        process_work_time_qty=0,
        must_allOk_qty=0,
        allOk_qty=0,
        isAllOk=False,
        normal_work_time=1,
        abnormal_cause_message='',
        create_at=now
    )

    session.add(row)
    session.flush()

    return row


# ------------------------------------------------------------------


def parse_datetime_or_none(val):
    if val is None or str(val).strip() == "":
        return None

    txt = str(val).strip()

    # ISO 格式
    try:
        return dt.fromisoformat(txt.replace("Z", ""))
    except Exception:
        pass

    # 常見格式
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ):
        try:
            return dt.strptime(txt, fmt)
        except Exception:
            continue

    raise ValueError(f"無法解析日期時間格式: {txt}")


def _to_int_or_none(v):
  if v is None or v == "":
    return None
  try:
    return int(v)
  except (TypeError, ValueError):
    raise ValueError("必須是整數或空字串/Null")


def order_has_lack(session, order_num: str) -> bool:
    # 只要同一張訂單底下（包含 A1/A2/A3）任何 BOM.receive == False，就算缺料
    return (
        session.query(Bom.id)
        .join(Material, Bom.material_id == Material.id)
        .filter(Material.order_num == order_num)
        .filter(Bom.receive.is_(False))
        .limit(1)
        .count()
        > 0
    )


def refresh_root_shortage_note(session, order_num: str) -> None:
    root = (
        session.query(Material)
        .filter(Material.order_num == order_num)
        .filter(Material.is_copied_from_id.is_(None))  # root = A1
        .order_by(Material.id.asc())
        .first()
    )
    if not root:
        return

    has_lack = order_has_lack(session, order_num)
    root.shortage_note = "(缺料)" if has_lack else ""


def refresh_root_status(session, order_num: str) -> None:
    # 1) 找 root(A1)
    root = (
        session.query(Material)
        .filter(Material.order_num == order_num)
        .filter(Material.is_copied_from_id.is_(None))  # root = A1
        .order_by(Material.id.asc())
        .first()
    )
    if not root:
        return

    # 2) 找同訂單所有 material.id（含 A1/A2/A3）
    mids = [
        r[0] for r in (
            session.query(Material.id)
            .filter(Material.order_num == order_num)
            .all()
        )
    ]
    if not mids:
        return

    # 3) 統計 BOM 總數 / receive=True 數
    total_bom = (
        session.query(Bom.id)
        .filter(Bom.material_id.in_(mids))
        .count()
    )

    received_bom = (
        session.query(Bom.id)
        .filter(Bom.material_id.in_(mids))
        .filter(Bom.receive.is_(True))
        .count()
    )

    # 4) 決定是否還缺料
    #    - total_bom == 0：通常視為「仍未建 BOM」→ 你可視需求當缺料或不缺料
    all_received = (total_bom > 0 and total_bom == received_bom)

    # 5) 更新 root 欄位
    if all_received:
        root.shortage_note = ""
        root.isLackMaterial = 99
    else:
        root.shortage_note = "(缺料)"
        root.isLackMaterial = 0


def order_has_lack(s, order_num):
    return s.query(Bom)\
        .join(Material, Bom.material_id == Material.id)\
        .filter(Material.order_num == order_num)\
        .filter(Bom.receive.is_(False))\
        .first() is not None


def normalize_cause_message_list(cause_message_list):
    # 如果是 list → 保持不變
    if isinstance(cause_message_list, list):
        return cause_message_list

    # 如果是字串 → 轉為 list（以「、」或「,」或空白分隔都支援）
    if isinstance(cause_message_list, str):
        # 先去除空白
        cause_message_list = cause_message_list.strip()
        # 判斷分隔符號
        if "、" in cause_message_list:
            return [s.strip() for s in cause_message_list.split("、") if s.strip()]
        elif "," in cause_message_list:
            return [s.strip() for s in cause_message_list.split(",") if s.strip()]
        else:
            # 若沒分隔符號，就視為單一項
            return [cause_message_list]

    # 其他型態（例如 None 或數字）→ 回傳空 list
    return []


# 生成唯一檔案名稱的函式
def get_unique_filename(target_dir, filename, chip):
    base, ext = os.path.splitext(filename)  # 分離檔案名稱與副檔名
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(target_dir, unique_filename)):  # 檢查檔案是否已存在
      unique_filename = f"{base}_{chip}_{counter}{ext}"  # 為檔名新增後綴
      counter += 1
    return unique_filename


# ------------------------------------------------------------------


@updateTable.route("/updatePassword", methods=['POST'])
def update_password():
    print("updatePassword....")

    request_data = request.get_json()
    userID = request_data['empID']
    newPassword = request_data['newPassword']

    s = Session()
    s.query(User).filter(User.emp_id == userID).update(
      {'password': generate_password_hash(newPassword, method='scrypt')}
    )

    s.commit()
    s.close()

    return jsonify({
      'status': True,
    })


@updateTable.route("/updateSetting", methods=['POST'])
def update_setting():
    print("updateSetting.")

    request_data = request.get_json(silent=True) or {}

    userID = (request_data.get('empID') or '').strip()
    new_isSee = request_data.get('seeIsOk')
    new_lastRoutingName = request_data.get('lastRoutingName')
    new_itemsPerPage = request_data.get('itemsPerPage', 0)

    if not userID:
      return jsonify({
        'status': False,
        'message': '缺少 empID'
      }), 400

    s = Session()
    try:
      _user = s.query(User).filter_by(emp_id=userID).first()
      if not _user:
        return jsonify({
          'status': False,
          'message': f'找不到使用者: {userID}'
        }), 404

      if not _user.setting_id:
        return jsonify({
          'status': False,
          'message': f'使用者 {userID} 沒有 setting_id'
        }), 400

      update_data = {
        'lastRoutingName': new_lastRoutingName,
        'isSee': new_isSee,
      }

      try:
        items_per_page = int(new_itemsPerPage or 0)
      except Exception:
        items_per_page = 0

      if items_per_page != 0:
        update_data['items_per_page'] = items_per_page

      rows = s.query(Setting).filter(Setting.id == _user.setting_id).update(update_data)

      if rows == 0:
        return jsonify({
          'status': False,
          'message': f'找不到對應 Setting: {_user.setting_id}'
        }), 404

      s.query(User).filter(User.emp_id == userID).update({'isOnline': False})

      s.commit()

      return jsonify({
        'status': True,
        'message': '設定更新成功'
      })
    except Exception as e:
      s.rollback()
      current_app.logger.exception("update_setting failed")
      return jsonify({
        'status': False,
        'message': str(e)
      }), 500
    finally:
      s.close()


@updateTable.route("/updateUser", methods=['POST'])
def update_user():
    print("updateUser.")

    request_data = request.get_json() or {}

    _emp_id = (request_data.get('emp_id') or '').strip()
    _emp_name = (request_data.get('emp_name') or '').strip()
    _dep_name = (request_data.get('dep_name') or '').strip()
    _emp_perm = request_data.get('emp_perm')
    _routingPriv = request_data.get('routingPriv', '')
    _password_reset = request_data.get('password_reset', 'no')

    # ===== 請假 / 代理資料 =====
    _leave_start = (request_data.get('leave_start') or '').strip()
    _leave_end = (request_data.get('leave_end') or '').strip()
    _leave_type = (request_data.get('leave_type') or '').strip()
    _delegate_emp_id = (request_data.get('delegate_emp_id') or '').strip()

    newPassword = 'a12345678'

    if _emp_id == "" or _emp_name == "":
        return jsonify({
            'status': False,
            'message': 'emp_id 或 emp_name 不可為空'
        }), 400

    s = Session()

    try:
        user = s.query(User).filter_by(emp_id=_emp_id).first()
        if not user:
            return jsonify({
                'status': False,
                'message': f'找不到使用者: {_emp_id}'
            }), 404

        if not user.isRemoved:
            return jsonify({
                'status': False,
                'message': f'使用者 {_emp_id} 已刪除或不可更新'
            }), 400

        try:
            _emp_perm = int(_emp_perm)
        except Exception:
            return jsonify({
                'status': False,
                'message': 'emp_perm 格式錯誤'
            }), 400

        _auth_name = (
            'member' if _emp_perm == 4 else
            ('staff' if _emp_perm == 3 else
             ('admin' if _emp_perm == 2 else
              ('system' if _emp_perm == 1 else 'member')))
        )

        # 1) 更新 Permission
        s.query(Permission).filter(Permission.id == user.perm_id).update({
            "auth_code": _emp_perm,
            "auth_name": _auth_name
        })

        print("使用者menu setting:", _routingPriv)
        # 2) 更新 Setting
        s.query(Setting).filter(Setting.id == user.setting_id).update({
            "routingPriv": _routingPriv
        })

        # 3) 更新 User
        update_user_data = {
            "emp_name": _emp_name,
            "dep_name": _dep_name,
        }

        if _password_reset == 'yes':
            update_user_data["password"] = generate_password_hash(newPassword, method='scrypt')

        s.query(User).filter(User.emp_id == _emp_id).update(update_user_data)

        # 4) 更新 / 新增 UserDelegate
        has_any_leave_field = any([_leave_start, _leave_end, _leave_type, _delegate_emp_id])
        leave_fully_set = all([_leave_start, _leave_end, _leave_type, _delegate_emp_id])

        if has_any_leave_field and not leave_fully_set:
            return jsonify({
                'status': False,
                'message': '請假資料需同時填寫：開始時間、結束時間、假別、代理人工號'
            }), 400

        if leave_fully_set:
            start_dt = parse_datetime_or_none(_leave_start)
            end_dt = parse_datetime_or_none(_leave_end)

            if start_dt is None or end_dt is None:
                return jsonify({
                    'status': False,
                    'message': '請假開始/結束日期時間不可為空'
                }), 400

            delegate_user = s.query(User).filter_by(emp_id=_delegate_emp_id).first()
            if not delegate_user:
                return jsonify({
                    'status': False,
                    'message': f'找不到代理人工號: {_delegate_emp_id}'
                }), 404

            delegate_row = (
                s.query(UserDelegate)
                .filter(UserDelegate.user_id == user.id)
                .order_by(UserDelegate.id.desc())
                .first()
            )

            if delegate_row:
                delegate_row.delegate_emp_id = _delegate_emp_id
                delegate_row.start_date = start_dt
                delegate_row.end_date = end_dt
                delegate_row.reason = _leave_type
            else:
                new_delegate = UserDelegate(
                    user_id=user.id,
                    delegate_emp_id=_delegate_emp_id,
                    start_date=start_dt,
                    end_date=end_dt,
                    reason=_leave_type
                )
                s.add(new_delegate)

            user.is_user_delegate = True
        else:
            user.is_user_delegate = False

        s.commit()

        return jsonify({
            'status': True,
            'message': '更新成功'
        })

    except Exception as e:
        s.rollback()
        current_app.logger.exception("updateUser failed")
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

    finally:
        s.close()


@updateTable.route('/updateDelegate', methods=['POST'])
def terminate_active():
    print("updateDelegate....")

    data = request.json
    user_id = int(data['user_id'])
    end_date = datetime.fromisoformat(data['end_date'].replace('Z','')) if data.get('end_date') else datetime.now()

    s = Session()
    rows = s.query(UserDelegate).filter(
        UserDelegate.user_id == user_id,
        UserDelegate.start_date <= datetime.now(),
        (UserDelegate.end_date.is_(None)) | (UserDelegate.end_date >= datetime.now())
    ).all()
    for r in rows:
        r.end_date = end_date
    s.commit()
    return jsonify(success=True, affected=len(rows))


@updateTable.route("/updateBoms", methods=['POST'])
def update_boms():
  print("updateBoms....")

  request_data = request.get_json()

  s = Session()
  return_value = True

  try:
      # 1️⃣ 把 request_data 統一轉成「list of dict」
      if isinstance(request_data, dict):
          bom_list = list(request_data.values())
      elif isinstance(request_data, list):
          bom_list = request_data
      else:
          bom_list = []
          print("updateBoms: unsupported payload type")

      #print("bom_list:", bom_list, "筆數:", len(bom_list))

      #print("bom_data:")
      for bom_data in bom_list:
          if not isinstance(bom_data, dict):
            continue
          bom_id = bom_data.get('id')
          if not bom_id:
            continue

          bom = s.query(Bom).get(bom_id)
          if not bom:
            print(f"updateBoms: Bom id={bom_id} not found")
            continue

          #print(bom_data)

          # 目前 dialog 主要在改的是 receive / lack / lack_bom_qty / isPickOK
          if 'receive' in bom_data:
              a=bom.receive
              b=bom_data['receive']
              c1=bom.seq_num
              if a != b:
                bom.receive = b
                s.query(Bom)\
                    .filter(Bom.seq_num == c1)\
                    .update({Bom.receive: b}, synchronize_session=False)

              #bom.receive = bom_data['receive']
          if 'lack' in bom_data:
              a=bom.lack
              b=bom_data['lack']
              c1=bom.seq_num
              if a != b:
                bom.lack = b
                s.query(Bom)\
                    .filter(Bom.seq_num == c1)\
                    .update({Bom.lack: b}, synchronize_session=False)
              #bom.lack = bom_data['lack']
          if 'lack_bom_qty' in bom_data:
              a=bom.lack_bom_qty
              b=bom_data['lack_bom_qty']
              c1=bom.seq_num
              if a != b:
                bom.lack_bom_qty = b
                s.query(Bom)\
                    .filter(Bom.seq_num == c1)\
                    .update({Bom.lack_bom_qty: b}, synchronize_session=False)
              #bom.lack_bom_qty = bom_data['lack_bom_qty']
          if 'isPickOK' in bom_data:
              a=bom.isPickOK
              b=bom_data['isPickOK']
              c1=bom.seq_num
              if a != b:
                bom.isPickOK = b
                s.query(Bom)\
                    .filter(Bom.seq_num == c1)\
                    .update({Bom.isPickOK: b}, synchronize_session=False)
              #bom.isPickOK = bom_data['isPickOK']

          # 如果還有其他欄位未來要改，也可以一併加上

      # 找出這次被更新的 BOM 屬於哪些訂單 →
      # 針對每張訂單，重新計算並更新 root  的 shortage_note

      # 把這次 request 裡「有 id 的 BOM」全部抓出來
      touched_bom_ids = [
        bd.get("id") for bd in bom_list
        if isinstance(bd, dict) and bd.get("id")
      ]

      if touched_bom_ids:
        order_nums = [
            x[0] for x in (
              s.query(Material.order_num)
              .join(Bom, Bom.material_id == Material.id)
              .filter(Bom.id.in_(touched_bom_ids))        # 只篩選這次被更新的 BOM
              .distinct()                                 # 避免同一張訂單被拿到多次
              .all()
            )
        ]

        # 對每一張被影響的訂單，重算缺料狀態
        for on in order_nums:
          # # 找出這張訂單的 root material（material.is_copied_from_id = NULL）
          #refresh_root_shortage_note(s, on)
          refresh_root_status(s, on)
      ###

      s.commit()

  except Exception as e:
    s.rollback()
    return_value = False
    print("Error in updateBoms:", e)

  finally:
    s.close()

  return jsonify({
      'status': return_value
  })


@updateTable.route("/updateBomsInMaterial", methods=['POST'])
def update_bom(material_id):
  data = request.json
  material_id = data.get("material_id")
  _bom_data = data.get("bom_data", [])

  s = Session()

  # 驗證 Material 是否存在
  material = s.query(Material).filter_by(id=material_id).first()
  if not material:
    return jsonify({"status": "error", "message": "Material ID not found"}), 404

  # 取得現有的 BOM 資料
  existing_bom = s.query(Bom).filter_by(material_id=material_id).all()
  existing_material_nums = {bom.material_num for bom in existing_bom}

  # 新增的 material_num
  new_entries = []
  for bom_entry in _bom_data:
    material_num = bom_entry.get("material_num")
    if material_num not in existing_material_nums:
      new_bom = Bom(
        material_id=material_id,
        material_num=material_num,
        seq_num=f"SEQ-{len(existing_bom) + len(new_entries) + 1}",  # 自動生成序號
        material_comment=f"Generated for {material_num}",
        req_qty=0
      )
      s.add(new_bom)
      s.flush()  # 提交後才能取得新 ID
      new_entries.append({
        "id": new_bom.id,
        "material_id": material_id,
        "material_num": material_num
      })

  # 提交到資料庫
  s.commit()

  return jsonify({
      "status": "success",
      "message": "BOM updated successfully",
      "new_entries": new_entries
  })


# 20260722 batch版
@updateTable.route('/updateAssembleProcessStep', methods=['POST'])
def update_assemble_process_step():
    print("updateAssembleProcessStep.")

    data = request.get_json(silent=True) or {}

    if 'id' not in data or 'assemble_id' not in data:
        return jsonify({
            "status": False,
            "message": "Missing parameters 'id' or 'assemble_id'"
        }), 400

    material_id = data['id']
    assemble_id = data['assemble_id']

    s = Session()

    try:
        def release_material_lock(material):
            material.isOpen = False
            material.isOpenEmpId = ''
            material.hasStarted = False
            material.startStatus = 1

        def finish_process_log(process_type):
            (
                s.query(Process)
                .filter(Process.material_id == material_id)
                .filter(Process.assemble_id == assemble_id)
                .filter(Process.process_type == process_type)
                .filter(Process.end_time.isnot(None))
                .filter(Process.end_time != '')
                .filter(Process.has_started.is_(True))
                .update({
                    Process.has_started: False,
                    Process.is_pause: True,
                    Process.pause_started_at: None,
                }, synchronize_session=False)
            )

        def finish_all_process_logs(process_type):

            # 工序已經 FULL END 時使用。
            #
            # 關閉同一 material_id + assemble_id + process_type
            # 的所有未結束／殘留 process。
            #
            # PARTIAL END 不可使用此函式，
            # 因為其他員工可能仍在繼續執行剩餘數量。

            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            logs = (
                s.query(Process)
                .filter(Process.material_id == material_id)
                .filter(Process.assemble_id == assemble_id)
                .filter(Process.process_type == process_type)
                .filter(
                    or_(
                        Process.has_started.is_(True),
                        Process.end_time.is_(None),
                        Process.end_time == ''
                    )
                )
                .with_for_update()
                .all()
            )

            for log in logs:
                # 尚未補 end_time 的殘留 process，現在一併關閉
                if not log.end_time:
                    log.end_time = now_str

                log.has_started = False
                log.is_pause = True
                log.pause_started_at = None

        def get_group_rows(work_num, release_batch_no=None):
            rows = [
                r for r in assemble_records
                if (r.work_num or '').strip() == work_num
                and to_int(r.schedule_id) > 0
                and to_int(r.ask_qty or r.must_receive_qty or r.must_receive_end_qty) > 0
                and (r.reason or '') != 'B110_DONE_COPY'
            ]

            if release_batch_no is not None:
                rows = [
                    r for r in rows
                    if to_int(getattr(r, 'release_batch_no', 0)) == to_int(release_batch_no)
                ]

            return rows

        def has_checked_b110_steps():
            steps = material_record.process_steps or default_process_steps()
            return any(
                x.get("checked")
                and not x.get("deleted", False)
                and x.get("id") is not None
                for x in (steps.get("check") or [])
            )

        def create_b109_direct_waiting_send(qty, total_done=None):
            qty = to_int(qty)
            total_done = to_int(total_done if total_done is not None else qty)

            if qty <= 0:
                return None

            src = assemble_record

            row = Assemble(
                material_id=src.material_id,
                material_num=src.material_num,
                material_comment=src.material_comment,
                seq_num=src.seq_num,
                work_num='B109',
                process_step_code=0,

                Incoming1_Abnormal=getattr(src, 'Incoming1_Abnormal', '') or '',

                must_receive_qty=qty,
                ask_qty=qty,
                total_ask_qty=qty,
                total_ask_qty_end=0,
                must_receive_end_qty=qty,

                abnormal_qty=0,
                user_id=src.user_id,
                writer_id=src.writer_id,
                write_date=src.write_date,

                good_qty=0,
                total_good_qty=0,
                non_good_qty=0,
                meinh_qty=0,

                completed_qty=qty,
                total_completed_qty=total_done,
                allOk_qty=total_done,

                reason='B109_DIRECT_WAIT_SEND',
                confirm_comment='',
                is_assemble_ok=0,

                currentStartTime=None,
                currentEndTime=None,

                input_disable=True,
                input_end_disable=True,
                input_allOk_disable=False,
                input_abnormal_disable=True,

                isAssembleStationShow=True,
                isWarehouseStationShow=False,

                alarm_enable=True,
                alarm_message='',
                isAssembleFirstAlarm=True,
                isAssembleFirstAlarm_message='',
                isAssembleFirstAlarm_qty=0,

                whichStation=2,
                show1_ok=1,
                show2_ok=9,
                show3_ok=9,

                schedule_id=src.schedule_id,
                is_copied_from_id=src.id,
                release_batch_no=current_batch_no,
            )

            s.add(row)
            s.flush()
            return row

        def create_b109_done_copy(qty):
            qty = to_int(qty)
            if qty <= 0:
                return None

            src = assemble_record

            row = Assemble(
                material_id=src.material_id,
                material_num=src.material_num,
                material_comment=src.material_comment,
                seq_num=src.seq_num,
                work_num='B109',
                process_step_code=0,

                Incoming1_Abnormal=getattr(src, 'Incoming1_Abnormal', '') or '',

                must_receive_qty=qty,
                ask_qty=qty,
                total_ask_qty=qty,
                total_ask_qty_end=0,
                must_receive_end_qty=qty,

                abnormal_qty=0,
                user_id=src.user_id,
                writer_id=src.writer_id,
                write_date=src.write_date,

                good_qty=0,
                total_good_qty=0,
                non_good_qty=0,
                meinh_qty=0,

                completed_qty=qty,
                total_completed_qty=previous_total,
                allOk_qty=previous_total + qty,

                reason='B109_DONE_COPY',
                confirm_comment='',
                is_assemble_ok=0,

                currentStartTime=None,
                currentEndTime=None,

                input_disable=True,
                input_end_disable=True,
                input_allOk_disable=True,
                input_abnormal_disable=True,

                isAssembleStationShow=True,
                isWarehouseStationShow=False,

                alarm_enable=True,
                alarm_message='',
                isAssembleFirstAlarm=True,
                isAssembleFirstAlarm_message='',
                isAssembleFirstAlarm_qty=0,

                whichStation=2,
                show1_ok=1,
                show2_ok=5,
                show3_ok=5,

                schedule_id=src.schedule_id,
                is_copied_from_id=src.id,
                release_batch_no=current_batch_no,
            )

            s.add(row)
            s.flush()
            return row

        # end define function

        material_record = (
            s.query(Material)
            .filter(Material.id == material_id)
            .with_for_update()
            .first()
        )

        if not material_record:
            return jsonify({
                "status": False,
                "message": f"Material with id {material_id} not found"
            }), 404

        assemble_record = (
            s.query(Assemble)
            .filter(Assemble.id == assemble_id)
            .filter(Assemble.material_id == material_id)
            .with_for_update()
            .first()
        )

        if not assemble_record:
            return jsonify({
                "status": False,
                "message": f"Assemble with id {assemble_id} and material_id {material_id} not found"
            }), 404

        assemble_records = (
            s.query(Assemble)
            .filter(Assemble.material_id == material_id)
            .order_by(Assemble.id.asc())
            .all()
        )

        if not assemble_records:
            return jsonify({
                "status": False,
                "message": "No assemble rows found"
            }), 200

        finished_work_num = (assemble_record.work_num or '').strip()
        current_batch_no = to_int(getattr(assemble_record, 'release_batch_no', 0))

        # ------------------------------------------------------------
        # 必須在 mark_assemble_finished() 前保存歷史累計量。
        # mark_assemble_finished() 可能已經把本次完成量寫回
        # total_completed_qty / allOk_qty；若之後再讀並加一次，
        # 例如本次完成 50，就會錯誤變成 100。
        # ------------------------------------------------------------
        previous_total_before_finish = max(
            to_int(getattr(assemble_record, 'total_completed_qty', 0)),
            to_int(getattr(assemble_record, 'allOk_qty', 0)),
            0
        )

        done_qty = mark_assemble_finished(assemble_record)

        if done_qty <= 0:
            done_qty = to_int(
                assemble_record.completed_qty
                or assemble_record.must_receive_end_qty
                or assemble_record.ask_qty
                or assemble_record.must_receive_qty
            )

        must_qty = to_int(
            assemble_record.must_receive_end_qty
            or assemble_record.ask_qty
            or assemble_record.must_receive_qty
        )

        is_partial_end = done_qty < must_qty

        # ------------------------------------------------------------
        # 這裡只能先記住「進入本次結束前」的累積值，
        # 不可以先覆寫 total_completed_qty / allOk_qty。
        #
        # 否則 B109 第一次 20、第二次 15 時，
        # 會把歷史累積值覆蓋掉，導致 B110 釋放量錯亂。
        # ------------------------------------------------------------

        # 不要在這裡覆寫 total_completed_qty / allOk_qty
        # 只先更新「本次完成量」
        current_done_qty = to_int(done_qty)
        assemble_record.completed_qty = current_done_qty

        # ============================================================
        # PARTIAL END
        # ============================================================
        if is_partial_end:
            if finished_work_num == 'B109':
                #
                # ------------------------------------------------------------
                # 本次輸入數量
                # ------------------------------------------------------------
                current_done_qty = to_int(done_qty)

                # ------------------------------------------------------------
                # 查詢此 assemble_id 已經結束的 B109 Process 完成量。
                #
                # 注意：
                # 不使用 previous_total_before_finish + current_done_qty，
                # 避免本次輸入50被重複計算成100。
                # ------------------------------------------------------------
                process_completed_total = (
                    s.query(func.coalesce(func.sum(Process.process_work_time_qty), 0))
                    .filter(Process.material_id == material_id)
                    .filter(Process.assemble_id == assemble_record.id)
                    .filter(Process.process_type == 21)
                    .filter(Process.end_time.isnot(None))
                    .filter(Process.end_time != '')
                    .scalar()
                ) or 0

                cumulative_done_qty = to_int(
                    process_completed_total
                )

                # ------------------------------------------------------------
                # 原始工序總數量
                #
                # total_ask_qty 是此工序最初應完成數量，例如72。
                # 不可使用 cumulative_done_qty + must_qty，
                # 因為 must_qty 此時仍可能是原始72：
                #
                #   50 + 72 = 122
                #   122 - 50 = 72  ← 錯誤
                # ------------------------------------------------------------
                original_required_qty = max(
                    to_int(
                        getattr(
                            assemble_record,
                            'total_ask_qty',
                            0
                        )
                    ),
                    to_int(
                        material_record.total_delivery_qty
                        or material_record.delivery_qty
                        or material_record.material_qty
                    ),
                    to_int(
                        getattr(
                            assemble_record,
                            'must_receive_qty',
                            0
                        )
                    ),
                    0
                )

                if original_required_qty <= 0:
                    original_required_qty = max(to_int(must_qty), cumulative_done_qty, 0)

                cumulative_done_qty = min(cumulative_done_qty, original_required_qty)

                remain_qty = max(original_required_qty - cumulative_done_qty, 0)

                print(
                    "[B109 PARTIAL QTY]",
                    {
                        "material_id": material_id,
                        "assemble_id": assemble_record.id,
                        "current_done_qty": current_done_qty,
                        "process_completed_total": process_completed_total,
                        "total_ask_qty": to_int(
                            getattr(
                                assemble_record,
                                'total_ask_qty',
                                0
                            )
                        ),
                        "must_qty_before_end": must_qty,
                        "original_required_qty": original_required_qty,
                        "cumulative_done_qty": cumulative_done_qty,
                        "remain_qty": remain_qty,
                    }
                )

                has_b110 = has_checked_b110_steps()

                b109_rows = [
                    r for r in assemble_records
                    if ((r.work_num or '').strip() == 'B109' and to_int(getattr(r, 'schedule_id', 0)) > 0)
                ]

                current_schedule_id = to_int(getattr(assemble_record, 'schedule_id', 0))

                for r in b109_rows:
                    # --------------------------------------------------------
                    # B109 PARTIAL 只能更新本次按 End 的工序。
                    #
                    # 其他 B109 可能已經 FULL END，例如 a2：
                    #   process_step_code = 0
                    #   isAssembleStationShow = False
                    #
                    # 不可重新改成 active，否則完成的 a2 會再次出現。
                    # --------------------------------------------------------
                    if (
                        to_int(r.id)
                        != to_int(assemble_record.id)
                    ):
                        continue

                    # --------------------------------------------------------
                    # 只有目前 partial 的工序回到 Begin
                    # --------------------------------------------------------
                    r.process_step_code = 3

                    r.show1_ok = 1
                    r.show2_ok = 3
                    r.show3_ok = 3

                    r.isWarehouseStationShow = False

                    # 剩餘數量
                    r.must_receive_qty = remain_qty
                    r.ask_qty = remain_qty
                    r.must_receive_end_qty = remain_qty

                    # 本次輸入欄位清空
                    r.completed_qty = 0

                    # 保存累計完成數量
                    r.total_completed_qty = (
                        cumulative_done_qty
                    )

                    r.allOk_qty = (
                        cumulative_done_qty
                    )

                    # 回 Begin 後重新等待開始
                    r.currentStartTime = None
                    r.currentEndTime = None

                    r.isAssembleStationShow = True

                    r.input_disable = False
                    r.input_end_disable = False
                    r.input_abnormal_disable = False
                    r.input_allOk_disable = True

                # end for loop

                finish_process_log(21)

                old_b110_rows = get_group_rows('B110', release_batch_no=0)

                for r in old_b110_rows:
                    r.isAssembleStationShow = False
                    r.isWarehouseStationShow = False

                    r.input_disable = True
                    r.input_end_disable = True
                    r.input_abnormal_disable = True
                    r.input_allOk_disable = True

                    r.currentStartTime = None
                    r.currentEndTime = None

                    r.show1_ok = 1
                    r.show2_ok = 7
                    r.show3_ok = 7

                # end for loop

                # ------------------------------------------------------------
                # B109 PARTIAL 時不可釋放 B110。
                # 只要任一 B109（例如 a1）仍有剩餘數量，Begin 只能顯示
                # 尚未完成的 B109；b1 / b2 必須等所有 B109 FULL END 後
                # 才由下方 B109 FULL END 區塊建立。
                # ------------------------------------------------------------
                release_result = {
                    "released": False,
                    "release_qty": 0,
                    "created_ids": [],
                    "min_done_qty": cumulative_done_qty,
                    "released_total": 0,
                    "message": (
                        "B109 partial finished; "
                        "B110 remains hidden until all B109 steps finish"
                    )
                }

                material_record.isAssembleStationShow = True
                material_record.isAssembleStation3TakeOk = False
                material_record.whichStation = 2
                material_record.show1_ok = 1
                material_record.show2_ok = 3
                material_record.show3_ok = 3

                s.commit()

                return jsonify({
                    "status": False,
                    "material_done": False,
                    "partial_end": True,

                    "released_next_group": bool(release_result.get("released")),

                    "released_count": release_result.get("release_qty", 0),

                    "created_ids": release_result.get("created_ids", []),

                    "current_done_qty": current_done_qty,

                    "total_completed_qty": cumulative_done_qty,

                    "remain_qty": remain_qty,

                    "message":
                        release_result.get(
                            "message",
                            "B109 partial finished"
                        )
                }), 200

            # end if_finished_work_num == 'B109':

            # ------------------------------------------------------------
            # B110 PARTIAL
            #
            # 只修改本次按結束的 B110。
            # 不可修改同批其他 b1 / b2，避免其他檢驗工序的
            # 領取數量、應完成總數量、已完成總數量被一起覆寫。
            # ------------------------------------------------------------
            if finished_work_num == 'B110':
                current_done_qty = to_int(done_qty)

                # --------------------------------------------------------
                # 先記住本次操作前的歷史累積量。
                #
                # 第一次 partial：
                #   previous_total = 0
                #   current_done   = 20
                #   new_total      = 20
                #
                # 第二次 partial：
                #   previous_total = 20
                #   current_done   = 5
                #   new_total      = 25
                # --------------------------------------------------------
                previous_total = previous_total_before_finish

                new_total = previous_total + current_done_qty
                remain_qty = max(must_qty - current_done_qty, 0)

                assemble_record.process_step_code = 2

                # 目前這筆回 Begin 補做剩餘數量
                assemble_record.must_receive_qty = remain_qty
                assemble_record.ask_qty = remain_qty
                assemble_record.must_receive_end_qty = remain_qty

                # 本次輸入量清零；歷史完成量保留累積
                assemble_record.completed_qty = 0
                assemble_record.total_completed_qty = new_total
                assemble_record.allOk_qty = new_total

                assemble_record.isAssembleStationShow = True
                assemble_record.isWarehouseStationShow = False

                assemble_record.input_disable = False
                assemble_record.input_end_disable = False
                assemble_record.input_abnormal_disable = False
                assemble_record.input_allOk_disable = True

                assemble_record.currentStartTime = None
                assemble_record.currentEndTime = None

                assemble_record.show1_ok = 1
                assemble_record.show2_ok = 5
                assemble_record.show3_ok = 5

                material_record.isAssembleStation3TakeOk = False

                finish_process_log(22)

                s.commit()

                return jsonify({
                    "status": False,
                    "material_done": False,
                    "partial_end": True,
                    "waiting_send": False,
                    "release_batch_no": current_batch_no,
                    "current_assemble_id": assemble_record.id,
                    "completed_qty": current_done_qty,
                    "total_completed_qty": new_total,
                    "remain_qty": remain_qty,
                    "message": "B110 partial finished, current row returns to Begin"
                }), 200

            # end if_finished_work_num == 'B110':

            assemble_record.process_step_code = 0

            for r in get_group_rows(finished_work_num):
                r.isAssembleStationShow = True
                r.isWarehouseStationShow = False
                r.input_disable = False
                r.input_end_disable = False
                r.input_abnormal_disable = False
                r.input_allOk_disable = True
                r.show1_ok = 1
                r.show2_ok = 3
                r.show3_ok = 3

            # end for loop

            material_record.isAssembleStation3TakeOk = False

            s.commit()

            return jsonify({
                "status": False,
                "material_done": False,
                "partial_end": True,
                "waiting_send": False,
                "current_assemble_id": assemble_record.id,
                "completed_qty": done_qty,
                "must_qty": must_qty,
                "message": "Partial end, process still active"
            }), 200

        # ============================================================
        # FULL END
        # ============================================================
        assemble_record.process_step_code = 0

        assemble_record.input_disable = True
        assemble_record.input_end_disable = True
        assemble_record.input_abnormal_disable = True
        assemble_record.input_allOk_disable = True

        if not assemble_record.currentEndTime:
            assemble_record.currentEndTime = (
                datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

        # end if

        # ------------------------------------------------------------
        # FULL END：
        # 同一 assemble_id 已經完全完成，
        # 所有員工殘留的 process 都必須一併結束。
        # ------------------------------------------------------------
        if finished_work_num == 'B109':
            finish_all_process_logs(21)

        elif finished_work_num == 'B110':
            finish_all_process_logs(22)

        # ============================================================
        # 異常返工：B109 完成
        # ============================================================
        if (
            finished_work_num == 'B109'
            and (assemble_record.reason or '').strip() == '異常返工'
        ):
            qty = to_int(done_qty or assemble_record.must_receive_end_qty or assemble_record.ask_qty or assemble_record.must_receive_qty)

            child_b110_rework = (
                s.query(Assemble)
                .filter(Assemble.material_id == material_id)
                .filter(Assemble.work_num == 'B110')
                .filter(Assemble.reason == '異常返工')
                .filter(Assemble.is_copied_from_id == assemble_record.id)
                .order_by(Assemble.id.asc())
                .first()
            )

            assemble_record.process_step_code = 0
            assemble_record.completed_qty = qty
            assemble_record.total_completed_qty = qty
            assemble_record.allOk_qty = qty
            assemble_record.isAssembleStationShow = False
            assemble_record.isWarehouseStationShow = False
            assemble_record.input_disable = True
            assemble_record.input_end_disable = True
            assemble_record.input_abnormal_disable = True
            assemble_record.input_allOk_disable = True
            assemble_record.currentStartTime = None
            assemble_record.currentEndTime = None
            assemble_record.show1_ok = 1
            assemble_record.show2_ok = 7
            assemble_record.show3_ok = 7

            if child_b110_rework:
                child_b110_rework.process_step_code = 2
                child_b110_rework.must_receive_qty = qty
                child_b110_rework.ask_qty = qty
                child_b110_rework.total_ask_qty = qty
                child_b110_rework.must_receive_end_qty = qty
                child_b110_rework.completed_qty = 0
                child_b110_rework.total_completed_qty = 0
                child_b110_rework.allOk_qty = 0
                child_b110_rework.isAssembleStationShow = True
                child_b110_rework.isWarehouseStationShow = False
                child_b110_rework.input_disable = False
                child_b110_rework.input_end_disable = False
                child_b110_rework.input_abnormal_disable = False
                child_b110_rework.input_allOk_disable = True
                child_b110_rework.currentStartTime = None
                child_b110_rework.currentEndTime = None
                child_b110_rework.show1_ok = 1
                child_b110_rework.show2_ok = 5
                child_b110_rework.show3_ok = 5

                s.commit()

                return jsonify({
                    "status": False,
                    "material_done": False,
                    "abnormal_rework": True,
                    "next_work_num": "B110",
                    "message": "B109 abnormal rework finished, open child B110 abnormal rework"
                }), 200

            # end if

            release_result = release_b109_to_b110_batch(
                session=s,
                material_id=material_id
            )

            material_record.isAssembleStationShow = True
            material_record.isAssembleStation3TakeOk = False
            material_record.whichStation = 2

            if release_result.get("released"):
                material_record.show1_ok = 3
                material_record.show2_ok = 5
                material_record.show3_ok = 5

            # end if

            s.commit()

            return jsonify({
                "status": False,
                "material_done": False,
                "abnormal_rework": True,
                "released_next_group": bool(release_result.get("released")),
                "released_count": release_result.get("release_qty", 0),
                "created_ids": release_result.get("created_ids", []),
                "message": "B109 abnormal rework finished, return to normal B110 flow"
            }), 200

        # end if 異常返工, B109 完成

        # ============================================================
        # 異常返工：B110 完成後直接待送出
        # ============================================================
        if (
            finished_work_num == 'B110'
            and (assemble_record.reason or '').strip() == '異常返工'
        ):
            qty = to_int(done_qty or assemble_record.must_receive_end_qty or assemble_record.ask_qty or assemble_record.must_receive_qty)

            assemble_record.process_step_code = 0
            assemble_record.completed_qty = qty
            assemble_record.total_completed_qty = qty
            assemble_record.allOk_qty = qty
            assemble_record.must_receive_qty = qty
            assemble_record.ask_qty = qty
            assemble_record.total_ask_qty = qty
            assemble_record.must_receive_end_qty = qty

            assemble_record.isAssembleStationShow = True
            assemble_record.isWarehouseStationShow = False
            assemble_record.input_disable = True
            assemble_record.input_end_disable = True
            assemble_record.input_abnormal_disable = True
            assemble_record.input_allOk_disable = False
            assemble_record.currentStartTime = None
            assemble_record.currentEndTime = None
            assemble_record.show1_ok = 1
            assemble_record.show2_ok = 9
            assemble_record.show3_ok = 9

            material_record.isAssembleStationShow = True
            material_record.isAssembleStation3TakeOk = True
            material_record.whichStation = 2
            material_record.show1_ok = 3
            material_record.show2_ok = 9
            material_record.show3_ok = 9

            release_material_lock(material_record)

            s.commit()

            return jsonify({
                "status": True,
                "material_done": False,
                "waiting_send": True,
                "abnormal_rework": True,
                "message": "B110 abnormal rework finished, waiting send"
            }), 200

        # end if 異常返工, B110 完成

        # ============================================================
        # B109 FULL END
        #
        # 情境：
        # 第 1 批：
        #   a2 完成 20 / 35
        #   a1 再完成 15
        #
        # 第 2 批：
        #   a2 補做剩餘 15
        #
        # 正確結果：
        #   1. 所有 B109(a1/a2) 全部從 Begin / End 隱藏
        #   2. 不再殘留 a1 已完成資料
        #   3. 釋放 B110 qty=15
        #   4. Begin 最後只保留：
        #        b1/b2 qty=20
        #        b1/b2 qty=15
        # ============================================================
        if finished_work_num == 'B109':

            current_done_qty = to_int(done_qty)

            # --------------------------------------------------------
            # 目前 a2 已完成最後剩餘數量，不可再出現在 Begin／End
            # --------------------------------------------------------
            assemble_record.process_step_code = 0

            assemble_record.isAssembleStationShow = False
            assemble_record.isWarehouseStationShow = False

            assemble_record.input_disable = True
            assemble_record.input_end_disable = True
            assemble_record.input_abnormal_disable = True
            assemble_record.input_allOk_disable = True

            assemble_record.currentStartTime = None

            if not assemble_record.currentEndTime:
                assemble_record.currentEndTime = (
                    datetime.datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

            # end if
            '''
            # 已釋放到 B110 的總量，才是真正 previous_total
            # 例：第一次已釋放 20，第二次補 15，所以 final_total=35
            if has_checked_b110_steps():
                released_batches_for_b109 = (
                    s.query(
                        Assemble.release_batch_no,
                        func.max(Assemble.ask_qty)
                    )
                    .filter(Assemble.material_id == material_id)
                    .filter(Assemble.work_num == 'B110')
                    .filter(Assemble.reason == 'B109_RELEASE_BATCH')
                    .filter(Assemble.release_batch_no > 0)
                    .filter(Assemble.schedule_id.isnot(None))
                    .filter(Assemble.schedule_id > 0)
                    .group_by(Assemble.release_batch_no)
                    .all()
                )

                previous_total = sum(
                    to_int(qty)
                    for _, qty in released_batches_for_b109
                )
            else:
                # 只選 B109 時，前一批完成量存在 B109 自己的 total_completed_qty / allOk_qty
                previous_total = max(
                    [
                        max(
                            to_int(r.total_completed_qty),
                            to_int(r.allOk_qty)
                        )
                        for r in assemble_records
                        if (r.work_num or '').strip() == 'B109'
                        and to_int(getattr(r, 'schedule_id', 0)) > 0
                        and to_int(r.id) != to_int(assemble_record.id)
                        and (r.reason or '').strip() not in (
                            'B109_DIRECT_WAIT_SEND',
                            'B109_DONE_COPY',
                        )
                    ] or [0]
                )

            # end if-else has_checked_b110_steps():

            final_total = previous_total + current_done_qty

            assemble_record.completed_qty = current_done_qty
            assemble_record.total_completed_qty = previous_total
            assemble_record.allOk_qty = final_total
            '''
            #
            # ------------------------------------------------------------
            # B109 FULL END 的真正累計完成量
            #
            # 必須直接加總此 assemble_id 已結束的 Process 數量。
            #
            # 本案例：
            #   第一次完成 50
            #   第二次完成 22
            #   Process 合計 = 72
            #
            # 不可只用已釋放 B110 的數量當 previous_total，
            # 因為 B109 PARTIAL 時目前沒有釋放 B110，
            # 會導致 previous_total=0、final_total=22。
            # ------------------------------------------------------------
            process_completed_total = (
                s.query(
                    func.coalesce(
                        func.sum(
                            Process.process_work_time_qty
                        ),
                        0
                    )
                )
                .filter(
                    Process.material_id == material_id
                )
                .filter(
                    Process.assemble_id == assemble_record.id
                )
                .filter(
                    Process.process_type == 21
                )
                .filter(
                    Process.end_time.isnot(None)
                )
                .filter(
                    Process.end_time != ''
                )
                .scalar()
            ) or 0

            final_total = to_int(
                process_completed_total
            )

            # 舊資料防呆：
            # 若 Process 數量未完整保存，才使用欄位累計。
            if final_total <= 0:
                final_total = max(
                    previous_total_before_finish
                    + current_done_qty,
                    to_int(
                        getattr(
                            assemble_record,
                            'total_completed_qty',
                            0
                        )
                    )
                    + current_done_qty,
                    to_int(
                        getattr(
                            assemble_record,
                            'allOk_qty',
                            0
                        )
                    )
                    + current_done_qty,
                    current_done_qty,
                    0
                )

            # 原始總數量上限
            original_required_qty = max(
                to_int(
                    getattr(
                        assemble_record,
                        'total_ask_qty',
                        0
                    )
                ),
                to_int(
                    material_record.total_delivery_qty
                    or material_record.delivery_qty
                    or material_record.material_qty
                ),
                0
            )

            if original_required_qty > 0:
                final_total = min(
                    final_total,
                    original_required_qty
                )

            previous_total = max(
                final_total - current_done_qty,
                0
            )

            assemble_record.completed_qty = current_done_qty
            assemble_record.total_completed_qty = final_total
            assemble_record.allOk_qty = final_total

            print(
                "[B109 FULL END QTY]",
                {
                    "material_id": material_id,
                    "assemble_id": assemble_record.id,
                    "current_done_qty": current_done_qty,
                    "process_completed_total": process_completed_total,
                    "previous_total": previous_total,
                    "final_total": final_total,
                    "original_required_qty": original_required_qty,
                }
            )
            #

            assemble_record.input_disable = True

            assemble_record.input_abnormal_disable = True
            assemble_record.input_allOk_disable = True

            assemble_record.currentStartTime = None
            assemble_record.currentEndTime = None

            assemble_record.show1_ok = 1
            assemble_record.show2_ok = 5
            assemble_record.show3_ok = 5

            # --------------------------------------------------------
            # 2) 取得目前所有「原始有效 B109 工序」
            #
            # 注意：
            # B109_DIRECT_WAIT_SEND = 已建立的待送出批次
            # B109_DONE_COPY        = End 顯示用的已完成資料
            #
            # 這兩種 copy row 不可以再參與：
            #   remaining_b109_rows
            #   all_b109_done
            #   全部 B109 隱藏處理
            #
            # 否則第二批完成時，會把第一批待送出資料一起隱藏。
            # --------------------------------------------------------
            b109_rows = [
                r for r in assemble_records
                if (r.work_num or '').strip() == 'B109'
                and to_int(getattr(r, 'schedule_id', 0)) > 0
                and (r.reason or '').strip() not in (
                    'B109_DIRECT_WAIT_SEND',
                    'B109_DONE_COPY',
                )
            ]

            # --------------------------------------------------------
            # 3) 判斷是否還有 B109 需要繼續加工
            #
            # 注意：
            # PARTIAL END 已把 must_receive_qty 改成剩餘量。
            #
            # 所以這裡不能再判斷：
            #   每一列是否 >= material 35
            #
            # 而是判斷：
            #   是否還存在 process_step_code=3 的 B109 active row
            # --------------------------------------------------------
            remaining_b109_rows = [
                r for r in b109_rows
                if (
                    to_int(r.process_step_code) == 3
                    and to_int(r.id) != to_int(assemble_record.id)
                )
            ]

            all_b109_done = len(remaining_b109_rows) == 0

            print(
                "[B109 FULL END]",
                "material_id=", material_id,
                "assemble_id=", assemble_id,
                "current_done_qty=", current_done_qty,
                "b109_rows=",
                [
                    (
                        r.id,
                        r.schedule_id,
                        r.process_step_code,
                        r.must_receive_qty,
                        r.ask_qty,
                        r.completed_qty,
                        r.total_completed_qty,
                        r.allOk_qty,
                    )
                    for r in b109_rows
                ],
                "remaining_ids=",
                [r.id for r in remaining_b109_rows],
                "all_b109_done=",
                all_b109_done,
            )

            # --------------------------------------------------------
            # 4) 若全部 B109 已完成：
            #    a1/a2 全部從 Begin / End 隱藏
            # --------------------------------------------------------
            if all_b109_done:
                for r in b109_rows:
                    r.process_step_code = 0

                    r.isAssembleStationShow = False
                    r.isWarehouseStationShow = False

                    r.input_disable = True
                    r.input_end_disable = True
                    r.input_abnormal_disable = True
                    r.input_allOk_disable = True

                    r.currentStartTime = None
                    r.currentEndTime = None

                    r.show1_ok = 1
                    r.show2_ok = 7
                    r.show3_ok = 7
            else:
                # --------------------------------------------------------
                # 還有其他 B109 尚未完成。
                #
                # 目前按結束的工序已經 FULL END，
                # 不論 previous_total 是否大於 0，都不可再顯示於 Begin／End。
                #
                # 例如：
                #   a2 partial 20，剩餘15
                #   a1 full end 35
                #
                # 此時只留下 a2 繼續做15，a1必須隱藏。
                # --------------------------------------------------------
                assemble_record.process_step_code = 0

                assemble_record.isAssembleStationShow = False
                assemble_record.isWarehouseStationShow = False

                assemble_record.input_disable = True
                assemble_record.input_end_disable = True
                assemble_record.input_abnormal_disable = True
                assemble_record.input_allOk_disable = True

                assemble_record.currentStartTime = None
                assemble_record.currentEndTime = None

                assemble_record.show1_ok = 1
                assemble_record.show2_ok = 7
                assemble_record.show3_ok = 7

            # end if-else all_b109_done:

            # --------------------------------------------------------
            # 5) B109 -> B110 增量釋放
            #
            # 第一次：
            #   release 20
            #
            # 第二次：
            #   release 15
            #
            # 不應建立 35
            # --------------------------------------------------------
            #
            if has_checked_b110_steps():
                release_result = release_b109_to_b110_batch(
                    session=s,
                    material_id=material_id
                )
            else:
                waiting_row = None
                done_copy_row = None
                release_qty = 0

                if all_b109_done:
                    # 最後補完，例如 a2 補做 15，直接成為待送出
                    release_qty = current_done_qty

                    if release_qty > 0:
                        # 批次2完成數量=15，但已完成總數量要顯示前批累積 20
                        waiting_row = create_b109_direct_waiting_send(
                            release_qty,
                            total_done=previous_total
                        )

                    # 全部 B109 完成後，B109_DONE_COPY 只是過程顯示資料，要隱藏
                    done_copy_rows = (
                        s.query(Assemble)
                        .filter(Assemble.material_id == material_id)
                        .filter(Assemble.work_num == 'B109')
                        .filter(Assemble.reason == 'B109_DONE_COPY')
                        .filter(Assemble.isAssembleStationShow.is_(True))
                        .all()
                    )

                    for r in done_copy_rows:
                        r.isAssembleStationShow = False
                        r.isWarehouseStationShow = False
                        r.input_disable = True
                        r.input_end_disable = True
                        r.input_abnormal_disable = True
                        r.input_allOk_disable = True
                        r.show1_ok = 1
                        r.show2_ok = 7
                        r.show3_ok = 7

                    # end for loop
                else:
                    # 還有其他 B109 未完成。
                    # 只有「前面真的有分批完成量」時，才建立待送出與已完成 copy。
                    # 例如 a2 先完成 20，a1 再完成 15，previous_total=20。
                    #
                    # 若是 a1 直接完成 35，previous_total=0，
                    # 代表不是分批，不可建立待送出，也不可建立 done_copy。
                    release_qty = previous_total

                    if release_qty > 0:
                        waiting_row = create_b109_direct_waiting_send(release_qty)
                        done_copy_row = create_b109_done_copy(current_done_qty)

                    assemble_record.isAssembleStationShow = False
                    assemble_record.isWarehouseStationShow = False
                    assemble_record.show1_ok = 1
                    assemble_record.show2_ok = 7
                    assemble_record.show3_ok = 7

                # end if-else all_b109_done:

                release_result = {
                    "released": waiting_row is not None,
                    "release_qty": release_qty if waiting_row else 0,
                    "created_ids": [waiting_row.id] if waiting_row else [],
                    "done_copy_id": done_copy_row.id if done_copy_row else None,
                    "min_done_qty": final_total,
                    "released_total": previous_total,
                    "message": "B109 direct waiting send, no B110 selected"
                }

            # end if-else has_checked_b110_steps():

            # --------------------------------------------------------
            # 6) 再次隱藏原始 B110 batch_no=0 template
            #
            # 避免 Begin 出現：
            #   b1/b2 qty=35
            # --------------------------------------------------------
            old_b110_rows = get_group_rows('B110', release_batch_no=0)

            for r in old_b110_rows:
                r.isAssembleStationShow = False
                r.isWarehouseStationShow = False

                r.input_disable = True
                r.input_end_disable = True
                r.input_abnormal_disable = True
                r.input_allOk_disable = True

                r.currentStartTime = None
                r.currentEndTime = None

                r.show1_ok = 1
                r.show2_ok = 7
                r.show3_ok = 7

            # end for loop

            # --------------------------------------------------------
            # 7) Material 狀態
            # --------------------------------------------------------
            material_record.isAssembleStation3TakeOk = False
            material_record.isAssembleStationShow = True
            material_record.whichStation = 2

            if release_result.get("released"):
                material_record.show1_ok = 3
                material_record.show2_ok = 5
                material_record.show3_ok = 5

            s.commit()

            return jsonify({
                "status": False,
                "material_done": False,

                "released_next_group": bool(release_result.get("released")),

                "released_count": release_result.get("release_qty", 0),

                "created_ids": release_result.get("created_ids", []),

                "min_done_qty": release_result.get("min_done_qty", 0),

                "released_total": release_result.get("released_total", 0),

                "all_b109_done": all_b109_done,

                "remaining_b109_ids": [r.id for r in remaining_b109_rows],

                "current_group_step": 3,

                "message": release_result.get("message", "")
            }), 200

        # end if B109 FULL END

        # ============================================================
        # B110
        # ============================================================
        if finished_work_num == 'B110':
            #current_batch_no = to_int(getattr(assemble_record, 'release_batch_no', 0))
            #
            #b110_rows = get_group_rows('B110', current_batch_no)
            #
            #
            current_batch_no = to_int(
                getattr(
                    assemble_record,
                    'release_batch_no',
                    0
                )
            )

            # ------------------------------------------------------------
            # B110 FULL END：
            # 將前次 partial 累計量，加上本次最後完成量。
            #
            # 本案例：
            #   previous_total_before_finish = 50
            #   current_done_qty             = 22
            #   current_total_qty            = 72
            # ------------------------------------------------------------
            current_done_qty = to_int(done_qty)

            current_total_qty = (
                previous_total_before_finish
                + current_done_qty
            )

            # 防止舊資料／重複送出造成超過本批應完成量
            '''
            current_required_qty = max(
                to_int(
                    getattr(
                        assemble_record,
                        'total_ask_qty',
                        0
                    )
                ),
                to_int(
                    getattr(
                        assemble_record,
                        'must_receive_qty',
                        0
                    )
                ),
                to_int(
                    getattr(
                        assemble_record,
                        'must_receive_end_qty',
                        0
                    )
                ),
                current_total_qty,
                0
            )
            '''

            #
            current_required_qty = max(
                to_int(
                    getattr(
                        assemble_record,
                        'total_ask_qty',
                        0
                    )
                ),
                to_int(
                    material_record.total_delivery_qty
                    or material_record.delivery_qty
                    or material_record.material_qty
                ),
                0
            )

            if current_required_qty > 0:
                current_total_qty = min(
                    current_total_qty,
                    current_required_qty
                )
            #

            if current_required_qty > 0:
                current_total_qty = min(
                    current_total_qty,
                    current_required_qty
                )

            assemble_record.completed_qty = current_done_qty
            assemble_record.total_completed_qty = current_total_qty
            assemble_record.allOk_qty = current_total_qty

            b110_rows = get_group_rows(
                'B110',
                current_batch_no
            )

            # 統一取得 B110 累計完成量。
            # 不可使用 completed_qty or total_completed_qty，
            # 因為 completed_qty=22 會遮住 total_completed_qty=72。
            def get_b110_done_qty(row):
                return max(
                    to_int(
                        getattr(
                            row,
                            'total_completed_qty',
                            0
                        )
                    ),
                    to_int(
                        getattr(
                            row,
                            'allOk_qty',
                            0
                        )
                    ),
                    to_int(
                        getattr(
                            row,
                            'completed_qty',
                            0
                        )
                    ),
                    0
                )
            #

            done_copy_rows = (
                s.query(Assemble)
                .filter(Assemble.material_id == material_id)
                .filter(Assemble.work_num == 'B110')
                .filter(Assemble.release_batch_no == current_batch_no)
                .filter(Assemble.reason == 'B110_DONE_COPY')
                .filter(Assemble.isAssembleStationShow.is_(True))
                .all()
            )

            old_waiting_rows = [
                r for r in b110_rows
                if to_int(r.id) != to_int(assemble_record.id)
                and to_int(r.process_step_code) == 0
                and to_int(r.show2_ok) in (9, 10)
                and to_int(r.completed_qty or r.total_completed_qty or r.allOk_qty) > 0
            ]

            if done_copy_rows and old_waiting_rows:
                old_waiting_row = old_waiting_rows[0]
                old_done_copy = done_copy_rows[0]

                base_min_qty = to_int(old_waiting_row.total_completed_qty or old_waiting_row.allOk_qty)
                if base_min_qty <= 0:
                    base_min_qty = to_int(old_done_copy.total_completed_qty or old_done_copy.allOk_qty)

                current_done_qty = to_int(done_qty)
                final_total_qty = base_min_qty + current_done_qty

                old_waiting_row.process_step_code = 0
                old_waiting_row.completed_qty = current_done_qty
                old_waiting_row.total_completed_qty = final_total_qty
                old_waiting_row.allOk_qty = final_total_qty
                old_waiting_row.must_receive_end_qty = current_done_qty

                old_waiting_row.isAssembleStationShow = True
                old_waiting_row.isWarehouseStationShow = False

                old_waiting_row.input_disable = True
                old_waiting_row.input_end_disable = True
                old_waiting_row.input_abnormal_disable = True
                old_waiting_row.input_allOk_disable = False

                old_waiting_row.show1_ok = 1
                old_waiting_row.show2_ok = 9
                old_waiting_row.show3_ok = 9

                for r in done_copy_rows:
                    r.isAssembleStationShow = False
                    r.isWarehouseStationShow = False
                    r.input_disable = True
                    r.input_end_disable = True
                    r.input_abnormal_disable = True
                    r.input_allOk_disable = True
                    r.show1_ok = 1
                    r.show2_ok = 7
                    r.show3_ok = 7

                assemble_record.process_step_code = 0
                assemble_record.completed_qty = base_min_qty
                assemble_record.total_completed_qty = final_total_qty
                assemble_record.allOk_qty = final_total_qty
                assemble_record.must_receive_end_qty = base_min_qty

                assemble_record.isAssembleStationShow = True
                assemble_record.isWarehouseStationShow = False

                assemble_record.input_disable = True
                assemble_record.input_end_disable = True
                assemble_record.input_abnormal_disable = True
                assemble_record.input_allOk_disable = False

                assemble_record.currentStartTime = None

                assemble_record.show1_ok = 1
                assemble_record.show2_ok = 9
                assemble_record.show3_ok = 9

                material_record.isAssembleStationShow = True
                material_record.isAssembleStation3TakeOk = True
                material_record.whichStation = 2
                material_record.show1_ok = 3
                material_record.show2_ok = 9
                material_record.show3_ok = 9
                material_record.assemble_qty = final_total_qty
                material_record.total_assemble_qty = final_total_qty

                release_material_lock(material_record)

                s.commit()

                return jsonify({
                    "status": True,
                    "material_done": False,
                    "waiting_send": True,
                    "final_b110_done": True,
                    "release_batch_no": current_batch_no,
                    "final_total_qty": final_total_qty,
                    "base_min_qty": base_min_qty,
                    "current_done_qty": current_done_qty,
                    "message": "B110 batch final waiting send rows ready"
                }), 200

            #not_finished = [
            #    r for r in b110_rows
            #    if to_int(r.completed_qty or r.total_completed_qty or r.allOk_qty) <= 0
            #]
            #
            #
            not_finished = [
                r for r in b110_rows
                if get_b110_done_qty(r) <= 0
            ]
            #

            if not_finished:
                # 目前這筆 B110 已完成，例如 b2=35
                # 但同批還有 b1 未完成，所以：
                #   b2 不可回 Begin
                #   b2 不可留 End
                #   只讓 b1 繼續留在 End
                current_done_qty = to_int(done_qty)

                assemble_record.process_step_code = 0
                assemble_record.completed_qty = current_done_qty
                assemble_record.total_completed_qty = current_done_qty
                assemble_record.allOk_qty = current_done_qty
                assemble_record.must_receive_end_qty = current_done_qty

                assemble_record.isAssembleStationShow = False
                assemble_record.isWarehouseStationShow = False

                assemble_record.input_disable = True
                assemble_record.input_end_disable = True
                assemble_record.input_abnormal_disable = True
                assemble_record.input_allOk_disable = True

                assemble_record.currentStartTime = None
                assemble_record.currentEndTime = None

                assemble_record.show1_ok = 1
                assemble_record.show2_ok = 7
                assemble_record.show3_ok = 7

                # 其他尚未完成的 B110，例如 b1，繼續留在 End
                for r in not_finished:
                    if to_int(r.id) == to_int(assemble_record.id):
                        continue

                    r.process_step_code = 2
                    r.isAssembleStationShow = True
                    r.isWarehouseStationShow = False

                    r.input_disable = False
                    r.input_end_disable = False
                    r.input_abnormal_disable = False
                    r.input_allOk_disable = True

                    r.show1_ok = 1
                    r.show2_ok = 5
                    r.show3_ok = 5

                material_record.isAssembleStation3TakeOk = False

                s.commit()

                return jsonify({
                    "status": False,
                    "material_done": False,
                    "waiting_send": False,
                    "release_batch_no": current_batch_no,
                    "current_assemble_id": assemble_record.id,
                    "message": "B110 row finished, wait other rows in same batch"
                }), 200

            #min_qty = min(
            #    to_int(r.completed_qty or r.total_completed_qty or r.allOk_qty)
            #    for r in b110_rows
            #)
            #
            min_qty = min(
                get_b110_done_qty(r)
                for r in b110_rows
            )

            #waiting_row = min(
            #    b110_rows,
            #    key=lambda r: (
            #        to_int(r.completed_qty or r.total_completed_qty or r.allOk_qty),
            #        to_int(r.id)
            #    )
            #)
            #
            waiting_row = min(
                b110_rows,
                key=lambda r: (
                    get_b110_done_qty(r),
                    to_int(r.id)
                )
            )

            #send_row = max(
            #    b110_rows,
            #    key=lambda r: (
            #        to_int(r.completed_qty or r.total_completed_qty or r.allOk_qty),
            #        to_int(r.id)
            #    )
            #)
            #
            send_row = max(
                b110_rows,
                key=lambda r: (
                    get_b110_done_qty(r),
                    to_int(r.id)
                )
            )

            #send_completed = to_int(
            #    send_row.completed_qty
            #    or send_row.total_completed_qty
            #    or send_row.allOk_qty
            #)
            #
            send_completed = get_b110_done_qty(
                send_row
            )

            remain_qty = max(send_completed - min_qty, 0)

            #
            print(
                "[B110 FULL END QTY]",
                {
                    "material_id": material_id,
                    "assemble_id": assemble_record.id,
                    "release_batch_no": current_batch_no,
                    "previous_total_before_finish":
                        previous_total_before_finish,
                    "current_done_qty":
                        current_done_qty,
                    "current_total_qty":
                        current_total_qty,
                    "rows": [
                        {
                            "id": r.id,
                            "completed_qty":
                                to_int(r.completed_qty),
                            "total_completed_qty":
                                to_int(r.total_completed_qty),
                            "allOk_qty":
                                to_int(r.allOk_qty),
                            "effective_done_qty":
                                get_b110_done_qty(r),
                        }
                        for r in b110_rows
                    ],
                    "min_qty": min_qty,
                    "send_completed": send_completed,
                    "remain_qty": remain_qty,
                }
            )
            #

            # --------------------------------------------------------
            # 若此 material 還有異常返工流程，代表 B110 的差額
            # 已經由 B109異常返工 -> B110異常返工 處理。
            #
            # 此時正常 B110 收尾不可再建立 B110_DONE_COPY，
            # 否則 End 會多顯示：
            #   B110(檢驗)[檢驗] 已完成資料
            # --------------------------------------------------------
            #has_abnormal_rework_flow = (
            #    s.query(Assemble.id)
            #    .filter(Assemble.material_id == material_id)
            #    .filter(Assemble.reason == '異常返工')
            #    .filter(Assemble.isWarehouseStationShow.is_(False))
            #    .first()
            #    is not None
            #)

            has_abnormal_rework_flow = (
                s.query(Assemble.id)
                .filter(Assemble.material_id == material_id)
                .filter(Assemble.reason == '異常返工')
                .filter(Assemble.isWarehouseStationShow.is_(False))
                .filter(Assemble.show2_ok.notin_([9, 10]))
                .first()
                is not None
            )

            if has_abnormal_rework_flow:
                remain_qty = 0
                send_completed = min_qty   # ⭐ 正常良品只送 30，不是 35

            for r in b110_rows:
                r.isAssembleStationShow = False
                r.isWarehouseStationShow = False

                r.input_disable = True
                r.input_end_disable = True
                r.input_abnormal_disable = True
                r.input_allOk_disable = True

                r.currentStartTime = None
                r.currentEndTime = None

                r.show1_ok = 1
                r.show2_ok = 7
                r.show3_ok = 7

            #
            send_row.isAssembleStationShow = True
            send_row.isWarehouseStationShow = False
            send_row.process_step_code = 0
            send_row.show2_ok = 9
            #

            '''
            send_row.process_step_code = 0
            send_row.completed_qty = send_completed
            send_row.total_completed_qty = min_qty
            send_row.allOk_qty = min_qty
            #send_row.must_receive_end_qty = remain_qty
            # 待送出列的應完成總數量要顯示本批完成量
            # 不可以用 remain_qty，否則完整完成 20/20 時會變 0
            send_row.must_receive_end_qty = min_qty
            '''
            #
            send_row.process_step_code = 0

            # 待送出列的本批完成數量與累計量都固定為共同完成量
            send_row.completed_qty = min_qty
            send_row.total_completed_qty = min_qty
            send_row.allOk_qty = min_qty

            send_row.must_receive_qty = min_qty
            send_row.ask_qty = min_qty
            send_row.total_ask_qty = min_qty
            send_row.must_receive_end_qty = min_qty
            #

            send_row.isAssembleStationShow = True
            send_row.isWarehouseStationShow = False

            send_row.input_disable = True
            send_row.input_end_disable = True
            send_row.input_abnormal_disable = True
            send_row.input_allOk_disable = False

            send_row.show1_ok = 1
            send_row.show2_ok = 9
            send_row.show3_ok = 9

            #
            # 只有「同批內有差額」才需要建立 B110_DONE_COPY
            # 例如 b1=20、b2=15，才需要保留差額 5
            # 若 b1=20、b2=20，remain_qty=0，不可建立，否則 Begin 會多出錯誤資料
            if remain_qty > 0:
                done_copy = Assemble(
                    material_id=send_row.material_id,
                    material_num=send_row.material_num,
                    material_comment=send_row.material_comment,
                    seq_num=send_row.seq_num,
                    work_num=send_row.work_num,
                    process_step_code=0,

                    Incoming1_Abnormal=getattr(send_row, 'Incoming1_Abnormal', '') or '',

                    total_ask_qty_end=0,

                    must_receive_qty=send_completed,
                    ask_qty=send_completed,
                    total_ask_qty=send_completed,
                    must_receive_end_qty=send_completed,

                    abnormal_qty=0,
                    user_id=send_row.user_id,
                    writer_id=send_row.writer_id,
                    write_date=send_row.write_date,

                    good_qty=0,
                    total_good_qty=0,
                    non_good_qty=0,
                    meinh_qty=0,

                    completed_qty=remain_qty,
                    total_completed_qty=min_qty,
                    allOk_qty=min_qty,

                    reason='B110_DONE_COPY',
                    confirm_comment='',
                    is_assemble_ok=0,

                    currentStartTime=None,
                    currentEndTime=send_row.currentEndTime,

                    input_disable=True,
                    input_end_disable=True,
                    input_allOk_disable=True,
                    input_abnormal_disable=True,

                    isAssembleStationShow=True,
                    isWarehouseStationShow=False,

                    alarm_enable=True,
                    alarm_message='',
                    isAssembleFirstAlarm=True,
                    isAssembleFirstAlarm_message='',
                    isAssembleFirstAlarm_qty=0,

                    whichStation=send_row.whichStation,
                    show1_ok=1,
                    show2_ok=5,
                    show3_ok=5,

                    schedule_id=send_row.schedule_id,
                    is_copied_from_id=send_row.id,
                    release_batch_no=current_batch_no,
                )

                s.add(done_copy)

            if (
                waiting_row
                and to_int(waiting_row.id) != to_int(send_row.id)
                and remain_qty > 0
            ):
                waiting_row.process_step_code = 2
                waiting_row.must_receive_qty = remain_qty
                waiting_row.ask_qty = remain_qty
                waiting_row.must_receive_end_qty = remain_qty

                waiting_row.completed_qty = 0
                waiting_row.total_completed_qty = min_qty
                waiting_row.allOk_qty = min_qty

                waiting_row.isAssembleStationShow = True
                waiting_row.isWarehouseStationShow = False

                waiting_row.input_disable = False
                waiting_row.input_end_disable = False
                waiting_row.input_abnormal_disable = False
                waiting_row.input_allOk_disable = True

                waiting_row.currentStartTime = None
                waiting_row.currentEndTime = None

                waiting_row.show1_ok = 1
                waiting_row.show2_ok = 5
                waiting_row.show3_ok = 5

            material_record.isAssembleStationShow = True
            material_record.isAssembleStation3TakeOk = False
            material_record.whichStation = 2
            material_record.show1_ok = 3
            material_record.show2_ok = 9
            material_record.show3_ok = 9
            material_record.assemble_qty = min_qty
            material_record.total_assemble_qty = min_qty

            release_material_lock(material_record)

            s.commit()

            return jsonify({
                "status": True,
                "material_done": False,
                "waiting_send": True,
                "release_batch_no": current_batch_no,
                "current_assemble_id": send_row.id,
                "done_copy_created": True,
                "min_completed_qty": min_qty,
                "remain_qty": remain_qty,
                "message": "B110 batch waiting send plus finished copy"
            }), 200

        # end if B110 FULL END

        material_record.isAssembleStation3TakeOk = False

        s.commit()

        return jsonify({
            "status": False,
            "material_done": False,
            "released_next_group": False,
            "message": "no state changed"
        }), 200

    except Exception as e:
        s.rollback()
        print("updateAssembleProcessStep error:", e)
        traceback.print_exc()
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:
        s.close()


# 20260722版
@updateTable.route('/sendAssembleToWarehouse', methods=['POST'])
def send_assemble_to_warehouse():
    print("sendAssembleToWarehouse...")

    data = request.get_json(silent=True) or {}

    material_id = data.get("id") or data.get("material_id")
    assemble_id = data.get("assemble_id")
    mode = str(data.get("mode") or "").strip().lower()

    if mode not in ("agv", "forklift"):
        return jsonify({
            "status": False,
            "message": "缺少或錯誤的搬運方式，mode 必須為 agv 或 forklift"
        }), 400

    if not material_id:
        return jsonify({
            "status": False,
            "message": "missing material_id"
        }), 400

    def safe_int(value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


    def get_effective_done_qty(row):
        return max(
            safe_int(row.total_completed_qty),
            safe_int(row.allOk_qty),
            safe_int(row.completed_qty),
            safe_int(row.total_ask_qty),
            safe_int(row.must_receive_qty),
            0,
        )

    try:
        material_id = int(material_id)
    except (TypeError, ValueError):
        return jsonify({
            "status": False,
            "message": "material_id 格式錯誤"
        }), 400

    if assemble_id not in (None, ''):
        try:
            assemble_id = int(assemble_id)
        except (TypeError, ValueError):
            return jsonify({
                "status": False,
                "message": "assemble_id 格式錯誤"
            }), 400
    else:
        assemble_id = None

    s = Session()
    try:
        # ------------------------------------------------------------
        # 1. 鎖定 material
        # ------------------------------------------------------------
        material = (
            s.query(Material)
            .filter(Material.id == material_id)
            .with_for_update()
            .first()
        )

        if not material:
            return jsonify({
                "status": False,
                "message": "找不到 material"
            }), 404

        # ------------------------------------------------------------
        # 2. 若前端傳 assemble_id，先找指定列
        # ------------------------------------------------------------
        target = None
        current_batch_no = 0

        if assemble_id is not None:
            target = (s.query(Assemble)
                .filter(Assemble.id == assemble_id, Assemble.material_id == material_id)
                .with_for_update()
                .first()
            )

            if not target:
                return jsonify({
                    "status": False,
                    "message": "找不到指定的 assemble 完成資料"
                }), 200

            current_batch_no = to_int(getattr(target, "release_batch_no", 0))

        # ------------------------------------------------------------
        # 3. 共用的「可送出」條件
        #
        # B109-only：
        #   work_num=B109、process_step_code=0，也可直接送出
        #
        # B110：
        #   若有 release_batch_no，僅送同一批 B110
        # ------------------------------------------------------------
        common_filters = [
            Assemble.material_id == material_id,
            Assemble.process_step_code == 0,
            Assemble.show2_ok.in_([9, 10]),
            Assemble.completed_qty > 0,
            #or_(
            #    Assemble.reason.is_(None),
            #    Assemble.reason != 'B110_DONE_COPY'
            #)
            or_(
                Assemble.reason.is_(None),
                Assemble.reason == '',
                Assemble.reason.notin_(['B110_DONE_COPY'])
            )
        ]

        targets = []

        if target:
            # --------------------------------------------------------
            # 3-1. 指定的是 B110：送同 release_batch_no 的 B110 群組
            # --------------------------------------------------------
            if (
                str(target.work_num or '').strip() == 'B110'
                and current_batch_no > 0
            ):
                targets = (
                    s.query(Assemble)
                    .filter(*common_filters)
                    .filter(Assemble.work_num == 'B110')
                    .filter(
                        Assemble.release_batch_no == current_batch_no
                    )
                    .order_by(Assemble.id.asc())
                    .with_for_update()
                    .all()
                )

            # --------------------------------------------------------
            # 3-2. 指定的是 B109-only，或舊資料 batch_no=0：
            #      只能送指定的完成列，不可無條件送 target
            # --------------------------------------------------------
            else:
                valid_target = (
                    s.query(Assemble)
                    .filter(*common_filters)
                    .filter(Assemble.id == target.id)
                    .with_for_update()
                    .first()
                )

                if valid_target:
                    targets = [valid_target]

        # ------------------------------------------------------------
        # 3-3. 前端沒有傳 assemble_id：
        #      取得該 material 所有符合條件的完成列
        # ------------------------------------------------------------
        else:
            targets = (
                s.query(Assemble)
                .filter(*common_filters)
                .order_by(Assemble.id.asc())
                .with_for_update()
                .all()
            )

        if not targets:
            return jsonify({
                "status": False,
                "message": "沒有可送出的組裝完成資料"
            }), 200

        # ------------------------------------------------------------
        # 4. 防止已在 Warehouse 的資料被重複送出
        # ------------------------------------------------------------
        pending_targets = [
            row for row in targets
            if not bool(row.isWarehouseStationShow)
        ]

        if not pending_targets:
            return jsonify({
                "status": False,
                "message": "此批資料已送至 Warehouse，請勿重複送出",
                "material_id": material.id,
                "assemble_ids": [row.id for row in targets]
            }), 200

        #
        # ------------------------------------------------------------
        # 5-0. 計算本次實際可送至 Warehouse 的完成數量
        #
        # 注意：
        # 不能只取前端指定 target 的 completed_qty。
        #
        # 例如：
        # 組立第一次完成50，第二位員工再完成22，
        # 最終整張工單實際完成量應為72，而不是50或22。
        # ------------------------------------------------------------
        completed_source_rows = (
            s.query(Assemble)
            .filter(
                Assemble.material_id == material_id,

                # 已經完成的工序或待送出列
                or_(
                    Assemble.process_step_code == 0,
                    Assemble.total_completed_qty > 0,
                    Assemble.completed_qty > 0,
                    Assemble.allOk_qty > 0,
                ),

                # 排除純歷史複製列
                or_(
                    Assemble.reason.is_(None),
                    Assemble.reason == '',
                    Assemble.reason != 'B110_DONE_COPY'
                )
            )
            .with_for_update()
            .all()
        )

        source_qty_list = []

        for source_row in completed_source_rows:
            source_qty_list.append(
                get_effective_done_qty(source_row)
            )

        material_delivery_qty = safe_int(
            material.delivery_qty
        )

        material_assemble_qty = safe_int(
            material.assemble_qty
        )

        material_total_assemble_qty = safe_int(
            material.total_assemble_qty
        )

        effective_completed_qty = max(
            source_qty_list + [
                material_delivery_qty,
                material_assemble_qty,
                material_total_assemble_qty,
                0,
            ]
        )

        # 不可超過應完成數量
        if material_delivery_qty > 0:
            effective_completed_qty = min(
                effective_completed_qty,
                material_delivery_qty
            )

        print(
            '[sendAssembleToWarehouse] effective qty:',
            {
                'material_id': material_id,
                'order_num': material.order_num,
                'delivery_qty': material_delivery_qty,
                'effective_completed_qty':
                    effective_completed_qty,
                'source_qty_list':
                    source_qty_list,
            }
        )
        #

        # ------------------------------------------------------------
        # 5. 執行送出
        #
        # 重要：
        # move_assemble_to_warehouse() 必須接收 mode，
        # 由 mode 決定只建立 AGV 或只建立堆高機資料。
        # ------------------------------------------------------------
        results = []

        for index, row in enumerate(pending_targets):
            result = move_assemble_to_warehouse(
                session=s,
                material_record=material,
                assemble_record=row,
                mode=mode,

                operator_user=(
                    data.get("user_id")
                    or data.get("emp_id")
                ),

                agv_wait_user='AGV2-1',
                agv_run_user='AGV2-2',

                # 同一 material 若有多筆 assemble，
                # 只有第一筆負責清理搬運 placeholder
                handle_transport=(index == 0)
            )

            results.append(result)

        # ------------------------------------------------------------
        # 6. 確保完成列正式進入 Warehouse
        #
        # move_assemble_to_warehouse() 負責搬運相關處理；
        # 這裡負責最後一致化 material / assemble 狀態。
        # ------------------------------------------------------------
        #now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        now_str = DateTime.now().strftime("%Y-%m-%d %H:%M:%S")

        for row in pending_targets:
            work_num = str(row.work_num or '').strip()

            reason = str(row.reason or '').strip()

            # --------------------------------------------------------
            # B109-only 或直接待送出列：
            # 數量必須同步成整張工單實際完成量。
            #
            # B110 批次列不要強制改成整張工單總量，
            # 否則分批72件可能每一批都被改成72。
            # --------------------------------------------------------
            is_direct_b109 = (work_num == 'B109' or reason == 'B109_DIRECT_WAIT_SEND')

            if is_direct_b109:
                row.must_receive_qty = effective_completed_qty

                row.ask_qty = effective_completed_qty

                row.total_ask_qty = (
                    effective_completed_qty
                )

                row.must_receive_end_qty = (
                    effective_completed_qty
                )

                row.completed_qty = (
                    effective_completed_qty
                )

                row.total_completed_qty = (
                    effective_completed_qty
                )

                row.allOk_qty = (
                    effective_completed_qty
                )

            # --------------------------------------------------------
            # B110 批次列：
            # 保留該批次原本數量，只修正明顯為0的欄位。
            # --------------------------------------------------------
            else:
                row_effective_qty = (
                    get_effective_done_qty(row)
                )

                if row_effective_qty <= 0:
                    row_effective_qty = (
                        effective_completed_qty
                    )

                if safe_int(row.completed_qty) <= 0:
                    row.completed_qty = (
                        row_effective_qty
                    )

                if (
                    safe_int(
                        row.total_completed_qty
                    )
                    <= 0
                ):
                    row.total_completed_qty = (
                        row_effective_qty
                    )

                if safe_int(row.allOk_qty) <= 0:
                    row.allOk_qty = (
                        row_effective_qty
                    )

            # --------------------------------------------------------
            # Warehouse 顯示狀態
            # --------------------------------------------------------
            row.process_step_code = 0

            row.isAssembleStationShow = False
            row.isWarehouseStationShow = True

            row.whichStation = 3

            row.show1_ok = 3
            row.show2_ok = 10
            row.show3_ok = 10

            row.input_disable = True
            row.input_end_disable = True
            row.input_abnormal_disable = True

            # Warehouse 頁面仍需輸入/確認入庫數量時，
            # input_allOk_disable 必須為 False
            row.input_allOk_disable = False

            row.update_time = now_str


        # ------------------------------------------------------------
        # 7. material 正式抵達成品區，等待入庫
        # ------------------------------------------------------------
        material.isAssembleStationShow = False
        material.isAssembleStation3TakeOk = True

        material.whichStation = 3

        material.show1_ok = 3
        material.show2_ok = 10
        material.show3_ok = 11

        # 同步實際完成數量
        material.assemble_qty = (
            effective_completed_qty
        )

        material.total_assemble_qty = (
            effective_completed_qty
        )

        material.must_allOk_qty = (
            effective_completed_qty
        )

        # 注意：
        # 此時還只是等待入庫，
        # 不可設定 material.total_allOk_qty
        # 也不可設定 material.isAllOk=True

        # 釋放 Begin / End 操作鎖
        material.isOpen = False
        material.isOpenEmpId = ''
        material.hasStarted = False
        material.startStatus = 1

        material.update_time = now_str
        #

        s.commit()

        return jsonify({
            "status": True,
            "message": (
                "已呼叫 AGV 送往成品區"
                if mode == "agv"
                else "已呼叫堆高機送往成品區"
            ),
            "mode": mode,
            "material_id": material.id,
            "order_num": material.order_num,
            "assemble_ids": [row.id for row in pending_targets],
            "count": len(pending_targets),
            "data": results
        }), 200

    except Exception as e:
        s.rollback()
        print("sendAssembleToWarehouse error:", e)

        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:
        s.close()


@updateTable.route('/sendProcessToWarehouse', methods=['POST'])
def send_process_to_warehouse():
    print("sendProcessToWarehouse.")

    data = request.get_json(silent=True) or {}
    material_id = data.get('id')
    assemble_id = data.get('assemble_id')
    mode = data.get('mode', 'manual')

    if not material_id or not assemble_id:
        return jsonify({
            "status": False,
            "message": "缺少 id 或 assemble_id"
        }), 400

    s = Session()
    try:
        material = s.query(P_Material).filter(P_Material.id == material_id).first()
        row = (
            s.query(P_Assemble)
             .filter(P_Assemble.id == assemble_id)
             .filter(P_Assemble.material_id == material_id)
             .first()
        )

        if not material or not row:
            return jsonify({
                "status": False,
                "message": "找不到 P_Material 或 P_Assemble"
            }), 404

        # 同一張加工工單只保留一筆進 Ware
        s.query(P_Assemble).filter(
            P_Assemble.material_id == material_id
        ).update({
            P_Assemble.isWarehouseStationShow: False
        }, synchronize_session=False)

        row.isAssembleStationShow = False
        row.isWarehouseStationShow = True
        row.isStockIn = True

        material.move_by_automatic_or_manual_2 = True if mode == 'agv' else False
        material.whichStation = 3
        material.show2_ok = 6   # 等待入庫作業
        material.show3_ok = 11  # 等待入庫作業 / 成品區

        s.commit()

        return jsonify({
            "status": True,
            "message": "加工件已送到成品區，可在 Ware~.vue 顯示"
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:
        s.close()


@updateTable.route("/updateModifyMaterialAndBoms", methods=['POST'])
def update_modify_material_and_Boms():
  print("updateModifyMaterialAndBoms....")

  data = request.json
  _id = data.get("id")
  _date = data.get("date")
  _qty = data.get("qty")
  #_fileName = data.get("file_name")
  #_bom_data = data.get("bom_data", [])
  #print("bom_data:", _bom_data)

  return_value = True

  update_data = {}
  if _date is not None:
      update_data["material_delivery_date"] = _date #訂單日期
  if _qty is not None:
      update_data["material_qty"] = _qty            #需求數量(訂單數量)
      update_data["total_delivery_qty"] = _qty      #應備數量
  s = Session()

  if update_data:
    rows_updated = s.query(Material).filter(Material.id == _id).update(update_data)

  if rows_updated == 0:
    return_value = False
    raise ValueError("Update failed: no rows affected")

  s.commit()
  '''
  # 取得現有的 BOM 資料
  existing_bom = s.query(Bom).filter_by(material_id = _id).all()
  existing_materials = {bom.material_num for bom in existing_bom}

  for bom_entry in _bom_data:
    material_num = bom_entry.get("material_num")
    if material_num not in existing_materials:
      print("bom_entry:",bom_entry)
      new_bom = Bom(
        material_id = _id,
        material_num = material_num,
        seq_num = bom_entry.get("seq_num"),
        material_comment = bom_entry.get("mtl_comment"),
        req_qty = bom_entry.get("qty"),
        start_date = _date
      )
      s.add(new_bom)

  s.commit()
  '''
  s.close()
  '''
  # 在程式的移動檔案邏輯中使用
  try:
    if return_value:
      _base_dir = current_app.config['baseDir']
      _modify_dir = _base_dir.replace("_in", "_modify")
      _target_dir = _base_dir.replace("_in", "_out")
      _path = _modify_dir + '\\' + _fileName
      print("file_name:", _fileName)

      unique_filename = get_unique_filename(_target_dir, _fileName, "mdf")  # 生成唯一檔案名稱
      unique_target_path = os.path.join(_target_dir, unique_filename)  # 獲取完整目標路徑
      shutil.move(_path, unique_target_path)  # 移動檔案到目標路徑
      print(f"檔案 {_path} 已成功移動到 {unique_target_path}")
  except PermissionError as e:
    print(f"無法移動文件 {_path}，因為它仍然被佔用: {e}")
  except Exception as e:
    print(f"移動檔案時發生錯誤: {e}")
'''
  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateModifyMaterialAndBomsP", methods=['POST'])
def update_modify_material_and_Boms_p():
  print("updateModifyMaterialAndBoms....")

  data = request.json
  _id = data.get("id")
  _date = data.get("date")
  _qty = data.get("qty")

  return_value = True

  update_data = {}
  if _date is not None:
      update_data["material_delivery_date"] = _date   #訂單日期
  if _qty is not None:
      update_data["material_qty"] = _qty              #需求數量(訂單數量)
      update_data["total_delivery_qty"] = _qty        #應備數量

  s = Session()

  if update_data:
    rows_updated = s.query(P_Material).filter(P_Material.id == _id).update(update_data)

  if rows_updated == 0:
    return_value = False
    raise ValueError("Update failed: no rows affected")

  s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateAssmbleDataByMaterialID", methods=['POST'])
def update_assemble_data_by_material_id():
  print("updateAssmbleDataByMaterialID....")

  request_data = request.get_json()

  _material_id = request_data.get('material_id')
  _delivery_qty = request_data.get('delivery_qty')
  _record_name1 = request_data.get('record_name1')
  _record_data1 = request_data.get('record_data1')
  _record_name2 = request_data.get('record_name2')
  _record_data2 = request_data.get('record_data2')
  _record_name3 = request_data.get('record_name3')
  _record_data3 = request_data.get('record_data3')
  _record_name4 = request_data.get('record_name4')
  _record_data4 = request_data.get('record_data4')

  #return_value = True  # true: 資料正確,
  s = Session()

  try:
      # 查詢所有符合條件的紀錄
      #assemble_records = s.query(Assemble).filter(
      #    Assemble.material_id == _material_id,
      #    Assemble.must_receive_qty == _delivery_qty
      #).all()
      #
      assemble_records = (
          s.query(Assemble)
          .filter(Assemble.material_id == _material_id)
          .filter(Assemble.isWarehouseStationShow.is_(False))
          .filter(
              or_(
                  Assemble.reason.is_(None),
                  Assemble.reason != 'B110_DONE_COPY'
              )
          )
          .all()
      )
      #

      # 動態設定欄位
      for asm in assemble_records:
        if _record_name1 and _record_data1 is not None:
          setattr(asm, _record_name1, _record_data1)
        if _record_name2 and _record_data2 is not None:
          setattr(asm, _record_name2, _record_data2)
        if _record_name3 and _record_data3 is not None:
          setattr(asm, _record_name3, _record_data3)
        if _record_name4 and _record_data4 is not None:
          setattr(asm, _record_name4, _record_data4)

      # 提交更新
      s.commit()
      print(f"更新成功，共 {len(assemble_records)} 筆資料")
      return_value = True
      #return
  except Exception as e:
      s.rollback()
      print("更新失敗:", str(e))
      return_value = False
      #return

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateAssmbleDataByMaterialIDP", methods=['POST'])
def update_assemble_data_by_material_id_p():
  print("updateAssmbleDataByMaterialIDP....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _material_id = request_data.get('material_id')
  _delivery_qty = request_data.get('delivery_qty')
  _record_name1 = request_data.get('record_name1')
  _record_data1 = request_data.get('record_data1')
  _record_name2 = request_data.get('record_name2')
  _record_data2 = request_data.get('record_data2')
  _record_name3 = request_data.get('record_name3')
  _record_data3 = request_data.get('record_data3')
  _record_name4 = request_data.get('record_name4')
  _record_data4 = request_data.get('record_data4')

  #return_value = True  # true: 資料正確,
  s = Session()

  try:
      # 查詢所有符合條件的紀錄
      assemble_records = s.query(P_Assemble).filter(
          P_Assemble.material_id == _material_id,
          P_Assemble.must_receive_qty == _delivery_qty
      ).all()

      # 動態設定欄位
      for asm in assemble_records:
        if _record_name1 and _record_data1 is not None:
          setattr(asm, _record_name1, _record_data1)
        if _record_name2 and _record_data2 is not None:
          setattr(asm, _record_name2, _record_data2)
        if _record_name3 and _record_data3 is not None:
          setattr(asm, _record_name3, _record_data3)
        if _record_name4 and _record_data4 is not None:
          setattr(asm, _record_name4, _record_data4)

      # 提交更新
      s.commit()
      print(f"更新P_Assemble table成功，共 {len(assemble_records)} 筆資料")
      return_value = True
      #return
  except Exception as e:
      s.rollback()
      print("更新P_Assemble table失敗:", str(e))
      return_value = False
      #return

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateProcessDataByMaterialID", methods=['POST'])
def update_process_data_by_material_id():
  print("updateProcessDataByMaterialID....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _material_id = request_data.get('material_id')
  _seq = request_data.get('seq')
  _record_name1 = request_data.get('record_name1')
  _record_data1 = request_data.get('record_data1')
  #print("material_id, seq, record_name1, record_data1:", _material_id, _seq, _record_name1, _record_data1)

  s = Session()

  try:
    material = s.query(Material).get(_material_id)
    #print("step1")
    if not material:
      return jsonify({'status': False, 'msg': 'Material not found'})
    #print("step2")

    target_process = (s.query(Process).filter(
      Process.material_id == _material_id,
      Process.assemble_id == 0,
      Process.has_started == True,
      Process.begin_time != '',
      Process.end_time != '',)
      .first())

    # 確保 _seq 不超過範圍
    #if _seq < 0 or _seq > len(material._process):
    if not target_process:
      return jsonify({'status': False, 'msg': 'seq out of range'})

    #print("step3")

    # 更新欄位
    if _record_name1 and _record_data1 is not None:
      setattr(target_process, _record_name1, _record_data1)
    #print("step4")

    # 提交更新
    s.commit()
    #print("target_process:", target_process)
    print(f"更新成功!")
    return_value = True
  except Exception as e:
    s.rollback()
    print("更新失敗:", str(e))
    return_value = False

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateProcessDataByMaterialIDP", methods=['POST'])
def update_process_data_by_material_id_p():
  print("updateProcessDataByMaterialIDP....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _material_id = request_data.get('material_id')
  _seq = request_data.get('seq')
  _record_name1 = request_data.get('record_name1')
  _record_data1 = request_data.get('record_data1')
  #print("material_id, seq, record_name1, record_data1:", _material_id, _seq, _record_name1, _record_data1)

  s = Session()

  try:
      material = s.query(P_Material).get(_material_id)
      #print("step1")
      if not material:
        return jsonify({'status': False, 'msg': 'Material not found'})
      #print("step2")

      target_process = (s.query(P_Process).filter(
                P_Process.material_id == _material_id,
                P_Process.assemble_id == 0,
                P_Process.has_started == True,
                P_Process.begin_time != '',
                P_Process.end_time != '',)
                .first())

      # 確保 _seq 不超過範圍
      #temp_len = len(material._process)
      #if _seq < 0 or _seq > temp_len:
      if not target_process:
        #print("step2-0 ")
        return jsonify({'status': False, 'msg': 'seq out of range'})

      #print("step3")

      # 取出對應的 Process
      #target_process = material._process[_seq-1]
      print("target_process:", target_process)
      # 更新欄位
      if _record_name1 and _record_data1 is not None:
        setattr(target_process, _record_name1, _record_data1)
      #print("step4")

      s.commit()

      print("target_process:", target_process)
      print(f"更新成功!")
      return_value = True
  except Exception as e:
      s.rollback()
      print("更新失敗:", str(e))
      return_value = False

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateAssembleMustReceiveQtyByAssembleID", methods=['POST'])
def update_assemble_must_receive_qty_by_assemble_id():
    print("updateAssembleMustReceiveQtyByAssembleID....")

    request_data = request.get_json()
    _id = request_data.get('assemble_id')
    #_must_receive_qty = request_data['must_receive_qty']
    #_completed_qty = request_data['completed_qty']

    return_value = True  # true: 資料正確,
    s = Session()

    # 1. 先找出該筆資料
    target = s.query(Assemble).filter(Assemble.id == _id).first()

    if not target:
      print(f"找不到 id={ _id } 的資料")
      return_value = False
      return

    material_id = target.material_id
    must_receive_qty = target.must_receive_qty

    # 2. 查找符合條件的其他資料
    matching_records = s.query(Assemble).filter(
      Assemble.material_id == material_id,
      Assemble.must_receive_qty == must_receive_qty,
      Assemble.process_step_code != 0
    ).all()

    print(f"符合條件的筆數: { len(matching_records) }")

    # 3. 更新符合條件的 must_receive_qty
    for record in matching_records:
      print(f"更新 id={ record.id } 的 must_receive_qty: { record.must_receive_qty } -> { target.completed_qty }")
      record.must_receive_qty = target.completed_qty

    s.commit()

    print("更新完成")

    return jsonify({
      'status': return_value
    })


@updateTable.route("/updateAssembleMustReceiveQtyByMaterialID", methods=['POST'])
def update_assembleMustReceiveQty_by_MaterialID():
  print("updateAssembleMustReceiveQtyByMaterialID....")

  request_data = request.get_json()

  _material_id = request_data.get('material_id')
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']

  return_value = True  # true: 資料正確,
  s = Session()

  # 確認 record_name 是 Assemble 的合法欄位
  valid_columns = [c.key for c in inspect(Assemble).mapper.column_attrs]
  if _record_name not in valid_columns:
    return_value = False
    raise ValueError(f"'{ _record_name }' 不是 Assemble 表中的合法欄位")

  # 查詢所有 material_id 相符的 Assemble 記錄
  assemble_records = s.query(Assemble).filter_by(material_id = _material_id).all()
  '''
  assemble_records = (s.query(Assemble).filter(and_(
            Assemble.material_id == _material_id,
            Assemble.must_receive_qty == 0
        )
    )
    .all()
  )
  '''
  if not assemble_records:
    return_value = False
    raise ValueError(f"No Assemble records found for material_id { _material_id }")

  updated_ids = []
  for record in assemble_records:
    setattr(record, _record_name, _record_data)  # 動態設欄位
    updated_ids.append(record.id)

  s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateAssembleMustReceiveQtyByMaterialIDAndDate", methods=['POST'])
def update_assembleMustReceiveQty_by_materialID_and_date():
    print("updateAssembleMustReceiveQtyByMaterialIDAndDate....")

    request_data = request.get_json() or {}

    _material_id   = request_data.get('material_id')
    _assemble_id   = request_data.get('assemble_id')   # ✅ 新增
    _raw_create_at = request_data.get('create_at')
    _record_name   = request_data.get('record_name')
    _record_data   = request_data.get('record_data')

    return_value = True
    s = Session()

    try:
        valid_columns = [c.key for c in inspect(Assemble).mapper.column_attrs]
        if _record_name not in valid_columns:
            return jsonify({
                'status': False,
                'msg': f'{_record_name} 不是 Assemble 合法欄位'
            })

        query = s.query(Assemble).filter(Assemble.material_id == _material_id)

        # ✅ 有 assemble_id 時，只更新單筆，避免 3378 的 50 被 3377 的 950 蓋掉
        if _assemble_id is not None and _assemble_id != '':
            query = query.filter(Assemble.id == _assemble_id)

        # ✅ 沒 assemble_id 才走舊邏輯：material_id + create_at
        else:
            if _raw_create_at is None:
                return jsonify({
                    'status': False,
                    'msg': '缺少 assemble_id 或 create_at'
                })

            target_create_at = normalize_create_at(_raw_create_at)
            query = query.filter(Assemble.create_at == target_create_at)

        assemble_records = query.all()

        if not assemble_records:
            return jsonify({
                'status': False,
                'msg': f'No Assemble records found, material_id={_material_id}, assemble_id={_assemble_id}, create_at={_raw_create_at}'
            })

        updated_ids = []

        for record in assemble_records:
            setattr(record, _record_name, _record_data)
            updated_ids.append(record.id)

        print("updated assemble ids:", updated_ids)

        s.commit()

        return jsonify({
            'status': True,
            'updated_ids': updated_ids
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        print("update_assembleMustReceiveQty_by_materialID_and_date error:", e)
        return jsonify({
            'status': False,
            'msg': str(e)
        })

    finally:
        s.close()


@updateTable.route("/updateAssembleMustReceiveQtyByMaterialIDAndDateP", methods=['POST'])
def update_assembleMustReceiveQty_by_materialID_and_date_p():
    print("updateAssembleMustReceiveQtyByMaterialIDAndDateP....")

    request_data = request.get_json() or {}

    _material_id   = request_data.get('material_id')
    _assemble_id   = request_data.get('assemble_id')   # ✅ 新增
    _raw_create_at = request_data.get('create_at')
    _record_name   = request_data.get('record_name')
    _record_data   = request_data.get('record_data')

    s = Session()

    try:
        valid_columns = [c.key for c in inspect(P_Assemble).mapper.column_attrs]
        if _record_name not in valid_columns:
            return jsonify({
                'status': False,
                'msg': f'{_record_name} 不是 P_Assemble 合法欄位'
            })

        query = s.query(P_Assemble).filter(P_Assemble.material_id == _material_id)

        # ✅ 有 assemble_id：只更新單筆 P_Assemble
        if _assemble_id is not None and _assemble_id != '':
            query = query.filter(P_Assemble.id == _assemble_id)

        # ✅ 沒 assemble_id：維持舊邏輯，更新同 material_id + create_at 那一批
        else:
            if _raw_create_at is None:
                return jsonify({
                    'status': False,
                    'msg': '缺少 assemble_id 或 create_at'
                })

            target_create_at = normalize_create_at(_raw_create_at)
            query = query.filter(P_Assemble.create_at == target_create_at)

        assemble_records = query.all()

        if not assemble_records:
            return jsonify({
                'status': False,
                'msg': f'No P_Assemble records found, material_id={_material_id}, assemble_id={_assemble_id}, create_at={_raw_create_at}'
            })

        updated_ids = []

        for record in assemble_records:
            setattr(record, _record_name, _record_data)
            updated_ids.append(record.id)

        print("updated p assemble ids:", updated_ids)

        s.commit()

        return jsonify({
            'status': True,
            'updated_ids': updated_ids
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        print("update_assembleMustReceiveQty_by_materialID_and_date_p error:", e)
        return jsonify({
            'status': False,
            'msg': str(e)
        })

    finally:
        s.close()


@updateTable.route("/updateMaterialFields", methods=['POST'])
def update_material_fields():
    data = request.get_json(silent=True) or {}
    mid = data.get("id")
    fields = data.get("fields") or {}
    if not mid or not isinstance(fields, dict) or not fields:
        return jsonify(success=False, message="id / fields 缺失"), 400

    # 允許更新哪些欄位（白名單）
    ALLOWED = {
        "isOpen", "isOpenEmpId", "hasStarted", "startStatus",
        # 需要的話把其他欄位加進來
    }
    BOOLS = {"isOpen", "hasStarted", "startStatus"}

    # 過濾＋型別歸一化
    patch = {}
    for k, v in fields.items():
        if k not in ALLOWED:
            continue
        if k in BOOLS:
            patch[k] = bool(v)
        else:
            patch[k] = v if v is not None else ""

    if not patch:
        return jsonify(success=False, message="無可更新欄位"), 400

    s = Session()
    try:
        # 行鎖避免併發踩踏
        mat = (
            s.query(Material)
             .filter(Material.id == mid)
             .with_for_update()
             .one_or_none()
        )
        if not mat:
            return jsonify(success=False, message="material not found"), 404

        for k, v in patch.items():
            setattr(mat, k, v)

        s.commit()
        return jsonify(success=True, id=mid, updated=patch)
    except Exception as e:
        s.rollback()
        print("update_material_fields failed:", e)  # 或用 logger
        return jsonify(success=False, message="internal error"), 500
    finally:
        s.close()


@updateTable.route("/updateAssembleScheduleRows", methods=['POST'])
def update_assemble_schedule_rows():
    print("updateAssembleScheduleRows....")

    request_data = request.get_json()
    material_id = request_data.get('id')
    process_steps = request_data.get('process_steps') or {}
    abnormal_qty = request_data.get('abnormal_qty', None)

    s = Session()

    try:
        material = s.query(Material).filter_by(id=material_id).first()

        if not material:
            return jsonify({'status': False, 'msg': 'material not found'})

        # -------------------------
        # 1️⃣ 更新 process_steps
        # -------------------------
        normalized_process_steps = {
            'assemble': [
                {
                    'id': int(x.get('id')) if x.get('id') is not None else None,
                    'name': x.get('name', ''),
                    'checked': bool(x.get('checked'))
                }
                for x in (process_steps.get('assemble') or [])
            ],
            'check': [
                {
                    'id': int(x.get('id')) if x.get('id') is not None else None,
                    'name': x.get('name', ''),
                    'checked': bool(x.get('checked'))
                }
                for x in (process_steps.get('check') or [])
            ]
        }

        #print("normalized_process_steps:", normalized_process_steps)

        material.process_steps = normalized_process_steps

        material.process_step_enable = True

        # -------------------------
        # 2️⃣ 同步 assemble rows
        # -------------------------
        # ✅ 有傳 abnormal_qty，而且不是空值，才帶 qty
        if abnormal_qty is not None and abnormal_qty != '':
            sync_assemble_schedule_rows(
                session=s,
                material_id=material_id,
                process_steps=normalized_process_steps,
                qty=abnormal_qty
            )
        else:
            sync_assemble_schedule_rows(
                session=s,
                material_id=material_id,
                process_steps=normalized_process_steps
            )

        #
        # 關鍵：sync 內有 delete copied rows，所以先 flush
        s.flush()

        # 關鍵：清掉 session 內舊的 Assemble ORM 狀態，避免 StaleDataError
        s.expire_all()

        # 重新抓 material，避免 expire_all 後物件狀態舊
        material = s.query(Material).filter(Material.id == material_id).first()
        if material:
            # material 重新 query 一次，因為 expire_all() 後原物件可能已過期。
            material.process_steps = normalized_process_steps
            material.process_step_enable = True
        #

        # -------------------------
        # 3️⃣ commit
        # -------------------------
        s.commit()

        return jsonify({
           'status': True,
           'process_steps': material.process_steps,
           'msg': 'ok!'
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        print("updateAssembleScheduleRows ERROR:", repr(e))
        return jsonify({
           'status': False,
           'msg': str(e),
        })
    finally:
        s.close()


def add_assemble_schedule_rows_by_abnormal(session, material_id, process_steps, qty):
    print("add_assemble_schedule_rows_by_abnormal....")
    print("material_id:", material_id)
    print("qty:", qty)

    material = session.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise Exception(f"material not found: {material_id}")

    try:
        target_qty = int(qty or 0)
    except Exception:
        target_qty = 0

    if target_qty <= 0:
        raise Exception("abnormal_qty must > 0")

    all_rows = (
        session.query(Assemble)
        .filter(Assemble.material_id == material_id)
        .all()
    )

    def get_any_template_row():
        # 優先找主列
        for row in all_rows:
            if row.is_copied_from_id is None:
                return row

        return all_rows[0] if all_rows else None

    def create_row_from_template(template, work_num, process_step_code, schedule_id, copied_from_id=None, reason_text=''):
        new_row = Assemble(
            material_id=material.id,
            material_num=material.material_num,
            material_comment=material.material_comment,
            seq_num=getattr(template, 'seq_num', 10) if template else 10,

            work_num=work_num,
            process_step_code=process_step_code,
            schedule_id=schedule_id,
            is_copied_from_id=copied_from_id,

            Incoming1_Abnormal=getattr(template, 'Incoming1_Abnormal', '') if template else '',

            # ✅ 異常返工數量
            must_receive_qty=target_qty,
            ask_qty=target_qty,
            total_ask_qty=target_qty,
            #total_ask_qty_end=0,
            must_receive_end_qty=target_qty,
            #reason=reason_text,

            #abnormal_qty=0,
            # 異常返工數量
            abnormal_qty=target_qty,

            user_id=getattr(template, 'user_id', material.isOpenEmpId) if template else material.isOpenEmpId,
            writer_id=None,
            write_date=None,

            good_qty=0,
            total_good_qty=0,
            non_good_qty=0,
            meinh_qty=0,

            completed_qty=0,
            total_completed_qty=0,
            allOk_qty=0,

            #reason='',
            #
            reason='異常返工',
            #
            confirm_comment='',
            is_assemble_ok=0,

            currentStartTime=None,
            currentEndTime=None,

            input_disable=1,
            input_end_disable=0,
            input_allOk_disable=0,
            input_abnormal_disable=0,

            isAssembleStationShow=getattr(template, 'isAssembleStationShow', 0) if template else 0,
            isWarehouseStationShow=getattr(template, 'isWarehouseStationShow', 0) if template else 0,

            alarm_enable=1,
            alarm_message='',

            isAssembleFirstAlarm=1,
            isAssembleFirstAlarm_message='',
            isAssembleFirstAlarm_qty=0,

            whichStation=getattr(template, 'whichStation', material.whichStation) if template else material.whichStation,
            show1_ok=getattr(template, 'show1_ok', material.show1_ok) if template else material.show1_ok,
            show2_ok=getattr(template, 'show2_ok', material.show2_ok) if template else material.show2_ok,
            show3_ok=getattr(template, 'show3_ok', material.show3_ok) if template else material.show3_ok,
        )

        session.add(new_row)
        session.flush()
        return new_row

    def add_group_rows(work_num, process_step_code, target_steps):
        checked_ids = [
            int(x.get('id'))
            for x in (target_steps or [])
            if x.get('checked') and x.get('id') is not None
        ]

        if not checked_ids:
            print(f"{work_num} no checked steps, skip")
            return []

        template = get_any_template_row()
        created_rows = []

        # 第一個 checked step 建主列
        base = create_row_from_template(
            template=template,
            work_num=work_num,
            process_step_code=process_step_code,
            schedule_id=checked_ids[0],
            copied_from_id=None,
            #target_qty=abnormal_qty,
            reason_text='異常返工',
        )

        created_rows.append(base)

        # 其餘 checked step 建 copied rows
        for sid in checked_ids[1:]:
            copied = create_row_from_template(
                template=base,
                work_num=work_num,
                process_step_code=process_step_code,
                schedule_id=sid,
                copied_from_id=base.id,
                reason_text='異常返工',
            )
            created_rows.append(copied)

        print(
            f"created abnormal schedule rows: "
            f"material_id={material_id}, work_num={work_num}, count={len(created_rows)}"
        )

        return created_rows

    created = []

    # B109 = 組裝
    created += add_group_rows(
        work_num='B109',
        process_step_code=3,
        target_steps=process_steps.get('assemble', [])
    )

    # B110 = 檢驗
    created += add_group_rows(
        work_num='B110',
        process_step_code=2,
        target_steps=process_steps.get('check', [])
    )

    return created


@updateTable.route("/addAssembleScheduleRows", methods=['POST'])
def add_assemble_schedule_rows():
    print("addAssembleScheduleRows....")

    request_data = request.get_json() or {}

    material_id = request_data.get('id')
    process_steps = request_data.get('process_steps') or {}
    abnormal_qty = request_data.get('abnormal_qty', None)

    s = Session()

    try:
        if not material_id:
            return jsonify({'status': False, 'msg': 'missing material id'})

        if abnormal_qty is None or abnormal_qty == '':
            return jsonify({'status': False, 'msg': 'missing abnormal_qty'})

        normalized_process_steps = {
            'assemble': [
                {
                    'id': int(x.get('id')) if x.get('id') is not None else None,
                    'name': x.get('name', ''),
                    'checked': bool(x.get('checked'))
                }
                for x in (process_steps.get('assemble') or [])
            ],
            'check': [
                {
                    'id': int(x.get('id')) if x.get('id') is not None else None,
                    'name': x.get('name', ''),
                    'checked': bool(x.get('checked'))
                }
                for x in (process_steps.get('check') or [])
            ]
        }

        #print("normalized_process_steps:", normalized_process_steps)
        #print("abnormal_qty:", abnormal_qty)

        created_rows = add_assemble_schedule_rows_by_abnormal(
            session=s,
            material_id=material_id,
            process_steps=normalized_process_steps,
            qty=abnormal_qty
        )

        s.commit()

        return jsonify({
            'status': True,
            'msg': 'add assemble schedule rows ok',
            'created_count': len(created_rows),
            'created_ids': [row.id for row in created_rows]
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        print("addAssembleScheduleRows ERROR:", repr(e))
        return jsonify({
            'status': False,
            'msg': str(e)
        })

    finally:
        s.close()


@updateTable.route("/updateAssembleFieldByAssembleID", methods=['POST'])
def update_assemble_field_by_assemble_id():
    print("updateAssembleFieldByAssembleID....")

    request_data = request.get_json() or {}
    assemble_id = request_data.get('assemble_id')
    record_name = request_data.get('record_name')
    record_data = request_data.get('record_data')

    if not assemble_id:
        return jsonify({'status': False, 'msg': 'missing assemble_id'})

    s = Session()

    try:
        valid_columns = [c.key for c in inspect(Assemble).mapper.column_attrs]
        if record_name not in valid_columns:
            return jsonify({
                'status': False,
                'msg': f'{record_name} 不是 Assemble 合法欄位'
            })

        asm = s.query(Assemble).filter(Assemble.id == assemble_id).first()
        if not asm:
            return jsonify({
                'status': False,
                'msg': f'assemble_id={assemble_id} not found'
            })

        setattr(asm, record_name, record_data)

        s.commit()

        return jsonify({
            'status': True,
            'assemble_id': assemble_id,
            'record_name': record_name,
            'record_data': record_data
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        return jsonify({'status': False, 'msg': str(e)})

    finally:
        s.close()


@updateTable.route("/updateMaterial", methods=['POST'])
def update_material():
    print("updateMaterial....")

    request_data = request.get_json() or {}

    _order_num = request_data.get('order_num')
    _id = request_data.get('id')
    _record_name = request_data.get('record_name')
    _record_data = request_data.get('record_data')

    s = Session()

    try:
        material_record = None

        if _id is not None:
            material_record = s.query(Material).filter_by(id=_id).first()
        elif _order_num is not None:
            material_record = s.query(Material).filter_by(order_num=_order_num).first()

        if material_record is None:
            return jsonify({'status': False, 'message': 'Material not found'})

        if not hasattr(material_record, _record_name):
            return jsonify({'status': False, 'message': f'欄位不存在: {_record_name}'})

        # boolean 欄位轉型
        if _record_name in ['process_step_enable', 'merge_enabled']:
            if isinstance(_record_data, str):
                v = _record_data.strip().lower()
                if v in ['1', 'true', 'yes', 'y', 'on']:
                    _record_data = True
                elif v in ['0', 'false', 'no', 'n', 'off', '']:
                    _record_data = False
            else:
                _record_data = bool(_record_data)

        setattr(material_record, _record_name, _record_data)

        s.commit()

        return jsonify({'status': True})

    except Exception as e:
        s.rollback()
        print("updateMaterial error:", e)
        return jsonify({'status': False, 'message': str(e)})

    finally:
        s.close()


@updateTable.route("/updateMaterialP", methods=['POST'])
def update_material_p():
    print("updateMaterialP....")

    request_data = request.get_json()

    _order_num = request_data.get('order_num')
    _id = request_data.get('id')
    _record_name = request_data['record_name']
    _record_data = request_data['record_data']

    return_value = True  # true: 資料正確, 註冊成功
    s = Session()

    # 檢查傳入的參數，選擇查詢條件
    material_record = None
    #if _order_num is not None:  # 如果傳入了 order_num
    #    material_record = s.query(P_Material).filter_by(order_num=_order_num).first()
    #elif _id is not None:  # 如果傳入了 id
    #    material_record = s.query(P_Material).filter_by(id=_id).first()
    #
    if _id is not None:
        material_record = s.query(P_Material).filter_by(id=_id).first()
    elif _order_num is not None:
        material_record = s.query(P_Material).filter_by(order_num=_order_num).first()
    #

    if material_record is None:
      return_value = False
    else:
      # 動態設置欄位值
      if hasattr(material_record, _record_name):
        setattr(material_record, _record_name, _record_data)
        s.commit()

    s.close()

    return jsonify({
      'status': return_value
    })


@updateTable.route("/updateAssemble", methods=['POST'])
def update_assemble():
  print("updateAssemble....")

  request_data = request.get_json()

  _assemble_id = request_data['assemble_id']
  _record_name = request_data['record_name']

  if 'record_data' not in request_data:
    return jsonify({
        'status': False,
        'message': '缺少 record_data'
    }), 400
  _record_data = request_data['record_data']

  return_value = True  # true: 資料正確, 註冊成功
  s = Session()

  # 查找對應的記錄
  assemble_record = s.query(Assemble).filter_by(id = _assemble_id).first()

  # 動態設置欄位值
  if hasattr(assemble_record, _record_name):

    # total_ask_qty 不允許前端任意累加
    if _record_name == 'total_ask_qty':
        ask_qty = int(assemble_record.ask_qty or 0)
        incoming = int(_record_data or 0)

        # 若前端送來剛好 2 倍，視為錯誤累加，強制改回 ask_qty
        if ask_qty > 0 and incoming == ask_qty * 2:
            _record_data = ask_qty

    setattr(assemble_record, _record_name, _record_data)

    # 保險：一般正常/非異常列，total_ask_qty 不應大於 ask_qty
    if (
        int(assemble_record.ask_qty or 0) > 0
        and int(assemble_record.total_ask_qty or 0) > int(assemble_record.ask_qty or 0)
        and (assemble_record.reason or '') != '異常返工'
    ):
        assemble_record.total_ask_qty = assemble_record.ask_qty

    s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateAssembleP", methods=['POST'])
def update_assemble_p():
  print("updateAssembleP....")

  request_data = request.get_json()

  _assemble_id = request_data['assemble_id']
  _record_name = request_data['record_name']

  if 'record_data' not in request_data:
    return jsonify({
        'status': False,
        'message': '缺少 record_data'
    }), 400
  _record_data = request_data['record_data']

  #print("_record_name:", _record_name)

  return_value = True  # true: 資料正確, 註冊成功
  s = Session()

  # 查找對應的記錄
  assemble_record = s.query(P_Assemble).filter_by(id = _assemble_id).first()

  # 動態設置欄位值
  if hasattr(assemble_record, _record_name):
    setattr(assemble_record, _record_name, _record_data)
    s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateProcessData", methods=['POST'])
def update_process_data():
  print("updateProcessData....")

  request_data = request.get_json()

  _process_id = request_data['process_id']
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']

  return_value = True  # true: 資料正確, 註冊成功
  s = Session()

  # 查找對應的記錄
  process_record = s.query(Process).filter_by(id = _process_id).first()

  # 動態設置欄位值
  if hasattr(process_record, _record_name):
    setattr(process_record, _record_name, _record_data)
    s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateProcessDataP", methods=['POST'])
def update_process_data_p():
  print("updateProcessDataP....")

  request_data = request.get_json()

  _process_id = request_data['process_id']
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']

  return_value = True  # true: 資料正確, 註冊成功
  s = Session()

  # 查找對應的記錄
  process_record = s.query(P_Process).filter_by(id = _process_id).first()

  # 動態設置欄位值
  if hasattr(process_record, _record_name):
    setattr(process_record, _record_name, _record_data)
    s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateMaterialRecord", methods=['POST'])
def update_material_record():
  print("updateMaterialRecord....")

  request_data = request.get_json()

  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  _show1_ok = request_data['show1_ok']
  _show2_ok = request_data['show2_ok']
  _show3_ok = request_data['show3_ok']
  _whichStation = request_data['whichStation']

  s = Session()

  if _order_num is not None:  # 如果傳入了 order_num
    s.query(Material).filter(Material.order_num == _order_num).update({
      "show1_ok": _show1_ok,
      "show2_ok": _show2_ok,
      "show3_ok": _show3_ok,
      "whichStation": _whichStation,
    })
  elif _id is not None:  # 如果傳入了 id
    s.query(Material).filter(Material.id == _id).update({
      "show1_ok": _show1_ok,
      "show2_ok": _show2_ok,
      "show3_ok": _show3_ok,
      "whichStation": _whichStation,
    })

  s.commit()

  s.close()

  return jsonify({
    'status': True
  })


@updateTable.route("/updateMaterialRecordP", methods=['POST'])
def update_material_record_p():
  print("updateMaterialRecordP....")

  request_data = request.get_json()

  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  _show1_ok = request_data['show1_ok']
  _show2_ok = request_data['show2_ok']
  _show3_ok = request_data['show3_ok']
  #_whichStation = request_data['whichStation']

  s = Session()

  if _order_num is not None:  # 如果傳入了 order_num
    s.query(P_Material).filter(P_Material.order_num == _order_num).update({
      "show1_ok": _show1_ok,
      "show2_ok": _show2_ok,
      "show3_ok": _show3_ok,
      #"whichStation": _whichStation,
    })
  elif _id is not None:  # 如果傳入了 id
    s.query(P_Material).filter(P_Material.id == _id).update({
      "show1_ok": _show1_ok,
      "show2_ok": _show2_ok,
      "show3_ok": _show3_ok,
      #"whichStation": _whichStation,
    })

  s.commit()

  s.close()

  return jsonify({
    'status': True
  })


@updateTable.route("/updatePermissions", methods=['POST'])
def update_permissions():
  print("updatePermissions....")

  request_data = request.get_json()

  _id = request_data['perm_empID']

  _system = request_data['perm_checkboxForSystem']
  _admin = request_data['perm_checkboxForAdmin']
  _member = request_data['perm_checkboxForMember']

  return_value = True  # true: 資料正確, 註冊成功
  if _id == "":
      return_value = False  # false: 資料不完全 註冊失敗

  s = Session()
  if return_value:
      # 以最高權限寫入資料庫
      if _member:
          _p_id = 4
      if _admin:
          _p_id = 3
      if _system:
          _p_id = 2

      s.query(User).filter(User.emp_id == _id).update(
          {"perm_id": _p_id})

      s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateAGV", methods=['POST'])
def update_agv():
  print("updateAGV....")

  request_data = request.get_json()

  _id = request_data['id']
  _status = request_data['status']
  _station =  request_data['station']

  s = Session()

  s.query(Agv).filter(Agv.id == _id).update({
    "status": _status,
    "station": _station
  })

  s.commit()

  s.close()

  return jsonify({
    'status': True
  })


@updateTable.route("/updateAssembleAlarmMessage", methods=["POST"])
def update_assemble_alarm_message():
    print("updateAssembleAlarmMessage....")

    data = request.get_json(silent=True) or {}

    assemble_id = data.get("assemble_id")
    raw_message = data.get("alarm_message", None)

    if raw_message is None:
        raw_message = data.get("cause_message", "")

    if isinstance(raw_message, list):
        alarm_message = "、".join(str(x).strip() for x in raw_message if str(x).strip())
    else:
        alarm_message = str(raw_message or "").strip()

    if not assemble_id:
        return jsonify({
            "status": False,
            "message": "assemble_id 不可為空"
        }), 400

    s = Session()

    try:
        assemble = (
            s.query(Assemble)
            .filter(Assemble.id == assemble_id)
            .first()
        )

        if not assemble:
            return jsonify({
                "status": False,
                "message": "找不到 Assemble"
            }), 404

        # --------------------------------------------------
        # 1. 更新來源列
        # --------------------------------------------------
        assemble.alarm_enable = False
        assemble.alarm_message = alarm_message
        assemble.confirm_comment = alarm_message
        assemble.Incoming1_Abnormal = alarm_message

        # --------------------------------------------------
        # 2. 找第一層返工列(B109)
        # --------------------------------------------------
        level1_ids = [
            r.id
            for r in (
                s.query(Assemble)
                .filter(Assemble.is_copied_from_id == assemble.id)
                .all()
            )
        ]

        # --------------------------------------------------
        # 3. 更新所有返工列(B109、B110...)
        # --------------------------------------------------
        rework_rows = (
            s.query(Assemble)
            .filter(
                Assemble.material_id == assemble.material_id
            )
            .filter(
                Assemble.reason == "異常返工"
            )
            .filter(
                or_(
                    Assemble.is_copied_from_id == assemble.id,
                    Assemble.is_copied_from_id.in_(level1_ids) if level1_ids else False
                )
            )
            .all()
        )

        for row in rework_rows:
            row.alarm_message = alarm_message
            row.confirm_comment = alarm_message
            row.Incoming1_Abnormal = alarm_message

        s.commit()

        return jsonify({
            "status": True,
            "message": "異常原因已更新",
            "update_count": len(rework_rows) + 1
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()

        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:
        s.close()


@updateTable.route("/updateBomXorReceive", methods=["POST"])
def update_bom_xor_receive():
    print("updateBomXorReceive....")

    data = request.get_json()
    copied_id = data.get("copied_material_id")
    print("copied_id", copied_id)

    s = Session()

    # 找到複製資料
    copied_material = s.query(Material).options(joinedload(Material._bom)).filter_by(id=copied_id).first()
    if not copied_material or not copied_material.is_copied_from_id:
        return jsonify({"error": "Invalid copied material or missing source ID"}), 400
    print("copied_material:",copied_material)

    # 找到原始資料
    source_material = s.query(Material).options(joinedload(Material._bom)).filter_by(id=copied_material.is_copied_from_id).first()
    if not source_material:
        return jsonify({"error": "Source material not found"}), 404
    print("source_material:",source_material)

    # 條件限制：兩者其中之一 isLackMaterial 必須為 0 才繼續
    if source_material.isLackMaterial != 0 and copied_material.isLackMaterial != 0:
        return jsonify({"message": "No update required, neither material has isLackMaterial == 0"}), 200

    # 建立 dict 以 seq_num 為 key 對應 receive
    source_boms = {bom.seq_num: bom for bom in source_material._bom}
    copied_boms = {bom.seq_num: bom for bom in copied_material._bom}
    #print("source_boms:",source_boms)
    #print("copied_boms:",copied_boms)

    updated = False
    for seq_num, source_bom in source_boms.items():
        if seq_num in copied_boms:
            copied_bom = copied_boms[seq_num]
            xor_result = int(source_bom.receive) ^ int(copied_bom.receive)
            if xor_result == 1:
                source_bom.receive = True  # 將缺料清除
                source_material.isLackMaterial = 99
                #source_material.show2_ok = 3        # 等待組裝作業
                copied_material.isLackMaterial = 0
                updated = True
            #else:
            #    source_material.isLackMaterial = 0
            #    updated = True
    '''
    if updated:

        refresh_root_shortage_note(s, source_material.order_num)

        s.commit()
    '''
    #
    if updated:
        refresh_root_shortage_note(s, source_material.order_num)
        refresh_root_status(s, source_material.order_num)

        # ✅ 若原始資料已經沒有缺料，copy 缺料資料要收尾
        still_lack = (
            s.query(Bom.id)
            .filter(Bom.material_id == source_material.id)
            .filter(Bom.receive.is_(False))
            .first()
        )

        if not still_lack:
            copied_material.isLackMaterial = 99
            copied_material.shortage_note = ""

            # copy 缺料資料不再顯示
            copied_material.isShow = False
            copied_material.isOpen = False
            copied_material.isOpenEmpId = ""
            copied_material.hasStarted = False
            copied_material.startStatus = 1

            copied_material.isAssembleStationShow = False
            copied_material.isAssembleStation1TakeOk = False
            copied_material.isAssembleStation2TakeOk = False
            copied_material.isAssembleStation3TakeOk = False

            copied_material.process_step_enable = 0

        s.commit()
    #

    s.close()

    return jsonify({
      'status': True,
      'message': "Updated successfully."
    })


@updateTable.route("/updateBomXorReceiveP", methods=["POST"])
def update_bom_xor_receive_p():
    print("updateBomXorReceiveP....")

    data = request.get_json()
    copied_id = data.get("copied_material_id")

    s = Session()

    # 找到複製資料
    copied_material = s.query(P_Material).options(joinedload(P_Material._bom)).filter_by(id=copied_id).first()
    if not copied_material or not copied_material.is_copied_from_id:
        return jsonify({"error": "Invalid copied p_material table or missing source ID"}), 400
    #print("copied_material:",copied_material)

    # 找到原始資料
    source_material = s.query(P_Material).options(joinedload(P_Material._bom)).filter_by(id=copied_material.is_copied_from_id).first()
    if not source_material:
        return jsonify({"error": "Source p_material not found"}), 404
    #print("source p_material:",source_material)

    # 條件限制：兩者其中之一 isLackMaterial 必須為 0 才繼續
    if source_material.isLackMaterial != 0 and copied_material.isLackMaterial != 0:
        return jsonify({"message": "No update required, neither material has isLackMaterial == 0"}), 200

    # 建立 dict 以 seq_num 為 key 對應 receive
    source_boms = {bom.seq_num: bom for bom in source_material._bom}
    copied_boms = {bom.seq_num: bom for bom in copied_material._bom}
    #print("source_boms:",source_boms)
    #print("copied_boms:",copied_boms)

    updated = False
    for seq_num, source_bom in source_boms.items():
        if seq_num in copied_boms:
            copied_bom = copied_boms[seq_num]
            xor_result = int(source_bom.receive) ^ int(copied_bom.receive)
            if xor_result == 1:
                source_bom.receive = True  #          將缺料清除
                source_material.isLackMaterial = 99
                copied_material.isLackMaterial = 0
                updated = True

    if updated:
        s.commit()

    s.close()

    return jsonify({
      'status': True,
      'message': "Updated successfully."
    })


@updateTable.route("/updateProduct", methods=["POST"])
def update_product():
    print("updateProduct....")

    s = Session()
    try:
        data = request.get_json(silent=True) or {}
        items = data.get("items", [])
        if not isinstance(items, list) or len(items) == 0:
            return jsonify({"ok": False, "error": "items 必須為非空陣列"}), 400

        # 取出所有 material_id
        try:
            mids = [int(it["material_id"]) for it in items if "material_id" in it]
        except (KeyError, TypeError, ValueError):
            return jsonify({"ok": False, "error": "每筆必須含 material_id（整數）"}), 400

        # 檢查 material 是否存在
        exist_mid = set(x[0] for x in s.query(Material.id).filter(Material.id.in_(mids)).all())
        not_found = [mid for mid in mids if mid not in exist_mid]
        if not_found:
            return jsonify({"ok": False, "error": f"找不到 material_id: {not_found}"}), 400

        # 先抓現有的 Product（假設一個 material_id 對應一筆 Product）
        exist_products = s.query(Product).filter(Product.material_id.in_(mids)).all()
        by_mid = {p.material_id: p for p in exist_products}

        # 處理每筆
        for it in items:
            mid = int(it["material_id"])
            p = by_mid.get(mid)
            if p is None:
                p = Product(
                    material_id   = mid,
                    delivery_qty  = 0,
                    assemble_qty  = 0,
                    allOk_qty     = 0,
                    good_qty      = 0,
                    non_good_qty  = 0,
                    reason        = None,
                    confirm_comment = None,
                )
                s.add(p)
                by_mid[mid] = p

            # ---- 1) 累加欄位 ----
            for f in ("allOk_qty", "good_qty", "non_good_qty"):
                if f in it:
                    inc = _to_int_or_none(it.get(f))
                    if inc is not None:
                        setattr(p, f, (getattr(p, f) or 0) + inc)

            # ---- 2) 直接覆寫欄位（有帶才動）----
            if "delivery_qty" in it:
                v = _to_int_or_none(it.get("delivery_qty"))
                if v is not None:
                    p.delivery_qty = v

            if "assemble_qty" in it:
                v = _to_int_or_none(it.get("assemble_qty"))
                if v is not None:
                    p.assemble_qty = v

            if "reason" in it:
                # 字串允許清空；要清空就傳 ""；不帶就不動
                rv = it.get("reason")
                p.reason = ("" if rv == "" else (str(rv) if rv is not None else p.reason))

            if "confirm_comment" in it:
                cv = it.get("confirm_comment")
                p.confirm_comment = ("" if cv == "" else (str(cv) if cv is not None else p.confirm_comment))

        s.commit()

        # 組回傳
        out = []
        for mid, p in by_mid.items():
            if mid in exist_mid:  # 只回這次有動到的 mids
                out.append({
                    "id": getattr(p, "id", None),
                    "material_id": p.material_id,
                    "delivery_qty": p.delivery_qty,
                    "assemble_qty": p.assemble_qty,
                    "allOk_qty": p.allOk_qty,
                    "good_qty": p.good_qty,
                    "non_good_qty": p.non_good_qty,
                    "reason": p.reason,
                    "confirm_comment": p.confirm_comment,
                })
        return jsonify({"ok": True, "updated": len(out), "items": out}), 200

    except ValueError as e:
        s.rollback()
        return jsonify({"ok": False, "error": str(e)}), 400
    except SQLAlchemyError as e:
        s.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    except Exception as e:
        s.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        s.close()


@updateTable.route("/updateAssembleTableData", methods=["POST"])
def update_assemble_table_data():
    print("updateAssembleTableData....")

    s = Session()
    try:
        data = request.get_json(force=True) or {}
        assemble_id = data.get("assemble_id")
        if not assemble_id:
            return jsonify({"status": False, "message": "assemble_id 為必填"}), 400

        patch = data.get("patch")
        if patch is None:
            patch = {k: v for k, v in data.items() if k != "assemble_id"}
        if not isinstance(patch, dict) or not patch:
            return jsonify({"status": False, "message": "沒有可更新欄位"}), 400

        obj = s.query(Assemble).get(int(assemble_id))
        if not obj:
            return jsonify({"status": False, "message": f"Assemble id={assemble_id} 不存在"}), 404

        before = serialize_assemble(obj)

        updated, ignored = [], []
        for k, v in patch.items():
            if k not in ALLOWED_FIELDS:
                ignored.append(k); continue
            setattr(obj, k, coerce_by_schema(k, v))
            updated.append(k)

        # 統一由後端覆寫 update_time
        obj.update_time = now_str()
        if "update_time" not in updated:
            updated.append("update_time")

        # 可選：驗證 is_copied_from_id
        if "is_copied_from_id" in updated and obj.is_copied_from_id:
            exists = s.query(Assemble.id).filter(Assemble.id == obj.is_copied_from_id).first()
            if not exists:
                obj.is_copied_from_id = None
                updated.remove("is_copied_from_id")
                ignored.append("is_copied_from_id(不存在的來源 id)")

        s.commit(); s.refresh(obj)
        after = serialize_assemble(obj)

        return jsonify({
            "status": True, "id": obj.id,
            "updated": sorted(updated), "ignored_fields": ignored,
            "before": before, "after": after
        }), 200

    except SQLAlchemyError as e:
        s.rollback()
        return jsonify({"status": False, "message": f"資料庫錯誤: {str(e)}"}), 500
    except Exception as e:
        s.rollback()
        return jsonify({"status": False, "message": f"伺服器錯誤: {str(e)}"}), 500
    finally:
        s.close()


# ------------------------------------------------------------------
# batch 批次識別
# ------------------------------------------------------------------
