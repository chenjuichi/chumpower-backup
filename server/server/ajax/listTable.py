import math
import random
import re
from datetime import datetime, date, timedelta

from datetime import datetime as dt
import time

from sqlalchemy import distinct, func, case, select
from flask import Blueprint, jsonify, request, current_app

from database.tables import User, UserDelegate, Material, Bom, Assemble, Permission, AbnormalCause, Process, Product, Setting, Session
from database.p_tables import P_Material, P_Assemble,  P_AbnormalCause, P_Process, P_Product, P_Part

from dotenv import dotenv_values

from collections import defaultdict

from sqlalchemy import func, or_, cast, Integer
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import selectinload, load_only

listTable = Blueprint('listTable', __name__)
#
#from log_util import setup_logger
#logger = setup_logger(__name__)  # 每個模組用自己的名稱
#


# ------------------------------------------------------------------


def normalize_routing_priv(raw, total_count=27):
    txt = (raw or '').strip()
    if not txt:
        return ''

    vals = []
    for part in txt.split(','):
        part = part.strip()
        if part == '':
            continue
        try:
            vals.append(int(part))
        except Exception:
            continue

    if not vals:
        return ''

    # 舊格式：27 個 0/1 bitmap
    if len(vals) == total_count and all(v in (0, 1) for v in vals):
        ids = [str(i + 1) for i, v in enumerate(vals) if v == 1]
        return ','.join(ids)

    # 新格式：id 清單
    ids = sorted(set(v for v in vals if v > 0))
    return ','.join(str(v) for v in ids)


def order_has_lack(session, order_num: str) -> bool:
    """
    訂單層級缺料判斷：
    - Bom.receive == False 或 Bom.receive is NULL 都算缺料
    """
    if not order_num:
        return False

    q = (
        session.query(Bom.id)
        .join(Material, Material.id == Bom.material_id)
        .filter(Material.order_num == order_num)
        .filter(or_(Bom.receive.is_(False), Bom.receive.is_(None)))
        .limit(1)
    )
    return session.query(q.exists()).scalar() is True


def shortage_note_by_order(session, order_num: str) -> str:
    return "(缺料)" if order_has_lack(session, order_num) else ""


def calc_shortage_note_by_material(session, material_id: int) -> str:
    has_lack = (
        session.query(Bom)
        .filter(Bom.material_id == material_id)
        .filter(or_(Bom.receive.is_(False), Bom.receive.is_(None)))
        .count() > 0
    )
    return "(缺料)" if has_lack else ""
"""
def calc_shortage_note_by_order(s, order_num: str) -> str:
    if not order_num:
        return ""

    # 只要同 order_num 任一 BOM.receive == False，就算缺料
    has_lack = (
        s.query(Bom.id)
         .join(Material, Bom.material_id == Material.id)
         .filter(Material.order_num == order_num)
         .filter(Bom.receive.is_(False))
         .first()
        is not None
    )
    return "(缺料)" if has_lack else ""
"""

def read_all_p_part_process_code_p():
    """
    從 p_part 資料表讀取所有製程資料，組出：

        code_to_assembleStep = { '100-01': step_code, '100-02': step_code, ... }

    規則：
      - 使用 P_Part.part_code 當 key 的來源，例如 'B100-01'
      - 若 part_code 以 'B' 開頭，就去掉 'B'，變成 '100-01' 當 dict 的 key
      - value 直接使用 P_Part.process_step_code
    """

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


def map_pt(row):
    """
    3 -> 21, 2 -> 22, 1 -> 23，其餘預設 23。
    支援欄位名：process_step_code / process_step / step_code
    row 可為 dict 或 ORM 物件。
    """
    code = get_val(row, 'process_step_code')
    if code is None:
        code = get_val(row, 'process_step')
    if code is None:
        code = get_val(row, 'step_code')

    try:
        code = int(code) if code is not None else None
    except Exception:
        code = None

    if code == 3:
        return 21
    if code == 2:
        return 22
    if code == 1:
        return 23
    return 23


def get_val(row, key, default=None):
    """同時支援 dict 與 ORM 物件取值。"""
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def active_count_map_by_material_multi(session, material_ids, process_types=(21,22,23), include_paused=True):
    """
    回傳格式：
    {
      "21": { "101": 2, "103": 1 },
      "22": { "101": 1 },
      "23": {}
    }
    include_paused: True → 只要未結束就算（包含暫停）
                     False → 只算「正在跑」（不含暫停）
    """
    if not material_ids:
        return {str(pt): {} for pt in process_types}

    q = (session.query(
            Process.material_id,
            Process.process_type,
            func.count(Process.id))
         .filter(Process.material_id.in_(material_ids))
         .filter(Process.process_type.in_(list(process_types)))
         .filter(Process.end_time.is_(None)))

    # 不要把暫停算進去 → 再加 is_paused = false 的條件
    if not include_paused:
        q = q.filter(or_(Process.is_pause.is_(False), Process.is_pause == 0, Process.is_pause.is_(None)))

    rows = q.group_by(Process.material_id, Process.process_type).all()

    result = {str(pt): {} for pt in process_types}
    for mid, ptype, cnt in rows:
        result[str(int(ptype))][str(int(mid))] = int(cnt)
    return result


def need_more_process_qty(k1: int, a1: int, t1: int, must_qty: int, s=None):
    #print("need_more_process_qty()...")

    """
    回傳 (is_insufficient, process_total)
    is_insufficient: True 表示加總 < must_qty；False 表示 >= must_qty
    process_total  : 依條件加總後的數量（int）
    """
    # 允許外部傳入 session；若沒傳就自行建立並在結尾關閉

    #print(k1, t1, must_qty)

    close_after = False
    if s is None:
        from database.tables import Session  # 若你的檔名不同請調整
        s = Session()
        close_after = True

    try:
        # end_time 欄位在你的 schema 是 String(30)，因此除了 not NULL，也一併排除空字串
        total = (
            s.query(func.coalesce(func.sum(Process.process_work_time_qty), 0))
             .filter(Process.material_id == k1)
             .filter(Process.assemble_id == a1)
             .filter(Process.process_type == t1)
             .filter(Process.has_started.is_(True))
             .filter(Process.end_time.isnot(None))
             .filter(Process.end_time != '')
             .scalar()
        ) or 0

        total = int(total)
        #print("total, must_qty:", total, must_qty)
        return (total < int(must_qty), total)
    finally:
        if close_after:
            s.close()


# ------------------------------------------------------------------


@listTable.route("/listFileOK", methods=['GET'])
def list_file_ok():
  print("listFileOK....")

  _file_ok = current_app.config['file_ok']
  print("file_ok flag value is: ", _file_ok)

  if _file_ok:
    current_app.config['file_ok'] = False
    #file_ok = False

  return jsonify({
    'outputs': _file_ok
  })


# list socket server ip
@listTable.route("/listSocketServerIP", methods=['GET'])
def list_Socket_Server_ip():
  print("listSocketServerIP....")

  _socket_server_ip = current_app.config['socket_server_ip']
  print("socket_server_ip is: ", _socket_server_ip)

  return jsonify({
    'socket_server_ip': _socket_server_ip
  })


# list all departments
@listTable.route("/listDepartments", methods=['GET'])
def list_departments():
  print("listDepartments....")

  env_vars = dotenv_values(current_app.config['envDir'])

  #部門資料
  departments_str= env_vars["chumpower_departments"]
  departments = departments_str.split(",")

  return jsonify({
    'departments': departments,
  })


# list all abnormalCauses
@listTable.route("/listAbnormalCauses", methods=['GET'])
def list_abnormal_causes():
  print("listAbnormalCauses....")

  s = Session()
  _abnormal_cause_results = []

  abnormal_cause_results = s.query(AbnormalCause).all()   # 查詢所有的 AbnormalCause

  # 將結果轉換為字典列表
  _abnormal_cause_results = [
    {
        "id": cause.id,
        "number": cause.number,
        "message": cause.message,
    }
    for cause in abnormal_cause_results
  ]

  s.close()

  temp_len = len(_abnormal_cause_results)
  print("listAbnormalCauses, 總數: ", temp_len)

  return jsonify({
    'abnormal_causes': _abnormal_cause_results,
  })


# list all Marquees
@listTable.route("/listMarquees", methods=['GET'])
def list_marquees():
  print("listMarquees....")

  env_vars = dotenv_values(current_app.config['envDir'])
  #marquees資料
  marquees = [env_vars["Marquee_0"], env_vars["Marquee_1"], env_vars["Marquee_2"], env_vars["Marquee_3"]]

  return jsonify({
    'marquees': marquees,
  })


# list all users
@listTable.route("/listUsers", methods=['GET'])
def list_users():
    print("listUsers....")

    s = Session()
    _user_results = []
    return_value = True
    _objects = s.query(User).all()
    users = [u.__dict__ for u in _objects]
    for user in users:
      #print("user:", user)
      if (user['isRemoved']):
        perm_item = s.query(Permission).filter_by(id = user['perm_id']).first()
        setting_item = s.query(Setting).filter_by(id = user['setting_id']).first()

        _user_object = {
          'emp_id': user['emp_id'],
          'emp_name': user['emp_name'],
          'dep_name': user['dep_name'],
          'emp_perm': perm_item.auth_code,    #4, 3, 2, 1
          'emp_lastRoutingName': setting_item.lastRoutingName,
          'routingPriv': setting_item.routingPriv,
        }
        _user_results.append(_user_object)
    s.close()

    temp_len = len(_user_results)
    print("listUsers, 員工總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    return jsonify({
        'status': return_value,
        'users': _user_results    #員工資料
    })


# list all users
@listTable.route("/listUsers2", methods=['GET'])
def list_users2():
    print("listUsers2....")

    s = Session()
    _user_results = []
    return_value = True
    _objects = s.query(User).all()
    users = [u.__dict__ for u in _objects]
    for user in users:
      if (user['isRemoved']):
        perm_item = s.query(Permission).filter_by(id = user['perm_id']).first()
        setting_item = s.query(Setting).filter_by(id = user['setting_id']).first()

        _user_object = {
          'emp_id': user['emp_id'],
          'emp_name': user['emp_name'],

          #'dep_name': user['dep_name'],
          'dep_name': re.sub(r"^\d+-", "", user['dep_name']),

          'is_user_delegate': user['is_user_delegate'],

          'emp_perm': perm_item.auth_code,    #4, 3, 2, 1
          'emp_lastRoutingName': setting_item.lastRoutingName,
          #'routingPriv': setting_item.routingPriv,
          'routingPriv': normalize_routing_priv(setting_item.routingPriv),
        }
        _user_results.append(_user_object)
    s.close()

    temp_len = len(_user_results)
    print("listUsers, 員工總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    return jsonify({
        'status': return_value,
        'users': _user_results    #員工資料
    })


@listTable.route('/listDelegates', methods=['GET'])
def list_delegates():
    print("listDelegates....")

    user_id = int(request.args.get('user_id'))
    s = Session()
    rows = s.query(UserDelegate).filter(UserDelegate.user_id == user_id).order_by(UserDelegate.start_date.desc(), UserDelegate.id.desc()).all()
    return jsonify(success=True, items=[{
        'id': r.id,
        'user_id': r.user_id,
        'delegate_emp_id': r.delegate_emp_id,
        'start_date': r.start_date.isoformat(),
        'end_date': r.end_date.isoformat() if r.end_date else None,
        'reason': r.reason,
    } for r in rows])


"""
@listTable.route("/listMaterialsP", methods=['GET'])
def list_materials_p():
    print("listMaterialsP....")

    s = Session()

    _results = []
    return_value = True

    _objects = s.query(P_Material).filter(P_Material.move_by_process_type == 4).all()
    materials = [u.__dict__ for u in _objects]
    print("len:",len(materials))
    processed_order_nums = set()  # 用於追踪已處理過的 order_num
    for record in materials:
      if not record['isShow']:   # 檢查 isShow 是否為 False
        cleaned_comment = record['material_comment'].strip()  # 刪除 material_comment 字串前後的空白
        temp_data = record['id']                              # 該筆訂單編號的table id
        if temp_data in processed_order_nums:                 # 如果這個 order_num 已經處理過，跳過本次處理
          continue

        # 計算 temp_delivery 的值
        order_num_id = temp_data
        material_qty = record['material_qty']
        delivery_qty = record['delivery_qty']
        temp_delivery=record['total_delivery_qty']

        # 標記這個 order_num 已處理過
        #processed_order_nums.add(order_num)
        processed_order_nums.add(order_num_id)
        _object = {
          'id': record['id'],
          'order_num': record['order_num'],                   #訂單編號
          'material_num': record['material_num'],             #物料編號
          'req_qty': material_qty,                            #需求數量(訂單數量)
          'delivery_qty': delivery_qty,                       #備料數量
          'total_delivery_qty': temp_delivery,                #應備數量
          'input_disable': record['input_disable'],
          'date': record['material_date'],                    #(建立日期)
          'delivery_date':record['material_delivery_date'],   #交期
          'shortage_note': record['shortage_note'],           #缺料註記 '元件缺料'
          'comment': cleaned_comment,                         #說明

          'isOpen': record['isOpen'],
          'isOpenEmpId': record['isOpenEmpId'],
          'hasStarted': record['hasStarted'],
          'startStatus': record['startStatus'],

          'isBom' : record['isBom'],

          'isTakeOk' : record['isTakeOk'],
          'isBatchFeeding' :  record['isBatchFeeding'],
          'isShow' : record['isShow'],
          'whichStation' : record['whichStation'],
          'show1_ok' : record['show1_ok'],
          'show2_ok' : record['show2_ok'],
          'show3_ok' : record['show3_ok'],
          'Incoming0_Abnormal': record['Incoming0_Abnormal'] == '',
          'Incoming0_Abnormal_message': record['Incoming0_Abnormal'],
          'is_copied': bool(record['is_copied_from_id'] and record['is_copied_from_id'] > 0),
        }

        _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listMaterialsP, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    ## 根據 isTakeOk 屬性的值進行排序
    #_results = sorted(_results, key=lambda x: not x['isTakeOk'])
    ## 根據 'order_num' 排序
    #_results = sorted(_results, key=lambda x: x['order_num'])
    # 根據 order_num 升序，再根據 isTakeOk 降序 (True > False)
    _results.sort(key=lambda x: (x['order_num'], not x['isTakeOk']))

    return jsonify({
      'status': return_value,
      'materials': _results
    })
"""


# list all p_materials
@listTable.route("/listMaterialsP", methods=['GET'])
def list_materials_p():
    print("listMaterialsP....")

    s = Session()
    try:
        return_value = True
        _results = []

        rows = (
            s.query(
                P_Material.id,
                P_Material.order_num,
                P_Material.material_num,
                P_Material.material_qty,
                P_Material.delivery_qty,
                P_Material.total_delivery_qty,
                P_Material.input_disable,
                P_Material.material_date,
                P_Material.material_delivery_date,
                P_Material.shortage_note,
                P_Material.material_comment,

                P_Material.isOpen,
                P_Material.isOpenEmpId,
                P_Material.hasStarted,
                P_Material.startStatus,

                P_Material.isBom,
                P_Material.isTakeOk,
                P_Material.isBatchFeeding,
                P_Material.isShow,
                P_Material.whichStation,
                P_Material.show1_ok,
                P_Material.show2_ok,
                P_Material.show3_ok,
                P_Material.Incoming0_Abnormal,
                P_Material.is_copied_from_id,
            )
            .filter(P_Material.move_by_process_type == 4)
            .filter(P_Material.isShow.is_(False))
            .all()
        )

        print("len:", len(rows))

        for row in rows:
            cleaned_comment = (row.material_comment or '').strip()

            _object = {
                'id': row.id,
                'order_num': row.order_num,                         # 訂單編號
                'material_num': row.material_num,                   # 物料編號
                'req_qty': row.material_qty,                        # 需求數量(訂單數量)
                'delivery_qty': row.delivery_qty,                   # 備料數量
                'total_delivery_qty': row.total_delivery_qty,       # 應備數量
                'input_disable': row.input_disable,
                'date': row.material_date,                          # 建立日期
                'delivery_date': row.material_delivery_date,        # 交期
                'shortage_note': row.shortage_note,                 # 缺料註記
                'comment': cleaned_comment,                         # 說明

                'isOpen': row.isOpen,
                'isOpenEmpId': row.isOpenEmpId,
                'hasStarted': row.hasStarted,
                'startStatus': row.startStatus,

                'isBom': row.isBom,

                'isTakeOk': row.isTakeOk,
                'isBatchFeeding': row.isBatchFeeding,
                'isShow': row.isShow,
                'whichStation': row.whichStation,
                'show1_ok': row.show1_ok,
                'show2_ok': row.show2_ok,
                'show3_ok': row.show3_ok,
                'Incoming0_Abnormal': (row.Incoming0_Abnormal == ''),
                'Incoming0_Abnormal_message': row.Incoming0_Abnormal,
                'is_copied': bool(row.is_copied_from_id and row.is_copied_from_id > 0),
            }

            _results.append(_object)

        temp_len = len(_results)
        print("listMaterialsP, 總數: ", temp_len)

        if temp_len == 0:
            return_value = False

        # 根據 order_num 升序，再根據 isTakeOk 排序（True 會排前面）
        _results.sort(key=lambda x: (x['order_num'] or '', not bool(x['isTakeOk'])))

        return jsonify({
            'status': return_value,
            'materials': _results
        })

    except Exception as e:
        import traceback
        print("listMaterialsP ERROR:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("listMaterialsP failed")
        except Exception:
            pass
        return jsonify({
            'status': False,
            'materials': []
        }), 200

    finally:
        s.close()

"""
# list all materials
@listTable.route("/listMaterials", methods=['GET'])
def list_materials():
  print("listMaterials....")

  _results = []
  return_value = True

  s = Session()
  try:
    # 先一次算出：每個 order_num 在 Material 表中的筆數（同樣套 move_by_process_type == 2）
    order_num_cnt_map = dict(
      s.query(
        Material.order_num,
        func.count(Material.id)
      )
      .filter(Material.move_by_process_type == 2)
      .group_by(Material.order_num)
      .all()
    )

    _objects = s.query(Material).filter(Material.move_by_process_type == 2).all()
    materials = [u.__dict__ for u in _objects]

    processed_order_nums = set()  # 用於追踪已處理過的 order_num

    for record in materials:
      if not record['isShow']:                                # 檢查 isShow 是否為 False
        cleaned_comment = record['material_comment'].strip()  # 刪除 material_comment 字串前後的空白
        temp_data = record['id']                              # 該筆訂單編號的table id

        if temp_data in processed_order_nums:   # 如果這個 order_num 已經處理過，跳過本次處理
          continue

        order_num_id = temp_data
        material_qty = record['material_qty']
        delivery_qty = record['delivery_qty']

        temp_delivery=record['total_delivery_qty']

        processed_order_nums.add(order_num_id)    # 標記這個 order_num 已處理過

        merge_cnts=int(order_num_cnt_map.get(record['order_num'], 0))

        _object = {
          'id': record['id'],
          'order_num': record['order_num'],                   #訂單編號
          'material_num': record['material_num'],             #物料編號
          'req_qty': material_qty,                            #需求數量(訂單數量)
          'delivery_qty': delivery_qty,                       #備料數量
          'total_delivery_qty': temp_delivery,                #應備數量
          'input_disable': record['input_disable'],
          'date': record['material_date'],                    #(建立日期)
          'delivery_date':record['material_delivery_date'],   #交期
          'shortage_note': record['shortage_note'],           #缺料註記 '元件缺料'
          'comment': cleaned_comment,                         #說明

          'isOpen': record['isOpen'],
          'isOpenEmpId': record['isOpenEmpId'],
          'hasStarted': record['hasStarted'],
          'startStatus': record['startStatus'],

          'isTakeOk' : record['isTakeOk'],
          'isLackMaterial' : record['isLackMaterial'],
          'isBatchFeeding' :  record['isBatchFeeding'],
          'isShow' : record['isShow'],
          'whichStation' : record['whichStation'],
          'show1_ok' : record['show1_ok'],
          'show2_ok' : record['show2_ok'],
          'show3_ok' : record['show3_ok'],
          'Incoming0_Abnormal': record['Incoming0_Abnormal'] == '',
          'Incoming0_Abnormal_message': record['Incoming0_Abnormal'],
          #'is_copied': bool((record['is_copied_from_id'] and record['is_copied_from_id'] > 0) or merge_cnts > 1),
          'is_copied': bool((record['is_copied_from_id'] and record['is_copied_from_id'] > 0)),
          'same_order_num_cnts': merge_cnts,
          'merge_enabled': record['merge_enabled'],

          'merge_radio_disable': record['is_copied_from_id'] is None
        }

        _results.append(_object)

  except Exception:
      current_app.logger.exception("list_wait_for_assemble failed")
      return jsonify(success=False), 500

  temp_len = len(_results)
  print("listMaterials, 總數: ", temp_len)
  if (temp_len == 0):
      return_value = False

  ## 根據 isTakeOk 屬性的值進行排序
  #_results = sorted(_results, key=lambda x: not x['isTakeOk'])
  ## 根據 'order_num' 排序
  #_results = sorted(_results, key=lambda x: x['order_num'])
  # 根據 order_num 升序，再根據 isTakeOk 降序 (True > False)
  _results.sort(key=lambda x: (x['order_num'], not x['isTakeOk']))

  return jsonify({
    'status': return_value,
    'materials': _results
  })
"""


# list all materials
@listTable.route("/listMaterials", methods=['GET'])
def list_materials():
    print("listMaterials....")

    _results = []
    return_value = True

    s = Session()
    try:
        # 1) 每個 order_num 的筆數（只算 move_by_process_type == 2）
        order_cnt_subq = (
            s.query(
                Material.order_num.label("order_num"),
                func.count(Material.id).label("same_order_num_cnts")
            )
            .filter(Material.move_by_process_type == 2)
            .group_by(Material.order_num)
            .subquery()
        )

        # 2) 只查這支 API 需要的欄位，直接 join 筆數
        rows = (
            s.query(
                Material.id,
                Material.order_num,
                Material.material_num,
                Material.material_qty,
                Material.delivery_qty,
                Material.total_delivery_qty,
                Material.input_disable,
                Material.material_date,
                Material.material_delivery_date,
                Material.shortage_note,
                Material.material_comment,

                Material.isOpen,
                Material.isOpenEmpId,
                Material.hasStarted,
                Material.startStatus,

                Material.isTakeOk,
                Material.isLackMaterial,
                Material.isBatchFeeding,
                Material.isShow,
                Material.whichStation,
                Material.show1_ok,
                Material.show2_ok,
                Material.show3_ok,
                Material.Incoming0_Abnormal,
                Material.is_copied_from_id,
                Material.merge_enabled,

                func.coalesce(order_cnt_subq.c.same_order_num_cnts, 0).label("same_order_num_cnts")
            )
            .outerjoin(order_cnt_subq, order_cnt_subq.c.order_num == Material.order_num)
            .filter(Material.move_by_process_type == 2)
            .filter(Material.isShow.is_(False))
            .order_by(Material.order_num.asc(), Material.isTakeOk.desc())
            .all()
        )

        for row in rows:
            cleaned_comment = (row.material_comment or "").strip()
            merge_cnts = int(row.same_order_num_cnts or 0)

            _object = {
                'id': row.id,
                'order_num': row.order_num,
                'material_num': row.material_num,
                'req_qty': row.material_qty,
                'delivery_qty': row.delivery_qty,
                'total_delivery_qty': row.total_delivery_qty,
                'input_disable': row.input_disable,
                'date': row.material_date,
                'delivery_date': row.material_delivery_date,
                'shortage_note': row.shortage_note,
                'comment': cleaned_comment,

                'isOpen': row.isOpen,
                'isOpenEmpId': row.isOpenEmpId,
                'hasStarted': row.hasStarted,
                'startStatus': row.startStatus,

                'isTakeOk': row.isTakeOk,
                'isLackMaterial': row.isLackMaterial,
                'isBatchFeeding': row.isBatchFeeding,
                'isShow': row.isShow,
                'whichStation': row.whichStation,
                'show1_ok': row.show1_ok,
                'show2_ok': row.show2_ok,
                'show3_ok': row.show3_ok,
                'Incoming0_Abnormal': row.Incoming0_Abnormal == '',
                'Incoming0_Abnormal_message': row.Incoming0_Abnormal,

                'is_copied': bool(row.is_copied_from_id and row.is_copied_from_id > 0),
                'same_order_num_cnts': merge_cnts,
                'merge_enabled': row.merge_enabled,

                'merge_radio_disable': row.is_copied_from_id is None,
            }

            _results.append(_object)

    except Exception:
        current_app.logger.exception("listMaterials failed")
        s.close()
        return jsonify(success=False), 500

    finally:
        s.close()

    temp_len = len(_results)
    print("listMaterials, 總數: ", temp_len)
    if temp_len == 0:
        return_value = False

    return jsonify({
        'status': return_value,
        'materials': _results
    })


# list working order status in the material table
@listTable.route("/listWorkingOrderStatus", methods=['GET'])
def list_working_order_status():
    print("listWorkingOrderStatus....")

    s = Session()
    '''
    #_objects = s.query(Material).with_for_update().all()
    _objects = s.query(Material).filter(func.date(Material.create_at) == func.current_date()).all()
    # 針對當天資料，計算 order_count、prepare_count、assemble_count、warehouse_count
    order_counts = (
      s.query(
        Material.order_num,
        func.count().label("order_count"),  # 總數
        func.sum(func.if_(Material.isShow == True, 1, 0)).label("prepare_count"),  # isShow = True
        func.sum(func.if_(Material.isAssembleStationShow == True, 1, 0)).label("assemble_count"),  # isAssembleStationShow = True
        func.sum(func.if_(Material.isAllOk == True, 1, 0)).label("warehouse_count")  # isAllOk = True
      )
      .filter(func.date(Material.create_at) == func.current_date())  # 當天資料
      .group_by(Material.order_num)  # 按 order_num 分組
      .all()
    )

    # 轉換成字典格式
    result = {
      order_num: {
        "order_count": order_count,
        "prepare_count": prepare_count,
        "assemble_count": assemble_count,
        "warehouse_count": warehouse_count
      }
      for order_num, order_count, prepare_count, assemble_count, warehouse_count in order_counts
    }

    for order_num, order_count, prepare_count, assemble_count, warehouse_count in order_counts:
      print(f"Order: {order_num}, Order Count: {order_count}, Prepare: {prepare_count}, Assemble: {assemble_count}, Warehouse: {warehouse_count}")
    '''

    '''
    # 1️⃣ 計算不同 order_num 的數量
    order_count = s.query(func.count(distinct(Material.order_num))).scalar()

    # 2️⃣ prepare_count：所有 isShow 都是 True 的 order_num
    prepare_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(~s.query(Material).filter(Material.order_num == Material.order_num, Material.isShow == False).exists())
        .scalar()
    )

    # 3️⃣ assemble_count：所有 isAssembleStationShow 都是 True 的 order_num
    assemble_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(~s.query(Material).filter(Material.order_num == Material.order_num, Material.isAssembleStationShow == False).exists())
        .scalar()
    )

    # 4️⃣ warehouse_count：所有 isAllOk 都是 True 的 order_num
    warehouse_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(~s.query(Material).filter(Material.order_num == Material.order_num, Material.isAllOk == False).exists())
        .scalar()
    )
    '''

    '''
    # 1️⃣ 計算不同 order_num 的數量
    order_count = s.query(func.count(distinct(Material.order_num))).scalar()

    # 2️⃣ prepare_count：至少有一筆 isShow=True 的 order_num 數量
    prepare_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(Material.isShow == True)
        .scalar()
    )

    # 3️⃣ assemble_count：至少有一筆 isAssembleStationShow=True 的 order_num 數量
    assemble_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(Material.isAssembleStationShow == True)
        .scalar()
    )

    # 4️⃣ warehouse_count：至少有一筆 isAllOk=True 的 order_num 數量
    warehouse_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(Material.isAllOk == True)
        .scalar()
    )
    '''

    today = date.today()  # 取得今天的日期
    print("today:",today)

    '''
    # 1️⃣ 計算不同 order_num 的數量
    order_count = s.query(func.count(distinct(Material.order_num))) \
        .filter(func.date(Material.create_at) == today) \
        .scalar()
    '''

    '''
    # 後 2 週的最後一天（2 週 = 14 天，包含今天與結束當天）
    post_14_day = today + timedelta(days=13)
    print("post_14_day:", post_14_day)

    # 如果你原本是只用今天來算，現在改成「今天到後 2 週」這段期間：
    order_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(func.date(Material.material_delivery_date).between(today, post_14_day))
        .scalar()
    )
    '''

    today = date.today()
    post_14_day = today + timedelta(days=13)

    order_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(
            func.str_to_date(Material.material_delivery_date, '%Y-%m-%d')
            .between(today, post_14_day)
        )
        .scalar()
    )

    '''
    prepare_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(
            func.str_to_date(Material.material_delivery_date, '%Y-%m-%d')
            .between(today, post_14_day)
        )
        .filter(Material.isShow==False )
        .scalar()
    )
    '''

    # 子查詢：找出符合條件的 material_id
    step_1_material_ids_subq = (
        s.query(Process.material_id)
        .filter(
            Process.process_type == 1,
            Process.has_started == 1,
            Process.begin_time != '',               # 有開始時間
            or_(Process.end_time == '', Process.end_time.is_(None))  # 沒有結束時間
        )
        .distinct()
        .subquery()
    )

    prepare_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(
            func.str_to_date(Material.material_delivery_date, '%Y-%m-%d')
            .between(today, post_14_day)
        )
        .filter(
           Material.id.in_(
            select(step_1_material_ids_subq.c.material_id)
          )    # Material.id 在「這些有 step1 未結束 process」的 material_id
        )
        .scalar()
    )

    step_21_22_23_material_ids_subq = (
        s.query(Process.material_id)
        .filter(
            Process.process_type.in_([21, 22, 23]),
            Process.has_started == 1,
            Process.begin_time != '',               # 有開始時間
            or_(Process.end_time == '', Process.end_time.is_(None))  # 沒有結束時間
        )
        .distinct()
        .subquery()
    )

    assemble_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(
            func.str_to_date(Material.material_delivery_date, '%Y-%m-%d')
            .between(today, post_14_day)
        )
        .filter(
          Material.id.in_(
            select(step_21_22_23_material_ids_subq.c.material_id)
          )   # Material.id 在「這些有 step_21_22_23 未結束 process」的 material_id
        )
        .scalar()
    )

    # 先找出「有 process_type = 31」的 material_id
    type_31_material_ids_subq = (
        s.query(Process.material_id)
        .filter(Process.process_type == 31)
        .distinct()
        .subquery()
    )

    # 再找「有 process_type 3 或 6，且已完成(begin/end都有)，且『沒有 31』」的 material_id
    step_31_material_ids_subq = (
        s.query(Process.material_id)
        .filter(
          Process.process_type.in_([3, 6]),                     # ✅ 有 3 或 6
          Process.begin_time != '',                             # ✅ 有開始時間
          Process.end_time != '',                               # ✅ 有結束時間
          ~Process.material_id.in_(                             # ❌ 沒有任何一筆 type 31
            select(type_31_material_ids_subq.c.material_id)
          )
        )
        .distinct()
        .subquery()
    )

    warehouse_count = (
      s.query(func.count(distinct(Material.order_num)))
      .filter(
        func.str_to_date(Material.material_delivery_date, '%Y-%m-%d')
        .between(today, post_14_day)
      )
      .filter(
        Material.id.in_(
          select(step_31_material_ids_subq.c.material_id)
        )   # Material.id 在「這些有 step_31 未結束 process」的 material_id
      )
      .scalar()
    )

    '''
    # 2️⃣ prepare_count：該 order_num 內所有 isShow = True
    prepare_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(func.date(Material.create_at) == today)
        .filter(~Material.order_num.in_(
            s.query(Material.order_num)
            .group_by(Material.order_num)
            .having(func.sum(case((Material.isShow == False, 1), else_=0)) > 0)  # 如果該 order_num 內有 False，就排除
        ))
        .scalar()
    )
    '''

    '''
    # 子查詢：找出「底下所有料件 isShow 都是 False」的訂單
    all_false_order_subq = (
        s.query(Material.order_num)
        .group_by(Material.order_num)
        .having(
            # 這個訂單底下：isShow == True 的筆數總和 == 0
            func.sum(
                case(
                    (Material.isShow == True, 1),   # True 算 1
                    else_=0                         # 其它（False）算 0
                )
            ) == 0,
            # 並且至少要有一筆料件，避免奇怪的空 group
            func.count(Material.id) > 0
        )
    )

    print("all_false_order_subq:", all_false_order_subq)

    prepare_count = (
        s.query(func.count(distinct(Material.order_num)))
        # 1️⃣ 交期在「今天 ~ 14 天後」之間
        .filter(
            func.str_to_date(Material.material_delivery_date, '%Y/%m/%d')
            .between(today, post_14_day)
        )
        # 2️⃣ 只保留「全部 isShow 都是 False 的訂單」
        .filter(
            Material.order_num.in_(all_false_order_subq)
        )
        .scalar()
    )
    '''

    '''
    # 3️⃣ assemble_count：該 order_num 內所有 isAssembleStationShow = True
    assemble_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(func.date(Material.create_at) == today)
        .filter(~Material.order_num.in_(
            s.query(Material.order_num)
            .group_by(Material.order_num)
            .having(func.sum(case((Material.isAssembleStationShow == False, 1), else_=0)) > 0)
        ))
        .scalar()
    )
    '''

    """
    # 4️⃣ warehouse_count：該 order_num 內所有 isAllOk = True
    warehouse_count = (
        s.query(func.count(distinct(Material.order_num)))
        .filter(func.date(Material.create_at) == today)
        .filter(~Material.order_num.in_(
            s.query(Material.order_num)
            .group_by(Material.order_num)
            .having(func.sum(case((Material.isAllOk == False, 1), else_=0)) > 0)
        ))
        .scalar()
    )
    """

    # 組裝結果
    result = {
        "order_count": order_count,
        "prepare_count": prepare_count,
        "assemble_count": assemble_count,
        "warehouse_count": warehouse_count,
    }

    print(result)

    s.close()
    return jsonify(result)


@listTable.route("/listWorkingOrderStatusP", methods=['GET'])
def list_working_order_status_p():
  print("listWorkingOrderStatusP....")

  s = Session()

  today = date.today()  # 取得今天的日期
  post_14_day = today + timedelta(days=13)  #間格2星期
  """
  order_count = (
    s.query(func.count(distinct(P_Material.order_num)))
    .filter(
      func.str_to_date(P_Material.material_delivery_date, '%Y-%m-%d')
      .between(today, post_14_day)
    )
    .scalar()
  )
  """
  rows = (
      s.query(distinct(P_Material.order_num))
      .filter(
          func.str_to_date(P_Material.material_delivery_date, '%Y-%m-%d')
          .between(today, post_14_day)
      )
      .all()
  )
  order_num_list = [r[0] for r in rows if r[0]]
  order_count = len(order_num_list)

  # 子查詢：找出符合條件的 material_id
  step_1_material_ids_subq = (
    s.query(P_Process.material_id)
    .filter(
      P_Process.process_type == 1,
      P_Process.has_started == 1,
      P_Process.begin_time != '',               # 有開始時間
      or_(P_Process.end_time == '', P_Process.end_time.is_(None))  # 沒有結束時間
    )
    .distinct()
    .subquery()
  )

  prepare_count = (
    s.query(func.count(distinct(P_Material.order_num)))
    .filter(
      func.str_to_date(P_Material.material_delivery_date, '%Y-%m-%d')
      .between(today, post_14_day)
    )
    .filter(
      P_Material.id.in_(
        select(step_1_material_ids_subq.c.material_id)
      )    # Material.id 在「這些有 step1 未結束 process」的 material_id
    )
    .scalar()
  )

  step_not_01_05_06_31_material_ids_subq = (
    s.query(P_Process.material_id)
    .filter(
      ~P_Process.process_type.in_([1, 5, 6, 31]),   # ✅ 不包含 01/05/06/31
      P_Process.has_started == 1,                   # ✅ 已開始
      P_Process.begin_time != '',                   # 有開始時間
      or_(P_Process.end_time == '', P_Process.end_time.is_(None))  # 沒有結束時間
    )
    .distinct()
    .subquery()
  )

  assemble_count = (
    s.query(func.count(distinct(P_Material.order_num)))
    .filter(
      func.str_to_date(P_Material.material_delivery_date, '%Y-%m-%d')
      .between(today, post_14_day)
    )
    .filter(
      P_Material.id.in_(
        select(step_not_01_05_06_31_material_ids_subq.c.material_id)
      )   # Material.id 在「這些有 step_21_22_23 未結束 process」的 material_id
    )
    .scalar()
  )

  # 先找出「有 process_type = 31」的 material_id
  type_31_material_ids_subq = (
    s.query(P_Process.material_id)
    .filter(P_Process.process_type == 31)
    .distinct()
    .subquery()
  )

  # 再找「有 process_type 3 或 6，且已完成(begin/end都有)，且『沒有 31』」的 material_id
  step_31_material_ids_subq = (
    s.query(P_Process.material_id)
    .filter(
      P_Process.process_type.in_([3, 6]),                     # ✅ 有 3 或 6
      P_Process.begin_time != '',                             # ✅ 有開始時間
      P_Process.end_time != '',                               # ✅ 有結束時間
      ~P_Process.material_id.in_(                             # ❌ 沒有任何一筆 type 31
        select(type_31_material_ids_subq.c.material_id)
      )
    )
    .distinct()
    .subquery()
  )

  warehouse_count = (
    s.query(func.count(distinct(P_Material.order_num)))
    .filter(
      func.str_to_date(P_Material.material_delivery_date, '%Y-%m-%d')
      .between(today, post_14_day)
    )
    .filter(
      P_Material.id.in_(
        select(step_31_material_ids_subq.c.material_id)
      )   # Material.id 在「這些有 step_31 未結束 process」的 material_id
    )
    .scalar()
  )

  # 組裝結果
  result = {
    "order_count": order_count,
    "prepare_count": prepare_count,
    "assemble_count": assemble_count,
    "warehouse_count": warehouse_count,
    "order_num_list": order_num_list,
  }

  print(result)

  s.close()
  return jsonify(result)


# list some data in the material table
@listTable.route("/listWaitForAssemble", methods=['GET'])
def list_wait_for_assemble():
    #print("listWaitForAssemble....")

    begin_count = 0
    end_count = 0
    allOk_count = 0

    nums = set()

    # 初始化一個暫存字典來存放每個 order_num 下的最大 process_step_code
    max_step_code_per_order = {}

    def safe_str(v, default=''):
      try:
          return '' if v is None else str(v)
      except Exception:
          return default

    s = Session()
    try:
      with s.begin():  # 這裡回傳的是 SessionTransaction，仍然用 s 來查詢
        _objects = s.query(Material).all()

        # 搜尋所有紀錄，找出每個訂單下最大的 process_step_code
        for material_record in _objects:  # loop_0
          for assemble_record in material_record._assemble:
            step_code = assemble_record.process_step_code   # 直接使用資料中的 step_code
            order_num_id = material_record.id               # 該筆訂單編號的table id

            # 設定或更新該 order_num_id 下的最大 step code
            if order_num_id not in max_step_code_per_order:
              max_step_code_per_order[order_num_id] = step_code
            else:
              current_max = max_step_code_per_order[order_num_id]
              max_step_code_per_order[order_num_id] = max(current_max, step_code)
        # end loop_0

        code_to_pt = {'106': 23, '109': 21, '110': 22}

        for material_record in _objects:  # loop_1

          if not material_record.isShow or material_record.isAssembleStationShow :   # 檢查 isShow 是否為 False
            continue

          assemble_records = s.query(Assemble).filter_by(material_id=material_record.id).all()
          #record_count = len(assemble_records)
          #print("筆數:", record_count)

          for end_assemble_record in assemble_records:  # loop_2_a
            if (end_assemble_record.input_disable and
                not end_assemble_record.input_end_disable
              ):

              end_count += 1
          # end loop_2_a

          pre_step_code = 99
          for begin_assemble_record in assemble_records:  # loop_2_b
            if begin_assemble_record.input_disable:
              continue

            work_num = safe_str(begin_assemble_record.work_num)     # 可能為 ''（避免 None）
            code = work_num[1:] if len(work_num) >= 2 else work_num
            pt =code_to_pt.get(code, 0)
            ok, process_total = need_more_process_qty(k1=begin_assemble_record.material_id, a1=begin_assemble_record.id, t1=pt, must_qty=begin_assemble_record.must_receive_end_qty, s=s)
            # ok 為 True 代表 process_total < 50；False 代表已達標或超過
            #print("ok:", ok, process_total)
            if not ok and process_total !=0:
              continue

              #if int(begin_assemble_record.isAssembleStationShow or 0) == 1 and all_zero_by_mid.get(mid, False):
              #    continue

            step_code = begin_assemble_record.process_step_code
            max_step_code = max_step_code_per_order.get(material_record.id, 0)
            step_enable = (step_code == max_step_code and material_record.whichStation==2)

            skip_condition = (not step_enable or begin_assemble_record.input_disable)
            if skip_condition:
                if pre_step_code == 0 and step_code != 0:
                    pre_step_code = step_code
                    pass  # 不跳過，繼續執行後續程式
                else:
                    pre_step_code = step_code
                    continue
            #
            # 缺料併單
            if material_record.isLackMaterial == 0 and material_record.is_copied_from_id and material_record.is_copied_from_id > 0:
              continue

            begin_count += 1
          # end loop_2_b
        # end loop_1
    except Exception:
        #s.rollback()
        current_app.logger.exception("list_wait_for_assemble failed")
        return jsonify(success=False), 500
    #finally:
    #    # 若在 app.py 有 @app.teardown_appcontext -> Session.remove()，這裡可省略
    #    Session.remove()
    ##s.close()
    print("begin_count:", begin_count)
    return jsonify({
      'begin_count': begin_count,
      'end_count': end_count
    })


# list all Warehouse For Assemble
@listTable.route("/listWarehouseForAssemble", methods=['GET'])
def list_Warehouse_For_assemble():
    print("listWarehouseForAssemble....")

    s = Session()

    _results = []
    return_value = True

    materials = [u.__dict__ for u in s.query(Material).all()]
    processed_order_nums = set()

    # 篩選 isAssembleStationShow 為 True 的資料
    filtered_materials = [record for record in materials if record['isAssembleStationShow']]
    for record in filtered_materials:
      cleaned_comment = record['material_comment'].strip()  # 刪除 material_comment 字串前後的空白

      _object = {
        'id': record['id'],
        'order_num': record['order_num'],                   #訂單編號
        'material_num': record['material_num'],             #物料編號
        'req_qty': record['material_qty'],                  #訂單數量
        'date': record['material_delivery_date'],           #交期
        'delivery_qty': record['assemble_qty'],             #組裝完成數量(到庫數量)
        'allOk_qty': record['allOk_qty'],                   #確認完成數量
        'total_allOk_qty': record['total_allOk_qty'],
        'input_disable': record['input_disable'],
        'delivery_date':record['material_delivery_date'],   #交期
        'shortage_note': record['shortage_note'],           #缺料註記 '元件缺料'
        'comment': cleaned_comment,                         #說明
        'isTakeOk' : record['isAllOk'],                     #true:成品已入庫
        'isShow' : record['isAssembleStationShow'],         #false:歷史檔案
        'isLackMaterial' : record['isLackMaterial'],
        'isBatchFeeding' :  record['isBatchFeeding'],
        'whichStation' : record['whichStation'],
        'show1_ok' : record['show1_ok'],
        'show2_ok' : record['show2_ok'],
        'show3_ok' : record['show3_ok'],
      }

      _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listWarehouseForAssemble, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 isTakeOk 屬性的值進行排序
    _results = sorted(_results, key=lambda x: not x['isTakeOk'])

    return jsonify({
      'status': return_value,
      'warehouse_for_assemble': _results
    })


"""
# list all materials and assemble data for process
@listTable.route("/listMaterialsAndAssemblesP", methods=['GET'])
def list_materials_and_assembles_p():
    print("listMaterialsAndAssemblesP....")

    _results = []
    _assemble_active_users = []

    def safe_str(v, default=''):
        try:
            return '' if v is None else str(v)
        except Exception:
            return default

    s = Session()

    try:
        _objects = s.query(P_Material).all()
        material_ids_all = [m.id for m in _objects]

        # 預先把 p_part table讀成 dict：
        # key = 去空白後的 part_code
        # value = {'comment': part_comment, 'process_step_code': process_step_code}
        part_info_map = {}
        for p in s.query(P_Part).all():
            code = (p.part_code or '').strip()
            if not code:
                continue
            part_info_map[code] = {
                'comment': (p.part_comment or '').strip(),
                'process_step_code': int(p.process_step_code or 0)
            }

        # 每個 material 的最小 seq_num
        min_seqnum_per_order = {}  # key: (material_id, update_time) -> (最小 seq_num, assemble_id)
        for material_record in _objects:
          for assemble_record in material_record._assemble:
            if assemble_record.process_step_code != 0:
              key = (assemble_record.material_id, assemble_record.update_time)
              seq = int(assemble_record.seq_num or 0)

              cur = min_seqnum_per_order.get(key)  # cur 可能是 None 或 (seq, id)
              if cur is None:
                min_seqnum_per_order[key] = (seq, assemble_record.id)
              else:
                cur_seq, cur_id = cur
                if seq < cur_seq:
                  min_seqnum_per_order[key] = (seq, assemble_record.id)
        #print("min_seqnum_per_order:",min_seqnum_per_order)

        # 每個 material_id 在「process_step_code != 0」下，最小 seq_num 的 assemble_id
        min_seqnum_assemble_id_by_material = {}  # key: material_id -> assemble_id
        for material_record in _objects:
          best = None
          best_seq = None
          for a in material_record._assemble:
            step = int(a.process_step_code or 0)
            if step == 0:
              continue  # 只看 process_step_code <> 0

            seq = int(a.seq_num or 0)

            if best is None or seq < best_seq:
              best = a
              best_seq = seq

          if best is not None:
            min_seqnum_assemble_id_by_material[int(material_record.id)] = int(best.id)

        index = 0
        for material_record in _objects:
            #print("step 1...",material_record.id)
            if not material_record.isShow:    #true:領料完成且已call AGV
              continue

            # 加工線已上線的筆數
            process_records = material_record._process
            total_records =len([p for p in process_records if ((p.material_id == material_record.id and p.assemble_id != 0))])

            for assemble_record in material_record._assemble:
                #print("step 2...", assemble_record.id)

                if assemble_record.must_receive_qty <= 0:   #應領取數量
                  continue
                #print("step 3...")

                # --- 規則：isSimultaneously=False 時，只保留同 material_id 最小 seq_num 且 step != 0 的那筆 ---
                step = int(assemble_record.process_step_code or 0)
                if step == 0:
                  continue

                is_simul = bool(assemble_record.isSimultaneously)  # 0/1 轉 bool
                if not is_simul:
                  keep_id = min_seqnum_assemble_id_by_material.get(int(assemble_record.material_id))
                  if keep_id and int(assemble_record.id) != int(keep_id):
                    continue

                matched_count = 0
                total_work_qty = 0      # 累加 process_work_time_qty
                show_timer = False      # 是否顯示計時器
                show_name = ''          # 要顯示的 user_id

                # === 從 p_part 對照 work_num，取得 show_message (part_comment) 與 show_code (process_step_code) ===
                work_num_clean = (assemble_record.work_num or '').strip()

                part_info = part_info_map.get(work_num_clean)

                show_comment = part_info['comment']
                show_code    = part_info['process_step_code']

                # 這裡一定要是 list，不是數字！
                target_procs = [
                  p for p in process_records
                  if (
                    p.material_id == assemble_record.material_id
                    and p.process_type == show_code
                    and p.assemble_id == assemble_record.id
                    and p.begin_time
                    and str(p.begin_time).strip()
                  )
                ]

                matched_count = len(target_procs)
                #print("matched_count:",matched_count)
                total_work_qty = sum((p.process_work_time_qty or 0) for p in target_procs)

                # a_statement: step != 0 且有對應 process，且已報工數量 >= 交期數量
                a_statement = (
                    show_code != 0
                    and total_records != 0
                    and matched_count > 0
                    and total_work_qty >= (material_record.delivery_qty or 0)
                )
                # 1) 已結束 step（process_step_code = 0）不顯示
                # 2) 報工數量已經 >= 交期數量的不顯示
                #if step == 0 or (step != 0 and matched_count == 0 and total_records != 0) or a_statement:
                #if step == 0 or assemble_record.user_id:

                #print("step 5...", show_code, a_statement)

                # ---- 安全取值區 ----
                cleaned_comment = safe_str(material_record.material_comment).strip()

                index += 1
                _object = {
                    'index': index,
                    'id': material_record.id,
                    'order_num': material_record.order_num,
                    'assemble_work': show_comment,
                    'material_num': material_record.material_num,
                    'assemble_id': assemble_record.id,
                    'req_qty': material_record.material_qty,

                    'delivery_qty': material_record.delivery_qty,
                    'total_receive_qty': f"({getattr(assemble_record, 'total_ask_qty', 0)})",
                    'total_receive_qty_num': getattr(assemble_record, 'total_ask_qty', 0),

                    #'must_receive_qty': assemble_record.must_receive_qty,
                    #'receive_qty': assemble_record.must_receive_qty,
                    'must_receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'receive_qty': getattr(assemble_record, 'must_receive_qty', 0),

                    'must_receive_end_qty': assemble_record.must_receive_end_qty,

                    'delivery_date': material_record.material_delivery_date,
                    'comment': cleaned_comment,
                    'isTakeOk': material_record.isTakeOk,
                    #'whichStation': material_record.whichStation,
                    'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,
                    'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,
                    'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,
                    'currentStartTime': getattr(assemble_record, 'currentStartTime', None),
                    'tooltipVisible': False,
                    'input_disable': getattr(assemble_record, 'input_disable', False),
                    'Incoming1_Abnormal': getattr(assemble_record, 'Incoming1_Abnormal', '') == '',
                    'is_copied_from_id': getattr(assemble_record, 'is_copied_from_id', None),
                    'create_at': assemble_record.create_at,
                    'show_timer': show_timer,
                    'show_name': show_name,
                    'isShowBomGif': assemble_record.isShowBomGif,
                    'process_step_code': assemble_record.process_step_code,
                    'isStockIn': '' if assemble_record.isStockIn else ' [不入庫]',
                    'assemble_process_num': int(assemble_record.show2_ok),
                }
                _results.append(_object)

        print("kkkkaaa _results length:",_results, len(_results))
        # 只有在前面的 _results 成功建好後，才去算使用中人數
        #from sqlalchemy import or_ as _or

        s.close()

        # 先依 id（升冪）排一次
        _results.sort(key=lambda x: x.get('id') or 0)

        # 再依 create_at（降冪）排一次 → 穩定排序會保留同日期下的 id 排序
        _results.sort(key=lambda x: x.get('create_at') or datetime.min, reverse=True)

        return jsonify({
            'status': bool(_results),
            'materials_and_assembles': _results or [],
            'assemble_active_users': _assemble_active_users or [],
        })

    except Exception as e:
        # 任何資料不乾淨都不讓它 500；記 log + 回傳空清單，避免前端炸掉
        import traceback
        print("listMaterialsAndAssemblesP ERROR:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("listMaterialsAndAssemblesP failed")
        except Exception:
            pass
        s.close()
        return jsonify({
            'status': False,
            'materials_and_assembles': [],
            'assemble_active_users': [],
        }), 200
"""


# list all materials and assemble data for process
@listTable.route("/listMaterialsAndAssemblesP", methods=['GET'])
def list_materials_and_assembles_p():
    print("listMaterialsAndAssemblesP....")

    _results = []
    _assemble_active_users = []

    def safe_str(v, default=''):
        try:
            return '' if v is None else str(v)
        except Exception:
            return default

    def norm_code(v):
        return (v or '').strip()

    s = Session()

    try:
        # ------------------------------------------------------------
        # 1) 只撈需要顯示的 P_Material，並一次載入關聯，避免 N+1
        # ------------------------------------------------------------
        _objects = (
            s.query(P_Material)
             .filter(P_Material.isShow.is_(True))
             .options(
                 selectinload(P_Material._assemble).load_only(
                     P_Assemble.id,
                     P_Assemble.material_id,
                     P_Assemble.must_receive_qty,
                     P_Assemble.must_receive_end_qty,
                     P_Assemble.total_ask_qty,
                     P_Assemble.work_num,
                     P_Assemble.process_step_code,
                     P_Assemble.isSimultaneously,
                     P_Assemble.seq_num,
                     P_Assemble.currentStartTime,
                     P_Assemble.input_disable,
                     P_Assemble.Incoming1_Abnormal,
                     P_Assemble.is_copied_from_id,
                     P_Assemble.create_at,
                     P_Assemble.isShowBomGif,
                     P_Assemble.isStockIn,
                     P_Assemble.show2_ok,
                 ),
                 selectinload(P_Material._process).load_only(
                     P_Process.id,
                     P_Process.material_id,
                     P_Process.assemble_id,
                     P_Process.process_type,
                     P_Process.begin_time,
                     P_Process.process_work_time_qty,
                     P_Process.user_id,
                 ),
             )
             .all()
        )

        if not _objects:
            return jsonify({
                'status': False,
                'materials_and_assembles': [],
                'assemble_active_users': [],
            })

        # ------------------------------------------------------------
        # 2) p_part 一次轉 dict，只留真的需要的欄位
        # ------------------------------------------------------------
        part_info_map = {}
        part_rows = (
            s.query(
                P_Part.part_code,
                P_Part.part_comment,
                P_Part.process_step_code
            ).all()
        )

        for part_code, part_comment, process_step_code in part_rows:
            code = norm_code(part_code)
            if not code:
                continue
            part_info_map[code] = {
                'comment': (part_comment or '').strip(),
                'process_step_code': int(process_step_code or 0),
            }

        # ------------------------------------------------------------
        # 3) 主迴圈：每個 material 只做一次預處理
        # ------------------------------------------------------------
        index = 0

        for material_record in _objects:
            assemble_records = list(material_record._assemble or [])
            process_records = list(material_record._process or [])

            # 加工線已上線的筆數（保留你原本邏輯）
            total_records = sum(
                1 for p in process_records
                if p.material_id == material_record.id and (p.assemble_id or 0) != 0
            )

            # --------------------------------------------------------
            # 3-1) 算「同 material_id 最小 seq_num 的 assemble_id」
            #      只看 process_step_code != 0
            # --------------------------------------------------------
            keep_assemble_id = None
            keep_seq = None

            for a in assemble_records:
                step = int(a.process_step_code or 0)
                if step == 0:
                    continue

                seq = int(a.seq_num or 0)
                if keep_assemble_id is None or seq < keep_seq:
                    keep_assemble_id = int(a.id)
                    keep_seq = seq

            # --------------------------------------------------------
            # 3-2) 預先把 process_records 彙總成 map
            #      key = (assemble_id, process_type)
            #      value = {count, qty_sum, last_user_id}
            # --------------------------------------------------------
            proc_stat_map = {}

            for p in process_records:
                if p.material_id != material_record.id:
                    continue

                aid = int(p.assemble_id or 0)
                ptype = int(p.process_type or 0)

                if aid == 0 or ptype == 0:
                    continue

                # 只有有 begin_time 的才算，保留你原本 target_procs 篩法
                if not p.begin_time or not str(p.begin_time).strip():
                    continue

                key = (aid, ptype)
                if key not in proc_stat_map:
                    proc_stat_map[key] = {
                        'count': 0,
                        'qty_sum': 0,
                        'last_proc_id': 0,
                        'last_user_id': '',
                    }

                proc_stat_map[key]['count'] += 1
                proc_stat_map[key]['qty_sum'] += int(p.process_work_time_qty or 0)

                pid = int(p.id or 0)
                if pid >= proc_stat_map[key]['last_proc_id']:
                    proc_stat_map[key]['last_proc_id'] = pid
                    proc_stat_map[key]['last_user_id'] = p.user_id or ''

            cleaned_comment = safe_str(material_record.material_comment).strip()

            # --------------------------------------------------------
            # 3-3) 組結果
            # --------------------------------------------------------
            for assemble_record in assemble_records:
                must_receive_qty = int(getattr(assemble_record, 'must_receive_qty', 0) or 0)
                if must_receive_qty <= 0:
                    continue

                step = int(assemble_record.process_step_code or 0)
                if step == 0:
                    continue

                is_simul = bool(assemble_record.isSimultaneously)
                if not is_simul and keep_assemble_id is not None:
                    if int(assemble_record.id) != keep_assemble_id:
                        continue

                work_num_clean = norm_code(assemble_record.work_num)
                part_info = part_info_map.get(work_num_clean, {
                    'comment': '',
                    'process_step_code': 0,
                })

                show_comment = part_info.get('comment', '')
                show_code = int(part_info.get('process_step_code', 0) or 0)

                stat = proc_stat_map.get((int(assemble_record.id), show_code), {
                    'count': 0,
                    'qty_sum': 0,
                    'last_user_id': '',
                })

                matched_count = int(stat['count'] or 0)
                total_work_qty = int(stat['qty_sum'] or 0)

                show_timer = False
                show_name = ''

                if matched_count > 0:
                    show_timer = True
                    show_name = stat.get('last_user_id', '') or ''

                # 保留你原本邏輯，即使目前沒有拿來 continue
                a_statement = (
                    show_code != 0
                    and total_records != 0
                    and matched_count > 0
                    and total_work_qty >= int(material_record.delivery_qty or 0)
                )

                index += 1
                _object = {
                    'index': index,
                    'id': material_record.id,
                    'order_num': material_record.order_num,
                    'assemble_work': show_comment,
                    'material_num': material_record.material_num,
                    'assemble_id': assemble_record.id,
                    'req_qty': material_record.material_qty,

                    'delivery_qty': material_record.delivery_qty,
                    'total_receive_qty': f"({getattr(assemble_record, 'total_ask_qty', 0)})",
                    'total_receive_qty_num': getattr(assemble_record, 'total_ask_qty', 0),

                    'must_receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'receive_qty': getattr(assemble_record, 'must_receive_qty', 0),

                    'must_receive_end_qty': assemble_record.must_receive_end_qty,

                    'delivery_date': material_record.material_delivery_date,
                    'comment': cleaned_comment,
                    'isTakeOk': material_record.isTakeOk,

                    'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,
                    'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,
                    'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,

                    'currentStartTime': getattr(assemble_record, 'currentStartTime', None),
                    'tooltipVisible': False,
                    'input_disable': getattr(assemble_record, 'input_disable', False),
                    'Incoming1_Abnormal': getattr(assemble_record, 'Incoming1_Abnormal', '') == '',
                    'is_copied_from_id': getattr(assemble_record, 'is_copied_from_id', None),
                    'create_at': assemble_record.create_at,
                    'show_timer': show_timer,
                    'show_name': show_name,
                    'isShowBomGif': assemble_record.isShowBomGif,
                    'process_step_code': assemble_record.process_step_code,
                    'isStockIn': '' if assemble_record.isStockIn else ' [不入庫]',
                    'assemble_process_num': int(assemble_record.show2_ok or 0),
                }
                _results.append(_object)

        print("kkkkaaa _results length:", len(_results))

        # 原本排序保留
        _results.sort(key=lambda x: x.get('id') or 0)
        _results.sort(key=lambda x: x.get('create_at') or datetime.min, reverse=True)

        return jsonify({
            'status': bool(_results),
            'materials_and_assembles': _results or [],
            'assemble_active_users': _assemble_active_users or [],
        })

    except Exception as e:
        import traceback
        print("listMaterialsAndAssemblesP ERROR:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("listMaterialsAndAssemblesP failed")
        except Exception:
            pass
        return jsonify({
            'status': False,
            'materials_and_assembles': [],
            'assemble_active_users': [],
        }), 200

    finally:
        s.close()


# list all materials and assemble data
"""
@listTable.route("/listMaterialsAndAssembles", methods=['GET'])
def list_materials_and_assembles():
    print("listMaterialsAndAssembles.")

    t0 = time.time()
    print("listMaterialsAndAssembles start")

    s = Session()
    _results = []
    _assemble_active_users = []

    def safe_str(v, default=''):
        try:
            return '' if v is None else str(v)
        except Exception:
            return default

    def safe_status_str(num, base_str, completed_qty, pos):

        ## 只在 num ∈ {5,7,9} 且 pos ∈ {1,2,3} 時，安全替換 '00/00/00' 的其中一段。
        try:
            if num in (5, 7, 9) and pos in (1, 2, 3):
                parts = (base_str or '00/00/00').split('/')
                if len(parts) == 3:
                    parts[pos - 1] = safe_str(completed_qty, '00')
                    return '/'.join(parts)
        except Exception:
            pass
        return base_str or '00/00/00'

    # ✅ 新增：用「訂單(order_num)」判斷是否缺料（跨拆單 A1/A2/A3）
    def calc_shortage_note_by_order(s, order_num: str) -> str:
        if not order_num:
            return ""

        # 找出該訂單所有 material.id（包含拆單）
        mids = [
            r[0] for r in (
                s.query(Material.id)
                 .filter(Material.order_num == order_num)
                 .all()
            )
        ]
        if not mids:
            return ""

        # 只要任一 BOM 還缺料，就算缺料
        # 兼容你現場的兩種狀態：receive=False 或 lack_qty > 0
        has_lack = (
            s.query(Bom)
              .filter(Bom.material_id.in_(mids))
              #.filter(
              #  (Bom.receive == False) | (Bom.lack_qty > 0)
              #)
              .filter(
                or_(
                   Bom.receive.is_(False), Bom.receive.is_(None), Bom.lack_qty > 0
                )
              )
             .count() > 0
        )
        return "(缺料)" if has_lack else ""

    try:
        _objects = s.query(Material).all()
        material_ids_all = [m.id for m in _objects]

        # 每個 material 的最大 step_code
        max_step_code_per_order = {}
        for material_record in _objects:
            for assemble_record in material_record._assemble:
                step_code = assemble_record.process_step_code
                order_num_id = material_record.id
                cur = max_step_code_per_order.get(order_num_id)
                max_step_code_per_order[order_num_id] = step_code if cur is None else max(cur, step_code)

        code_to_name = {'106': '雷射', '109': '組裝', '110': '檢驗'}
        str2 = ['未備料','備料中','備料完成','等待組裝作業','組裝進行中','00/00/00','檢驗進行中','00/00/00','雷射進行中','00/00/00','等待入庫作業','入庫進行中','入庫完成']
        code_to_pt = {'106': 23, '109': 21, '110': 22}

        index = 0
        pre_p_id = 0

        ###
        order_nums = {m.order_num for m in _objects if m.order_num}
        roots = (
          s.query(Material.order_num, Material.merge_enabled)
          .filter(Material.is_copied_from_id.is_(None))
          .filter(Material.order_num.in_(order_nums))
          .all()
        )
        merge_map = {on: bool(me) for on, me in roots}
        ###

        for material_record in _objects:

            merge_enabled = merge_map.get(material_record.order_num, True)
            if merge_enabled and material_record.is_copied_from_id is not None:
              continue

            if not material_record.isShow:
              continue

            # ✅ P6：只顯示 root(A1)，拆單(A2/A3)不顯示
            #if material_record.is_copied_from_id is not None:
            #    continue

            process_records = material_record._process
            total_records = len([
                p for p in process_records
                if (p.material_id == material_record.id and p.assemble_id != 0)
            ])
            begin_records = len([
                p for p in process_records
                if (p.material_id == material_record.id and p.assemble_id != 0 and p.has_started)
            ])

            assemble_records = material_record._assemble

            # 先算出：在同一個 material_id 裡，每個 update_time 的 max_step_code
            max_by_ut = {}  # { update_time -> max_step_code }
            for a in assemble_records:
                step = int(a.process_step_code or 0)
                if step == 0:
                    continue
                ut = a.update_time
                cur = max_by_ut.get(ut)
                if cur is None or step > cur:
                    max_by_ut[ut] = step

            for assemble_record in material_record._assemble:
                if assemble_record.must_receive_qty <= 0:
                    continue

                # 先給預設值，避免後面任何分支沒賦值就被拿去用
                temp_isLackMaterial = material_record.isLackMaterial

                step = int(assemble_record.process_step_code or 0)

                # 依 work_num 判斷對應的 process_type
                work = assemble_record.work_num or ''
                target_pt = None
                if 'B109' in work:
                    target_pt = 21
                elif 'B110' in work:
                    target_pt = 22
                elif 'B106' in work:
                    target_pt = 23

                matched_count = 0
                total_work_qty = 0
                show_timer = False
                show_name = ''

                if target_pt is not None:
                    target_procs = [
                      p for p in process_records
                      if (
                        p.material_id == assemble_record.material_id
                        and p.process_type == target_pt
                        and p.assemble_id == assemble_record.id
                        and p.begin_time
                        and str(p.begin_time).strip()
                      )
                    ]
                    matched_count = len(target_procs)
                    total_work_qty = sum((p.process_work_time_qty or 0) for p in target_procs)

                    if target_procs:
                        latest_p = max(target_procs, key=lambda x: x.id)
                        show_timer = True
                        show_name = latest_p.user_id or ''

                # a_statement: step != 0 且有對應 process，且已報工數量 >= 交期數量
                a_statement = (
                  step != 0
                  and total_records != 0
                  and matched_count > 0
                  and total_work_qty >= (material_record.delivery_qty or 0)
                )

                # 你原本這段邏輯保留
                if step == 0 and not a_statement:
                    continue

                cleaned_comment = safe_str(material_record.material_comment).strip()
                work_num = safe_str(assemble_record.work_num)
                code = work_num[1:] if len(work_num) >= 2 else work_num
                name = code_to_name.get(code, '')
                pt = code_to_pt.get(code, 0)

                ok, process_total = need_more_process_qty(
                    k1=assemble_record.material_id,
                    a1=assemble_record.id,
                    t1=pt,
                    must_qty=assemble_record.must_receive_end_qty,
                    s=s
                )

                ut = assemble_record.update_time
                max_step_code = max_by_ut.get(ut)
                if max_step_code is None:
                    continue
                if step != max_step_code:
                    continue

                num = int(getattr(assemble_record, 'show2_ok', 0) or 0)
                base = str2[num] if 0 <= num < len(str2) else '00/00/00'
                total_ask_end = getattr(assemble_record, 'total_ask_qty_end', None)
                completed_qty = getattr(assemble_record, 'completed_qty', 0)
                temp_temp_show2_ok_str = safe_status_str(num, base, completed_qty, total_ask_end)

                format_name = f"{work_num}({name})" if name else work_num

                index += 1

                # ✅ shortage_note 改用「order_num」跨拆單判斷
                shortage_note = calc_shortage_note_by_order(s, material_record.order_num)

                ###
                order_num = material_record.order_num
                material_id = material_record.id

                # ✅ merge_enabled=True：用「訂單」統計（跨 A1/A2/A3）
                # ✅ merge_enabled=False：用「單筆 material」統計
                if merge_enabled:
                    mids = [
                        r[0] for r in (
                            s.query(Material.id)
                            .filter(Material.order_num == order_num)
                            .all()
                        )
                    ]

                    if mids:
                        has_bom = (
                            s.query(Bom.id)
                            .filter(Bom.material_id.in_(mids))
                            .count()
                        )
                        has_receive_true = (
                            s.query(Bom.id)
                            .filter(Bom.material_id.in_(mids))
                            .filter(Bom.receive.is_(True))
                            .count()
                        )
                        # 缺料數（可選：debug 用）
                        has_receive_false_or_null = (
                            s.query(Bom.id)
                            .filter(Bom.material_id.in_(mids))
                            .filter(or_(Bom.receive.is_(False), Bom.receive.is_(None)))
                            .count()
                        )
                    else:
                        has_bom = 0
                        has_receive_true = 0
                        has_receive_false_or_null = 0

                else:
                    # 不併單：只算這筆 material 自己的 BOM
                    has_bom = (
                        s.query(Bom.id)
                        .filter(Bom.material_id == material_id)
                        .count()
                    )
                    has_receive_true = (
                        s.query(Bom.id)
                        .filter(Bom.material_id == material_id)
                        .filter(Bom.receive.is_(True))
                        .count()
                    )
                    has_receive_false_or_null = (
                        s.query(Bom.id)
                        .filter(Bom.material_id == material_id)
                        .filter(or_(Bom.receive.is_(False), Bom.receive.is_(None)))
                        .count()
                    )

                ###

                temp_isLackMaterial = material_record.isLackMaterial

                _object = {
                    'index': index,
                    'id': material_record.id,                 # 只會是 root(A1)
                    'order_num': material_record.order_num,
                    'assemble_work': format_name,
                    'material_num': material_record.material_num,
                    'assemble_process': '' if num > 2 else temp_temp_show2_ok_str,

                    'assemble_process_num': num,
                    'assemble_id': assemble_record.id,
                    'req_qty': material_record.material_qty,
                    'delivery_qty': material_record.delivery_qty,
                    'total_receive_qty': f"({getattr(assemble_record, 'total_ask_qty', 0)})",
                    'total_receive_qty_num': getattr(assemble_record, 'total_ask_qty', 0),

                    'must_receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'must_receive_end_qty': getattr(assemble_record, 'must_receive_end_qty', 0),

                    'delivery_date': material_record.material_delivery_date,
                    'comment': cleaned_comment,
                    'isTakeOk': material_record.isTakeOk,
                    'whichStation': material_record.whichStation,
                    'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,
                    'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,
                    'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,
                    'currentStartTime': getattr(assemble_record, 'currentStartTime', None),
                    'tooltipVisible': False,
                    'input_disable': getattr(assemble_record, 'input_disable', False),

                    'process_step_code': max_step_code,
                    'isLackMaterial': temp_isLackMaterial,
                    #'isLackMaterial': material_record.isLackMaterial,
                    'Incoming1_Abnormal': getattr(assemble_record, 'Incoming1_Abnormal', '') == '',
                    'is_copied_from_id': getattr(assemble_record, 'is_copied_from_id', None),
                    'create_at': assemble_record.create_at,

                    'show_timer': show_timer,
                    'show_name': show_name,
                    'begin_records': begin_records,

                    'has_bom': has_bom,
                    'has_receive_true': has_receive_true,

                    # ✅ 讓前端能直接顯示 (缺料)
                    'shortage_note': shortage_note,
                    #'shortage_note': calc_shortage_note_by_order(s, material_record.order_num),
                    #'shortage_note': shortage_note_by_order(s, material_record.order_num),

                    'merge_enabled': merge_enabled,
                    'row_key': f"{material_record.id}_{assemble_record.id}",
                }
                _results.append(_object)

        s.close()

        # 原本排序保留
        _results.sort(key=lambda x: x.get('id') or 0)
        _results.sort(key=lambda x: x.get('create_at') or datetime.min, reverse=True)

        return jsonify({
            'status': bool(_results),
            'materials_and_assembles': _results or [],
            'assemble_active_users': _assemble_active_users or [],
            #'temp_isLackMaterial': temp_isLackMaterial,
        })

    except Exception as e:
        import traceback
        print("listMaterialsAndAssembles ERROR:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("listMaterialsAndAssembles failed")
        except Exception:
            pass
        s.close()

        print("listMaterialsAndAssembles cost:", time.time()-t0)

        return jsonify({
            'status': False,
            'materials_and_assembles': [],
            'assemble_active_users': [],
        }), 200
"""


# list all materials and assemble data
@listTable.route("/listMaterialsAndAssembles", methods=['GET'])
def list_materials_and_assembles():
    print("listMaterialsAndAssembles.")

    t0 = time.time()
    print("listMaterialsAndAssembles start")

    s = Session()
    _results = []
    _assemble_active_users = []

    def safe_str(v, default=''):
        try:
            return '' if v is None else str(v)
        except Exception:
            return default

    def safe_status_str(num, base_str, completed_qty, pos):
        """
        只在 num ∈ {5,7,9} 且 pos ∈ {1,2,3} 時，安全替換 '00/00/00' 的其中一段。
        """
        try:
            if num in (5, 7, 9) and pos in (1, 2, 3):
                parts = (base_str or '00/00/00').split('/')
                if len(parts) == 3:
                    parts[pos - 1] = safe_str(completed_qty, '00')
                    return '/'.join(parts)
        except Exception:
            pass
        return base_str or '00/00/00'

    try:
        # ------------------------------------------------------------
        # 1) 先把 Material + 關聯 Assemble / Process 一次載入，避免 lazy-load N+1
        # ------------------------------------------------------------
        _objects = (
            s.query(Material)
             .options(
                 selectinload(Material._assemble),
                 selectinload(Material._process),
             )
             .all()
        )

        material_ids_all = [m.id for m in _objects]
        order_nums = {m.order_num for m in _objects if m.order_num}

        if not _objects:
            s.close()
            return jsonify({
                'status': False,
                'materials_and_assembles': [],
                'assemble_active_users': [],
            })

        # ------------------------------------------------------------
        # 2) merge_enabled map（root order_num -> merge_enabled）
        # ------------------------------------------------------------
        roots = (
            s.query(Material.order_num, Material.merge_enabled)
             .filter(Material.is_copied_from_id.is_(None))
             .filter(Material.order_num.in_(order_nums))
             .all()
        )
        merge_map = {on: bool(me) for on, me in roots}

        # ------------------------------------------------------------
        # 3) order_num -> material_ids
        # ------------------------------------------------------------
        material_ids_by_order = defaultdict(list)
        for m in _objects:
            if m.order_num:
                material_ids_by_order[m.order_num].append(m.id)

        # ------------------------------------------------------------
        # 4) 缺料訂單集合：只要同 order 任一 BOM 還缺料，就記錄
        # ------------------------------------------------------------
        shortage_order_set = {
            row[0]
            for row in (
                s.query(Material.order_num)
                 .join(Bom, Bom.material_id == Material.id)
                 .filter(Material.order_num.in_(order_nums))
                 .filter(or_(Bom.receive.is_(False), Bom.receive.is_(None), Bom.lack_qty > 0))
                 .distinct()
                 .all()
            )
        }

        # ------------------------------------------------------------
        # 5) 每個 material 的 BOM 統計
        # ------------------------------------------------------------
        bom_count_by_mid = defaultdict(int)
        bom_receive_true_by_mid = defaultdict(int)
        bom_receive_false_or_null_by_mid = defaultdict(int)

        bom_rows = (
            s.query(
                Bom.material_id,
                func.count(Bom.id).label("bom_cnt"),
                func.sum(case((Bom.receive.is_(True), 1), else_=0)).label("recv_true_cnt"),
                func.sum(case((or_(Bom.receive.is_(False), Bom.receive.is_(None)), 1), else_=0)).label("recv_false_cnt"),
            )
            .filter(Bom.material_id.in_(material_ids_all))
            .group_by(Bom.material_id)
            .all()
        )

        for mid, bom_cnt, recv_true_cnt, recv_false_cnt in bom_rows:
            bom_count_by_mid[mid] = int(bom_cnt or 0)
            bom_receive_true_by_mid[mid] = int(recv_true_cnt or 0)
            bom_receive_false_or_null_by_mid[mid] = int(recv_false_cnt or 0)

        # ------------------------------------------------------------
        # 6) 每個 order 的 BOM 統計（merge_enabled=True 時直接拿）
        # ------------------------------------------------------------
        order_bom_count = defaultdict(int)
        order_recv_true_count = defaultdict(int)
        order_recv_false_count = defaultdict(int)

        for order_num, mids in material_ids_by_order.items():
            order_bom_count[order_num] = sum(bom_count_by_mid.get(mid, 0) for mid in mids)
            order_recv_true_count[order_num] = sum(bom_receive_true_by_mid.get(mid, 0) for mid in mids)
            order_recv_false_count[order_num] = sum(bom_receive_false_or_null_by_mid.get(mid, 0) for mid in mids)

        # ------------------------------------------------------------
        # 7) Process 完成數量總表（取代 need_more_process_qty 每筆查 DB）
        #    key = (material_id, assemble_id, process_type)
        # ------------------------------------------------------------
        process_qty_map = defaultdict(int)

        proc_sum_rows = (
            s.query(
                Process.material_id,
                Process.assemble_id,
                Process.process_type,
                func.coalesce(func.sum(Process.process_work_time_qty), 0).label("total_qty")
            )
            .filter(Process.material_id.in_(material_ids_all))
            .filter(Process.has_started.is_(True))
            .filter(Process.end_time.isnot(None))
            .filter(Process.end_time != '')
            .group_by(Process.material_id, Process.assemble_id, Process.process_type)
            .all()
        )

        for mid, aid, ptype, total_qty in proc_sum_rows:
            process_qty_map[(mid, aid, ptype)] = int(total_qty or 0)

        # ------------------------------------------------------------
        # 8) Process 顯示用總表：
        #    key = (material_id, assemble_id, process_type)
        #    value = {
        #      matched_count,
        #      total_work_qty,
        #      show_timer,
        #      show_name,
        #    }
        # ------------------------------------------------------------
        process_group_map = {}

        proc_group_rows = (
            s.query(
                Process.material_id,
                Process.assemble_id,
                Process.process_type,
                func.count(Process.id).label("matched_count"),
                func.coalesce(func.sum(Process.process_work_time_qty), 0).label("total_work_qty"),
                func.max(Process.id).label("latest_pid"),
            )
            .filter(Process.material_id.in_(material_ids_all))
            .filter(Process.begin_time.isnot(None))
            .filter(Process.begin_time != '')
            .group_by(Process.material_id, Process.assemble_id, Process.process_type)
            .all()
        )

        latest_pids = [row.latest_pid for row in proc_group_rows if row.latest_pid]
        latest_user_by_pid = {}
        if latest_pids:
            latest_rows = (
                s.query(Process.id, Process.user_id)
                 .filter(Process.id.in_(latest_pids))
                 .all()
            )
            latest_user_by_pid = {pid: (uid or '') for pid, uid in latest_rows}

        for row in proc_group_rows:
            process_group_map[(row.material_id, row.assemble_id, row.process_type)] = {
                'matched_count': int(row.matched_count or 0),
                'total_work_qty': int(row.total_work_qty or 0),
                'show_timer': bool(row.latest_pid),
                'show_name': latest_user_by_pid.get(row.latest_pid, ''),
            }

        # ------------------------------------------------------------
        # 9) 常數
        # ------------------------------------------------------------
        code_to_name = {'106': '雷射', '109': '組裝', '110': '檢驗'}
        str2 = [
            '未備料', '備料中', '備料完成', '等待組裝作業', '組裝進行中', '00/00/00',
            '檢驗進行中', '00/00/00', '雷射進行中', '00/00/00', '等待入庫作業', '入庫進行中', '入庫完成'
        ]
        code_to_pt = {'106': 23, '109': 21, '110': 22}

        index = 0

        # ------------------------------------------------------------
        # 10) 主迴圈：純讀 map，不再在迴圈內打 DB
        # ------------------------------------------------------------
        for material_record in _objects:
            merge_enabled = merge_map.get(material_record.order_num, True)

            # 併單：只顯示 root；拆單不顯示
            if merge_enabled and material_record.is_copied_from_id is not None:
                continue

            if not material_record.isShow:
                continue

            process_records = material_record._process or []
            assemble_records = material_record._assemble or []

            total_records = sum(
                1 for p in process_records
                if (p.material_id == material_record.id and p.assemble_id != 0)
            )
            begin_records = sum(
                1 for p in process_records
                if (p.material_id == material_record.id and p.assemble_id != 0 and p.has_started)
            )

            # 在同一個 material_id 裡，每個 update_time 的 max_step_code
            max_by_ut = {}
            for a in assemble_records:
                step = int(a.process_step_code or 0)
                if step == 0:
                    continue
                ut = a.update_time
                cur = max_by_ut.get(ut)
                if cur is None or step > cur:
                    max_by_ut[ut] = step

            # 這筆 material / order 的 BOM 統計
            order_num = material_record.order_num
            material_id = material_record.id

            if merge_enabled:
                has_bom = order_bom_count.get(order_num, 0)
                has_receive_true = order_recv_true_count.get(order_num, 0)
                has_receive_false_or_null = order_recv_false_count.get(order_num, 0)
            else:
                has_bom = bom_count_by_mid.get(material_id, 0)
                has_receive_true = bom_receive_true_by_mid.get(material_id, 0)
                has_receive_false_or_null = bom_receive_false_or_null_by_mid.get(material_id, 0)

            shortage_note = "(缺料)" if order_num in shortage_order_set else ""

            for assemble_record in assemble_records:
                if (assemble_record.must_receive_qty or 0) <= 0:
                    continue

                temp_isLackMaterial = material_record.isLackMaterial
                step = int(assemble_record.process_step_code or 0)

                work = assemble_record.work_num or ''
                target_pt = None
                if 'B109' in work:
                    target_pt = 21
                elif 'B110' in work:
                    target_pt = 22
                elif 'B106' in work:
                    target_pt = 23

                matched_count = 0
                total_work_qty = 0
                show_timer = False
                show_name = ''

                if target_pt is not None:
                    g = process_group_map.get(
                        (assemble_record.material_id, assemble_record.id, target_pt),
                        {}
                    )
                    matched_count = int(g.get('matched_count', 0) or 0)
                    total_work_qty = int(g.get('total_work_qty', 0) or 0)
                    show_timer = bool(g.get('show_timer', False))
                    show_name = g.get('show_name', '') or ''

                a_statement = (
                    step != 0
                    and total_records != 0
                    and matched_count > 0
                    and total_work_qty >= int(material_record.delivery_qty or 0)
                )

                if step == 0 and not a_statement:
                    continue

                cleaned_comment = safe_str(material_record.material_comment).strip()
                work_num = safe_str(assemble_record.work_num)
                code = work_num[1:] if len(work_num) >= 2 else work_num
                name = code_to_name.get(code, '')
                pt = code_to_pt.get(code, 0)

                process_total = process_qty_map.get(
                    (assemble_record.material_id, assemble_record.id, pt),
                    0
                )
                ok = process_total < int(assemble_record.must_receive_end_qty or 0)

                ut = assemble_record.update_time
                max_step_code = max_by_ut.get(ut)
                if max_step_code is None:
                    continue
                if step != max_step_code:
                    continue

                num = int(getattr(assemble_record, 'show2_ok', 0) or 0)
                base = str2[num] if 0 <= num < len(str2) else '00/00/00'
                total_ask_end = getattr(assemble_record, 'total_ask_qty_end', None)
                completed_qty = getattr(assemble_record, 'completed_qty', 0)
                temp_temp_show2_ok_str = safe_status_str(num, base, completed_qty, total_ask_end)

                format_name = f"{work_num}({name})" if name else work_num

                index += 1

                _object = {
                    'index': index,
                    'id': material_record.id,
                    'order_num': material_record.order_num,
                    'assemble_work': format_name,
                    'material_num': material_record.material_num,
                    'assemble_process': '' if num > 2 else temp_temp_show2_ok_str,

                    'assemble_process_num': num,
                    'assemble_id': assemble_record.id,
                    'req_qty': material_record.material_qty,
                    'delivery_qty': material_record.delivery_qty,
                    'total_receive_qty': f"({getattr(assemble_record, 'total_ask_qty', 0)})",
                    'total_receive_qty_num': getattr(assemble_record, 'total_ask_qty', 0),

                    'must_receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'must_receive_end_qty': getattr(assemble_record, 'must_receive_end_qty', 0),

                    'delivery_date': material_record.material_delivery_date,
                    'comment': cleaned_comment,
                    'isTakeOk': material_record.isTakeOk,
                    'whichStation': material_record.whichStation,
                    'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,
                    'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,
                    'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,
                    'currentStartTime': getattr(assemble_record, 'currentStartTime', None),
                    'tooltipVisible': False,
                    'input_disable': getattr(assemble_record, 'input_disable', False),

                    'process_step_code': max_step_code,
                    'isLackMaterial': temp_isLackMaterial,
                    'Incoming1_Abnormal': getattr(assemble_record, 'Incoming1_Abnormal', '') == '',
                    'is_copied_from_id': getattr(assemble_record, 'is_copied_from_id', None),
                    'create_at': assemble_record.create_at,

                    'show_timer': show_timer,
                    'show_name': show_name,
                    'begin_records': begin_records,

                    'has_bom': has_bom,
                    'has_receive_true': has_receive_true,

                    'shortage_note': shortage_note,
                    'merge_enabled': merge_enabled,
                    'row_key': f"{material_record.id}_{assemble_record.id}",

                    # 若前端後面要用，也先帶出去
                    'process_total': process_total,
                    'need_more_process_qty': ok,
                    'has_receive_false_or_null': has_receive_false_or_null,
                }
                _results.append(_object)

        s.close()

        _results.sort(key=lambda x: x.get('id') or 0)
        _results.sort(key=lambda x: x.get('create_at') or datetime.min, reverse=True)

        print("listMaterialsAndAssembles cost:", time.time() - t0)

        return jsonify({
            'status': bool(_results),
            'materials_and_assembles': _results or [],
            'assemble_active_users': _assemble_active_users or [],
        })

    except Exception as e:
        import traceback
        print("listMaterialsAndAssembles ERROR:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("listMaterialsAndAssembles failed")
        except Exception:
            pass
        s.close()

        print("listMaterialsAndAssembles cost:", time.time() - t0)

        return jsonify({
            'status': False,
            'materials_and_assembles': [],
            'assemble_active_users': [],
        }), 200


# list all materials for information list
"""
@listTable.route("/listInformations", methods=['GET'])
def list_informations():
    print("listInformation....")

    #false: 全部顯示
    #true: 只顯示未完成
    only_unfinished = request.args.get("only_unfinished", "0") in ("1", "true", "True")
    print('\033[42m' + 'only_unfinished:' + '\033[0m',   only_unfinished)

    limit  = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))

    s = Session()

    _results = []
    return_value = True
    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                 3              4            5           6             7            8             9          10                  11            12           13          14          15            16           17            18
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '檢驗進行中', '00/00/00',  '雷射進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)     16(agv_start)   17
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '檢驗進行中', '檢驗已結束', '雷射進行中', '雷射已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業', 'agv Start',     '推車送料至組裝區中',]

    # ✅ 彙總：每個 material_id 的 總入庫（現況數量：product.allOk_qty）
    prd_stockin = (
        s.query(
            Product.material_id.label("mid"),
            func.coalesce(func.sum(Product.allOk_qty), 0).label("stockin_qty"),
        )
        .group_by(Product.material_id)
        .subquery()
    )

    # ✅ 統一查詢：永遠回 (Material, stockin_qty)
    q = (
        s.query(
            Material,
            func.coalesce(prd_stockin.c.stockin_qty, 0).label("stockin_qty"),
        )
        .outerjoin(prd_stockin, prd_stockin.c.mid == Material.id)
    )

    # ✅ only_unfinished=1：訂單數量 != 總入庫
    if only_unfinished:
        q = q.filter(
            func.coalesce(Material.material_qty, 0) != func.coalesce(prd_stockin.c.stockin_qty, 0)
        )

    total = q.count()  # ✅ 總筆數（給前端算總頁數）
    #q = q.order_by(Material.order_num).limit(limit).offset(offset)

    _objects = q.all()

    if not _objects:
        s.close()
        return jsonify({'status': False, 'informations': []})

    for record, stockin_qty in _objects:
      assemble_records = record._assemble   # 存取與該 Material 物件關聯的所有 Assemble 物件

      cleaned_comment = record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

      temp_show2_ok = int(record.show2_ok)

      temp_temp_show2_ok_str = str2[temp_show2_ok]

      # 處理 show2_ok 的情況
      if temp_show2_ok == 5 or temp_show2_ok == 7 or temp_show2_ok == 9:
        for assemble_record in assemble_records:
          # 如果 `total_ask_qty_end` 為 1, 2 或 3，替換 `00/00/00` 的相應部分
          if assemble_record.total_ask_qty_end in [1, 2, 3]:
            completed_qty = str(assemble_record.completed_qty)  # 將數值轉換為字串
            date_parts = temp_temp_show2_ok_str.split('/')  # 分割 `00/00/00` 為 ['00', '00', '00']
            date_parts[assemble_record.total_ask_qty_end - 1] = completed_qty  # 替換對應位置
            temp_temp_show2_ok_str = '/'.join(date_parts)  # 合併回字串
        print("temp_show2_ok, temp_temp_show2_ok_str:", temp_show2_ok, temp_temp_show2_ok_str)

      if (temp_show2_ok == 1):
        user = s.query(User).filter_by(emp_id=record.isOpenEmpId).first()
        temp_name=''
        if user:
          temp_name = '(' + user.emp_name + ')'
        temp_temp_show2_ok_str = temp_temp_show2_ok_str + temp_name
        temp_temp_show2_ok_str = temp_temp_show2_ok_str + record.shortage_note

      temp_temp_show2_ok_str = re.sub(r'\b00\b', '00', temp_temp_show2_ok_str)

      _object = {
        'id': record.id,                                #訂單編號的table id
        'order_num': record.order_num,                  #訂單編號
        'material_num': record.material_num,            #物料編號
        'isTakeOk': record.isTakeOk,
        'whichStation': record.whichStation,
        'req_qty': record.material_qty,                 #需求數量
        'delivery_date':record.material_delivery_date,  #交期
        #'delivery_qty':record.delivery_qty,             #現況數量
        'delivery_qty': int(stockin_qty or 0),
        'comment': cleaned_comment,                     #說明
        'show1_ok' : str1[int(record.show1_ok) - 1],    #現況進度
        'show2_ok' : temp_temp_show2_ok_str,            #現況進度(途程)
        'show3_ok' : str3[int(record.show3_ok)] if temp_temp_show2_ok_str != '入庫完成' else '入庫完成',        #現況備註
        'isOpenEmpId': record.isOpenEmpId,
      }

      _results.append(_object)

    s.close()

    temp_len = len(_results)
    #print("listInformations, 資料: ", _results)
    print("listInformations, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 'order_num' 排序
    _results = sorted(_results, key=lambda x: x['order_num'])

    return jsonify({
      'status': return_value,
      'total': total,
      'informations': _results
    })
"""


# list all materials for information list(Python loop)
"""
@listTable.route("/listInformations", methods=['GET'])
def list_informations():
    print("listInformation....")

    only_unfinished = request.args.get("only_unfinished", "0") in ("1", "true", "True")
    print('\033[42m' + 'only_unfinished:' + '\033[0m', only_unfinished)

    limit  = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))

    s = Session()

    _results = []
    return_value = True

    str1=['備料站', '組裝站', '成品站']

    str2=[
        '未備料','備料中','備料完成','等待組裝作業',
        '組裝進行中','00/00/00',
        '檢驗進行中','00/00/00',
        '雷射進行中','00/00/00',
        '等待入庫作業','入庫進行中','入庫完成'
    ]

    str3=[
        '', '等待agv','agv移至組裝區中','等待組裝作業','組裝進行中','組裝已結束',
        '檢驗進行中','檢驗已結束','雷射進行中','雷射已結束',
        'agv移至成品區中','等待入庫作業','入庫進行中','入庫完成',
        'agv移至備料區中','等待備料作業','agv Start','推車送料至組裝區中'
    ]

    try:

        # -------------------------------
        # 1️⃣ Product 入庫數量彙總
        # -------------------------------
        prd_stockin = (
            s.query(
                Product.material_id.label("mid"),
                func.coalesce(func.sum(Product.allOk_qty),0).label("stockin_qty")
            )
            .group_by(Product.material_id)
            .subquery()
        )

        # -------------------------------
        # 2️⃣ 主查詢 (Material + stockin)
        # -------------------------------
        q = (
            s.query(
                Material,
                func.coalesce(prd_stockin.c.stockin_qty,0).label("stockin_qty")
            )
            .options(

                # ⭐ 只載入需要欄位
                load_only(
                    Material.id,
                    Material.order_num,
                    Material.material_num,
                    Material.material_qty,
                    Material.material_delivery_date,
                    Material.material_comment,
                    Material.show1_ok,
                    Material.show2_ok,
                    Material.show3_ok,
                    Material.isTakeOk,
                    Material.whichStation,
                    Material.isOpenEmpId,
                    Material.shortage_note
                ),

                # ⭐ 預載 assemble
                selectinload(Material._assemble).load_only(
                    Assemble.material_id,
                    Assemble.total_ask_qty_end,
                    Assemble.completed_qty
                )

            )
            .outerjoin(prd_stockin, prd_stockin.c.mid==Material.id)
        )

        if only_unfinished:
            q = q.filter(
                func.coalesce(Material.material_qty,0) !=
                func.coalesce(prd_stockin.c.stockin_qty,0)
            )

        total = q.count()

        # 目前仍然整批
        _objects = q.all()

        if not _objects:
            s.close()
            return jsonify({'status': False,'total':total,'informations':[]})

        # -------------------------------------------------------
        # 3️⃣ SQL 彙總 assemble completed_qty
        # -------------------------------------------------------
        assemble_rows = (
            s.query(
                Assemble.material_id,
                Assemble.total_ask_qty_end,
                func.coalesce(func.sum(cast(Assemble.completed_qty,Integer)),0)
            )
            .filter(Assemble.total_ask_qty_end.in_([1,2,3]))
            .group_by(Assemble.material_id,Assemble.total_ask_qty_end)
            .all()
        )

        assemble_qty_map = {}

        for mid,pos,total_qty in assemble_rows:

            if mid not in assemble_qty_map:
                assemble_qty_map[mid]={1:0,2:0,3:0}

            assemble_qty_map[mid][int(pos)] = int(total_qty or 0)

        # -------------------------------------------------------
        # 4️⃣ User name map
        # -------------------------------------------------------
        emp_ids = {
            r.isOpenEmpId
            for r,_ in _objects
            if int(r.show2_ok or 0)==1 and r.isOpenEmpId
        }

        user_name_map={}

        if emp_ids:

            users = (
                s.query(User.emp_id,User.emp_name)
                .filter(User.emp_id.in_(emp_ids))
                .all()
            )

            user_name_map={eid:name for eid,name in users}

        # -------------------------------------------------------
        # 5️⃣ 組結果
        # -------------------------------------------------------
        for record,stockin_qty in _objects:

            cleaned_comment = (record.material_comment or "").strip()

            temp_show2_ok = int(record.show2_ok or 0)

            temp_temp_show2_ok_str = str2[temp_show2_ok]

            # ⭐ SQL map 版本
            if temp_show2_ok in (5,7,9):

                parts = temp_temp_show2_ok_str.split('/')

                if len(parts)==3:

                    qty_map = assemble_qty_map.get(record.id,{1:0,2:0,3:0})

                    parts[0] = str(qty_map.get(1,0))
                    parts[1] = str(qty_map.get(2,0))
                    parts[2] = str(qty_map.get(3,0))

                    temp_temp_show2_ok_str = "/".join(parts)

            if temp_show2_ok==1:

                emp_name = user_name_map.get(record.isOpenEmpId,'')

                if emp_name:
                    temp_temp_show2_ok_str += f"({emp_name})"

                temp_temp_show2_ok_str += (record.shortage_note or "")

            _object = {

                'id':record.id,
                'order_num':record.order_num,
                'material_num':record.material_num,

                'isTakeOk':record.isTakeOk,
                'whichStation':record.whichStation,

                'req_qty':record.material_qty,
                'delivery_date':record.material_delivery_date,

                'delivery_qty':int(stockin_qty or 0),

                'comment':cleaned_comment,

                'show1_ok':str1[int(record.show1_ok)-1] if int(record.show1_ok or 0) in (1,2,3) else '',
                'show2_ok':temp_temp_show2_ok_str,
                'show3_ok':str3[int(record.show3_ok)] if temp_temp_show2_ok_str!='入庫完成' else '入庫完成',

                'isOpenEmpId':record.isOpenEmpId

            }

            _results.append(_object)

        s.close()

        temp_len=len(_results)

        print("listInformations, 總數:",temp_len)

        if temp_len==0:
            return_value=False

        _results = sorted(_results,key=lambda x:x['order_num'])

        return jsonify({
            'status':return_value,
            'total':total,
            'informations':_results
        })

    except Exception as e:

        import traceback

        print("listInformations ERROR:",repr(e))
        traceback.print_exc()

        s.close()

        return jsonify({
            'status':False,
            'total':0,
            'informations':[]
        }),200
"""


# list all materials for information list(SQL JOIN版本)
@listTable.route("/listInformations", methods=['GET'])
def list_informations():

    print("listInformation....")

    only_unfinished = request.args.get("only_unfinished", "0") in ("1","true","True")

    s = Session()

    str1=['備料站','組裝站','成品站']

    str2=[
        '未備料','備料中','備料完成',
        '等待組裝作業','組裝進行中','00/00/00',
        '檢驗進行中','00/00/00',
        '雷射進行中','00/00/00',
        '等待入庫作業','入庫進行中','入庫完成'
    ]

    str3=[
        '', '等待agv','agv移至組裝區中','等待組裝作業','組裝進行中','組裝已結束',
        '檢驗進行中','檢驗已結束','雷射進行中','雷射已結束',
        'agv移至成品區中','等待入庫作業','入庫進行中','入庫完成',
        'agv移至備料區中','等待備料作業','agv Start','推車送料至組裝區中'
    ]

    try:

        # ------------------------------------------------
        # product stockin qty
        # ------------------------------------------------
        stockin_sub = (
            s.query(
                Product.material_id.label("mid"),
                func.coalesce(func.sum(Product.allOk_qty),0).label("stockin_qty")
            )
            .group_by(Product.material_id)
            .subquery()
        )

        # ------------------------------------------------
        # assemble qty 1/2/3
        # ------------------------------------------------
        asm_sub = (
            s.query(

                Assemble.material_id.label("mid"),

                func.sum(
                    case(
                        (Assemble.total_ask_qty_end==1,Assemble.completed_qty),
                        else_=0
                    )
                ).label("qty1"),

                func.sum(
                    case(
                        (Assemble.total_ask_qty_end==2,Assemble.completed_qty),
                        else_=0
                    )
                ).label("qty2"),

                func.sum(
                    case(
                        (Assemble.total_ask_qty_end==3,Assemble.completed_qty),
                        else_=0
                    )
                ).label("qty3")

            )
            .group_by(Assemble.material_id)
            .subquery()
        )

        # ------------------------------------------------
        # 主查詢
        # ------------------------------------------------
        q = (
            s.query(

                Material,

                func.coalesce(stockin_sub.c.stockin_qty,0).label("stockin_qty"),

                func.coalesce(asm_sub.c.qty1,0).label("qty1"),
                func.coalesce(asm_sub.c.qty2,0).label("qty2"),
                func.coalesce(asm_sub.c.qty3,0).label("qty3"),

                User.emp_name

            )

            .outerjoin(stockin_sub,stockin_sub.c.mid==Material.id)

            .outerjoin(asm_sub,asm_sub.c.mid==Material.id)

            .outerjoin(User,User.emp_id==Material.isOpenEmpId)

        )

        if only_unfinished:

            q = q.filter(
                func.coalesce(Material.material_qty,0) !=
                func.coalesce(stockin_sub.c.stockin_qty,0)
            )

        rows = q.all()

        if not rows:
            s.close()
            return jsonify({'status':False,'informations':[]})

        _results=[]

        for record,stockin_qty,qty1,qty2,qty3,emp_name in rows:

            temp_show2_ok=int(record.show2_ok or 0)

            temp_show2_ok_str=str2[temp_show2_ok]

            if temp_show2_ok in (5,7,9):

                temp_show2_ok_str=f"{qty1}/{qty2}/{qty3}"

            if temp_show2_ok==1:

                if emp_name:
                    temp_show2_ok_str+=f"({emp_name})"

                temp_show2_ok_str+=record.shortage_note or ""

            _results.append({

                'id':record.id,
                'order_num':record.order_num,
                'material_num':record.material_num,

                'isTakeOk':record.isTakeOk,
                'whichStation':record.whichStation,

                'req_qty':record.material_qty,
                'delivery_date':record.material_delivery_date,

                'delivery_qty':int(stockin_qty),

                'comment':(record.material_comment or "").strip(),

                'show1_ok':str1[int(record.show1_ok)-1] if record.show1_ok else '',

                'show2_ok':temp_show2_ok_str,

                'show3_ok':str3[int(record.show3_ok)]
                    if temp_show2_ok_str!='入庫完成'
                    else '入庫完成',

                'isOpenEmpId':record.isOpenEmpId

            })

        s.close()

        _results.sort(key=lambda x:x['order_num'])

        return jsonify({
            'status':True,
            'informations':_results
        })

    except Exception as e:

        import traceback
        print("listInformations ERROR:",e)
        traceback.print_exc()

        s.close()

        return jsonify({
            'status':False,
            'informations':[]
        }),200


@listTable.route("/listInformationsP", methods=['GET'])
def list_informations_p():
    print("listInformationsP....")

    #false: 全部顯示
    #true: 只顯示未完成
    only_unfinished = request.args.get("only_unfinished", "0") in ("1", "true", "True")
    print('\033[42m' + 'only_unfinished:' + '\033[0m',   only_unfinished)

    limit  = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))

    s = Session()

    _results = []
    return_value = True
    str1=['領料站', '加工站', '成品站']
    #      0        1         2            3              4                5               6              7            8
    str2=['未領料', '領料中', '領料已完成', '等待加工作業', '加工作業進行中', '加工作業已完成', '等待入庫作業', '入庫進行中', '入庫完成']

    # ✅ 彙總：每個 material_id 的 廢品（p_assemble）
    asm_scrap = (
        s.query(
            P_Assemble.material_id.label("mid"),
            func.coalesce(func.sum(P_Assemble.abnormal_qty), 0).label("scrap_qty"),
        )
        .group_by(P_Assemble.material_id)
        .subquery()
    )

    # ✅ 彙總：每個 material_id 的 入庫（現況數量：p_product.allOk_qty）
    prd_stockin = (
        s.query(
            P_Product.material_id.label("mid"),
            func.coalesce(func.sum(P_Product.allOk_qty), 0).label("stockin_qty"),
        )
        .group_by(P_Product.material_id)
        .subquery()
    )

    # ✅ 統一查詢：永遠回 (P_Material, scrap_qty, stockin_qty)
    q = (
        s.query(
            P_Material,
            func.coalesce(asm_scrap.c.scrap_qty, 0).label("scrap_qty"),
            func.coalesce(prd_stockin.c.stockin_qty, 0).label("stockin_qty"),
        )
        .outerjoin(asm_scrap, asm_scrap.c.mid == P_Material.id)
        .outerjoin(prd_stockin, prd_stockin.c.mid == P_Material.id)
    )

    # ✅ switchValue=ON：只顯示未完成
    if only_unfinished:
        q = q.filter(
            func.coalesce(P_Material.material_qty, 0) !=
            (func.coalesce(asm_scrap.c.scrap_qty, 0) + func.coalesce(prd_stockin.c.stockin_qty, 0))
        )

    total = q.count()  # ✅ 總筆數（給前端算總頁數）
    #q = q.order_by(P_Material.order_num).limit(limit).offset(offset)

    _objects = q.all()

    def norm_code(x: str) -> str:
      return (x or "").strip().upper().replace(" ", "")

    # 把 B102KL-01 / B102KT-01 這種轉成 B102-01 的 alias
    # 規則：^(B\d{3})[A-Z]*-(\d+)$  =>  B102KL-01 -> B102-01
    def alias_code(x: str) -> str:
      x = norm_code(x)
      m = re.match(r'^(B\d{3})[A-Z]*-(\d+)$', x)
      if not m:
        return x
      return f"{m.group(1)}-{m.group(2)}"

    part_info_map = {}
    for p in s.query(P_Part).all():
      code_raw = (p.part_code or "")
      code = norm_code(code_raw)
      if not code:
        continue

      info = {
          "comment": (p.part_comment or "").strip(),
          "process_step_code": int(p.process_step_code or 0),
      }

      # 1) 原始 key：B102KL-01
      part_info_map[code] = info

      # 2) alias key：B102-01（讓 work_num=B102-01 也查得到）
      akey = alias_code(code)
      part_info_map.setdefault(akey, info)

    for record, scrap_qty, stockin_qty in _objects:
      assemble_records = record._assemble   # 存取與該 Material 物件關聯的所有 Assemble 物件

      process_records = record._process
      total_process_records =len([p for p in process_records if ((p.material_id == record.id and p.has_started == 1 and p.begin_time != ''))])

      cleaned_comment = record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

      raw = getattr(record, "show2_ok", None)
      num = -1
      try:
        num = int(raw)
      except Exception as e:
        print("❌ show2_ok parse failed",
              "material_id:", record.id,
              "order_num:", record.order_num,
              "raw:", raw,
              "err:", repr(e))
        num = -1

      # ✅ 兼容兩種：0-based(0~8) / 1-based(1~9)
      if 0 <= num < len(str2):
          temp_show2_ok_str = str2[num]
      elif 1 <= num <= len(str2):
          temp_show2_ok_str = str2[num - 1]
      else:
          print("❌ show2_ok OUT OF RANGE", "num:", num, "len(str2):", len(str2))
          temp_show2_ok_str = f"未知狀態({raw})"

      temp_show2_ok = num  # 後面 if temp_show2_ok == 5 ... 才不會用到舊值

      if (temp_show2_ok == 1):
        user = s.query(User).filter_by(emp_id=record.isOpenEmpId).first()
        temp_name=''
        if user:
          temp_name = '(' + user.emp_name + ')'
        temp_show2_ok_str = temp_show2_ok_str + temp_name

      temp_show2_ok_str = re.sub(r'\b00\b', '00', temp_show2_ok_str)

      # 處理 show3_ok 的情況
      show3_ok_val = int(record.show3_ok)
      show_comment =''

      if (record.isBom) or (not record.isBom and record.isTakeOk and record.isShow):
        if record._assemble:
          valid_assembles = [
              a for a in record._assemble
              if (a.work_num not in (None,'','0') and a.seq_num is not None and str(a.seq_num).isdigit())
          ]

          if valid_assembles:   # if_loop_b
            min_assemble_record = min(
              valid_assembles,
              key=lambda a: int(a.seq_num)
            )

            show3_ok = (min_assemble_record.work_num or "").strip()

            key = norm_code(show3_ok)
            part_info = part_info_map.get(key)
            if not part_info:
              # 再試一次 alias（萬一 work_num 反而帶 KL/KT 之類）
              part_info = part_info_map.get(alias_code(key))

            if part_info:
              show_comment = part_info.get("comment", "")
            else:
              show_comment = ""
              print(f"[DEBUG show3_ok] miss, work_num={show3_ok}, key={key}")

          # end if_loop_b

      stockin_total = int(stockin_qty or 0)

      def _to_int(v, default=0):
          try:
              if v is None:
                  return default
              return int(v)
          except Exception:
              return default

      # ✅ 若尚未入庫(stockin_total=0)，現況數量改用「扣報廢後的良品量」
      # p_assemble 第一筆 must_receive_end_qty=190，第二筆 abnormal_qty=10 → 現況要顯示 190
      net_good_qty = 0
      for a in assemble_records:
          net_good_qty = max(net_good_qty, _to_int(getattr(a, "must_receive_end_qty", 0), 0))
          # 資料中已有 total_ask_qty_end=190，保留當 fallback
          if net_good_qty == 0:
              net_good_qty = max(net_good_qty, _to_int(getattr(a, "total_ask_qty_end", 0), 0))

      delivery_qty = int(stockin_total) if int(stockin_total) > 0 else (net_good_qty if net_good_qty > 0 else _to_int(record.delivery_qty, 0))

      _object = {
        'id': record.id,                                #訂單編號的table id
        'order_num': record.order_num,                  #訂單編號
        'material_num': record.material_num,            #物料編號
        'isTakeOk': record.isTakeOk,
        'whichStation': record.whichStation,
        'req_qty': record.material_qty,                 #需求數量
        'delivery_date':record.material_delivery_date,  #交期
        #'delivery_qty':record.delivery_qty,             #現況數量
        #'delivery_qty': int(stockin_total) if int(stockin_total) > 0 else record.delivery_qty,
        'delivery_qty': delivery_qty,
        'comment': cleaned_comment,                     #說明
        'show1_ok' : str1[int(record.show1_ok) - 1],    #現況進度(上面文字說明)
        'show2_ok' : temp_show2_ok_str,                 #現況進度(下面文字說明)
        'show3_ok' : show_comment if temp_show2_ok_str != '入庫完成' else '入庫完成',                      #現況備註(加工製程)
        'isOpenEmpId': record.isOpenEmpId,
        'total_process_records': total_process_records,
      }

      _results.append(_object)

    s.close()

    if not _objects:
        print("⚠️ 沒有資料")
        #s.close()
        return jsonify({'status': False, 'informations': []})

    temp_len = len(_results)
    #print("listInformations, 資料: ", _results)
    print("listInformationsP, 總數: ", temp_len)
    #if (temp_len == 0):
    #  return_value = False
    #else:
    # 根據 'order_num' 排序
    #_results = sorted(_results, key=lambda x: x['order_num'])

    # total_process_records != 0 的資料 → 排在前面, 其餘再依 order_num 排序
    _results = sorted(
      _results,
      key=lambda x: (x.get('total_process_records', 0) == 0, x['order_num'])
    )

    return jsonify({
      'status': True,
      'total': total,
      'informations': _results
    })


@listTable.route("/listInformationsPFiltered", methods=["POST"])
def list_informations_p_filtered():
    print("listInformationsPFiltered....")

    payload = request.get_json(silent=True) or {}
    start_date = (payload.get("start_date") or "").strip()
    end_date   = (payload.get("end_date") or "").strip()
    order_nums = payload.get("order_nums") or []
    order_wildcard = (payload.get("order_wildcard") or "").strip()
    unfinished_only = bool(payload.get("unfinished_only", False))
    limit = int(payload.get("limit") or 2000)

    s = Session()
    try:
        # ✅ 同工單去重：只留每個 order_num 最大 id 的那筆
        latest_id_sq = (
            s.query(func.max(P_Material.id).label("id"))
             .group_by(P_Material.order_num)
             .subquery()
        )

        q = s.query(P_Material).filter(P_Material.id.in_(latest_id_sq))

        # ✅ 日期範圍
        # 你 DB 欄位是 material_delivery_date（date/datetime）
        # 這裡用字串 YYYY-MM-DD 轉 date
        def _to_date(x):
            try:
                return datetime.datetime.strptime(x, "%Y-%m-%d").date()
            except Exception:
                return None

        sd = _to_date(start_date) if start_date else None
        ed = _to_date(end_date) if end_date else None
        if sd and ed:
            q = q.filter(P_Material.material_delivery_date >= sd)\
                 .filter(P_Material.material_delivery_date <= ed)

        # ✅ 工單清單（多選優先）
        if isinstance(order_nums, list) and len(order_nums) > 0:
            q = q.filter(P_Material.order_num.in_(order_nums))
        else:
            # ✅ 萬用字元：* ? → LIKE
            if order_wildcard:
                def wildcard_to_like(p: str) -> str:
                    esc = "\\"
                    p = p.replace(esc, esc + esc)
                    p = p.replace("%", esc + "%").replace("_", esc + "_")
                    p = p.replace("*", "%").replace("?", "_")
                    return p

                like_pat = wildcard_to_like(order_wildcard)
                q = q.filter(P_Material.order_num.like(like_pat, escape="\\"))

        # ✅ 入庫總數（p_product）
        stockin_sq = (
            s.query(
                P_Product.material_id.label("mid"),
                func.coalesce(func.sum(P_Product.allOk_qty), 0).label("stockin_total")
            )
            .group_by(P_Product.material_id)
            .subquery()
        )

        q = q.outerjoin(stockin_sq, stockin_sq.c.mid == P_Material.id)

        # ✅ 只顯示未完成（入庫量 < 訂單量）
        if unfinished_only:
            q = q.filter(func.coalesce(stockin_sq.c.stockin_total, 0) < func.coalesce(P_Material.material_qty, 0))

        # ✅ 上限
        q = q.order_by(P_Material.order_num).limit(limit)

        rows = q.all()

        # ===== 以下：維持原 listInformationsP 的回傳格式（只針對 rows 迭代）=====
        _results = []
        return_value = True
        str1 = ['領料站', '加工站', '成品站']
        str2 = ['未領料', '領料中', '領料已完成', '等待加工作業', '加工作業進行中', '加工作業已完成', '等待入庫作業', '入庫進行中', '入庫完成']

        # part map（你原本那套 그대로）
        def norm_code(x: str) -> str:
            return (x or "").strip().upper().replace(" ", "")

        def alias_code(x: str) -> str:
            x = norm_code(x)
            m = re.match(r'^(B\d{3})[A-Z]*-(\d+)$', x)
            if not m:
                return x
            return f"{m.group(1)}-{m.group(2)}"

        part_info_map = {}
        for p in s.query(P_Part).all():
            code = norm_code(p.part_code or "")
            if not code:
                continue
            info = {"comment": (p.part_comment or "").strip(),
                    "process_step_code": int(p.process_step_code or 0)}
            part_info_map[code] = info
            part_info_map.setdefault(alias_code(code), info)

        def _to_int(v, default=0):
            try:
                if v is None:
                    return default
                return int(v)
            except Exception:
                return default

        for record in rows:
            assemble_records = record._assemble
            process_records = record._process
            total_process_records = len([p for p in process_records if (p.material_id == record.id and p.has_started == 1 and (p.begin_time or '') != '')])

            cleaned_comment = (record.material_comment or "").strip()

            raw = getattr(record, "show2_ok", None)
            try:
                num = int(raw)
            except Exception:
                num = -1

            if 0 <= num < len(str2):
                temp_show2_ok_str = str2[num]
            elif 1 <= num <= len(str2):
                temp_show2_ok_str = str2[num - 1]
            else:
                temp_show2_ok_str = f"未知狀態({raw})"

            if num == 1:
                user = s.query(User).filter_by(emp_id=record.isOpenEmpId).first()
                if user and getattr(user, "emp_name", None):
                    temp_show2_ok_str += f"({user.emp_name})"

            # show3_ok（最小 seq 的工序 comment）
            show_comment = ""
            try:
                show3_ok_val = int(record.show3_ok or 0)
            except Exception:
                show3_ok_val = 0

            if record.isBom or (not record.isBom and record.isTakeOk and record.isShow):
                if record._assemble:
                    valid_assembles = [
                        a for a in record._assemble
                        if (a.work_num not in (None, '', '0') and a.seq_num is not None and str(a.seq_num).isdigit())
                    ]
                    if valid_assembles:
                        min_a = min(valid_assembles, key=lambda a: int(a.seq_num))
                        key = norm_code((min_a.work_num or "").strip())
                        part_info = part_info_map.get(key) or part_info_map.get(alias_code(key))
                        show_comment = (part_info.get("comment", "") if part_info else "")

            # stockin_total
            stockin_total = (
                s.query(func.coalesce(func.sum(P_Product.allOk_qty), 0))
                 .filter(P_Product.material_id == record.id)
                 .scalar()
            ) or 0

            net_good_qty = 0
            for a in assemble_records:
                net_good_qty = max(net_good_qty, _to_int(getattr(a, "must_receive_end_qty", 0), 0))
                if net_good_qty == 0:
                    net_good_qty = max(net_good_qty, _to_int(getattr(a, "total_ask_qty_end", 0), 0))

            delivery_qty = int(stockin_total) if int(stockin_total) > 0 else (net_good_qty if net_good_qty > 0 else _to_int(record.delivery_qty, 0))

            _results.append({
                'id': record.id,
                'order_num': record.order_num,
                'material_num': record.material_num,
                'isTakeOk': record.isTakeOk,
                'whichStation': record.whichStation,
                'req_qty': record.material_qty,
                'delivery_date': record.material_delivery_date,
                'delivery_qty': delivery_qty,
                'comment': cleaned_comment,
                'show1_ok': str1[int(record.show1_ok) - 1] if str(record.show1_ok).isdigit() and 1 <= int(record.show1_ok) <= len(str1) else '',
                'show2_ok': temp_show2_ok_str,
                'show3_ok': show_comment,
                'isOpenEmpId': record.isOpenEmpId,
                'total_process_records': total_process_records,
            })

        if len(_results) == 0:
            return_value = False

        return jsonify({'status': return_value, 'informations': _results})

    finally:
        s.close()


# list all materials for information list
@listTable.route("/listInformationsForAssembleError", methods=['GET'])
def list_informations_for_assemble_error():
    print("listInformationsForAssembleError....")

    _history_flag = False

    s = Session()

    _results = []
    return_value = True
    str1=['備料站', '組裝站', '成品站']
    #       0        1         2          3              4            5            6           7           8             9         10        11           12           13          14          15            16          17
    str2=['未備料', '備料中',  '備料完成', '等待組裝作業', '組裝進行中', '00/00/00', '檢驗進行中', '00/00/00',  '雷射進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0    1          2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)    7(結束鍵)     8(開始鍵)    9(結束鍵)     10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(開始鍵)        15(結束鍵)   16(開始鍵)    17(結束鍵)    18(agv_begin)    19(agv_end)  20(agv_alarm)
    #str3=['',  '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業', 'agv Start']
    str3=['',  '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '檢驗進行中', '檢驗已結束', '雷射進行中', '雷射已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業', 'agv Start']
    #      0    1          2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)    7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)      11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)    16(agv_start)

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for material_record in _objects:
      skip_material = False  # 標誌變數，預設為 False
      user_ids = []  # 用於存儲處理後的 user_id
      #print("step a...", material_record.id)
      for assemble_record in material_record._assemble:
        #print("assemble_record.material_id:", assemble_record.material_id)
        #print("assemble_record:", assemble_record)
        if assemble_record.material_id != material_record.id:
          skip_material = True
        if assemble_record.alarm_enable == False:
          continue
        user_id = assemble_record.user_id.lstrip('0')  # 去除前導的 0
        user_ids.append(user_id)  # 將處理後的值加入列表

      if skip_material:
          continue                # 跳過當前 material_record，進入下一個 _objects 的迴圈

      temp_alarm_message=assemble_record.alarm_message.strip()
      temp_alarm_enable=assemble_record.alarm_enable
      if not _history_flag and temp_alarm_enable and temp_alarm_message:
        continue

      user = ', '.join(user_ids)  # 將列表轉換為以逗號分隔的字符串
      print("user:", user)
      cleaned_comment = material_record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

      temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
      temp_show2_ok = int(material_record.show2_ok)
      if (temp_show2_ok == 1):
        temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note
      '''
      # 取得所有相關聯的 AbnormalCause 資料
      abnormal_cause = (
        {
          "cause_id": material_record._abnormal_cause[0].id,
          "cause_number": material_record._abnormal_cause[0].number,
          "cause_message": material_record._abnormal_cause[0].message,
        }
        if material_record._abnormal_cause and len(material_record._abnormal_cause) > 0
        else {
          "cause_id": '',
          "cause_number": '',
          "cause_message": '',
        }
      )
      '''
      _object = {
        'id': material_record.id,                                # 訂單編號的 table id
        'order_num': material_record.order_num,                  # 訂單編號
        'material_num': material_record.material_num,            # 物料編號
        'isTakeOk': material_record.isTakeOk,
        'whichStation': material_record.whichStation,
        'req_qty': material_record.material_qty,                 # 需求數量
        'delivery_date': material_record.material_delivery_date, # 交期
        'delivery_qty': material_record.delivery_qty,            # 現況數量
        'comment': cleaned_comment,                              # 說明
        'show1_ok': str1[int(material_record.show1_ok) - 1],     # 現況進度
        'show2_ok': temp_temp_show2_ok_str,
        'show3_ok': str3[int(material_record.show3_ok)],         # 現況備註
        'user': user,
        #**abnormal_cause                                         # 將 cause_id, cause_number, cause_message 展開加入字典
        #'cause_number': '',
        'cause_message': temp_alarm_message,
      }

      _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listInformationsForAssembleError, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 'order_num' 排序
    _results = sorted(_results, key=lambda x: x['order_num'])

    return jsonify({
      'status': return_value,
      'informations_for_assemble_error': _results
    })


# list all materials for information list
@listTable.route("/listAssembleInformations", methods=['GET'])
def list_assemble_informations():
    print("listAssembleInformations....")

    s = Session()

    _results = []
    return_value = True
    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                 3              4             5          6             7             8             9          10                 11             12           13          14          15            16          17
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '檢驗進行中', '00/00/00',  '雷射進行中',  '00/00/00',  '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)     16(avg_start)
    #str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業', 'agv Start']
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '檢驗進行中', '檢驗已結束', '雷射進行中', '雷射已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業', 'agv Start']

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for record in _objects:
      if record.isAssembleStation3TakeOk:   # 檢查 isAssembleStation3TakeOk 是否為 True, 異常
        cleaned_comment = record.material_comment.strip()  # 刪除 material_comment 字串前後的空白
        temp_temp_show2_ok_str = str2[int(record.show2_ok)]
        temp_show2_ok = int(record.show2_ok)
        if (temp_show2_ok == 1):
          temp_temp_show2_ok_str = temp_temp_show2_ok_str + record.shortage_note

        _object = {
          'order_num': record.order_num,                 #訂單編號

          'isTakeOk': record.isTakeOk,
          'whichStation': record.whichStation,
          'req_qty': record.material_qty,                #需求數量
          'delivery_date':record.material_delivery_date, #交期
          'comment': cleaned_comment,                    #說明
          'show1_ok' : str1[int(record.show1_ok) - 1],                  #現況進度
          'show2_ok' : temp_temp_show2_ok_str,
          'show3_ok' : str3[int(record.show3_ok)],                  #現況備註
        }

        _results.append(_object)

    s.close()

    temp_len = len(_results)
    #print("listInformations, 資料: ", _results)
    print("listInformations, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 'order_num' 排序
    _results = sorted(_results, key=lambda x: x['order_num'])

    return jsonify({
        'status': return_value,
        'informations': _results
    })


@listTable.route('/createDelegate', methods=['POST'])
def create_delegate():
    data = request.json
    user_id = int(data['user_id'])
    delegate_emp_id = data['delegate_emp_id'].strip()
    start_date = datetime.fromisoformat(data['start_date'].replace('Z','')) if data.get('start_date') else None
    end_date = datetime.fromisoformat(data['end_date'].replace('Z','')) if data.get('end_date') else None
    reason = (data.get('reason') or '').strip()

    if not user_id or not delegate_emp_id or not start_date:
        return jsonify(success=False, message='user_id / delegate_emp_id / start_date 為必填')

    s = Session()
    # 檢查重疊
    overlap = s.query(UserDelegate).filter(
        UserDelegate.user_id == user_id,
        UserDelegate.start_date <= (end_date or datetime.max),
        start_date <= func.ifnull(UserDelegate.end_date, datetime.max)  # MySQL: IFNULL
    ).count()
    if overlap > 0:
        return jsonify(success=False, message='期間與既有代理重疊，請調整')

    ud = UserDelegate(
        user_id=user_id,
        delegate_emp_id=delegate_emp_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason
    )
    s.add(ud)
    s.commit()

    return jsonify(success=True, id=ud.id)


@listTable.route('/terminateActiveDelegate', methods=['POST'])
def terminate_active_delegate():
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


@listTable.route('/deleteDelegate', methods=['POST'])
def delete_delegate():
    data = request.json
    row_id = int(data['id'])
    s = Session()
    r = s.get(UserDelegate, row_id)
    if not r:
        return jsonify(success=False, message='not found')
    s.delete(r)
    s.commit()

    return jsonify(success=True)


@listTable.route("/listProducts", methods=["GET"])
def list_products():
    print("listProducts....")

    s = Session()
    try:
        limit_n = request.args.get("limit", "100")

        # 子查詢：每個 material 的最新 process.create_at
        latest_proc_sub = (
            s.query(
                Process.material_id.label("mid"),
                func.max(Process.create_at).label("mx_created")
            )
            .group_by(Process.material_id)
            .subquery()
        )

        # 主查詢：左連到最新時間，再連回同一筆 Process
        q = (
            s.query(Product, Material, Process)
             .join(Material, Product.material_id == Material.id)
             .outerjoin(latest_proc_sub, latest_proc_sub.c.mid == Material.id)
             .outerjoin(
                 Process,
                 (Process.material_id == latest_proc_sub.c.mid) &
                 (Process.create_at  == latest_proc_sub.c.mx_created)
             )
             .filter(Product.allOk_qty != 0)
             .order_by(Product.create_at.desc())
             .limit(limit_n)
        )

        rows = q.all()

        items = []
        for p, m, proc in rows:
            items.append({
                #"product_id":      p.id,
                #"material_id":     p.material_id,
                #"delivery_qty":    p.delivery_qty or 0,
                #"assemble_qty":    p.assemble_qty or 0,
                "allOk_qty":       p.allOk_qty or 0,
                #"good_qty":        p.good_qty or 0,
                #"non_good_qty":    p.non_good_qty or 0,
                #"reason":          p.reason or "",
                #"confirm_comment": p.confirm_comment or "",
                "create_at":       p.create_at.isoformat() if getattr(p, "create_at", None) else None,

                "id":               m.id,
                "order_num":        m.order_num,
                "material_num":     m.material_num,
                "req_qty":          m.material_qty,
                "date":             m.material_delivery_date,
                "comment": (m.material_comment or "").strip(),
                "Incoming2_Abnormal": (getattr(m, "Incoming2_Abnormal", "") == ""),

                #"req_qty":          m.material_qty or 0,
                #"date":             m.material_delivery_date or "",
                #"input_disable":    bool(m.input_disable),
                #"shortage_note":    m.shortage_note or "",
                #"isLackMaterial":   m.isLackMaterial or 0,

                # 一律輸出 False
                "isAllOk": False,

                # 最新 process 的欄位（可能沒有 → 給 0）
                "must_allOk_qty":        (getattr(proc, "must_allOk_qty", 0) or 0),
                "delivery_qty": (getattr(proc, "process_work_time_qty", 0) or 0),
            })

        print("items:", items)

        return jsonify({"status": True, "count": len(items), "items": items}), 200

    except Exception as e:
        return jsonify({"status": False, "error": str(e)}), 500
    finally:
        s.close()