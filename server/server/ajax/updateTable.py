import os
import time
import datetime
from datetime import datetime as dt
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
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_

from database.tables import User, UserDelegate, Permission, Setting, Bom, Material, Assemble, AbnormalCause, Process, Product, Agv, Session
from database.p_tables import P_Material, P_Assemble,  P_AbnormalCause, P_Process, P_Product, P_Part

from werkzeug.security import generate_password_hash

from operator import itemgetter, attrgetter

from .assemble_update_utils import (
    ALLOWED_FIELDS, FIELD_SCHEMAS,
    coerce_by_schema, serialize_assemble, now_str
)

updateTable = Blueprint('updateTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


def normalize_cause_message_list(cause_message_list):
    # 如果是 list → 保持不變
    if isinstance(cause_message_list, list):
        return cause_message_list

    # 如果是字串 → 轉為 list（以「、」或「,」或空白分隔都支援）
    if isinstance(cause_message_list, str):
        # 先去除空白
        cause_message_list = cause_message_list.strip()
        # 判斷分隔符號
        if "、" in cause_message_list:
            return [s.strip() for s in cause_message_list.split("、") if s.strip()]
        elif "," in cause_message_list:
            return [s.strip() for s in cause_message_list.split(",") if s.strip()]
        else:
            # 若沒分隔符號，就視為單一項
            return [cause_message_list]

    # 其他型態（例如 None 或數字）→ 回傳空 list
    return []


# 生成唯一檔案名稱的函式
def get_unique_filename(target_dir, filename, chip):
    base, ext = os.path.splitext(filename)  # 分離檔案名稱與副檔名
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(target_dir, unique_filename)):  # 檢查檔案是否已存在
      unique_filename = f"{base}_{chip}_{counter}{ext}"  # 為檔名新增後綴
      counter += 1
    return unique_filename


def normalize_create_at(raw):
    """
    把前端丟來的 create_at 正常化成 datetime 物件：
    - 若本來就是 datetime → 直接回傳
    - 若是 timestamp(int/float) → 轉成 datetime
    - 若是字串 → 嘗試用幾種格式解析（含 'Tue, 18 Nov 2025 13:11:52 GMT'）
    """
    if raw is None:
        return None

    # 已經是 datetime.datetime，就直接用
    if isinstance(raw, dt):
        return raw

    # 若是 timestamp（秒或毫秒）
    if isinstance(raw, (int, float)):
        ts = raw / 1000.0 if raw > 10**10 else raw
        return dt.fromtimestamp(ts)

    # 若是字串
    if isinstance(raw, str):
        txt = raw.strip()
        if not txt:
            return None

        # 1) 先試 RFC 1123 / HTTP Date 格式: "Tue, 18 Nov 2025 13:11:52 GMT"
        try:
            # 注意：這個格式完全符合你 log 看到的字串
            return dt.strptime(txt, "%a, %d %b %Y %H:%M:%S GMT")
        except ValueError:
            pass

        # 2) 再試 ISO 格式（2025-11-18T13:11:52 或 2025-11-18 13:11:52）
        try:
            return dt.fromisoformat(txt.replace('Z', ''))
        except ValueError:
            pass

        # 3) 其它常見格式（看你 DB 實際有沒有用到）
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
        ):
            try:
                return dt.strptime(txt, fmt)
            except ValueError:
                continue

        # 4) 有小數秒的情況：2025-11-18 13:11:52.123456
        try:
            base, _, _ = txt.partition(".")
            return dt.strptime(base, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

        raise ValueError(f"無法解析 create_at 字串格式: {txt}")

    # 其它型態不支援
    raise TypeError(f"不支援的 create_at 型態: {type(raw)}")


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


@updateTable.route('/updateDelegate', methods=['POST'])
def terminate_active():
    print("updateDelegate....")


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


# from bom table update some data
"""
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
"""


@updateTable.route("/updateBoms", methods=['POST'])
def update_boms():
    print("updateBoms....")
    request_data = request.get_json()
    print("request_data =", request_data, type(request_data))

    s = Session()
    return_value = True

    try:
        # 1️⃣ 把 request_data 統一轉成「list of dict」
        if isinstance(request_data, dict):
            # 如果改成 { "101": {...}, "102": {...} } 也ok
            bom_list = list(request_data.values())
        elif isinstance(request_data, list):
            bom_list = request_data
        else:
            bom_list = []
            print("updateBoms: unsupported payload type")

        for bom_data in bom_list:
            if not isinstance(bom_data, dict):
                continue

            bom_id = bom_data.get('id')
            if not bom_id:
                continue

            bom = s.query(Bom).get(bom_id)
            if not bom:
                print(f"updateBoms: Bom id={bom_id} not found")
                continue

            # 目前 dialog 主要在改的是 receive / lack / lack_bom_qty / isPickOK
            if 'receive' in bom_data:
                bom.receive = bom_data['receive']
            if 'lack' in bom_data:
                bom.lack = bom_data['lack']
            if 'lack_bom_qty' in bom_data:
                bom.lack_bom_qty = bom_data['lack_bom_qty']
            if 'isPickOK' in bom_data:
                bom.isPickOK = bom_data['isPickOK']

            # 如果還有其他欄位未來要改，也可以一併加上

        s.commit()

    except Exception as e:
        s.rollback()
        return_value = False
        print("Error in updateBoms:", e)

    finally:
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

  target_create_at = normalize_create_at(assemble_record.create_at)

  if not assemble_record:
    return jsonify({"error": f"Assemble with id {assemble_id} and material_id {material_id} not found"}), 404

  #assemble_records = material_record._assemble
  #assemble_records = s.query(Assemble).filter_by(material_id=material_id).all()
  assemble_records = (
    s.query(Assemble)
      .filter(
        and_(
          Assemble.material_id == material_id,
          Assemble.create_at == target_create_at
        )
      )
      .all()
  )



  #if not assemble_records:
  #  return jsonify({"message": f"No assemble records linked to material_id {material_id}"}), 200

  # 檢查 process_step_code 是否全部為 0
  #all_process_step_zero = all(record.process_step_code == 0 for record in assemble_records)


  # 只看 is_copied_from_id 與當前 assemble_record 相同的那一組
  same_group = [r for r in assemble_records
                if r.is_copied_from_id == assemble_record.is_copied_from_id]
                #if r.update_time == assemble_record.update_time]

  # 如果同組至少有一筆，判斷是否全部都是 step=0
  all_process_step_zero = bool(assemble_records) and all(r.process_step_code == 0 for r in assemble_records)

  # 如果條件滿足，更新 material 表
  if all_process_step_zero:
    print("updateAssembleProcessStep , all_process_step_zero", all_process_step_zero)

    material_record.isAssembleStation3TakeOk = True
    assemble_record.isAssembleStationShow = True
    return_value = True
    #return jsonify({"message": "Material updated successfully"}), 200
  else:
    print("updateAssembleProcessStep , not all_process_step_zero")

    material_record.isAssembleStation3TakeOk = False
    assemble_record.isAssembleStationShow = False

    sorted_records = sorted(assemble_records, key=lambda r: r.id)
    current_index = next((i for i, r in enumerate(sorted_records) if r.id == assemble_id), None)

    print("current_index, current_index + 1, len(sorted_records:",current_index, current_index + 1, len(sorted_records))
    if current_index is not None and current_index + 1 < len(sorted_records):
        next_record = sorted_records[current_index + 1]
        #material_record.next_assemble_id = next_record.id  # 設定到 material
        print(f"next_assemble_id 設為 {next_record.id}")

        # 2️⃣ 修改 next_assemble_id record 的 show2_ok = 5
        if next_record.process_step_code == 2:  #下一個程序為檢驗
          next_record.show2_ok = 5
          next_record.total_ask_qty_end = 1
        if next_record.process_step_code == 3:  #下一個程序為雷射
          next_record.show2_ok = 7
          next_record.total_ask_qty_end = 2

        #next_record.completed_qty = assemble_record.completed_qty
        next_record.completed_qty = 0
        print(f"更新 assemble id={next_record.id} 的 show2_ok 為 5")

    return_value = False
    #return jsonify({"message": "Not all process_step_code are zero"}), 200
  s.commit()

  return jsonify({
    'status': return_value
  })


@updateTable.route('/updateAssembleProcessStepP', methods=['POST'])
def update_assemble_process_step_p():
  print("updateAssembleProcessStepP....")

  data = request.json

  if not data or 'id' not in data or 'assemble_id' not in data:
    return jsonify({"error": "Missing parameters 'id' or 'assemble_id'"}), 400

  material_id = data['id']
  assemble_id = data['assemble_id']
  return_value = False

  s = Session()

  material_record = s.query(P_Material).filter_by(id=material_id).first()
  if not material_record:
    return jsonify({"error": f"P_Material with id {material_id} not found"}), 404

  assemble_record = s.query(P_Assemble).filter_by(id=assemble_id, material_id=material_id).first()
  if not assemble_record:
    return jsonify({"error": f"P_Assemble with id {assemble_id} and material_id {material_id} not found"}), 404

  target_create_at = normalize_create_at(assemble_record.create_at)

  assemble_records = (s.query(P_Assemble)
    .filter(and_(P_Assemble.material_id == material_id, P_Assemble.create_at == target_create_at))
    .all()
  )

  # 如果同組至少有一筆，判斷是否全部都是 process_step_code=0
  all_process_step_zero = bool(assemble_records) and all(r.process_step_code == 0 for r in assemble_records)

  # 如果條件滿足，更新 material 表
  if all_process_step_zero:
    print("updateAssembleProcessStepP , all_process_step_zero", all_process_step_zero)

    material_record.isAssembleStation3TakeOk = True
    assemble_record.isAssembleStationShow = True

    return_value = True
  else:
    print("updateAssembleProcessStepP , not all_process_step_zero")

    material_record.isAssembleStation3TakeOk = False
    assemble_record.isAssembleStationShow = False

    # 把同一批加工製程排好順序，找出『現在做的是第幾道』，然後抓『下一道製程』出來。

    # assemble.seq_num 越小 → 越前面的製程
    sorted_records = sorted(assemble_records, key=lambda r: r.seq_num)

    # 現在在哪一個製程
    current_index = next((i for i, r in enumerate(sorted_records) if r.id == assemble_id), None)

    print("current_index, current_index + 1, len(sorted_records:",current_index, current_index + 1, len(sorted_records))
    if current_index is not None and current_index + 1 < len(sorted_records):
      next_record = sorted_records[current_index + 1]
      print(f"next_assemble_id 已設為 {next_record.id}")

      next_record.completed_qty = 0

    return_value = False
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
  #_fileName = data.get("file_name")
  #_bom_data = data.get("bom_data", [])
  #print("bom_data:", _bom_data)

  return_value = True

  update_data = {}
  if _date is not None:
      update_data["material_delivery_date"] = _date #訂單日期
  if _qty is not None:
      update_data["material_qty"] = _qty            #需求數量(訂單數量)
      update_data["total_delivery_qty"] = _qty      #應備數量
  s = Session()

  if update_data:
    rows_updated = s.query(Material).filter(Material.id == _id).update(update_data)

  if rows_updated == 0:
    return_value = False
    raise ValueError("Update failed: no rows affected")

  s.commit()
  '''
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
  '''
  s.close()
  '''
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
'''
  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateModifyMaterialAndBomsP", methods=['POST'])
def update_modify_material_and_Boms_p():
  print("updateModifyMaterialAndBoms....")

  data = request.json
  _id = data.get("id")
  _date = data.get("date")
  _qty = data.get("qty")

  return_value = True

  update_data = {}
  if _date is not None:
      update_data["material_delivery_date"] = _date   #訂單日期
  if _qty is not None:
      update_data["material_qty"] = _qty              #需求數量(訂單數量)
      update_data["total_delivery_qty"] = _qty        #應備數量

  s = Session()

  if update_data:
    rows_updated = s.query(P_Material).filter(P_Material.id == _id).update(update_data)

  if rows_updated == 0:
    return_value = False
    raise ValueError("Update failed: no rows affected")

  s.commit()

  s.close()

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


@updateTable.route("/updateAssmbleDataByMaterialIDP", methods=['POST'])
def update_assemble_data_by_material_id_p():
  print("updateAssmbleDataByMaterialIDP....")

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
      assemble_records = s.query(P_Assemble).filter(
          P_Assemble.material_id == _material_id,
          P_Assemble.must_receive_qty == _delivery_qty
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
      print(f"更新P_Assemble table成功，共 {len(assemble_records)} 筆資料")
      return_value = True
      #return
  except Exception as e:
      s.rollback()
      print("更新P_Assemble table失敗:", str(e))
      return_value = False
      #return

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateProcessDataByMaterialID", methods=['POST'])
def update_process_data_by_material_id():
  print("updateProcessDataByMaterialID....")

  request_data = request.get_json()
  print("request_data", request_data)
  _material_id = request_data.get('material_id')
  _seq = request_data.get('seq')
  _record_name1 = request_data.get('record_name1')
  _record_data1 = request_data.get('record_data1')
  print("material_id, seq, record_name1, record_data1:", _material_id, _seq, _record_name1, _record_data1)

  s = Session()

  try:
      material = s.query(Material).get(_material_id)
      print("step1")
      if not material:
        return jsonify({'status': False, 'msg': 'Material not found'})
      print("step2")

      target_process = (s.query(Process).filter(
          Process.material_id == _material_id,
          Process.assemble_id == 0,
          Process.has_started == True,
          Process.begin_time != '',
          Process.end_time != '',)
          .first())

      # 確保 _seq 不超過範圍
      #if _seq < 0 or _seq > len(material._process):
      if not target_process:
        return jsonify({'status': False, 'msg': 'seq out of range'})

      print("step3")

      # 取出對應的 Process
      #target_process = material._process[_seq-1]
      print("target_process:", target_process)
      # 更新欄位
      if _record_name1 and _record_data1 is not None:
        setattr(target_process, _record_name1, _record_data1)
      print("step4")

      # 提交更新
      s.commit()
      print("target_process:", target_process)
      print(f"更新成功!")
      return_value = True
  except Exception as e:
      s.rollback()
      print("更新失敗:", str(e))
      return_value = False

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateProcessDataByMaterialIDP", methods=['POST'])
def update_process_data_by_material_id_p():
  print("updateProcessDataByMaterialIDP....")

  request_data = request.get_json()
  print("request_data", request_data)
  _material_id = request_data.get('material_id')
  _seq = request_data.get('seq')
  _record_name1 = request_data.get('record_name1')
  _record_data1 = request_data.get('record_data1')
  print("material_id, seq, record_name1, record_data1:", _material_id, _seq, _record_name1, _record_data1)

  s = Session()

  try:
      material = s.query(P_Material).get(_material_id)
      #print("step1")
      if not material:
        return jsonify({'status': False, 'msg': 'Material not found'})
      #print("step2")

      target_process = (s.query(P_Process).filter(
                P_Process.material_id == _material_id,
                P_Process.assemble_id == 0,
                P_Process.has_started == True,
                P_Process.begin_time != '',
                P_Process.end_time != '',)
                .first())

      # 確保 _seq 不超過範圍
      #temp_len = len(material._process)
      #if _seq < 0 or _seq > temp_len:
      if not target_process:
        print("step2-0 ")
        return jsonify({'status': False, 'msg': 'seq out of range'})

      print("step3")

      # 取出對應的 Process
      #target_process = material._process[_seq-1]
      print("target_process:", target_process)
      # 更新欄位
      if _record_name1 and _record_data1 is not None:
        setattr(target_process, _record_name1, _record_data1)
      print("step4")

      s.commit()

      print("target_process:", target_process)
      print(f"更新成功!")
      return_value = True
  except Exception as e:
      s.rollback()
      print("更新失敗:", str(e))
      return_value = False

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


@updateTable.route("/updateAssembleMustReceiveQtyByMaterialIDP", methods=['POST'])
def update_assembleMustReceiveQty_by_MaterialID_p():
  print("updateAssembleMustReceiveQtyByMaterialIDP....")

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
    raise ValueError(f"'{ _record_name }' 不是 P_Assemble 表中的合法欄位")

  # 查詢所有 material_id 相符的 Assemble 記錄
  assemble_records = s.query(P_Assemble).filter_by(material_id = _material_id).all()

  if not assemble_records:
    return_value = False
    raise ValueError(f"No P_Assemble records found for material_id { _material_id }")

  updated_ids = []
  for record in assemble_records:
    setattr(record, _record_name, _record_data)  # 動態設欄位
    updated_ids.append(record.id)

  s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateAssembleMustReceiveQtyByMaterialIDAndDate", methods=['POST'])
def update_assembleMustReceiveQty_by_materialID_and_date():
    print("updateAssembleMustReceiveQtyByMaterialIDAndDate....")

    request_data = request.get_json()
    print("request_data", request_data)

    _material_id   = request_data.get('material_id')
    _raw_create_at = request_data.get('create_at')
    _record_name   = request_data['record_name']
    _record_data   = request_data['record_data']

    print("_material_id, _record_name, _record_data:", _material_id, _record_name, _record_data)
    print("raw create_at type:", type(_raw_create_at), "value:", _raw_create_at)

    return_value = True
    s = Session()

    try:
        # 1) 檢查欄位是否合法
        valid_columns = [c.key for c in inspect(Assemble).mapper.column_attrs]
        if _record_name not in valid_columns:
            return_value = False
            raise ValueError(f"'{_record_name}' 不是 Assemble 表中的合法欄位")

        # 2) 正常化 create_at
        if _raw_create_at is None:
            return_value = False
            raise ValueError("缺少 create_at 參數")

        target_create_at = normalize_create_at(_raw_create_at)
        print("normalized create_at:", target_create_at, "type:", type(target_create_at))

        # 3) 查出同 material_id + 同 create_at 的那一批資料
        assemble_records = (
            s.query(Assemble)
             .filter(
                and_(
                    Assemble.material_id == _material_id,
                    Assemble.create_at == target_create_at
                )
             )
             .all()
        )

        if not assemble_records:
            return_value = False
            raise ValueError(
                f"No Assemble records found for material_id={_material_id} and create_at={_raw_create_at}"
            )

        updated_ids = []
        for record in assemble_records:
            setattr(record, _record_name, _record_data)
            updated_ids.append(record.id)

        print("updated assemble ids:", updated_ids)

        s.commit()

    except Exception as e:
        s.rollback()
        print("update_assembleMustReceiveQty_by_materialID_and_date error:", e)
        raise
    finally:
        s.close()

    return jsonify({
        'status': return_value
    })


@updateTable.route("/updateAssembleMustReceiveQtyByMaterialIDAndDateP", methods=['POST'])
def update_assembleMustReceiveQty_by_materialID_and_date_p():
    print("updateAssembleMustReceiveQtyByMaterialIDAndDateP....")

    request_data = request.get_json()
    print("request_data", request_data)

    _material_id   = request_data.get('material_id')
    _raw_create_at = request_data.get('create_at')
    _record_name   = request_data['record_name']
    _record_data   = request_data['record_data']

    print("_material_id, _record_name, _record_data:", _material_id, _record_name, _record_data)
    print("raw create_at type:", type(_raw_create_at), "value:", _raw_create_at)

    return_value = True
    s = Session()

    try:
        # 1) 檢查欄位是否合法
        valid_columns = [c.key for c in inspect(P_Assemble).mapper.column_attrs]
        if _record_name not in valid_columns:
            return_value = False
            raise ValueError(f"'{_record_name}' 不是 P_Assemble 表中的合法欄位")

        # 2) 正常化 create_at
        if _raw_create_at is None:
            return_value = False
            raise ValueError("缺少 create_at 參數")

        target_create_at = normalize_create_at(_raw_create_at)
        print("normalized create_at:", target_create_at, "type:", type(target_create_at))

        # 3) 查出同 material_id + 同 create_at 的那一批資料
        assemble_records = (
            s.query(P_Assemble)
             .filter(
                and_(
                    P_Assemble.material_id == _material_id,
                    P_Assemble.create_at == target_create_at
                )
             )
             .all()
        )

        if not assemble_records:
            return_value = False
            raise ValueError(
                f"No P_Assemble records found for material_id={_material_id} and create_at={_raw_create_at}"
            )

        updated_ids = []
        for record in assemble_records:
            setattr(record, _record_name, _record_data)
            updated_ids.append(record.id)

        print("updated p assemble ids:", updated_ids)

        s.commit()

    except Exception as e:
        s.rollback()
        print("update_assembleMustReceiveQty_by_materialID_and_date_p error:", e)
        raise
    finally:
        s.close()

    return jsonify({
        'status': return_value
    })


@updateTable.route("/updateMaterialFields", methods=['POST'])
def update_material_fields():
    data = request.get_json(silent=True) or {}
    mid = data.get("id")
    fields = data.get("fields") or {}
    if not mid or not isinstance(fields, dict) or not fields:
        return jsonify(success=False, message="id / fields 缺失"), 400

    # 允許更新哪些欄位（白名單）
    ALLOWED = {
        "isOpen", "isOpenEmpId", "hasStarted", "startStatus",
        # 需要的話把其他欄位加進來
    }
    BOOLS = {"isOpen", "hasStarted", "startStatus"}

    # 過濾＋型別歸一化
    patch = {}
    for k, v in fields.items():
        if k not in ALLOWED:
            continue
        if k in BOOLS:
            patch[k] = bool(v)
        else:
            patch[k] = v if v is not None else ""

    if not patch:
        return jsonify(success=False, message="無可更新欄位"), 400

    s = Session()
    try:
        # 行鎖避免併發踩踏
        mat = (
            s.query(Material)
             .filter(Material.id == mid)
             .with_for_update()
             .one_or_none()
        )
        if not mat:
            return jsonify(success=False, message="material not found"), 404

        for k, v in patch.items():
            setattr(mat, k, v)

        s.commit()
        return jsonify(success=True, id=mid, updated=patch)
    except Exception as e:
        s.rollback()
        print("update_material_fields failed:", e)  # 或用 logger
        return jsonify(success=False, message="internal error"), 500
    finally:
        s.close()


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


@updateTable.route("/updateMaterialP", methods=['POST'])
def update_material_p():
    print("updateMaterialP....")

    request_data = request.get_json()
    #print("request_data", request_data)
    _order_num = request_data.get('order_num')
    _id = request_data.get('id')
    _record_name = request_data['record_name']
    _record_data = request_data['record_data']
    print("_order_num, _id, _record_name, _record_data:", _order_num, _id, _record_name, _record_data)

    return_value = True  # true: 資料正確, 註冊成功
    s = Session()

    # 檢查傳入的參數，選擇查詢條件
    material_record = None
    if _order_num is not None:  # 如果傳入了 order_num
        material_record = s.query(P_Material).filter_by(order_num=_order_num).first()
    elif _id is not None:  # 如果傳入了 id
        material_record = s.query(P_Material).filter_by(id=_id).first()

    if material_record is None:
      return_value = False
    else:
      # 動態設置欄位值
      if hasattr(material_record, _record_name):
        setattr(material_record, _record_name, _record_data)
        s.commit()

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
@updateTable.route("/updateAssembleP", methods=['POST'])
def update_assemble_p():
  print("updateAssembleP....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _assemble_id = request_data['assemble_id']
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']

  print("_record_name:", _record_name)

  return_value = True  # true: 資料正確, 註冊成功
  s = Session()

  # 查找對應的記錄
  assemble_record = s.query(P_Assemble).filter_by(id = _assemble_id).first()

  # 動態設置欄位值
  if hasattr(assemble_record, _record_name):
    setattr(assemble_record, _record_name, _record_data)
    s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


# from material table update some data by id
@updateTable.route("/updateProcessData", methods=['POST'])
def update_process_data():
  print("updateProcessData....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _process_id = request_data['process_id']
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']

  #print("_record_name:", _record_name)

  return_value = True  # true: 資料正確, 註冊成功
  s = Session()

  # 查找對應的記錄
  process_record = s.query(Process).filter_by(id = _process_id).first()

  # 動態設置欄位值
  if hasattr(process_record, _record_name):
    setattr(process_record, _record_name, _record_data)
    s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateProcessDataP", methods=['POST'])
def update_process_data_p():
  print("updateProcessDataP....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _process_id = request_data['process_id']
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']

  return_value = True  # true: 資料正確, 註冊成功
  s = Session()

  # 查找對應的記錄
  process_record = s.query(P_Process).filter_by(id = _process_id).first()

  # 動態設置欄位值
  if hasattr(process_record, _record_name):
    setattr(process_record, _record_name, _record_data)
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


@updateTable.route("/updateMaterialRecordP", methods=['POST'])
def update_material_record_p():
  print("updateMaterialRecordP....")

  request_data = request.get_json()

  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  _show1_ok = request_data['show1_ok']
  _show2_ok = request_data['show2_ok']
  _show3_ok = request_data['show3_ok']
  #_whichStation = request_data['whichStation']

  s = Session()

  if _order_num is not None:  # 如果傳入了 order_num
    s.query(P_Material).filter(P_Material.order_num == _order_num).update({
      "show1_ok": _show1_ok,
      "show2_ok": _show2_ok,
      "show3_ok": _show3_ok,
      #"whichStation": _whichStation,
    })
  elif _id is not None:  # 如果傳入了 id
    s.query(P_Material).filter(P_Material.id == _id).update({
      "show1_ok": _show1_ok,
      "show2_ok": _show2_ok,
      "show3_ok": _show3_ok,
      #"whichStation": _whichStation,
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

"""
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

  s = Session()

  try:
    # 取得 Assemble 資料
    assemble_record = s.query(Assemble).get(assemble_id)

    # 儲存進資料庫
    assemble_record.alarm_message = cause_message_list
    assemble_record.writer_id = cause_user
    assemble_record.write_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    s.commit()

    return jsonify({"status": True, "message": "Alarm message updated successfully"})

  except Exception as e:
    s.rollback()
    return jsonify({"status": False, "message": str(e)}), 500

  finally:
    s.close()
"""


@updateTable.route("/updateAssembleAlarmMessage", methods=["POST"])
def update_assemble_alarm_message():
    print("updateAssembleAlarmMessage....")

    data = request.get_json()

    assemble_id = data.get("assemble_id")
    print("assemble_id:", assemble_id)
    cause_message_list = data.get("cause_message")  # 前端預期傳 list 或字串
    print("cause_message_list:", cause_message_list)
    cause_user = data.get("cause_user")
    print("cause_user:", cause_user)

    s = Session()

    try:
        # 1) 先抓本尊那筆 assemble
        assemble_record = s.query(Assemble).get(assemble_id)
        pre_assemble_record = s.query(Assemble).get(assemble_id-1)
        if not assemble_record or not pre_assemble_record:
            s.close()
            return jsonify({"status": False, "message": "Assemble record not found"}), 404

        # 2) 把 cause_message_list 轉成要存進 String(250) 的字串
        #    - 若是 list: 用 "、" 接起來
        #    - 若是字串: 直接用
        #    - 其他型態: 強制轉字串
        if isinstance(cause_message_list, list):
            alarm_message_str = "、".join(str(x).strip() for x in cause_message_list if str(x).strip())
        elif isinstance(cause_message_list, str):
            alarm_message_str = cause_message_list.strip()
        else:
            alarm_message_str = str(cause_message_list or "").strip()

        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        # 3) 更新本尊那筆
        assemble_record.alarm_message = alarm_message_str
        #assemble_record.alarm_message = ''
        assemble_record.writer_id = cause_user
        assemble_record.write_date = now_str
        assemble_record.isAssembleFirstAlarm = True
        assemble_record.alarm_enable = False

        # 4) 同步到所有「從這筆複製出去」的資料
        #    透過 model 上設定的 backref: copied_to
        #    copied_to = 所有 is_copied_from_id = assemble_record.id 的子筆數
        for child in assemble_record.copied_to:
          print("child.id:", child.id)
          # 只更新 user_id 有值的子筆數
          if child.user_id and str(child.user_id).strip() != "":
              child.alarm_message = alarm_message_str
              child.writer_id = cause_user
              child.write_date = now_str
              child.isAssembleFirstAlarm = False
              child.alarm_enable = False

        for child in pre_assemble_record.copied_to:
          print("child.id:", child.id)
          # 只更新 user_id 有值的子筆數
          if child.user_id and str(child.user_id).strip() != "":
              child.alarm_message = alarm_message_str
              child.writer_id = cause_user
              child.write_date = now_str
              child.isAssembleFirstAlarm = False
              child.alarm_enable = False

        # 如果沒有用 backref，也可以用下面這種查詢方式 (擇一即可)
        # children = (
        #     s.query(Assemble)
        #      .filter(Assemble.is_copied_from_id == assemble_id)
        #      .all()
        # )
        # for child in children:
        #     child.alarm_message = alarm_message_str
        #     child.writer_id = cause_user
        #     child.write_date = now_str

        s.commit()

        return jsonify({
            "status": True,
            "message": "Alarm message updated successfully"
        })

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



@updateTable.route("/updateBomXorReceiveP", methods=["POST"])
def update_bom_xor_receive_p():
    print("updateBomXorReceiveP....")

    data = request.get_json()
    copied_id = data.get("copied_material_id")
    print("copied_id", copied_id)

    s = Session()

    # 找到複製資料
    copied_material = s.query(P_Material).options(joinedload(P_Material._bom)).filter_by(id=copied_id).first()
    if not copied_material or not copied_material.is_copied_from_id:
        return jsonify({"error": "Invalid copied p_material table or missing source ID"}), 400
    print("copied_material:",copied_material)

    # 找到原始資料
    source_material = s.query(P_Material).options(joinedload(P_Material._bom)).filter_by(id=copied_material.is_copied_from_id).first()
    if not source_material:
        return jsonify({"error": "Source p_material not found"}), 404
    print("source p_material:",source_material)

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
                source_bom.receive = True  #          將缺料清除
                source_material.isLackMaterial = 99
                copied_material.isLackMaterial = 0
                updated = True

    if updated:
        s.commit()

    s.close()

    return jsonify({
      'status': True,
      'message': "Updated successfully."
    })


def _to_int_or_none(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        raise ValueError("必須是整數或空字串/Null")

@updateTable.route("/updateProduct", methods=["POST"])
def update_product():
    s = Session()
    try:
        data = request.get_json(silent=True) or {}
        items = data.get("items", [])
        if not isinstance(items, list) or len(items) == 0:
            return jsonify({"ok": False, "error": "items 必須為非空陣列"}), 400

        # 取出所有 material_id
        try:
            mids = [int(it["material_id"]) for it in items if "material_id" in it]
        except (KeyError, TypeError, ValueError):
            return jsonify({"ok": False, "error": "每筆必須含 material_id（整數）"}), 400

        # 檢查 material 是否存在
        exist_mid = set(x[0] for x in s.query(Material.id).filter(Material.id.in_(mids)).all())
        not_found = [mid for mid in mids if mid not in exist_mid]
        if not_found:
            return jsonify({"ok": False, "error": f"找不到 material_id: {not_found}"}), 400

        # 先抓現有的 Product（假設一個 material_id 對應一筆 Product）
        exist_products = s.query(Product).filter(Product.material_id.in_(mids)).all()
        by_mid = {p.material_id: p for p in exist_products}

        # 處理每筆
        for it in items:
            mid = int(it["material_id"])
            p = by_mid.get(mid)
            if p is None:
                p = Product(
                    material_id   = mid,
                    delivery_qty  = 0,
                    assemble_qty  = 0,
                    allOk_qty     = 0,
                    good_qty      = 0,
                    non_good_qty  = 0,
                    reason        = None,
                    confirm_comment = None,
                )
                s.add(p)
                by_mid[mid] = p

            # ---- 1) 累加欄位 ----
            for f in ("allOk_qty", "good_qty", "non_good_qty"):
                if f in it:
                    inc = _to_int_or_none(it.get(f))
                    if inc is not None:
                        setattr(p, f, (getattr(p, f) or 0) + inc)

            # ---- 2) 直接覆寫欄位（有帶才動）----
            if "delivery_qty" in it:
                v = _to_int_or_none(it.get("delivery_qty"))
                if v is not None:
                    p.delivery_qty = v

            if "assemble_qty" in it:
                v = _to_int_or_none(it.get("assemble_qty"))
                if v is not None:
                    p.assemble_qty = v

            if "reason" in it:
                # 字串允許清空；要清空就傳 ""；不帶就不動
                rv = it.get("reason")
                p.reason = ("" if rv == "" else (str(rv) if rv is not None else p.reason))

            if "confirm_comment" in it:
                cv = it.get("confirm_comment")
                p.confirm_comment = ("" if cv == "" else (str(cv) if cv is not None else p.confirm_comment))

        s.commit()

        # 組回傳
        out = []
        for mid, p in by_mid.items():
            if mid in exist_mid:  # 只回這次有動到的 mids
                out.append({
                    "id": getattr(p, "id", None),
                    "material_id": p.material_id,
                    "delivery_qty": p.delivery_qty,
                    "assemble_qty": p.assemble_qty,
                    "allOk_qty": p.allOk_qty,
                    "good_qty": p.good_qty,
                    "non_good_qty": p.non_good_qty,
                    "reason": p.reason,
                    "confirm_comment": p.confirm_comment,
                })
        return jsonify({"ok": True, "updated": len(out), "items": out}), 200

    except ValueError as e:
        s.rollback()
        return jsonify({"ok": False, "error": str(e)}), 400
    except SQLAlchemyError as e:
        s.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    except Exception as e:
        s.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        s.close()


@updateTable.route("/updateAssembleTableData", methods=["POST"])
def update_assemble_table_data():
    s = Session()
    try:
        data = request.get_json(force=True) or {}
        assemble_id = data.get("assemble_id")
        if not assemble_id:
            return jsonify({"status": False, "message": "assemble_id 為必填"}), 400

        patch = data.get("patch")
        if patch is None:
            patch = {k: v for k, v in data.items() if k != "assemble_id"}
        if not isinstance(patch, dict) or not patch:
            return jsonify({"status": False, "message": "沒有可更新欄位"}), 400

        obj = s.query(Assemble).get(int(assemble_id))
        if not obj:
            return jsonify({"status": False, "message": f"Assemble id={assemble_id} 不存在"}), 404

        before = serialize_assemble(obj)

        updated, ignored = [], []
        for k, v in patch.items():
            if k not in ALLOWED_FIELDS:
                ignored.append(k); continue
            setattr(obj, k, coerce_by_schema(k, v))
            updated.append(k)

        # 統一由後端覆寫 update_time
        obj.update_time = now_str()
        if "update_time" not in updated:
            updated.append("update_time")

        # 可選：驗證 is_copied_from_id
        if "is_copied_from_id" in updated and obj.is_copied_from_id:
            exists = s.query(Assemble.id).filter(Assemble.id == obj.is_copied_from_id).first()
            if not exists:
                obj.is_copied_from_id = None
                updated.remove("is_copied_from_id")
                ignored.append("is_copied_from_id(不存在的來源 id)")

        s.commit(); s.refresh(obj)
        after = serialize_assemble(obj)

        return jsonify({
            "status": True, "id": obj.id,
            "updated": sorted(updated), "ignored_fields": ignored,
            "before": before, "after": after
        }), 200

    except SQLAlchemyError as e:
        s.rollback()
        return jsonify({"status": False, "message": f"資料庫錯誤: {str(e)}"}), 500
    except Exception as e:
        s.rollback()
        return jsonify({"status": False, "message": f"伺服器錯誤: {str(e)}"}), 500
    finally:
        s.close()

