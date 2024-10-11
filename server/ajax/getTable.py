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
  print("_order_num:", _order_num)

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
      'receive_qty': information_details.receive_qty,       # 領取數量
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
