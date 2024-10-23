from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash
from database.tables import User, Material, Bom, Permission, Setting, Session
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


# list all bom
@getTable.route("/getBoms", methods=['POST'])
def get_boms():
  print("getBoms....")

  request_data = request.get_json()
  _order_num = request_data['order_num']
  print("_order_num:", _order_num)
  return_value = True
  s = Session()

  # 查詢 Material，根據 order_num 取得對應的 Material 資料
  material = s.query(Material).filter(Material.order_num == _order_num).first()
  #print("material:", material)
  boms = material._bom  # 透過關聯屬性取得所有 bom
  #print("boms:", boms)

  # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
  results = [
    {
      'id': bom.id,
      'order_num': material.order_num,
      'seq_num': bom.seq_num,           # 項目編號
      'material_num': bom.material_num,     # 物料編號
      'mtl_comment': bom.material_comment,  # 物料說明
      'qty': bom.req_qty,                   # 數量
      'date': material.material_date,       # 日期
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
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'boms': results
  })


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


# list all materials and assemble data by current user
@getTable.route("/getMaterialsAndAssemblesByUser", methods=['POST'])
def get_materials_and_assembles_by_user():
    print("getMaterialsAndAssemblesByUser....")

    request_data = request.get_json()
    print("request_data:", request_data)
    _user_id = request_data['user_id']
    print("user_id:", _user_id)

    s = Session()

    _results = []
    return_value = True
    code_to_name = {
      '106': '雷射',
      '109': '組裝',
      '110': '檢驗'
    }
    code_to_assembleStep = {
      '109': 3,
      '106': 2,
      '110': 1
    }

    #       0         1        2          3        4            5           6            7           8            9
    str2=['未備料', '備料中', '備料完成', '未組裝', '組裝作業中', 'aa/00/00', '雷射作業中', 'aa/bb/00', '檢驗作業中', 'aa/bb/cc',]


    # 使用 with_for_update() 來加鎖
    _objects = s.query(Material).with_for_update().all()

    # 初始化一個暫存字典來存放每個 order_num 下的最大 process_step_code
    max_step_code_per_order = {}

    # 搜尋所有紀錄，找出每個訂單下最大的 process_step_code
    for material_record in _objects:
      for assemble_record in material_record._assemble:
        # 檢查員工編號是否符合
        if assemble_record.user_id != _user_id or assemble_record.total_ask_qty == 0:
          continue  # 如果不符合，跳過這筆紀錄

        code = assemble_record.work_num[1:]                # 取得字串中的代碼 (去掉字串中的第一個字元)
        step_code = code_to_assembleStep.get(code, 0)      # 取得對應的 step code

        order_num = material_record.order_num              # 訂單編號

        # 設定或更新該 order_num 下的最大 step code
        if order_num not in max_step_code_per_order:
            max_step_code_per_order[order_num] = step_code
        else:
            max_step_code_per_order[order_num] = max(max_step_code_per_order[order_num], step_code)

    # 在此期間，_objects 中的資料會被鎖定，其他進程或交易無法修改這些資料, 但自己可以執行你需要的操作，如更新或處理資料
    #_objects = s.query(Material).all()
    for material_record in _objects:
      for assemble_record in material_record._assemble:
        # 檢查員工編號是否符合
        if assemble_record.user_id != _user_id or assemble_record.total_ask_qty == 0:
          continue  # 如果不符合，跳過這筆紀錄

        cleaned_comment = material_record.material_comment.strip()          # 刪除 material_comment 字串前後的空白

        code = assemble_record.work_num[1:]             # 取得字串中的代碼 (去掉字串中的第一個字元)
        name = code_to_name.get(code, '')               # 查找對應的中文名稱
        #step_code = code_to_assembleStep.get(code, 0)   #
        step_code = assemble_record.process_step_code
        order_num = material_record.order_num                       # 訂單編號

        # 比較該筆記錄的 step_code 是否為該訂單下最大的
        max_step_code = max_step_code_per_order.get(order_num, 0)
        step_enable = (step_code == max_step_code)  # 如果是最大值，則啟用
        format_name = f"{assemble_record.work_num}({name})"
        num = int(material_record.show2_ok)

        _object = {
          'order_num': material_record.order_num,                   #訂單編號
          'assemble_work': format_name,                             #工序
          'material_num': material_record.material_num,             #物料編號
          #'assemble_process': str2[num],                            #途程目前狀況 material_record.isTakeOk & step_enable
          'assemble_process': '' if (num > 2 and not step_enable) else str2[num],                            #途程目前狀況 isTakeOk & step_enable
          'assemble_process_num': num,
          'assemble_id': assemble_record.id,
          'req_qty': assemble_record.meinh_qty,                                   #需求數量(作業數量)
          'total_receive_qty': '(' + str(assemble_record.total_good_qty) + ')',   #已完成數量
          'total_receive_qty_num': assemble_record.total_good_qty,                #已完成數量
          'receive_qty': assemble_record.good_qty,                                #完成數量
          'delivery_date': material_record.material_delivery_date,  #交期
          'comment': cleaned_comment,                               #說明
          'isTakeOk' : material_record.isTakeOk,
          'whichStation' : material_record.whichStation,
          'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,       # true:組裝站製程1完成
          'isAssembleStation2TakeOk': material_record.isAssembleStation1TakeOk,       # true:組裝站製程2完成
          'isAssembleStation3TakeOk': material_record.isAssembleStation1TakeOk,       # true:組裝站製程3完成
          'currentStartTime': assemble_record.currentStartTime,
          'tooltipVisible': False,
          'input_disable': False,
          #'process_step_code': step_code,
          'process_step_enable': step_enable,
        }
        #print(_object)
        _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listMaterialsAndAssemblesByUser, 總數: ", temp_len)
    if (temp_len == 0):
      return_value = False

    return jsonify({
        'status': return_value,
        'materials_and_assembles_by_user': _results
    })
