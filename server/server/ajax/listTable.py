import math
import random
import re
from datetime import datetime, date, timedelta

from datetime import datetime as dt

from sqlalchemy import distinct, func, case, select
from flask import Blueprint, jsonify, request, current_app

from database.tables import User, UserDelegate, Material, Bom, Assemble, Permission, AbnormalCause, Process, Product, Setting, Session
from database.p_tables import P_Material, P_Assemble,  P_AbnormalCause, P_Process, P_Product

from dotenv import dotenv_values

from collections import defaultdict

from sqlalchemy import func, or_

listTable = Blueprint('listTable', __name__)
#
#from log_util import setup_logger
#logger = setup_logger(__name__)  # 每個模組用自己的名稱
#

# ------------------------------------------------------------------


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


'''
# list all bom
@listTable.route("/listBoms", methods=['GET'])
def list_boms():
    print("listBoms....")

    request_data = request.get_json()
    _order_num = request_data['order_num']
    print("_order_num:", _order_num)
    return_value = True
    s = Session()

    # 查詢 Material，根據 order_num 取得對應的 Material 資料
    material = s.query(Material).filter(Material.order_num == _order_num).first()
    print("material:", material)
    boms = material._bom  # 透過關聯屬性取得所有 bom
    print("boms:", bom)

    # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
    result = [
      {
        'seq_num': bom.seq_num,           # 項目編號
        'material_num': bom.material_num,     # 物料編號
        'mtl_comment': bom.material_comment,  # 物料說明
        'qty': bom.req_qty,                   # 數量
        'date': material.material_date,       # 日期
        'date_alarm': '',
        'receive': True,                      #領取
        'lack': False                         #缺料
      }
      for bom in boms if not bom.isPickOK
    ]

    s.close()

    temp_len = len(results)
    print("listBoms, 總數: ", temp_len)
    if (temp_len == 0):
      return_value = False

    return jsonify({
      'status': return_value,
      'boms': results
    })
'''


# list all materials
@listTable.route("/listMaterialsP", methods=['GET'])
def list_materials_p():
    print("listMaterialsP....")

    s = Session()

    _results = []
    return_value = True

    _objects = s.query(P_Material).filter(P_Material.move_by_process_type == 4).all()
    materials = [u.__dict__ for u in _objects]
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
          'isBom' : record['isBom'],
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


# list all materials
@listTable.route("/listMaterials", methods=['GET'])
def list_materials():
    print("listMaterials....")

    _results = []
    return_value = True

    s = Session()
    try:
      with s.begin():
        #_objects = s.query(Material).all()
        _objects = s.query(Material).filter(Material.move_by_process_type == 2).all()
        materials = [u.__dict__ for u in _objects]
        processed_order_nums = set()  # 用於追踪已處理過的 order_num
        for record in materials:
          #if not record['isTakeOk']:   # 檢查 isTakeOk 是否為 False
          #if not record['isShow'] and record['isLackMaterial'] != 0 and record['isBatchFeeding'] != 0:   # 檢查 isShow 是否為 False
          if not record['isShow']:   # 檢查 isShow 是否為 False
            cleaned_comment = record['material_comment'].strip()  # 刪除 material_comment 字串前後的空白
            #temp_data = record['order_num']             # 訂單編號
            temp_data = record['id']                    # 該筆訂單編號的table id
            if temp_data in processed_order_nums:       # 如果這個 order_num 已經處理過，跳過本次處理
              continue
            # 計算 temp_delivery 的值
            #order_num = record['order_num']
            #order_num = temp_data
            order_num_id = temp_data
            material_qty = record['material_qty']
            delivery_qty = record['delivery_qty']
            '''
            # 找出所有具有相同 order_num 的資料
            same_order_records = [r for r in materials if r['order_num'] == order_num]

            if all(r['delivery_qty'] == 0 for r in same_order_records):  # 若所有相同 order_num 的 delivery_qty 都為 0
              temp_delivery = material_qty
            else:  # 若有相同 order_num 的資料且 delivery_qty 都不為 0
              total_delivery_qty_sum = sum(r['total_delivery_qty'] for r in same_order_records)
              #temp_delivery = material_qty - total_delivery_qty_sum
              #if temp_delivery == 0:
              #  temp_delivery = total_delivery_qty_sum
              temp_delivery = total_delivery_qty_sum if material_qty - total_delivery_qty_sum == 0 else material_qty - total_delivery_qty_sum
            '''
            temp_delivery=record['total_delivery_qty']

            # 標記這個 order_num 已處理過
            #processed_order_nums.add(order_num)
            processed_order_nums.add(order_num_id)
            #print("record['Incoming0_Abnormal']:", record['order_num'], record['Incoming0_Abnormal'], record['Incoming0_Abnormal'] == '')
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
              'is_copied': bool(record['is_copied_from_id'] and record['is_copied_from_id'] > 0),
            }

            #print("materials => i, isOpen:", record['id'], record['order_num'], record['isOpen'])

            _results.append(_object)

    except Exception:
        #s.rollback()
        current_app.logger.exception("list_wait_for_assemble failed")
        return jsonify(success=False), 500
    #finally:
    #    # 若在 app.py 有 @app.teardown_appcontext -> Session.remove()，這裡可省略
    #    Session.remove()
    ##s.close()

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
          select(step_31_material_ids_subq)
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


# list all materials and assemble data
@listTable.route("/listMaterialsAndAssembles", methods=['GET'])
def list_materials_and_assembles():
    print("listMaterialsAndAssembles....")
    s = Session()
    _results = []
    _assemble_active_users = []
    return_value = True

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
        test_index = 0
        pre_p_id=0
        for material_record in _objects:
            if not material_record.isShow:
                continue

            process_records = material_record._process
            total_records =len([p for p in process_records if ((p.material_id == material_record.id and p.assemble_id != 0))])

            assemble_records = material_record._assemble

            # 先算出：在同一個 material_id 裡，每個 update_time 的 max_step_code
            max_by_ut = {}  # { update_time -> max_step_code }
            for a in assemble_records:
                step = int(a.process_step_code or 0)
                if step == 0:
                    continue
                ut = a.update_time
                #if ut is None:
                #    continue  # 若你想把 NULL 當成一組可改成保留
                cur = max_by_ut.get(ut)
                if cur is None or step > cur:
                  max_by_ut[ut] = step

            for assemble_record in material_record._assemble:
                if assemble_record.must_receive_qty <= 0:
                   continue

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
                total_work_qty = 0  # 累加 process_work_time_qty
                show_timer = False      # 是否顯示計時器
                show_name = ''          # 要顯示的 user_id
                if target_pt is not None:
                  # 這裡一定要是 list，不是數字！
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
                  print("matched_count:",matched_count)
                  total_work_qty = sum((p.process_work_time_qty or 0) for p in target_procs)

                  # 從 target_procs 中，再篩同一個 assemble_id 的紀錄
                  # 只要有任一筆 begin_time 有值：
                  #   show_timer = True
                  #   show_name  = 該筆的 p.user_id

                  print("1.##hello:pre_p_id", pre_p_id)
                  """
                  for p in target_procs:
                    print("2.##hello:pre_p_id, p.id", pre_p_id, p.id)
                    if pre_p_id != p.id and p.assemble_id == assemble_record.id and bool(p.begin_time and str(p.begin_time).strip()):
                      pre_p_id=p.id
                      show_timer = True
                      show_name = p.user_id or ''
                      print("3.##hello:p.id", p.id, show_name)
                      break
                  """
                  if target_procs:
                    latest_p = max(target_procs, key=lambda x: x.id)  # 或 key=lambda x: x.begin_time
                    show_timer = True
                    show_name = latest_p.user_id or ''
                    print("### latest process.id:", latest_p.id, "user:", show_name)




                # a_statement: step != 0 且有對應 process，且已報工數量 >= 交期數量
                a_statement = (
                    step != 0
                    and total_records != 0
                    and matched_count > 0
                    and total_work_qty >= (material_record.delivery_qty or 0)
                )
                print("$$$ step, matched_count:", step, a_statement, assemble_record.id)
                # 1) 已結束 step（process_step_code = 0）不顯示
                # 2) 報工數量已經 >= 交期數量的不顯示
                #if step == 0 or (step != 0 and matched_count == 0 and total_records != 0) or a_statement:
                #if step == 0 or assemble_record.user_id:
                if step == 0 and not a_statement:
                  continue

                print("2. $$$ step, matched_count:", step, a_statement, assemble_record.id)

                # ---- 安全取值區 ----
                cleaned_comment = safe_str(material_record.material_comment).strip()
                work_num = safe_str(assemble_record.work_num)     # 可能為 ''（避免 None）
                code = work_num[1:] if len(work_num) >= 2 else work_num
                name = code_to_name.get(code, '')
                pt =code_to_pt.get(code, 0)

                ok, process_total = need_more_process_qty(k1=assemble_record.material_id, a1=assemble_record.id, t1=pt, must_qty=assemble_record.must_receive_end_qty, s=s)

                # 找出該組(max) → 「同 material_id 且同 update_time」
                ut = assemble_record.update_time
                max_step_code = max_by_ut.get(ut)
                if max_step_code is None:
                    continue

                if step != max_step_code:
                    continue

                print("max_step_code:", max_step_code, assemble_record.id, assemble_record.material_id)

                # 缺料併單排除
                if material_record.isLackMaterial == 0 and material_record.is_copied_from_id and material_record.is_copied_from_id > 0:
                  continue

                num = int(getattr(assemble_record, 'show2_ok', 0) or 0)
                base = str2[num] if 0 <= num < len(str2) else '00/00/00'
                ##print("**********id, num, show2_ok:", assemble_record.id, num, assemble_record.show2_ok, base, len(str2))
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
                    #'assemble_process': '' if (num > 2 and not (step_enable or sub_process_step_enable)) else temp_temp_show2_ok_str,
                    'assemble_process': '' if num > 2 else temp_temp_show2_ok_str,

                    'assemble_process_num': num,
                    'assemble_id': assemble_record.id,
                    'req_qty': material_record.material_qty,

                    'delivery_qty': material_record.delivery_qty,
                    'total_receive_qty': f"({getattr(assemble_record, 'total_ask_qty', 0)})",
                    'total_receive_qty_num': getattr(assemble_record, 'total_ask_qty', 0),
                    #'total_receive_qty_num': process_total,

                    'must_receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'must_receive_end_qty': getattr(assemble_record, 'must_receive_qty', 0),

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
                    #'process_step_enable': bool(step_enable or sub_process_step_enable),
                    'process_step_code': max_step_code,
                    #'completed_qty': str(assemble_record.completed_qty),

                    'isLackMaterial': material_record.isLackMaterial,
                    'Incoming1_Abnormal': getattr(assemble_record, 'Incoming1_Abnormal', '') == '',
                    'is_copied_from_id': getattr(assemble_record, 'is_copied_from_id', None),
                    'create_at': assemble_record.create_at,
                    'show_timer': show_timer,
                    'show_name': show_name,

                }
                _results.append(_object)

        print("kkkkaaa _results length:", len(_results))
        # 只有在前面的 _results 成功建好後，才去算使用中人數
        #from sqlalchemy import or_ as _or
        counts_by_type = active_count_map_by_material_multi(
            s,
            material_ids=material_ids_all,
            process_types=(21, 22, 23),
            include_paused=False
        )

        ###
        def _contains_code(s: str, code: str) -> bool:
            # 嚴謹判斷，避免 '1109' 被當成 '109'
            return re.search(rf'(?<!\d){re.escape(code)}(?!\d)', str(s or "")) is not None

        def _to_qty_str(v):
            if v is None: return "0"
            try:
                if isinstance(v, float) and v.is_integer():
                    return str(int(v))
                return str(v)
            except Exception:
                return str(v)

        def _to_int_or_none(x):
            try:
                return int(x)
            except Exception:
                return None

        # ① 預取：k=row.assemble_id 的「前一筆 h=k-1 是否存在且 step==0」
        def prepare_prev_step0_flags(session, rows):
            ks = set()
            for r in rows:
                k = _to_int_or_none(r.get('assemble_id'))
                if k is not None:
                    ks.add(k)
            prev_ids = {k - 1 for k in ks if k and k > 0}
            if not prev_ids:
                return {}

            recs = (session.query(Assemble.id, Assemble.process_step_code)
                          .filter(Assemble.id.in_(prev_ids))
                          .all())
            id_to_step = {aid: step for aid, step in recs}
            # 回傳：k -> (ok, h)
            return {k: ((id_to_step.get(k - 1) == 0), (k - 1)) for k in ks}

        # ② 預取：(assemble_id=h, material_id=mid) → 最新 qty
        def prepare_latest_qty_by_pair_h_mid(session, rows, prev_ok_map):
            pairs = set()
            for r in rows:
                k = _to_int_or_none(r.get('assemble_id'))
                mid = _to_int_or_none(r.get('id'))
                num = _to_int_or_none(r.get('work_num'))
                if k is None or mid is None:
                    continue
                ok, h = prev_ok_map.get(k, (False, None))
                if not ok or h is None:
                    continue
                pairs.add((h, mid))

            if not pairs:
                return {}

            hs  = {h for h, _ in pairs}
            mids = {mid for _, mid in pairs}
            nums = {num for _, num in pairs}

            q = (session.query(
                    Process.assemble_id,         # h
                    Process.material_id,         # mid
                    Process.process_work_time_qty,
                    Process.end_time,
                    Process.id
                )
                .filter(Process.assemble_id.in_(hs),
                        Process.material_id.in_(mids))
            )

            buckets = defaultdict(list)
            for a_id, m_id, qty, end_time, pid in q:
                buckets[(a_id, m_id)].append((end_time, pid, qty))

            latest_qty = {}
            for key, items in buckets.items():
                ended = [it for it in items if it[0] is not None]
                if ended:
                    ended.sort(key=lambda t: (t[0], t[1]), reverse=True)   # end_time DESC, id DESC
                    latest_qty[key] = _to_qty_str(ended[0][2])
                else:
                    items.sort(key=lambda t: t[1], reverse=True)           # id DESC
                    latest_qty[key] = _to_qty_str(items[0][2])
            return latest_qty

        # ③ 主修補：符合條件時，把 aa/bb/cc 改為 (h, mid) 的最新 qty
        def patch_assemble_process_from_h_mid(session, rows):
            prev_ok_map = prepare_prev_step0_flags(session, rows)
            qty_map     = prepare_latest_qty_by_pair_h_mid(session, rows, prev_ok_map)
            print("prev_ok_map:",prev_ok_map)
            print("qty_map:",qty_map)
            for row in rows:
                k   = _to_int_or_none(row.get('assemble_id'))  # k = m = row.assemble_id
                mid = _to_int_or_none(row.get('id'))           # mid = row.id
                if k is None or mid is None:
                    continue

                ok, h = prev_ok_map.get(k, (False, None))
                if not ok or h is None:
                    continue  # h=k-1 不存在或 step!=0 → 不處理

                num = row.get('assemble_work') or ""               # num = assemble.work_num
                ap  = row.get('assemble_process') or ""
                print("k, mid:", k, mid)
                print("ok, h:", ok, h)

                print("ap:", ap)
                parts = ap.split('/') if ap else []
                print("parts:",parts)
                while len(parts) < 3:
                    parts.append('0')

                pair_qty = qty_map.get((k-1, mid), "0")        # (assemble_id=h, material_id=mid)
                print("pair_qty:",pair_qty)
                print("num:",num)
                # 109 → aa(0), 110 → bb(1), 106 → cc(2)
                if _contains_code(num, '109'):
                    parts[2] = pair_qty
                    print("parts[0]:", parts[0])
                if _contains_code(num, '110'):
                    parts[0] = pair_qty
                    print("parts[1]:", parts[1])
                if _contains_code(num, '106'):
                    parts[1] = pair_qty
                    print("parts[2]:", parts[2])

                row['assemble_process'] = '/'.join(parts[:3])
                print("row['assemble_process'] :", row['assemble_process'])

        ###

        #print("_results:",_results)
        # 先依「h = k-1 為 step==0」條件回填 assemble_process
        patch_assemble_process_from_h_mid(s, _results)

        # 安全讀值的 map_pt / get_val 已在檔案上方定義
        for row in _results:
            try:
                pt = str(map_pt(row))                  # '21'/'22'/'23'
                mid = str(get_val(row, 'id'))         # material_id
                temp_count = counts_by_type.get(pt, {}).get(mid, 0)
                row['active_user_count'] = temp_count
                _assemble_active_users.append(temp_count)

            except Exception as e:
                print("listMaterialsAndAssembles: skip bad row =>", e, row)
                continue

        """
        # 1) 找出需剔除的 material_id 清單
        mids_to_remove = {
            mid for (mid,) in (
                s.query(Process.material_id)
                .filter(Process.normal_work_time == 3)
                .filter(Process.end_time.isnot(None))
                .filter(Process.end_time != '')
                .distinct()
                .all()
            )
        }

        if mids_to_remove:
            mids_to_remove_str = {str(m) for m in mids_to_remove}

            # 2) _results 與 _assemble_active_users 一起過濾，保持索引一致
            _results_kept = []
            _counts_kept  = []
            for i, row in enumerate(_results):
                rid = str(row.get('id'))
                if rid not in mids_to_remove_str:
                    _results_kept.append(row)
                    # 這裡假設 _assemble_active_users 與 _results 先前是一一對應 append 的
                    if i < len(_assemble_active_users):
                        _counts_kept.append(_assemble_active_users[i])

            _results = _results_kept
            _assemble_active_users = _counts_kept
        """
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
        print("listMaterialsAndAssembles ERROR:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("listMaterialsAndAssembles failed")
        except Exception:
            pass
        s.close()
        return jsonify({
            'status': False,
            'materials_and_assembles': [],
            'assemble_active_users': [],
        }), 200


# list all materials for information list
@listTable.route("/listInformations", methods=['GET'])
def list_informations():
    print("listInformation....")

    s = Session()

    _results = []
    return_value = True
    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                 3              4            5           6             7            8             9          10                  11            12           13          14          15            16           17            18
    #str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '檢驗進行中', '00/00/00',  '雷射進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)     16(agv_start)   17
    #str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業', 'agv Start']
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '檢驗進行中', '檢驗已結束', '雷射進行中', '雷射已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業', 'agv Start',     '推車送料至組裝區中',]

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for record in _objects:
      assemble_records = record._assemble   # 存取與該 Material 物件關聯的所有 Assemble 物件
      #print("record:", record)
      cleaned_comment = record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

      temp_show2_ok = int(record.show2_ok)
      #temp_temp_show2_ok_str = str2[int(record.show2_ok)]
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
        'delivery_qty':record.delivery_qty,             #現況數量
        'comment': cleaned_comment,                     #說明
        'show1_ok' : str1[int(record.show1_ok) - 1],    #現況進度
        'show2_ok' : temp_temp_show2_ok_str,            #現況進度(途程)
        'show3_ok' : str3[int(record.show3_ok)],        #現況備註
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
        'informations': _results
    })


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