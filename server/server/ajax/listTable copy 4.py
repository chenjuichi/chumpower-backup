import math
import random
import re
from datetime import datetime, date, timedelta

import traceback

from datetime import datetime as dt
import time

from sqlalchemy import and_,  distinct, func, case, select
from flask import Blueprint, jsonify, request, current_app

from database.tables import User, UserDelegate, Material, Bom, Assemble, Permission, AbnormalCause, Process, Product, Setting, Session
from database.p_tables import P_Material, P_Assemble,  P_AbnormalCause, P_Process, P_Product, P_Part
from database.tables import default_process_steps

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


def order_has_lack_by_id(session, id: int) -> bool:
    """
    訂單層級缺料判斷：
    - Bom.receive == False 或 Bom.receive is NULL 都算缺料
    """
    if not id:
        return False

    q = (
        session.query(Bom.id)
        .join(Material, Material.id == Bom.material_id)
        .filter(Material.id == id)
        .filter(or_(Bom.receive.is_(False), Bom.receive.is_(None)))
        .limit(1)
    )
    return session.query(q.exists()).scalar() is True


def shortage_note_by_order(session, order_num: str) -> str:
    return "(缺料)" if order_has_lack(session, order_num) else ""


def shortage_note_by_order_id(session, id: int) -> str:
    return "(缺料)" if order_has_lack_by_id(session, id) else ""

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
    '''
    從 p_part 資料表讀取所有製程資料，組出：

        code_to_assembleStep = { '100-01': step_code, '100-02': step_code, ... }

    規則：
      - 使用 P_Part.part_code 當 key 的來源，例如 'B100-01'
      - 若 part_code 以 'B' 開頭，就去掉 'B'，變成 '100-01' 當 dict 的 key
      - value 直接使用 P_Part.process_step_code
    '''

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
    '''
    3 -> 21, 2 -> 22, 1 -> 23，其餘預設 23。
    支援欄位名：process_step_code / process_step / step_code
    row 可為 dict 或 ORM 物件。
    '''
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
    # 同時支援 dict 與 ORM 物件取值。
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def active_count_map_by_material_multi(session, material_ids, process_types=(21,22,23), include_paused=True):
    '''
    回傳格式：
    {
      "21": { "101": 2, "103": 1 },
      "22": { "101": 1 },
      "23": {}
    }
    include_paused: True → 只要未結束就算（包含暫停）
                     False → 只算「正在跑」（不含暫停）
    '''
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

    '''
    回傳 (is_insufficient, process_total)
    is_insufficient: True 表示加總 < must_qty；False 表示 >= must_qty
    process_total  : 依條件加總後的數量（int）
    '''
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
  #print("file_ok flag value is: ", _file_ok)

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
  #print("socket_server_ip is: ", _socket_server_ip)

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
        #import traceback
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
            #print("_object:", _object)
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
    #print("today:",today)

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

    #print(result)

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

  #print(result)

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


# 20260710版
@listTable.route("/listMaterialsAndAssembles", methods=['GET'])
def list_materials_and_assembles():
    print("listMaterialsAndAssembles.")

    t0 = time.time()
    s = Session()

    _results = []
    _assemble_active_users = []

    #_user_id = (request.args.get("user_id") or "").strip()
    _user_id_raw = request.args.get("user_id")

    def safe_str(v, default=''):
        try:
            return '' if v is None else str(v).strip()
        except Exception:
            return default

    #
    def normalize_user_id(v):
        # 員工編號統一格式：
        # - 去除前後空白
        # - 去除前導 0
        # - 全部以字串比較

        txt = safe_str(v)

        if not txt:
            return ""

        normalized = txt.lstrip("0")

        # 避免全為 0 時變空字串
        return normalized or "0"
    #

    def process_type_by_work_num(work_num):
        w = safe_str(work_num)
        if w == 'B109':
            return 21
        if w == 'B110':
            return 22
        if w == 'B106':
            return 23
        return 0

    def work_name_by_work_num(work_num):
        w = safe_str(work_num)
        if w == 'B109':
            return '組裝'
        if w == 'B110':
            return '檢驗'
        if w == 'B106':
            return '雷射'
        return ''

    def is_not_empty_time(v):
        if v is None:
            return False
        txt = safe_str(v)
        return txt not in ('', 'None', '0000-00-00 00:00:00')

    def is_process_running(p):
        if not is_not_empty_time(getattr(p, "begin_time", None)):
            return False
        if is_not_empty_time(getattr(p, "end_time", None)):
            return False
        if not bool(getattr(p, "has_started", False)):
            return False
        return True

    _user_id = normalize_user_id(_user_id_raw)

    try:
        _objects = (
            s.query(Material)
            .filter(Material.move_by_process_type == 2)
            .filter(Material.isShow.is_(True))
            .options(
                selectinload(Material._assemble),
                selectinload(Material._process),
            )
            .all()
        )

        if not _objects:
            return jsonify({
                "status": False,
                "materials_and_assembles": [],
                "assemble_active_users": [],
            })

        material_ids_all = [int(m.id) for m in _objects if m.id]
        order_nums = list({safe_str(m.order_num) for m in _objects if safe_str(m.order_num)})

        bom_count_by_mid = {}
        bom_receive_true_by_mid = {}
        bom_lack_by_mid = {}

        if material_ids_all:
            for mid, cnt in (
                s.query(Bom.material_id, func.count(Bom.id))
                .filter(Bom.material_id.in_(material_ids_all))
                .group_by(Bom.material_id)
                .all()
            ):
                bom_count_by_mid[int(mid)] = int(cnt or 0)

            for mid, cnt in (
                s.query(Bom.material_id, func.count(Bom.id))
                .filter(Bom.material_id.in_(material_ids_all))
                .filter(Bom.receive.is_(True))
                .group_by(Bom.material_id)
                .all()
            ):
                bom_receive_true_by_mid[int(mid)] = int(cnt or 0)

            for mid, cnt in (
                s.query(Bom.material_id, func.count(Bom.id))
                .filter(Bom.material_id.in_(material_ids_all))
                .filter(or_(Bom.receive.is_(False), Bom.receive.is_(None)))
                .group_by(Bom.material_id)
                .all()
            ):
                bom_lack_by_mid[int(mid)] = int(cnt or 0)

        shortage_order_set = set()

        if order_nums:
            rows = (
                s.query(Material.order_num)
                .join(Bom, Bom.material_id == Material.id)
                .filter(Material.order_num.in_(order_nums))
                .filter(or_(Bom.receive.is_(False), Bom.receive.is_(None)))
                .distinct()
                .all()
            )
            shortage_order_set = {safe_str(r[0]) for r in rows if safe_str(r[0])}

        process_total_map = {}

        if material_ids_all:
            rows = (
                s.query(
                    Process.material_id,
                    Process.assemble_id,
                    Process.process_type,
                    func.coalesce(func.sum(Process.process_work_time_qty), 0)
                )
                .filter(Process.material_id.in_(material_ids_all))
                .filter(Process.process_type.in_([21, 22, 23]))
                .filter(Process.has_started.is_(True))
                .filter(Process.end_time.isnot(None))
                .filter(Process.end_time != '')
                .group_by(Process.material_id, Process.assemble_id, Process.process_type)
                .all()
            )

            for mid, aid, ptype, total in rows:
                process_total_map[(int(mid or 0), int(aid or 0), int(ptype or 0))] = int(total or 0)

        active_process_by_assemble = {}
        my_active_process_by_assemble = {}
        running_mid_set = set()

        if material_ids_all:
            active_rows = (
                s.query(Process)
                .join(Assemble, Process.assemble_id == Assemble.id)
                .filter(Process.material_id.in_(material_ids_all))
                .filter(Process.process_type.in_([21, 22, 23]))
                .filter(Process.has_started.is_(True))
                .filter(Process.begin_time.isnot(None))
                .filter(Process.begin_time != '')
                .filter(Process.end_time.is_(None))
                .filter(
                    or_(
                        Assemble.currentEndTime.is_(None),
                        Assemble.currentEndTime == ''
                    )
                )
                .filter(
                    or_(
                        and_(Assemble.work_num == 'B109', Process.process_type == 21),
                        and_(Assemble.work_num == 'B110', Process.process_type == 22),
                        and_(Assemble.work_num == 'B106', Process.process_type == 23),
                    )
                )
                .order_by(Process.id.desc())
                .all()
            )

            for p in active_rows:
                if not is_process_running(p):
                    continue

                mid = int(p.material_id or 0)
                aid = int(p.assemble_id or 0)

                running_mid_set.add(mid)
                active_process_by_assemble.setdefault(aid, []).append(p)

                #if _user_id and safe_str(p.user_id) == _user_id:
                #    if aid not in my_active_process_by_assemble:
                #        my_active_process_by_assemble[aid] = p
                #
                process_user_id = normalize_user_id(
                    getattr(p, "user_id", "")
                )

                if (
                    _user_id
                    and process_user_id == _user_id
                ):
                    if aid not in my_active_process_by_assemble:
                        my_active_process_by_assemble[aid] = p

        current_step_group_by_mid = {}

        for m in _objects:
            max_step = 0
            for a in (m._assemble or []):
                step = int(getattr(a, "process_step_code", 0) or 0)
                if step > max_step:
                    max_step = step
            current_step_group_by_mid[int(m.id)] = max_step

        index = 0

        for material_record in _objects:
            material_id = int(material_record.id or 0)
            order_num = safe_str(material_record.order_num)

            assemble_records = list(material_record._assemble or [])
            if not assemble_records:
                continue

            cleaned_comment = safe_str(material_record.material_comment)
            current_group_step = current_step_group_by_mid.get(material_id, 0)

            shortage_note = "(缺料)" if order_num in shortage_order_set else ""

            has_bom = bom_count_by_mid.get(material_id, 0)
            has_receive_true = bom_receive_true_by_mid.get(material_id, 0)
            has_receive_false_or_null = bom_lack_by_mid.get(material_id, 0)

            has_scheduled_rows = any(
                int(getattr(a, "schedule_id", 0) or 0) > 0
                for a in assemble_records
            )

            #
            # ------------------------------------------------------------
            # 尚未按「+工序」時，找出一筆 B109 樣板列
            #
            # 條件：
            # material.process_step_enable = 0
            # schedule_id 為 NULL/0
            # work_num = B109
            # isAssembleStationShow = True
            # ------------------------------------------------------------
            unscheduled_b109_template_id = 0

            if not bool(getattr(material_record, "process_step_enable", False)):
                #template_rows = [
                #    a for a in assemble_records
                #    if (
                #        safe_str(getattr(a, "work_num", "")) == "B109"
                #        and int(getattr(a, "process_step_code", 0) or 0) > 0
                #        and int(getattr(a, "schedule_id", 0) or 0) == 0
                #        and bool(getattr(a, "isAssembleStationShow", False))
                #        and not bool(getattr(a, "isWarehouseStationShow", False))
                #    )
                #]
                #
                template_rows = [
                    a for a in assemble_records
                    if (
                        safe_str(getattr(a, "work_num", "")) == "B109"
                        and int(getattr(a, "schedule_id", 0) or 0) == 0
                        and bool(getattr(a, "isAssembleStationShow", False))
                        and not bool(getattr(a, "isWarehouseStationShow", False))
                    )
                ]
                #

                if template_rows:
                    unscheduled_b109_template_id = min(
                        int(getattr(a, "id", 0) or 0)
                        for a in template_rows
                    )
            #

            for assemble_record in assemble_records:
                assemble_id = int(assemble_record.id or 0)
                work_num = safe_str(getattr(assemble_record, "work_num", ""))
                pt = process_type_by_work_num(work_num)

                if pt == 0:
                    continue

                # 已送到 Warehouse 的 assemble row 不顯示 Begin
                if bool(getattr(assemble_record, "isWarehouseStationShow", False)):
                    continue

                # B110 已完成補筆只給 End 顯示，不可出現在 Begin
                if (
                    work_num == "B110"
                    and safe_str(getattr(assemble_record, "reason", "")) == "B110_DONE_COPY"
                ):
                    continue

                # B109 已完成資料只給 End 顯示，不可出現在 Begin
                if (
                    work_num == "B109"
                    and int(getattr(assemble_record, "process_step_code", 0) or 0) == 0
                    and int(getattr(assemble_record, "completed_qty", 0) or 0) > 0
                    and int(getattr(assemble_record, "show2_ok", 0) or 0) == 5
                ):
                    continue

                step = int(getattr(assemble_record, "process_step_code", 0) or 0)
                schedule_id = int(getattr(assemble_record, "schedule_id", 0) or 0)
                must_receive_qty = int(getattr(assemble_record, "must_receive_qty", 0) or 0)
                must_receive_end_qty = int(getattr(assemble_record, "must_receive_end_qty", 0) or 0)
                assemble_show2 = int(getattr(assemble_record, "show2_ok", 0) or 0)

                #
                # ------------------------------------------------------------
                # 是否為「尚未按 +工序」的唯一 B109 樣板列
                # ------------------------------------------------------------
                is_unscheduled_template = (
                    not bool(getattr(material_record, "process_step_enable", False))
                    and work_num == "B109"
                    and schedule_id == 0
                    and assemble_id == unscheduled_b109_template_id
                )
                #

                is_released_check_batch = (
                    work_num == "B110"
                    and safe_str(getattr(assemble_record, "reason", "")) == "B109_RELEASE_BATCH"
                )

                #
                # ----------------------------------------------------
                # Begin 不可顯示 End 待送出資料
                # 例如批次1 b1/b2 已完成後 show2_ok=9，
                # 只能留在 End.vue 藍字待送出，不可再出現在 Begin。
                # ----------------------------------------------------
                if (
                    work_num == "B110"
                    and step <= 0
                    and assemble_show2 in (9, 10)
                    and my_active_process_by_assemble.get(assemble_id) is None
                ):
                    continue

                # B110_DONE_COPY 不可出現在 Begin
                if (
                    work_num == "B110"
                    and safe_str(getattr(assemble_record, "reason", "")) == "B110_DONE_COPY"
                ):
                    continue
                #

                #if must_receive_qty <= 0:
                #    continue
                #
                # 正式排程列必須有 must_receive_qty；
                # 未按 +工序的 B109 樣板列允許數量為 0。
                if must_receive_qty <= 0 and not is_unscheduled_template:
                    continue
                #

                my_active_process = my_active_process_by_assemble.get(assemble_id)
                active_processes = active_process_by_assemble.get(assemble_id, [])

                # ------------------------------------------------------------
                # B109 已全部完成，不再顯示於 Begin
                # ------------------------------------------------------------
                if (
                    work_num in ("B109", "B110")
                    and step == 0
                    and assemble_show2 == 7
                    and my_active_process is None
                ):
                    continue

                has_any_running_process = len(active_processes) > 0

                active_user_ids = []
                for p in active_processes:
                    #uid = safe_str(getattr(p, "user_id", ""))
                    uid = normalize_user_id(getattr(p, "user_id", ""))
                    if uid and uid not in active_user_ids:
                        active_user_ids.append(uid)

                # 已待送出 / 入庫前資料不顯示 Begin
                if step <= 0 and my_active_process is None and assemble_show2 >= 9:
                    continue

                if (
                    current_group_step
                    and step < current_group_step
                    and my_active_process is None
                    and not is_released_check_batch
                    and assemble_show2 >= 9
                ):
                    continue

                #if has_scheduled_rows and schedule_id <= 0 and my_active_process is None:
                #    continue
                #
                if (
                    has_scheduled_rows
                    and schedule_id <= 0
                    and my_active_process is None
                    and not is_unscheduled_template
                ):
                    continue
                #

                if work_num == "B110" and my_active_process is None and not is_released_check_batch:
                    remaining_b109 = [
                        a for a in assemble_records
                        if safe_str(getattr(a, "work_num", "")) == "B109"
                        and int(getattr(a, "process_step_code", 0) or 0) > 0
                    ]

                    if remaining_b109:
                        continue

                process_total = process_total_map.get((material_id, assemble_id, pt), 0)

                need_more = True
                if must_receive_end_qty > 0:
                    need_more = process_total < must_receive_end_qty

                if (
                    (not need_more)
                    and process_total != 0
                    and my_active_process is None
                    and assemble_show2 >= 9
                ):
                    continue

                #display_active_process = my_active_process or (active_processes[0] if active_processes else None)
                #show_timer = display_active_process is not None
                #show_name = safe_str(getattr(display_active_process, "user_id", "")) if display_active_process else ""
                #
                display_active_process = (
                    my_active_process
                    or (active_processes[0] if active_processes else None)
                )

                # -------------------------------------------------
                # Timer 只能顯示目前登入者自己的 process
                # -------------------------------------------------
                show_timer = my_active_process is not None

                show_name = (
                    safe_str(getattr(my_active_process, "user_id", ""))
                    if my_active_process
                    else ""
                )
                #

                begin_records = []
                for p in active_processes:
                    '''
                    begin_records.append({
                        "process_id": int(getattr(p, "id", 0) or 0),
                        "user_id": safe_str(getattr(p, "user_id", "")),
                        "begin_time": safe_str(getattr(p, "begin_time", "")),
                        "elapsedActive_time": int(getattr(p, "elapsedActive_time", 0) or 0),
                        "str_elapsedActive_time": safe_str(getattr(p, "str_elapsedActive_time", "")),
                    })
                    '''
                    #
                    raw_process_user_id = safe_str(getattr(p, "user_id", ""))

                    begin_records.append({
                        "process_id": int(getattr(p, "id", 0) or 0),

                        # 前端判斷本人使用統一格式
                        "user_id": normalize_user_id(raw_process_user_id),

                        # 保留資料庫原始值供除錯
                        "raw_user_id": raw_process_user_id,

                        "begin_time": safe_str(getattr(p, "begin_time", "")),

                        "elapsedActive_time": int(getattr(p, "elapsedActive_time", 0) or 0),

                        "str_elapsedActive_time": safe_str(getattr(p, "str_elapsedActive_time", "")),

                        "end_time": safe_str(getattr(p, "end_time", "")),
                    })

                    #
                    print(
                        "[active process user compare]",
                        {
                            "assemble_id": aid,
                            "process_id": int(
                                getattr(p, "id", 0) or 0
                            ),
                            "request_user_raw": _user_id_raw,
                            "request_user_normalized": _user_id,
                            "process_user_raw": safe_str(
                                getattr(p, "user_id", "")
                            ),
                            "process_user_normalized":
                                normalize_user_id(
                                    getattr(p, "user_id", "")
                                ),
                            "matched": (
                                normalize_user_id(
                                    getattr(p, "user_id", "")
                                ) == _user_id
                            )
                        }
                    )
                # end active_processes loop

                is_begin_reworkable_row = (
                    not bool(getattr(assemble_record, "isWarehouseStationShow", False))
                    and int(getattr(assemble_record, "show2_ok", 0) or 0) < 9
                )

                #
                work_num = (assemble_record.work_num or '').strip()
                step = int(assemble_record.process_step_code or 0)
                is_show = bool(getattr(assemble_record, 'isAssembleStationShow', False))
                is_warehouse_show = bool(getattr(assemble_record, 'isWarehouseStationShow', False))

                # Begin 只顯示還在組裝站的資料
                if not is_show:
                    continue

                # Begin 不顯示已結束 / template / 歷史列
                #if work_num in ('B109', 'B110') and step <= 0:
                #    continue
                #
                # 已完成 / 歷史列不顯示；
                # 尚未按 +工序的 B109 樣板列例外保留。
                if (
                    work_num in ('B109', 'B110')
                    and step <= 0
                    and not is_unscheduled_template
                ):
                    continue
                #

                # Begin 不顯示已經送到 Warehouse 的列
                if is_warehouse_show:
                    continue

                index += 1

                _object = {
                    "index": index,
                    "id": material_record.id,
                    "assemble_id": assemble_record.id,
                    "row_key": f"{material_record.id}_{assemble_record.id}",

                    "order_num": material_record.order_num,
                    "material_num": material_record.material_num,
                    "material_comment": material_record.material_comment,
                    "comment": cleaned_comment,

                    "req_qty": material_record.material_qty,
                    "delivery_qty": material_record.delivery_qty,
                    "total_delivery_qty": material_record.total_delivery_qty,

                    "total_receive_qty": f"({getattr(assemble_record, 'total_ask_qty', 0)})",
                    "total_receive_qty_num": getattr(assemble_record, "total_ask_qty", 0),

                    "must_receive_qty": must_receive_qty,
                    "receive_qty": must_receive_qty,
                    "must_receive_end_qty": must_receive_end_qty,

                    "delivery_date": material_record.material_delivery_date,
                    "date": material_record.material_date,

                    "isTakeOk": material_record.isTakeOk,
                    "whichStation": getattr(material_record, "whichStation", None),

                    "isAssembleStation1TakeOk": material_record.isAssembleStation1TakeOk,
                    "isAssembleStation2TakeOk": material_record.isAssembleStation2TakeOk,
                    "isAssembleStation3TakeOk": material_record.isAssembleStation3TakeOk,

                    "currentStartTime": (
                        safe_str(getattr(display_active_process, "begin_time", ""))
                        if display_active_process
                        else getattr(assemble_record, "currentStartTime", None)
                    ),
                    "currentEndTime": getattr(assemble_record, "currentEndTime", None),

                    "tooltipVisible": False,

                    "input_allOk_disable": bool(getattr(assemble_record, "input_allOk_disable", False)),

                    "input_disable": False if is_begin_reworkable_row else bool(getattr(assemble_record, "input_disable", False)),
                    "input_end_disable": False if is_begin_reworkable_row else bool(getattr(assemble_record, "input_end_disable", False)),
                    "input_abnormal_disable": False if is_begin_reworkable_row else bool(getattr(assemble_record, "input_abnormal_disable", False)),

                    "Incoming1_Abnormal": getattr(assemble_record, "Incoming1_Abnormal", "") == "",
                    "is_copied_from_id": getattr(assemble_record, "is_copied_from_id", None),
                    "create_at": assemble_record.create_at,

                    "show_timer": show_timer,
                    "show_name": show_name,
                    "begin_records": begin_records,

                    "active_process_id": int(getattr(display_active_process, "id", 0) or 0) if display_active_process else 0,
                    "active_begin_time": safe_str(getattr(display_active_process, "begin_time", "")) if display_active_process else "",
                    "active_elapsedActive_time": int(getattr(display_active_process, "elapsedActive_time", 0) or 0) if display_active_process else 0,
                    "active_str_elapsedActive_time": safe_str(getattr(display_active_process, "str_elapsedActive_time", "")) if display_active_process else "",

                    #"my_process_id": int(getattr(display_active_process, "id", 0) or 0) if display_active_process else 0,
                    #"my_begin_time": safe_str(getattr(display_active_process, "begin_time", "")) if display_active_process else "",
                    #"my_elapsedActive_time": int(getattr(display_active_process, "elapsedActive_time", 0) or 0) if display_active_process else 0,
                    #
                    "my_process_id": (
                        int(getattr(my_active_process, "id", 0) or 0)
                        if my_active_process
                        else 0
                    ),

                    "my_begin_time": (
                        safe_str(getattr(my_active_process, "begin_time", ""))
                        if my_active_process
                        else ""
                    ),

                    "my_elapsedActive_time": (
                        int(
                            getattr(my_active_process, "elapsedActive_time", 0) or 0
                        )
                        if my_active_process
                        else 0
                    ),
                    #

                    "active_user_ids": active_user_ids,
                    "users_for_press_start": len(active_user_ids),

                    "has_any_running_process": has_any_running_process,

                    "has_bom": has_bom,
                    "has_receive_true": has_receive_true,
                    "has_receive_false_or_null": has_receive_false_or_null,

                    "isLackMaterial": material_record.isLackMaterial,
                    "shortage_note": shortage_note,
                    "merge_enabled": bool(getattr(material_record, "merge_enabled", True)),

                    "process_step_code": step,
                    "top_work_rank": step,
                    "is_current_group": True,

                    "process_total": process_total,
                    "need_more_process_qty": need_more,

                    "process_step_enable": bool(getattr(material_record, "process_step_enable", False)),
                    "process_steps": material_record.process_steps or default_process_steps(),

                    "schedule_id": schedule_id,
                    "work_num": work_num,
                    "assemble_work": work_name_by_work_num(work_num),
                    "assemble_process_num": assemble_show2,

                    "is_abnormal_process": (getattr(assemble_record, "reason", "") == "異常返工"),
                    "abnormal_qty": int(getattr(assemble_record, "abnormal_qty", 0) or 0),
                    "isAssembleFirstAlarm_qty": int(getattr(assemble_record, "isAssembleFirstAlarm_qty", 0) or 0),

                    "isAssembleStationShow": bool(getattr(assemble_record, "isAssembleStationShow", False)),
                    "isWarehouseStationShow": bool(getattr(assemble_record, "isWarehouseStationShow", False)),

                    "transport_mode": "自" if bool(getattr(material_record, "move_by_automatic_or_manual", False)) else "人",
                    "alarm_enable": getattr(assemble_record, "alarm_enable", True),

                    "icon_disabled": False,

                    "remain_receive_qty": must_receive_end_qty,

                    "release_batch_no": int(getattr(assemble_record, "release_batch_no", 0) or 0),
                    #
                    "is_unscheduled_template": is_unscheduled_template,
                    #
                }

                _results.append(_object)

        #
        order_nums_for_started = list({
            r.get("order_num")
            for r in _results
            if r.get("order_num")
        })

        started_order_nums = set()

        if order_nums_for_started:
            started_rows = (
                s.query(Material.order_num)
                .join(Process, Process.material_id == Material.id)
                .filter(
                    Material.order_num.in_(order_nums_for_started),
                    Material.move_by_process_type == 2,
                    Process.process_type.in_([21, 22, 23]),
                    Process.begin_time.isnot(None),
                    Process.begin_time != '',
                )
                .distinct()
                .all()
            )

            started_order_nums = {
                safe_str(r[0])
                for r in started_rows
                if safe_str(r[0])
            }
        #

        merged = {}

        for row in _results:
            row["has_any_running_process"] = row.get("order_num") in started_order_nums

            merge_enabled = row.get("merge_enabled") in (1, True, "1", "true", "True")

            #
            release_batch_no = int(row.get("release_batch_no") or 0)

            if merge_enabled:
                if int(row.get("schedule_id") or 0) > 0:
                    key = (
                        f'{row.get("order_num")}_'
                        f'{row.get("work_num")}_'
                        f'{row.get("schedule_id")}_'
                        f'batch{release_batch_no}_'
                        f'{row.get("assemble_id")}'
                    )
                else:
                    key = f'{row.get("order_num")}_batch{release_batch_no}'
            else:
                key = (
                    f'{row.get("order_num")}_'
                    f'{row.get("id")}_'
                    f'{row.get("work_num")}_'
                    f'{row.get("schedule_id")}_'
                    f'batch{release_batch_no}_'
                    f'{row.get("assemble_id")}'
                )
            #

            if key not in merged:
                merged[key] = row
            else:
                if int(row.get("id") or 0) > int(merged[key].get("id") or 0):
                    merged[key] = row

        results = list(merged.values())

        #
        results.sort(
            key=lambda x: (
                safe_str(x.get("order_num")),
                0 if x.get("show_timer") else 1,
                -int(x.get("top_work_rank") or 0),
                int(x.get("release_batch_no") or 0),
                int(x.get("schedule_id") or 0),
                int(x.get("assemble_id") or 0),
            )
        )
        #

        print("listMaterialsAndAssembles cost:", time.time() - t0)

        return jsonify({
            "status": bool(results),
            "materials_and_assembles": results or [],
            "assemble_active_users": _assemble_active_users or [],
        })

    except Exception as e:
        print("listMaterialsAndAssembles ERROR:", repr(e))
        traceback.print_exc()

        try:
            current_app.logger.exception("listMaterialsAndAssembles failed")
        except Exception:
            pass

        print("listMaterialsAndAssembles cost:", time.time() - t0)

        return jsonify({
            "status": False,
            "materials_and_assembles": [],
            "assemble_active_users": [],
        }), 200

    finally:
        s.close()


# 20260709版
@listTable.route("/listInformations", methods=['GET'])
def list_informations():
    print("listInformation....")

    only_unfinished = request.args.get("only_unfinished", "0") in ("1", "true", "True")

    s = Session()

    str1 = ['備料站', '組裝站', '成品站']

    str2 = [
        '未備料', '備料中', '備料完成',
        '等待組裝作業', '組裝進行中', '00/00/00',
        '檢驗進行中', '00/00/00',
        '雷射進行中', '00/00/00',
        '等待入庫作業', '入庫進行中', '入庫完成'
    ]

    str3 = [
        '', '等待agv', 'agv移至組裝區中', '等待組裝作業',
        '組裝進行中', '組裝已結束',
        '檢驗進行中', '檢驗已結束',
        '雷射進行中', '雷射已結束',
        'agv移至成品區中', '等待入庫作業',
        '入庫進行中', '入庫完成',
        'agv移至備料區中', '等待備料作業',
        'agv Start', '推車送料至組裝區中'
    ]

    try:
        stockin_sub = (
            s.query(
                Product.material_id.label("mid"),
                func.coalesce(func.sum(Product.allOk_qty), 0).label("stockin_qty")
            )
            .group_by(Product.material_id)
            .subquery()
        )

        latest_asm_sub = (
            s.query(
                Assemble.material_id.label("mid"),
                Assemble.work_num.label("work_num"),
                func.max(Assemble.id).label("max_asm_id")
            )
            .filter(Assemble.completed_qty > 0)
            .filter(Assemble.work_num.in_(["B109", "B110", "B106"]))
            .group_by(Assemble.material_id, Assemble.work_num)
            .subquery()
        )

        asm_sub = (
            s.query(
                Assemble.material_id.label("mid"),
                func.max(case((Assemble.work_num == "B109", Assemble.completed_qty), else_=0)).label("qty1"),
                func.max(case((Assemble.work_num == "B110", Assemble.completed_qty), else_=0)).label("qty2"),
                func.max(case((Assemble.work_num == "B106", Assemble.completed_qty), else_=0)).label("qty3"),
            )
            .join(
                latest_asm_sub,
                and_(
                    Assemble.id == latest_asm_sub.c.max_asm_id,
                    Assemble.material_id == latest_asm_sub.c.mid,
                    Assemble.work_num == latest_asm_sub.c.work_num,
                )
            )
            .group_by(Assemble.material_id)
            .subquery()
        )

        q = (
            s.query(
                Material,
                func.coalesce(stockin_sub.c.stockin_qty, 0).label("stockin_qty"),
                func.coalesce(asm_sub.c.qty1, 0).label("qty1"),
                func.coalesce(asm_sub.c.qty2, 0).label("qty2"),
                func.coalesce(asm_sub.c.qty3, 0).label("qty3"),
                User.emp_name
            )
            .outerjoin(stockin_sub, stockin_sub.c.mid == Material.id)
            .outerjoin(asm_sub, asm_sub.c.mid == Material.id)
            .outerjoin(User, User.emp_id == Material.isOpenEmpId)
        )

        if only_unfinished:
            q = q.filter(
                func.coalesce(Material.material_qty, 0) !=
                func.coalesce(stockin_sub.c.stockin_qty, 0)
            )

        rows = q.all()

        status_ids = {
            "not_prepare": [],
            "prepare": [],
            "assemble": [],
            "warehouse": [],
            "stockin": [],
        }

        status_orders = {
            "not_prepare": set(),
            "prepare": set(),
            "assemble": set(),
            "warehouse": set(),
            "stockin": set(),
        }

        if not rows:
            return jsonify({
                "status": False,
                "total": 0,
                "informations": [],
                "status_ids": status_ids,
                "status_counts": {
                    "not_prepare": 0,
                    "prepare": 0,
                    "assemble": 0,
                    "warehouse": 0,
                    "stockin": 0,
                }
            })

        _results = []
        order_priority = {}
        order_category = {}

        priority_map = {
            "not_prepare": 1,
            "prepare": 2,
            "assemble": 3,
            "warehouse": 4,
            "stockin": 5,
        }

        def get_category(show2_code, show1_code):
            try:
                show2_code = int(show2_code or 0)
            except Exception:
                show2_code = 0

            try:
                show1_code = int(show1_code or 0)
            except Exception:
                show1_code = 0

            if show2_code == 0:
                return "not_prepare"

            if show2_code in (1, 2):
                return "prepare"

            if show2_code in (3, 4, 5, 6, 7, 8, 9):
                return "assemble"

            if show2_code in (10, 11):
                return "warehouse"

            if show2_code == 12:
                return "stockin"

            if show1_code == 3:
                return "warehouse"

            if show1_code == 2:
                return "assemble"

            return "not_prepare"

        for record, stockin_qty, qty1, qty2, qty3, emp_name in rows:

            #
            '''
            if record.order_num == '121100019957':
                print(
                    '[RAW ORM]',
                    'id=', record.id,
                    'show1=', record.show1_ok,
                    'show2=', record.show2_ok,
                    'show3=', record.show3_ok,
                    'session_bind=', s.get_bind().url
                )
            '''
            #

            show1_code = int(record.show1_ok or 0)
            db_show2_code = int(record.show2_ok or 0)
            show3_code = int(record.show3_ok or 0)

            temp_show2_ok = db_show2_code
            temp_show2_ok_str = str2[temp_show2_ok] if 0 <= temp_show2_ok < len(str2) else ''

            if temp_show2_ok in (5, 7, 9):
                temp_show2_ok_str = f"{qty1}/{qty2}/{qty3}"

            if temp_show2_ok == 1:
                if emp_name:
                    temp_show2_ok_str += f"({emp_name})"
                temp_show2_ok_str += record.shortage_note or ""

            # ------------------------------------------------------------
            # 入庫完成優先判斷
            # material 已是 3 / 12 / 13 時，不可再被 70/70/0 覆蓋
            # ------------------------------------------------------------
            if show1_code == 3 and db_show2_code == 12 and show3_code == 13:
                temp_show2_ok = 12
                temp_show2_ok_str = '入庫完成'
                show3_code = 13
                show3_text = '入庫完成'
            else:
                show3_text = str3[show3_code] if 0 <= show3_code < len(str3) else ''

            show1_text = str1[show1_code - 1] if show1_code in (1, 2, 3) else ''

            row_obj = {
                'id': record.id,
                'order_num': record.order_num,
                'material_num': record.material_num,
                'isTakeOk': record.isTakeOk,
                'whichStation': record.whichStation,
                'req_qty': record.material_qty,
                'delivery_date': record.material_delivery_date,
                'delivery_qty': int(stockin_qty or 0),
                'comment': (record.material_comment or "").strip(),
                'show1_ok': show1_text,
                'show2_ok': temp_show2_ok_str,
                'show3_ok': show3_text,
                'isOpenEmpId': record.isOpenEmpId,
                'show1_code': show1_code,
                'show2_code': temp_show2_ok,
                'show3_code': show3_code,
            }

            _results.append(row_obj)

            category = get_category(temp_show2_ok, show1_code)
            status_ids[category].append(record.id)

            order_num = record.order_num
            old_priority = order_priority.get(order_num, 0)
            new_priority = priority_map.get(category, 0)

            if new_priority > old_priority:
                order_priority[order_num] = new_priority
                order_category[order_num] = category

        for order_num, category in order_category.items():
            status_orders[category].add(order_num)

        _results.sort(key=lambda x: x['order_num'])

        #for x in _results:
        #    if x.get('order_num') == '121100019957':
        #        print('[DEBUG 121100019957]', x)

        return jsonify({
            "status": True,
            "total": len(_results),
            "informations": _results,
            "status_ids": status_ids,
            "status_counts": {
                "not_prepare": len(status_orders["not_prepare"]),
                "prepare": len(status_orders["prepare"]),
                "assemble": len(status_orders["assemble"]),
                "warehouse": len(status_orders["warehouse"]),
                "stockin": len(status_orders["stockin"]),
            }
        })

    except Exception as e:
        print("listInformations ERROR:", repr(e))
        traceback.print_exc()

        return jsonify({
            "status": False,
            "total": 0,
            "informations": [],
            "status_ids": {
                "not_prepare": [],
                "prepare": [],
                "assemble": [],
                "warehouse": [],
                "stockin": [],
            },
            "status_counts": {
                "not_prepare": 0,
                "prepare": 0,
                "assemble": 0,
                "warehouse": 0,
                "stockin": 0,
            }
        }), 200

    finally:
        s.close()


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
    str3=['',  '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '檢驗進行中', '檢驗已結束', '雷射進行中', '雷射已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業', 'agv Start']
    #      0    1          2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)    7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)      11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)    16(agv_start)

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for material_record in _objects:
      skip_material = False  # 標誌變數，預設為 False
      user_ids = []  # 用於存儲處理後的 user_id

      for assemble_record in material_record._assemble:
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

      cleaned_comment = material_record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

      temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
      temp_show2_ok = int(material_record.show2_ok)
      if (temp_show2_ok == 1):
        temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note

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
          'show1_ok' : str1[int(record.show1_ok) - 1],   #現況進度
          'show2_ok' : temp_temp_show2_ok_str,
          'show3_ok' : str3[int(record.show3_ok)],       #現況備註
        }

        _results.append(_object)

    s.close()

    temp_len = len(_results)

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
                "allOk_qty":       p.allOk_qty or 0,
                "create_at":       p.create_at.isoformat() if getattr(p, "create_at", None) else None,

                "id":               m.id,
                "order_num":        m.order_num,
                "material_num":     m.material_num,
                "req_qty":          m.material_qty,
                "date":             m.material_delivery_date,
                "comment": (m.material_comment or "").strip(),
                "Incoming2_Abnormal": (getattr(m, "Incoming2_Abnormal", "") == ""),

                "isAllOk": False,

                # 最新 process 的欄位（可能沒有 → 給 0）
                "must_allOk_qty":        (getattr(proc, "must_allOk_qty", 0) or 0),
                "delivery_qty": (getattr(proc, "process_work_time_qty", 0) or 0),
            })

        #print("items:", items)

        return jsonify({"status": True, "count": len(items), "items": items}), 200

    except Exception as e:
        return jsonify({"status": False, "error": str(e)}), 500
    finally:
        s.close()

