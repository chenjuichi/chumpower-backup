import math
import random
import re
from datetime import datetime, date
#from sqlalchemy import distinct, func, and_, not_
from sqlalchemy import distinct, func, case
from flask import Blueprint, jsonify, request, current_app
#from sqlalchemy.sql import func
from database.tables import User, Material, Bom, Permission, AbnormalCause, Product, Setting, Session

from flask_cors import CORS

from operator import itemgetter

from dotenv import dotenv_values

import pymysql
from sqlalchemy import exc

listTable = Blueprint('listTable', __name__)


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
@listTable.route("/listMaterials", methods=['GET'])
def list_materials():
    print("listMaterials....")

    s = Session()

    _results = []
    return_value = True

    _objects = s.query(Material).all()
    materials = [u.__dict__ for u in _objects]
    processed_order_nums = set()  # 用於追踪已處理過的 order_num
    for record in materials:
      #if not record['isTakeOk']:   # 檢查 isTakeOk 是否為 False
      #if not record['isShow'] and record['isLackMaterial'] != 0 and record['isBatchFeeding'] != 0:   # 檢查 isShow 是否為 False
      if not record['isShow']:   # 檢查 isShow 是否為 False
        cleaned_comment = record['material_comment'].strip()  # 刪除 material_comment 字串前後的空白
        #temp_data = record['order_num']  # 訂單編號
        temp_data = record['id']          # 該筆訂單編號的table id
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

        _object = {
          'id': record['id'],
          'order_num': record['order_num'],                   #訂單編號
          'material_num': record['material_num'],   #物料編號
          'req_qty': material_qty,                  #需求數量(訂單數量)
          'delivery_qty': delivery_qty,             #備料數量
          'total_delivery_qty': temp_delivery,      #應備數量
          'input_disable': record['input_disable'],
          'date': record['material_date'],                    #(建立日期)
          'delivery_date':record['material_delivery_date'],   #交期
          'shortage_note': record['shortage_note'],           #缺料註記 '元件缺料'
          'comment': cleaned_comment,                         #說明
          'isTakeOk' : record['isTakeOk'],
          'isLackMaterial' : record['isLackMaterial'],
          'isBatchFeeding' :  record['isBatchFeeding'],
          'isShow' : record['isShow'],
          'whichStation' : record['whichStation'],
          'show1_ok' : record['show1_ok'],
          'show2_ok' : record['show2_ok'],
          'show3_ok' : record['show3_ok'],
        }

        _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listMaterials, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 isTakeOk 屬性的值進行排序
    _results = sorted(_results, key=lambda x: not x['isTakeOk'])

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


    # 1️⃣ 計算不同 order_num 的數量
    order_count = s.query(func.count(distinct(Material.order_num))) \
        .filter(func.date(Material.create_at) == today) \
        .scalar()


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
    print("listWaitForAssemble....")

    s = Session()

    begin_count = 0
    end_count = 0
    allOk_count = 0

    _objects = s.query(Material).with_for_update().all()
    for material_record in _objects:
      #record['delivery_qty'] != 0
      #record['isShow']
      #record['isShow']
      if material_record.delivery_qty == 0 or not material_record.isShow or material_record.isAssembleStationShow :   # 檢查 isShow 是否為 False
        continue
      nums = set()
      for end_record in material_record._assemble:
        if end_record.input_disable and not end_record.input_end_disable:
          end_count += 1
          nums.add(end_record.material_num)
          break

      for begin_record in material_record._assemble:
        if begin_record.material_num in nums:
          break
        if begin_record.process_step_code!=0 and not begin_record.input_disable:
          #print("begin_record id:",begin_record.id)
          begin_count += 1
          break

    s.close()

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

    # 過濾掉 isAssembleStationShow 為 True 的資料
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
    return_value = True
    code_to_name = {
      '106': '雷射',  #第2個動作
      '109': '組裝',  #第1個動作
      '110': '檢驗'   #第3個動作
    }
    code_to_assembleStep = {    #組裝區工作順序, 3:最優先
      '109': 3,
      '106': 2,
      '110': 1
    }

    #       0         1        2          3             4            5            6            7            8             9           10              11           12
    str2=['未備料', '備料中', '備料完成', '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業', '入庫進行中', '入庫完成']

    # 使用 with_for_update() 來加鎖
    _objects = s.query(Material).with_for_update().all()

    # 初始化一個暫存字典來存放每個 order_num 下的最大 process_step_code
    max_step_code_per_order = {}
    '''
    # 搜尋所有紀錄，找出每個訂單下最大的 process_step_code
    for material_record in _objects:
      for assemble_record in material_record._assemble:
        #code = assemble_record.work_num[1:]                # 取得字串中的代碼 (去掉字串中的第一個字元)
        code = assemble_record.process_step_code
        step_code = code_to_assembleStep.get(code, 0)      # 取得對應的 step code, 以設定工作順序

        #order_num = material_record.order_num              # 訂單編號
        order_num_id = material_record.id                  # 該筆訂單編號的table id

        ## 設定或更新該 order_num 下的最大 step code
        #if order_num not in max_step_code_per_order:
        #    max_step_code_per_order[order_num] = step_code
        #else:
        #    max_step_code_per_order[order_num] = max(max_step_code_per_order[order_num], step_code)

        # 設定或更新該 order_num_id 下的最大 step code
        if order_num_id not in max_step_code_per_order:
            max_step_code_per_order[order_num_id] = step_code
        else:
            max_step_code_per_order[order_num_id] = max(max_step_code_per_order[order_num_id], step_code)
    '''
    # 搜尋所有紀錄，找出每個訂單下最大的 process_step_code
    for material_record in _objects:
      for assemble_record in material_record._assemble:
        #code = assemble_record.work_num[1:]  # 取得字串中的代碼 (去掉字串中的第一個字元)
        step_code = assemble_record.process_step_code  # 直接使用資料中的 step_code

        order_num_id = material_record.id  # 該筆訂單編號的table id

        print(f"Processing material id={order_num_id}, assemble work_num={assemble_record.work_num}, step_code={step_code}")

        # 設定或更新該 order_num_id 下的最大 step code
        if order_num_id not in max_step_code_per_order:
          max_step_code_per_order[order_num_id] = step_code
          print(f"Set initial max step_code for id={order_num_id}: {step_code}")
        else:
          current_max = max_step_code_per_order[order_num_id]
          max_step_code_per_order[order_num_id] = max(current_max, step_code)
          print(f"Updated max step_code for id={order_num_id}: {current_max} -> {max_step_code_per_order[order_num_id]}")

    print("Final max_step_code_per_order:", max_step_code_per_order)

    # 在此期間，_objects 中的資料會被鎖定，其他進程或交易無法修改這些資料, 但自己可以執行你需要的操作，如更新或處理資料
    #_objects = s.query(Material).all()
    print("start:")
    for material_record in _objects:
      if material_record.isAssembleStationShow:
      #if not material_record.isShow or material_record.isAssembleStationShow:
        continue
      num = int(material_record.show2_ok)
      temp_temp_show2_ok_str = str2[num]
      assemble_records = material_record._assemble   # 存取與該 Material 物件關聯的所有 Assemble 物件
      # 處理 show2_ok 的情況
      if num == 5 or num == 7 or num == 9:
        for assemble_record in assemble_records:
          # 如果 `total_ask_qty_end` 為 1, 2 或 3，替換 `00/00/00` 的相應部分
          if assemble_record.total_ask_qty_end in [1, 2, 3]:
            completed_qty = str(assemble_record.completed_qty)  # 將數值轉換為字串
            date_parts = temp_temp_show2_ok_str.split('/')  # 分割 `00/00/00` 為 ['00', '00', '00']
            date_parts[assemble_record.total_ask_qty_end - 1] = completed_qty  # 替換對應位置
            temp_temp_show2_ok_str = '/'.join(date_parts)  # 合併回字串
        #print("temp_show2_ok, temp_temp_show2_ok_str:", temp_show2_ok, temp_temp_show2_ok_str)

      for assemble_record in material_record._assemble:

        cleaned_comment = material_record.material_comment.strip()    # 刪除 material_comment 字串前後的空白

        code = assemble_record.work_num[1:]                           # 取得字串中的代碼 (去掉字串中的第一個字元)
        name = code_to_name.get(code, '')                             # 查找對應的中文名稱
        #step_code = code_to_a
        step_code = assemble_record.process_step_code
        print("assemble_record.process_step_code:", assemble_record.process_step_code)
        #order_num = material_record.order_num                        # 訂單編號
        order_num_id = material_record.id                             # 該筆訂單編號的table id

        # 比較該筆記錄的 step_code 是否為該訂單中最先作動的工作中心工作順序編號
        #max_step_code = max_step_code_per_order.get(order_num, 0)
        max_step_code = max_step_code_per_order.get(order_num_id, 0)
        step_enable = (step_code == max_step_code and material_record.whichStation==2)
        #print("material_record.whichStation:",material_record.whichStation)                  # 如果是最大值，則啟用
        #print("max_step_code_per_order:",max_step_code_per_order)
        #print("step_code , max_step_code:", step_code , max_step_code, step_enable)

        format_name = f"{assemble_record.work_num}({name})"
        #num = int(material_record.show2_ok)

        _object = {
          'id': material_record.id,                                 #訂單編號的table id
          'order_num': material_record.order_num,                   #訂單編號
          'assemble_work': format_name,                             #工序
          'material_num': material_record.material_num,             #物料編號(成品)
          #'assemble_process': str2[num],                           #途程目前狀況 material_record.isTakeOk & step_enable
          #'assemble_process': '' if (num > 2 and not step_enable) else str2[num],                            #途程目前狀況 isTakeOk & step_enable
          'assemble_process': '' if (num > 2 and not step_enable) else temp_temp_show2_ok_str,                            #途程目前狀況 isTakeOk & step_enable
          'assemble_process_num': num,
          'assemble_id': assemble_record.id,
          #'req_qty': assemble_record.meinh_qty,                                #需求數量(作業數量)
          #'req_qty': assemble_record.good_qty,                                  # 需求數量(作業數量)
          'req_qty': material_record.material_qty,                                  # 需求數量(作業數量)

          'delivery_qty': material_record.delivery_qty,                         # 備料數量(現況數量)
          'total_receive_qty': f"({assemble_record.total_ask_qty})",            # 已完成總數量
          'total_receive_qty_num': assemble_record.total_ask_qty,               #領取總數量
          'receive_qty': assemble_record.ask_qty,                               #領取數輛
          'delivery_date': material_record.material_delivery_date,  #交期
          'comment': cleaned_comment,                               #說明
          'isTakeOk' : material_record.isTakeOk,
          'whichStation' : material_record.whichStation,
          'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,       # true:組裝站製程1完成
          'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,       # true:組裝站製程2完成
          'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,       # true:組裝站製程3完成
          'currentStartTime': assemble_record.currentStartTime,
          'tooltipVisible': False,
          'input_disable': assemble_record.input_disable,
          #'process_step_code': step_code,
          'process_step_enable': step_enable,
        }
        #print(_object)
        _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listMaterialsAndAssembles, 總數: ", temp_len)
    if (temp_len == 0):
      return_value = False

    return jsonify({
        'status': return_value,
        'materials_and_assembles': _results
    })


# list all materials for information list
@listTable.route("/listInformations", methods=['GET'])
def list_informations():
    print("listInformation....")

    s = Session()

    _results = []
    return_value = True
    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                 3              4            5           6             7            8             9          10                  11            12           13          14          15            16          17
    #str2=['未備料', '備料中', '備料完成',       '未組裝',      '組裝作業中', '00/00/00',  '雷射作業中', '00/00/00',  '檢驗作業中',  '00/00/00', '未入庫',           '檢料作業中',  'aa/00/00',  '雷刻作業中', 'aa/bb/00', '包裝作業中', 'aa/bb/cc', '完成入庫']
    #str2=['未備料', '備料中', '備料完成',       '未組裝',      '組裝作業中', '00/00/00',  '雷射作業中', '00/00/00',  '檢驗作業中',  '00/00/00', '未入庫',           '入庫作業中',  '00',        '入庫完成']
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)     16(agv_start)
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業', 'agv Start']

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for record in _objects:
      assemble_records = record._assemble   # 存取與該 Material 物件關聯的所有 Assemble 物件
      #print("record:", record)
      cleaned_comment = record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

      temp_temp_show2_ok_str = str2[int(record.show2_ok)]
      temp_show2_ok = int(record.show2_ok)

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
        temp_temp_show2_ok_str = temp_temp_show2_ok_str + record.shortage_note

      temp_temp_show2_ok_str = re.sub(r'\b00\b', 'na', temp_temp_show2_ok_str)

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
    #       0        1         2         3         4             5          6             7           8             9         10        11           12           13          14          15            16          17
    #str2=['未備料', '備料中', '備料完成', '未組裝', '組裝作業中', 'aa/00/00', '雷射作業中', 'aa/bb/00', '檢驗作業中', 'aa/bb/cc', '未入庫', '檢料作業中', 'aa/00/00', '雷刻作業中', 'aa/bb/00', '包裝作業中', 'aa/bb/cc', '完成入庫']
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0    1          2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)    7(結束鍵)     8(開始鍵)    9(結束鍵)     10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(開始鍵)        15(結束鍵)   16(開始鍵)    17(結束鍵)    18(agv_begin)    19(agv_end)  20(agv_alarm)
    str3=['',  '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業', 'agv Start']
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
    #str2=['未備料', '備料中', '備料完成',       '未組裝',       '組裝作業中', 'aa/00/00', '雷射作業中', 'aa/bb/00',   '檢驗作業中', 'aa/bb/cc',  '未入庫',           '檢料作業中',  'aa/00/00', '雷刻作業中', 'aa/bb/00', '包裝作業中', 'aa/bb/cc', '完成入庫']
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00',  '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)     16(avg_start)
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業', 'agv Start']

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