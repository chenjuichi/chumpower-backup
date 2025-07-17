import os
import time
import datetime
import shutil
import pytz

from flask import Blueprint, jsonify, request, current_app

import pymysql
from sqlalchemy import exc
from sqlalchemy import func
from sqlalchemy import distinct
from sqlalchemy import inspect
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from database.tables import User, Permission, Setting, Bom, Material, Assemble, AbnormalCause, Product, Agv, Session

from werkzeug.security import generate_password_hash

from operator import itemgetter, attrgetter   # 2023-08-27  add

updateTable = Blueprint('updateTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


# 生成唯一檔案名稱的函式
def get_unique_filename(target_dir, filename, chip):
    base, ext = os.path.splitext(filename)  # 分離檔案名稱與副檔名
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(target_dir, unique_filename)):  # 檢查檔案是否已存在
      unique_filename = f"{base}_{chip}_{counter}{ext}"  # 為檔名新增後綴
      counter += 1
    return unique_filename


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
    print("request_data =", request_data)

    return_value = True
    s = Session()

    try:
        for key, bom_data in request_data.items():
            print(f"key={key}, type(bom_data)={type(bom_data)}, bom_data={bom_data}")

            if isinstance(bom_data, dict):
                bom_id = bom_data.get('id')
                receive_val = bom_data.get('receive')

                # 查找並更新對應資料
                bom_record = s.query(Bom).filter_by(id=bom_id).first()
                if bom_record:
                    print(f"Before update: id={bom_id}, receive={bom_record.receive}")
                    bom_record.receive = receive_val
                    print(f"After update: id={bom_id}, receive={bom_record.receive}")
            else:
                print(f"Warning: bom_data 不是 dict，跳過 key={key}")

        s.commit()

    except Exception as e:
        s.rollback()
        print(f"Error: {e}")
        return_value = False

    s.close()

    return jsonify({
        'status': return_value
    })


'''
@updateTable.route("/updateBomsInMaterial", methods=['POST'])
def update_bom(material_id):
  session = Session()
  try:
      # 取得請求的 BOM 資料
      data = request.json
      material_id = data.get("material_id")
      bom_items = data.get("bom_items", [])

      # 確認 `Material` 是否存在
      material = session.query(Material).filter_by(id=material_id).first()
      if not material:
          return jsonify({"error": f"Material id {material_id} not found"}), 404

      # 取得現有的 BOM 資料
      existing_boms = session.query(Bom).filter_by(material_id=material_id).all()
      existing_ids = {bom.id for bom in existing_boms}

      # 從請求資料中分離出來的 ID
      request_ids = {item["id"] for item in bom_items if "id" in item}

      # 刪除不在請求中的 BOM 資料
      boms_to_delete = [bom for bom in existing_boms if bom.id not in request_ids]
      for bom in boms_to_delete:
          session.delete(bom)

      # 更新或新增 BOM
      for item in bom_items:
          if "id" in item and item["id"] in existing_ids:
              # 更新現有的 BOM
              bom = session.query(Bom).filter_by(id=item["id"]).first()
              bom.material_num = item["material_num"]
          else:
              # 新增新的 BOM
              new_bom = Bom(
                  material_id=material_id,
                  material_num=item["material_num"],
                  seq_num="",
                  material_comment="",
                  req_qty=0
              )
              session.add(new_bom)

      # 提交事務
      session.commit()
      return jsonify({"message": "BOM updated successfully"}), 200

  except SQLAlchemyError as e:
      session.rollback()
      return jsonify({"error": str(e)}), 500
  finally:
      session.close()
'''

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


@updateTable.route('/updateAssembleProcessStep', methods=['POST'])
def update_assemble_process_step():
  print("updateAssembleProcessStep....")

  data = request.json

  if not data or 'id' not in data or 'assemble_id' not in data:
    return jsonify({"error": "Missing parameters 'id' or 'assemble_id'"}), 400

  material_id = data['id']
  assemble_id = data['assemble_id']
  return_value = False

  s = Session()

  material_record = s.query(Material).filter_by(id=material_id).first()

  if not material_record:
    return jsonify({"error": f"Material with id {material_id} not found"}), 404

  assemble_record = s.query(Assemble).filter_by(id=assemble_id, material_id=material_id).first()

  if not assemble_record:
    return jsonify({"error": f"Assemble with id {assemble_id} and material_id {material_id} not found"}), 404


  assemble_records = material_record._assemble

  #if not assemble_records:
  #  return jsonify({"message": f"No assemble records linked to material_id {material_id}"}), 200

  # 檢查 process_step_code 是否全部為 0
  all_process_step_zero = all(record.process_step_code == 0 for record in assemble_records)

  # 如果條件滿足，更新 material 表
  if all_process_step_zero:
    print("updateAssembleProcessStep , all_process_step_zero")

    material_record.isAssembleStation3TakeOk = True
    assemble_record.isAssembleStationShow = True
    return_value = True
    #return jsonify({"message": "Material updated successfully"}), 200
  else:
    print("updateAssembleProcessStep , not all_process_step_zero")

    material_record.isAssembleStation3TakeOk = False
    assemble_record.isAssembleStationShow = False
    return_value = False
    #return jsonify({"message": "Not all process_step_code are zero"}), 200
  s.commit()

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateModifyMaterialAndBoms", methods=['POST'])
def update_modify_material_and_Boms():
  print("updateModifyMaterialAndBoms....")

  data = request.json
  _id = data.get("id")
  _date = data.get("date")
  _qty = data.get("qty")
  _fileName = data.get("file_name")
  _bom_data = data.get("bom_data", [])
  print("bom_data:", _bom_data)

  return_value = True

  s = Session()

  update_data = {}
  if _date is not None:
      update_data["material_delivery_date"] = _date
  if _qty is not None:
      update_data["material_qty"] = _qty

  if update_data:
    rows_updated = s.query(Material).filter(Material.id == _id).update(update_data)

  if rows_updated == 0:
    return_value = False
    raise ValueError("Update failed: no rows affected")

  s.commit()

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

  s.close()

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

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateAssmbleDataByMaterialID", methods=['POST'])
def update_assemble_data_by_material_id():
  print("updateAssmbleDataByMaterialID....")

  request_data = request.get_json()
  print("request_data", request_data)
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
      assemble_records = s.query(Assemble).filter(
          Assemble.material_id == _material_id,
          Assemble.must_receive_qty == _delivery_qty
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
  print("request_data", request_data)
  _material_id = request_data.get('material_id')
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']
  print("_order_num, _id, _record_name, _record_data:", _material_id, _record_name, _record_data)

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
    print("_order_num, _id, _record_name, _record_data:", _order_num, _id, _record_name, _record_data)

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

  print("_record_name:", _record_name)

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


@updateTable.route("/updateAssembleAlarmMessage", methods=["POST"])
def update_assemble_alarm_message():
  print("updateAssembleAlarmMessage....")

  data = request.get_json()

  assemble_id = data.get("assemble_id")
  print("assemble_id:",assemble_id)
  cause_message_list = data.get("cause_message")  # 預期是一個 list，例如 ["異常1", "異常2"]
  print("cause_message_list:",cause_message_list)
  cause_user = data.get("cause_user")
  print("cause_user:",cause_user)


  if not assemble_id or not isinstance(cause_message_list, list):
    return jsonify({"status": False, "message": "Missing or invalid data"}), 400

  s = Session()

  try:
    # 取得 Assemble 資料
    assemble_record = s.query(Assemble).get(assemble_id)
    if not assemble_record:
      return jsonify({"status": False, "message": "Assemble record not found"}), 404

    # 取得所有異常資料
    _alarm_objects = s.query(AbnormalCause).all()
    _alarm_objects_dict = {item.message.strip(): item.id for item in _alarm_objects}

    # 比對字串，取得對應的 ID
    cause_id_list = []
    '''
    for msg in cause_message_list:
      msg_stripped = msg.strip()
      if msg_stripped in _alarm_objects_dict:
        cause_id_list.append(str(_alarm_objects_dict[msg_stripped]))
    '''
    for msg in cause_message_list:
        # 取出括號前的異常名稱（例：'散爪(M01002)' → '散爪'）
        msg_stripped = msg.split('(')[0].strip()
        if msg_stripped in _alarm_objects_dict:
            cause_id_list.append(str(_alarm_objects_dict[msg_stripped]))


    # 將 ID 列表轉為逗號分隔字串
    new_alarm_id = ", ".join(cause_id_list)
    print("new_alarm_id:", new_alarm_id)

    # 儲存進資料庫
    assemble_record.alarm_message = new_alarm_id
    assemble_record.writer_id = cause_user
    assemble_record.write_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    s.commit()

    return jsonify({"status": True, "message": "Alarm message updated successfully"})

  except Exception as e:
    s.rollback()
    return jsonify({"status": False, "message": str(e)}), 500

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
    print("source_boms:",source_boms)
    print("copied_boms:",copied_boms)

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

    if updated:
        s.commit()

    s.close()

    return jsonify({
      'status': True,
      'message': "Updated successfully."
    })

