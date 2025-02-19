from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash
from database.tables import User, Material, Bom, Agv, Permission, Setting, Session
from sqlalchemy import and_, or_, not_

from flask_cors import CORS

from operator import itemgetter   # 2023-08-25  add

getTable = Blueprint('getTable', __name__)


# ------------------------------------------------------------------


# list user, department, permission and setting table all data
@getTable.route('/login', methods=['POST'])
def login():
    print("login....")

    request_data = request.get_json()
    userID = (request_data['empID'] or '')
    password = (request_data['password'] or '')

    s = Session()

    _user_object = {}
    user = s.query(User).filter_by(emp_id=userID).first()
    if user and user.isRemoved:
        print("login user: ", user)

        if user.isOnline:
          print("step1...")
          s.close()
          return jsonify({
            'status': False,          # false: 資料錯誤
            'message': '使用者已上線!'
          })

        if not check_password_hash(user.password, password):
          print("step2...")
          s.close()
          return jsonify({
            'status': False,          # false: 資料錯誤
            'message': '密碼錯誤!'
          })

        perm_item = s.query(Permission).filter_by(id=user.perm_id).first()
        setting_item = s.query(Setting).filter_by(id=user.setting_id).first()

        s.query(User).filter(User.emp_id == userID).update({'isOnline': True})   # true: user已經上線
        s.commit()

        _user_object = {
          'empID': user.emp_id,
          'name': user.emp_name,
          'dep': user.dep_name,
          'perm_name': perm_item.auth_name,
          'perm': perm_item.auth_code,
          'password': password,
          'isOnline': user.isOnline,
          'setting_items_per_page': setting_item.items_per_page,
          'setting_isSee': setting_item.isSee,
          'setting_message': setting_item.message,
          'setting_routingPriv': setting_item.routingPriv,
          'setting_lastRoutingName': setting_item.lastRoutingName,
        }
    else:
      print("step3...")
      s.close()
      return jsonify({
        'status': False,                        # false: 資料錯誤
        'message': '錯誤! 找不到工號' + userID
      })

    print("step4...")
    s.close()

    return jsonify({
      'status': True,
      'user': _user_object,
    })

'''
# get material by order_num
@getTable.route("/getMaterial", methods=['POST'])
def get_material():
  print("getMaterial....")

  request_data = request.get_json()
  _order_num = request_data['order_num']
  print("_order_num:", _order_num)
  return_value = False
  s = Session()

  # 查詢 Material，根據 order_num 取得對應的 Material 資料
  material = s.query(Material).filter(Material.order_num == _order_num).first()
  if material and material.isTakeOk:
    return_value = True

  return jsonify({
    'status': return_value
  })
'''

# list all bom
@getTable.route("/getBoms", methods=['POST'])
def get_boms():
  print("getBoms....")

  request_data = request.get_json()
  #_order_num = request_data['order_num']
  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  #print("_order_num:", _order_num)
  return_value = True
  s = Session()


  # 檢查傳入的參數，選擇查詢條件
  material_record = None
  if _order_num is not None:  # 如果傳入了 order_num
    #print("step for order_num")
    material_record = s.query(Material).filter_by(order_num=_order_num).first()
  elif _id is not None:       # 如果傳入了 id
    #print("step for id")
    material_record = s.query(Material).filter_by(id=_id).first()

  #if material_record is None:
  #  return_value = False
  #else:
  boms = material_record._bom


  # 查詢 Material，根據 order_num 取得對應的 Material 資料
  #material = s.query(Material).filter(Material.order_num == _order_num).first()
  #print("material:", material)
  #boms = material._bom  # 透過關聯屬性取得所有 bom
  #print("boms:", boms)

  # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
  results = [
    {
      'id': bom.id,
      'order_num': material_record.order_num,
      'seq_num': bom.seq_num,           # 項目編號
      'material_num': bom.material_num,     # 物料編號
      'mtl_comment': bom.material_comment,  # 物料說明
      'qty': bom.req_qty,                   # 數量
      'date': material_record.material_date,       # 日期
      'date_alarm': '',
      'receive': bom.receive,               #領取
      'lack': bom.lack,                     #缺料
      'isPickOK': bom.isPickOK
    }
    for bom in boms if not bom.isPickOK
  ]

  s.close()

  temp_len = len(results)
  print("getBoms, 總數: ", temp_len)
  #print("getBoms: ", results)
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'boms': results
  })

'''
# list all bom
@getTable.route("/getAbnormalCauses", methods=['POST'])
def get_abnormal_causes():
  print("getAbnormalCauses....")

  request_data = request.get_json()
  #_order_num = request_data['order_num']
  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  #print("_order_num:", _order_num)
  return_value = True
  s = Session()


  # 檢查傳入的參數，選擇查詢條件
  material_record = None
  if _order_num is not None:  # 如果傳入了 order_num
    #print("step for order_num")
    material_record = s.query(Material).filter_by(order_num=_order_num).first()
  elif _id is not None:       # 如果傳入了 id
    #print("step for id")
    material_record = s.query(Material).filter_by(id=_id).first()
  # 下面代處理:
  boms = material_record._bom


  # 查詢 Material，根據 order_num 取得對應的 Material 資料
  #material = s.query(Material).filter(Material.order_num == _order_num).first()
  #print("material:", material)
  #boms = material._bom  # 透過關聯屬性取得所有 bom
  #print("boms:", boms)

  # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
  results = [
    {
      'id': bom.id,
      'order_num': material_record.order_num,
      'seq_num': bom.seq_num,           # 項目編號
      'material_num': bom.material_num,     # 物料編號
      'mtl_comment': bom.material_comment,  # 物料說明
      'qty': bom.req_qty,                   # 數量
      'date': material_record.material_date,       # 日期
      'date_alarm': '',
      'receive': bom.receive,               #領取
      'lack': bom.lack,                     #缺料
      'isPickOK': bom.isPickOK
    }
    for bom in boms if not bom.isPickOK
  ]

  s.close()

  temp_len = len(results)
  print("getBoms, 總數: ", temp_len)
  #print("getBoms: ", results)
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'boms': results
  })
'''

# list detail information by order_num
@getTable.route("/getInformationDetails", methods=['POST'])
def get_information_details():
  print("getInformationDetails....")

  request_data = request.get_json()
  _order_num = request_data['order_num']
  print("order_num:", _order_num)

  code_to_name = {
    '106': '雷射',
    '109': '組裝',
    '110': '檢驗'
  }
  return_value = True
  s = Session()

  # 查詢 Material，根據 order_num 取得對應的 Material 資料
  material = s.query(Material).filter(Material.order_num == _order_num).first()
  #print("material:", material)
  information_details = material._assemble  # 透過關聯屬性取得所有 bom
  #print("information_details:", information_details)

  work_name = code_to_name.get(information_details.work_num, 'Unknown')  # 使用字典的 get() 方法來獲取名稱
  # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
  results = [
    {
      'id': information_details.id,
      'order_num': information_details.order_num,
      'work_name': work_name,                               # 工作中心名稱
      'material_num': information_details.material_num,     # 物料編號
      'mtl_comment': information_details.material_comment,  # 物料說明
      'receive_qty': information_details.ask_qty,       # 領取數量
      'delivery_date': material.material_delivery_date,     # 交期
      'actual_spent_time':  spent,
      'isPickOK': bom.isPickOK
    }
    for bom in boms if bom.good_qty !=0
  ]

  s.close()

  temp_len = len(results)
  print("getInformationDetails, 總數: ", temp_len)
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'information_details': results
  })


# get all assemble error information by history
@getTable.route("/getInformationsForAssembleErrorByHistory", methods=['POST'])
def get_informations_for_assemble_error_by_history():
    print("getInformationsForAssembleErrorByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True
    str1=['備料站', '組裝站', '成品站']
    #       0        1         2         3         4             5          6             7           8             9         10        11           12           13          14          15            16          17
    str2=['未備料', '備料中', '備料完成', '未組裝', '組裝作業中', 'aa/00/00', '雷射作業中', 'aa/bb/00', '檢驗作業中', 'aa/bb/cc', '未入庫', '檢料作業中', 'aa/00/00', '雷刻作業中', 'aa/bb/00', '包裝作業中', 'aa/bb/cc', '完成入庫']
    #      0    1          2(agv_begin)     3(agv_end)   4(開始鍵)     5(結束鍵)     6(開始鍵)    7(結束鍵)     8(開始鍵)    9(結束鍵)     10(agv_begin)     11(agv_end)  12(開始鍵)    13(結束鍵)   14(開始鍵)    15(結束鍵)   16(開始鍵)    17(結束鍵)    18(agv_begin)    19(agv_end)  20(agv_alarm)
    str3=['', '等待agv', 'agv移至組裝區中', '等待組裝中', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫中', '檢料進行中', '檢料已結束', '雷刻進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至備料區中', '等待備料中', 'agv待處理中...']

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for material_record in _objects:
      #print("material id:", material_record.id)
      skip_material = False  # 標誌變數，預設為 False
      user_ids = []  # 用於存儲處理後的 user_id
      #print("step a...", material_record.id)
      assemble_ok = False
      for assemble_record in material_record._assemble:
        if assemble_record.material_id != material_record.id:
          skip_material = True
        if assemble_record.alarm_enable == False:
          continue

        assemble_ok = True
        #print("assemble id:", assemble_record.id)
        user_id = assemble_record.user_id.lstrip('0')  # 去除前導的 0
        #user_ids.append(user_id)  # 將處理後的值加入列表
        # 檢查 user_id 是否已存在於 user_ids 中
        if user_id not in user_ids:
          user_ids.append(user_id)  # 如果不存在，則插入列表

      if skip_material or not assemble_ok:
          continue                # 跳過當前 material_record，進入下一個 _objects 的迴圈

      #print("material id:", material_record.id)

      temp_alarm_message=assemble_record.alarm_message.strip()
      temp_alarm_enable=assemble_record.alarm_enable
      if not _history_flag and temp_alarm_enable and temp_alarm_message:
        continue

      user = ', '.join(user_ids)  # 將列表轉換為以逗號分隔的字符串
      print("user:", user)
      print("material order num:", material_record.order_num)
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
        'assemble_id': assemble_record.id,
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


# list all materials and assemble data by current user
@getTable.route("/getMaterialsAndAssemblesByUser", methods=['POST'])
def get_materials_and_assembles_by_user():
    print("getMaterialsAndAssemblesByUser....")

    request_data = request.get_json()
    print("request_data:", request_data)
    _user_id = request_data['user_id']
    print("user_id:", _user_id)
    #_history = request_data['history']

    s = Session()

    _results = []
    return_value = True
    code_to_name = {'106':'雷射', '109':'組裝', '110':'檢驗'}
    code_to_assembleStep = {
      '109': 3,   #第1, 1,      個製程
      '106': 2,   #第2     1,   個製程
      '110': 1    #第3, 2, 2, 1 個製程
    }

    #       0         1        2          3        4            5           6            7           8            9           10         11            12
    str2=['未備料', '備料中', '備料完成', '未組裝', '組裝作業中', 'aa/00/00', '雷射作業中', 'aa/bb/00', '檢驗作業中', 'aa/bb/cc', '等待入庫', '入庫作業中', '入庫完成']

    # 使用 with_for_update() 來加鎖
    _objects = s.query(Material).with_for_update().all()

    ## 初始化一個 set 來追蹤已處理的 (order_num, format_name)
    # 初始化一個 set 來追蹤已處理的 (order_num_id, format_name)
    processed_records = set()

    ## 初始化一個暫存字典來存放每個 order_num 下的最大 process_step_code
    # 初始化一個暫存字典來存放每個 order_num_id 下的最大 process_step_code
    max_step_code_per_order = {}

    # 搜尋所有紀錄，找出每個訂單下最大的 process_step_code
    for material_record in _objects:
      for assemble_record in material_record._assemble:

        # 檢查員工編號是否符合, 且生產報工的已領取總數是否為0
        if assemble_record.user_id != _user_id or assemble_record.total_ask_qty == 0:
          continue  # 如果不符合，跳過這筆紀錄

        #code = assemble_record.work_num[1:]                  # 取得字串中的代碼 (去掉字串中的第一個字元)
        #step_code = code_to_assembleStep.get(code, 0)        # 取得對應的 step code
        step_code = assemble_record.process_step_code         # 直接使用資料中的 step_code

        #order_num = material_record.order_num               # 訂單編號
        order_num_id = material_record.id                   # 該筆訂單編號的table id

        ## 設定或更新該 order_num_id 下的最大 step code
        #if order_num_id not in max_step_code_per_order:
        #    max_step_code_per_order[order_num_id] = step_code
        #else:
        #    max_step_code_per_order[order_num_id] = max(max_step_code_per_order[order_num_id], step_code)

        #    print(f"Processing material id={order_num_id}, assemble work_num={assemble_record.work_num}, step_code={step_code}")

        # 設定或更新該 order_num_id 下的最大 step code
        if order_num_id not in max_step_code_per_order:
            max_step_code_per_order[order_num_id] = step_code
            print(f"Set initial max step_code for id={order_num_id}: {step_code}")
        else:
            current_max = max_step_code_per_order[order_num_id]
            max_step_code_per_order[order_num_id] = max(current_max, step_code)
            print(f"Updated max step_code for id={order_num_id}: {current_max} -> {max_step_code_per_order[order_num_id]}")

    print("Final max_step_code_per_order:", max_step_code_per_order)

    #流程追蹤與狀態管理：
    #根據工序代碼（如 '106', '109', '110'）判斷當前流程階段，並匹配對應的名稱和步驟。
    #追蹤每個訂單的最大進度階段，確保顯示的資料反映正確的流程狀態。

    index = 0
    for material_record in _objects:
      for assemble_record in material_record._assemble:
        # 檢查員工編號是否符合及生產報工的已領取總數不為0
        if assemble_record.user_id != _user_id or assemble_record.total_ask_qty == 0 or material_record.isAssembleStationShow:
          continue  # 如果不符合，跳過這筆紀錄

        code = assemble_record.work_num[1:]  # 取得字串中的代碼 (去掉字串中的第一個字元)
        name = code_to_name.get(code, '')  # 查找對應的中文名稱
        format_name = f"{assemble_record.work_num}({name})"
        order_num_id = material_record.id  # 該筆訂單編號的table id

        # 如果 (order_num_id, format_name) 組合已經存在，則跳過
        if (order_num_id, format_name) in processed_records:
          continue

        # 比較該筆記錄的 step_code 是否為該訂單下最大的
        max_step_code = max_step_code_per_order.get(order_num_id, 0)
        step_code = assemble_record.process_step_code
        step_enable = (step_code == max_step_code and material_record.whichStation == 2)  # 如果是最大值，則啟用

        num = int(material_record.show2_ok)
        print("bug num:", num)
        cleaned_comment = material_record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

        temp_assemble_process_str = str2[num]
        temp_show2_ok = int(material_record.show2_ok)

        # 處理 show2_ok 的情況
        if temp_show2_ok in [5, 7, 9]:
          for assemble_record in material_record._assemble:
            if assemble_record.total_ask_qty_end in [1, 2, 3]:
              completed_qty = str(assemble_record.completed_qty)  # 將數值轉換為字串
              date_parts = temp_assemble_process_str.split('/')  # 分割 00/00/00 為 ['00', '00', '00']
              date_parts[assemble_record.total_ask_qty_end - 1] = completed_qty  # 替換對應位置
              temp_assemble_process_str = '/'.join(date_parts)  # 合併回字串
          #print("temp_show2_ok, temp_assemble_process_str:", temp_show2_ok, temp_assemble_process_str)

        if temp_show2_ok == 1:
          temp_assemble_process_str = temp_assemble_process_str + material_record.shortage_note

        index += 1

        _object = {
            'index': index,
            'id': material_record.id,
            'order_num': material_record.order_num,
            'assemble_work': format_name,
            'material_num': material_record.material_num,
            'assemble_process': '' if (num > 2 and not step_enable) else temp_assemble_process_str,
            'assemble_process_num': num,
            'assemble_id': assemble_record.id,
            'req_qty': assemble_record.meinh_qty,
            'total_ask_qty': assemble_record.total_ask_qty,
            'total_ask_qty_end': assemble_record.total_ask_qty_end,
            'process_step_code': assemble_record.process_step_code,
            'total_receive_qty_num': assemble_record.total_completed_qty,
            'total_receive_qty': f"({assemble_record.total_completed_qty})",
            'receive_qty': assemble_record.completed_qty,
            'delivery_date': material_record.material_delivery_date,
            'delivery_qty': material_record.delivery_qty,
            'assemble_qty': material_record.assemble_qty,
            'total_assemble_qty': material_record.total_assemble_qty,
            'comment': cleaned_comment,
            'isAssembleAlarm': material_record.isAssembleAlarm,
            'alarm_enable': assemble_record.alarm_enable,
            'whichStation': material_record.whichStation,
            'isTakeOk': material_record.isAssembleStation3TakeOk,
            'isLackMaterial': material_record.isLackMaterial,
            'isShow': assemble_record.isAssembleStationShow,
            'currentStartTime': assemble_record.currentStartTime,
            'tooltipVisible': False,
            'input_disable': assemble_record.input_end_disable,
            'process_step_enable': step_enable,
        }

        processed_records.add((order_num_id, format_name))
        _results.append(_object)
        print("getMaterialsAndAssemblesByUser, _object:", _object)

    s.close()

    temp_len = len(_results)
    print("getMaterialsAndAssemblesByUser, 總數: ", temp_len)
    if (temp_len == 0):
      return_value = False

    return jsonify({
      'status': return_value,
      'materials_and_assembles_by_user': _results
    })


# get agv status by id
@getTable.route("/getAGV", methods=['POST'])
def get_agv():
  print("getAGV....")

  request_data = request.get_json()
  #_id = request_data['id']
  _id = request_data.get('agv_id')
  #print("request_data", request_data, _id)
  s = Session()

  myAgv = s.query(Agv).filter(Agv.id == _id).first()
  #print("myAgv", myAgv, myAgv.station)
  _object = {
    #'id': myAgv.id,
    'status': myAgv.status,
    'station': myAgv.station
  }

  s.close()

  return jsonify({
    'agv_data': _object
  })
