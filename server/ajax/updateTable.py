import time
import datetime
import pytz

from flask import Blueprint, jsonify, request
import pymysql
from sqlalchemy import exc
from sqlalchemy import func
from sqlalchemy import distinct

from database.tables import User, Permission, Setting, Session

from werkzeug.security import generate_password_hash

from operator import itemgetter, attrgetter   # 2023-08-27  add

updateTable = Blueprint('updateTable', __name__)

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


# update user's setting from user table some data
@updateTable.route("/updateSetting", methods=['POST'])
def update_setting():
    print("updateSetting....")

    request_data = request.get_json()
    print("request_data:", request_data)

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
    print("request_data", request_data)
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


# from reagent table update some data by id
@ updateTable.route("/updatePermissions", methods=['POST'])
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
