import time
import datetime
import pytz

from flask import Blueprint, jsonify, request
import pymysql
from sqlalchemy import exc
from sqlalchemy import func
from sqlalchemy import distinct

from database.tables import User, Permission, Setting, Bom, Material, Assemble, Agv, Session

from werkzeug.security import generate_password_hash

from operator import itemgetter, attrgetter   # 2023-08-27  add

updateTable = Blueprint('updateTable', __name__)


# ------------------------------------------------------------------


# update user's password from user table
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


# update user's setting from user table some data
@updateTable.route("/updateSetting", methods=['POST'])
def update_setting():
    print("updateSetting....")

    request_data = request.get_json()
    #print("request_data:", request_data)

    userID = request_data['empID']
    new_isSee = request_data['seeIsOk']
    new_lastRoutingName = request_data['lastRoutingName']
    new_itemsPerPage = request_data['itemsPerPage']

    s = Session()
    # 修改user的設定資料
    _user = s.query(User).filter_by(emp_id = userID).first()
    if new_itemsPerPage != 0:
      s.query(Setting).filter(Setting.id == _user.setting_id).update(
        { 'items_per_page': new_itemsPerPage, 'lastRoutingName': new_lastRoutingName, 'isSee': new_isSee }
      )
    else:
      s.query(Setting).filter(Setting.id == _user.setting_id).update(
        { 'lastRoutingName': new_lastRoutingName, 'isSee': new_isSee }
      )

    s.query(User).filter(User.emp_id == userID).update({'isOnline': False})  # false:user已經登出(logout)

    s.commit()
    s.close()

    return jsonify({
      'status': True,
    })


# from user table update some data by id
@updateTable.route("/updateUser", methods=['POST'])
def update_user():
    print("updateUser....")

    request_data = request.get_json()
    #print("request_data", request_data)
    _emp_id = request_data['emp_id']
    _emp_name = request_data['emp_name']
    _dep_name = request_data['dep_name']
    _emp_perm = request_data['emp_perm']
    _routingPriv = request_data['routingPriv']
    _password_reset = request_data['password_reset']
    newPassword = 'a12345678'

    return_value = True  # true: 資料正確, 註冊成功
    if _emp_id == "" or _emp_name == "":
        return_value = False  # false: 資料不完全 註冊失敗

    s = Session()
    user = s.query(User).filter_by(emp_id=_emp_id).first()
    if user and user.isRemoved:
      _auth_name = 'member' if _emp_perm == 4 else ('staff' if _emp_perm == 3 else ('admin' if _emp_perm == 2 else ('system' if _emp_perm == 1 else 'member')))
      s.query(Permission).filter(Permission.id == user.perm_id).update(
        {"auth_code": _emp_perm, "auth_name": _auth_name}
      )

      s.query(Setting).filter(Setting.id == user.setting_id).update(
        {"routingPriv": _routingPriv}
      )

      if _password_reset=='yes':
        s.query(User).filter(User.emp_id == _emp_id).update({
          "emp_name": _emp_name,
          "dep_name": _dep_name,
          "password": generate_password_hash(newPassword, method='scrypt')
        })
      else:
        s.query(User).filter(User.emp_id == _emp_id).update({
          "emp_name": _emp_name,
          "dep_name": _dep_name,
        })

      s.commit()

    s.close()

    return jsonify({
        'status': return_value
    })


# from bom table update some data
@updateTable.route("/updateBoms", methods=['POST'])
def update_boms():
    print("updateBoms....")
    request_data = request.get_json()
    #print("request_data", request_data)

    return_value = True  # true: 資料正確, 註冊成功
    s = Session()

    try:
      # 遍歷傳入的每一筆資料
      for key, bom_data in request_data.items():
        bom_id = bom_data.get('id')

        # 查找對應的記錄
        bom_record = s.query(Bom).filter_by(id=bom_id).first()

        if bom_record:
            # 更新記錄的各個欄位
            '''
            bom_record.date = bom_data.get('date')
            bom_record.date_alarm = bom_data.get('date_alarm')
            bom_record.seq_num = bom_data.get('seq_num')
            bom_record.lack = bom_data.get('lack')
            bom_record.material_num = bom_data.get('material_num')
            bom_record.mtl_comment = bom_data.get('mtl_comment')
            bom_record.qty = bom_data.get('qty')
            '''
            bom_record.receive = bom_data.get('receive')
            #bom_record.isPickOK = True    #領料完成

      s.commit()

    except Exception as e:
        s.rollback()  # 如果發生錯誤，回滾變更
        print(f"Error: {e}")
        return_value = False

    s.close()

    return jsonify({
        'status': return_value
    })


# from material table update some data by id or orde_num
@updateTable.route("/updateMaterial", methods=['POST'])
def update_material():
    print("updateMaterial....")

    request_data = request.get_json()
    #print("request_data", request_data)
    _order_num = request_data.get('order_num')
    _id = request_data.get('id')
    _record_name = request_data['record_name']
    _record_data = request_data['record_data']

    return_value = True  # true: 資料正確, 註冊成功
    s = Session()

    # 查找對應的記錄
    #material_record = s.query(Material).filter_by(order_num = _order_num).first()

    # 檢查傳入的參數，選擇查詢條件
    material_record = None
    if _order_num is not None:  # 如果傳入了 order_num
        material_record = s.query(Material).filter_by(order_num=_order_num).first()
    elif _id is not None:  # 如果傳入了 id
        material_record = s.query(Material).filter_by(id=_id).first()

    if material_record is None:
      return_value = False
    else:
      # 動態設置欄位值
      if hasattr(material_record, _record_name):
        setattr(material_record, _record_name, _record_data)
        s.commit()

    '''
    try:
      # 查找對應的記錄
      material_record = s.query(Material).filter_by(order_num = _order_num).first()

      # 動態設置欄位值
      if hasattr(material_record, _record_name):
          setattr(material_record, _record_name, _record_data)
          s.commit()
          #print(f"Updated {material_record} with {_record_name} = {_record_data}")
      else:
          #print(f"Field {_record_name} does not exist in Material.")
          return_value = False

    except Exception as e:
        s.rollback()
        print(f"Error: {e}")
        return_value = False
    '''
    s.close()

    return jsonify({
      'status': return_value
    })


# from material table update some data by id
@updateTable.route("/updateAssemble", methods=['POST'])
def update_assemble():
  print("updateAssemble....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _assemble_id = request_data['assemble_id']
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']

  return_value = True  # true: 資料正確, 註冊成功
  s = Session()

  # 查找對應的記錄
  assemble_record = s.query(Assemble).filter_by(id = _assemble_id).first()

  # 動態設置欄位值
  if hasattr(assemble_record, _record_name):
    setattr(assemble_record, _record_name, _record_data)
    s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


# from material table update some data by id
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


# from reagent table update some data by id
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



# create agv data table
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
