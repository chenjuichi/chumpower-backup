import math
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import func
from database.tables import User, Process, Agv, Material, Assemble, Bom, Permission, Product, Process, Setting, Session
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

import pymysql
from sqlalchemy import exc

createTable = Blueprint('createTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------

# create user data and perm.id=4 into table
@createTable.route("/register", methods=['POST'])
def register():
    print("register....")

    request_data = request.get_json()
    print("request_data:", request_data)
    emp_id = request_data['emp_id']
    emp_name = request_data['emp_name']
    dep_name = request_data['dep_name']
    sPWD = request_data['password']  # convert null into empty string
    emp_perm = request_data['emp_perm']
    routingPriv = request_data['routingPriv']

    #return_value = True  # true: 資料正確, 註冊成功

    s = Session()
    #前端已做檢查, 所以暫時mark
    #old_user = s.query(User).filter_by(emp_id=emp_id).first()
    #if old_user:
    #  return_value = False  # if the user exist

    #if return_value:
    message='hello ' + emp_name
    perm = s.query(Permission).filter_by(auth_code=emp_perm).first()
    new_user_setting = Setting(message=message, lastRoutingName='Main', routingPriv=routingPriv,)
    s.add(new_user_setting)
    s.flush()
    new_user = User(
      emp_id=emp_id,
      emp_name=emp_name,
      dep_name=dep_name,
      password=generate_password_hash(sPWD, method='scrypt'),   # 生成密碼
      perm_id=perm.id,
      setting_id=new_user_setting.id
    )
    s.add(new_user)

    s.commit()

    s.close()

    return jsonify({
      #'status': return_value,
      'status': True,
    })


# create user data and perm.id=4 into table
@createTable.route("/createUser", methods=['POST'])
def createUser():
    print("createUser....")

    request_data = request.get_json()

    emp_id = (request_data['emp_id'] or '')
    emp_name = (request_data['emp_name'] or '')
    dep_name = request_data['dep_name']
    sPWD = (request_data['password'] or '')  # convert null into empty string

    return_value = True  # true: 資料正確, 註冊成功
    tempID = ""
    tempName = ""
    if emp_id == "" or emp_name == "" or sPWD == "":
      return_value = False  # false: 資料不完全 註冊失敗

    #dep = (request_data['dep'] or '')  # convert null into empty string
    # code = request_data['perm_id']

    s = Session()
    #department = s.query(Department).filter_by(dep_name=dep).first()
    #if not department:
    #    return_value = False  # if the user's department does not exist

    # permission = s.query(Permission).filter_by(auth_code=code).first()
    # if not permission:
    #    return_value = False  # if the user's permission does not exist

    old_user = s.query(User).filter_by(emp_id=emp_id).first()
    if old_user:
        tempID = old_user.emp_id  # 歷史資料中的員工編號
        tempName = old_user.emp_name
        return_value = False  # if the user exist

    if return_value:
        new_user_setting = Setting(
            message='add ' + emp_name,)
        s.add(new_user_setting)
        s.flush()
        new_user = User(emp_id=emp_id, emp_name=emp_name, depp_name=dep_name,
                        #password=generate_password_hash(sPWD, method='sha256'),
                        password=generate_password_hash(sPWD, method='scrypt'),   # 生成密碼, Werkzeug 3.0 版本
                        #dep_id=department.id,
                        # perm_id=permission.id,
                        perm_id=4,  # first permission,auth_code=0:none
                        setting_id=new_user_setting.id,)
        s.add(new_user)
        s.commit()

    s.close()
    return jsonify({
        'status': return_value,
        'returnID': tempID,
        'returnName': tempName,
    })

'''
@createTable.route("/createSpindleRunins", methods=['POST'])
def create_spindle_runins():
    print("createSpindleRunins....")

    request_data = request.get_json()
    #print("request_data: ", request_data)

    _obj = request_data['block']
    #_count = request_data['count']
    _cat=request_data['spindleRunIn_spindle_cat']
    _empID = request_data['spindleRunIn_employer_emp_id']


    return_value = True  # true: 資料正確, true
    return_message=''
    s = Session()

    _spindle = s.query(Spindle).filter_by(spindle_cat=_cat).first()
    _user = s.query(User).filter_by(emp_id=_empID).first()

    _spindleRunIn_excel_file = request_data['spindleRunIn_excel_file']
    _spindleRunIn_customer = request_data['spindleRunIn_customer']
    _spindleRunIn_work_id = request_data['spindleRunIn_id']
    _spindleRunIn_date = request_data['spindleRunIn_date']

    if (not _spindle or not _user):
      return_value = False  # true: 資料正確, true
      return_message= '錯誤! 在' + _spindleRunIn_excel_file + '內, 系統沒有主軸' + _cat + '或員工編號' + _empID + '資料...'
    else:
      new_spindle_runin = SpindleRunIn(
        spindleRunIn_excel_file = _spindleRunIn_excel_file,
        spindleRunIn_customer = _spindleRunIn_customer,
        spindleRunIn_work_id = _spindleRunIn_work_id,
        spindleRunIn_spindle_id = _spindle.id,
        spindleRunIn_employer = _user.id,
        spindleRunIn_date = _spindleRunIn_date,
      )

      s.add(new_spindle_runin)
      s.flush()
      spindle_runin_id = new_spindle_runin.id
      print("spindle_runin_id: ", spindle_runin_id)

      runin_data_total_size = len(_obj)
      _objects = []
      for x in range(runin_data_total_size):
        u = RunInData(
        spindleRunIn_id = spindle_runin_id,
        spindleRunIn_period = _obj[x]['spindleRunIn_period'],
        spindleRunIn_speed_level = _obj[x]['spindleRunIn_speed_level'],
        spindleRunIn_speed = _obj[x]['spindleRunIn_speed'],
        spindleRunIn_stator_temp = _obj[x]['spindleRunIn_stator_temp'],
        spindleRunIn_inner_frontBearing_temp = _obj[x]['spindleRunIn_inner_frontBearing_temp'],
        spindleRunIn_inner_backBearing_temp = _obj[x]['spindleRunIn_inner_backBearing_temp'],
        spindleRunIn_outer_frontBearing_temp = _obj[x]['spindleRunIn_outer_frontBearing_temp'],
        spindleRunIn_outer_backBearing_temp = _obj[x]['spindleRunIn_outer_backBearing_temp'],
        spindleRunIn_room_temp = _obj[x]['spindleRunIn_room_temp'],
        spindleRunIn_coolWater_temp = _obj[x]['spindleRunIn_coolWater_temp'],
        spindleRunIn_Rphase_current = _obj[x]['spindleRunIn_Rphase_current'],
        spindleRunIn_Sphase_current = _obj[x]['spindleRunIn_Sphase_current'],
        spindleRunIn_Tphase_current = _obj[x]['spindleRunIn_Tphase_current'],
        spindleRunIn_cool_pipeline_flow = _obj[x]['spindleRunIn_cool_pipeline_flow'],
        spindleRunIn_cool_pipeline_pressure = _obj[x]['spindleRunIn_cool_pipeline_pressure'],
        spindleRunIn_frontBearing_vibration_speed1 = _obj[x]['spindleRunIn_frontBearing_vibration_speed1'],
        spindleRunIn_frontBearing_vibration_acc1 = _obj[x]['spindleRunIn_frontBearing_vibration_acc1'],
        spindleRunIn_frontBearing_vibration_disp1 = _obj[x]['spindleRunIn_frontBearing_vibration_disp1'],
        spindleRunIn_frontBearing_vibration_speed2 = _obj[x]['spindleRunIn_frontBearing_vibration_speed2'],
        spindleRunIn_frontBearing_vibration_acc2 = _obj[x]['spindleRunIn_frontBearing_vibration_acc2'],
        spindleRunIn_frontBearing_vibration_disp2 = _obj[x]['spindleRunIn_frontBearing_vibration_disp2'],
        spindleRunIn_backBearing_vibration_speed1 = _obj[x]['spindleRunIn_backBearing_vibration_speed1'],
        spindleRunIn_backBearing_vibration_acc1 = _obj[x]['spindleRunIn_backBearing_vibration_acc1'],
        spindleRunIn_backBearing_vibration_disp1 = _obj[x]['spindleRunIn_backBearing_vibration_disp1'],
        spindleRunIn_backBearing_vibration_speed2 = _obj[x]['spindleRunIn_backBearing_vibration_speed2'],
        spindleRunIn_backBearing_vibration_acc2 = _obj[x]['spindleRunIn_backBearing_vibration_acc2'],
        spindleRunIn_backBearing_vibration_disp2 = _obj[x]['spindleRunIn_backBearing_vibration_disp2'],
        )
        _objects.append(u)

      s.bulk_save_objects(_objects)

      try:
          s.commit()
      except pymysql.err.IntegrityError as e:
          s.rollback()
      except exc.IntegrityError as e:
          s.rollback()
      except Exception as e:
          s.rollback()

      spindle_runin_record = s.query(SpindleRunIn).filter_by(id=spindle_runin_id).first()
      runin_data_records = s.query(RunInData).filter_by(spindleRunIn_id=spindle_runin_id).all()

      for array in runin_data_records:
        spindle_runin_record._runin_data.append(array)

      try:
          s.commit()
      except pymysql.err.IntegrityError as e:
          s.rollback()
      except exc.IntegrityError as e:
          s.rollback()
      except Exception as e:
          s.rollback()
    #end if-else

    s.close()

    return jsonify({
      'status': return_value,
      'message': return_message,
    })


# create InTag data into table
@createTable.route("/createStockInGrids", methods=['POST'])
def create_stockin_grids():
    print("createStockInGrids....")

    request_data = request.get_json()
    print("request_data: ", request_data)

    _work_id = request_data['work_id']    #製令單號
    _empID = request_data['empID']        #員工編號
    _spindle_id = request_data['spindle_id']
    _stockin_date = request_data['stockin_date']        #入庫日
    _stockin_period = request_data['stockin_period']    #效期
    _grid_id = request_data['grid_id']
    _count = request_data['count']

    return_value = True  # true: 資料正確, true
    return_message=''

    s = Session()
    _user = s.query(User).filter_by(emp_id=_empID).first()
    _grid = s.query(Grid).filter_by(id=_grid_id).first()

    new_intag = InTag(work_id=_work_id, user_id=_user.id, spindle_id=_spindle_id, date=_stockin_date, period=_stockin_period, count=_count)

    s.flush()

    _grid._intags_g_i.extend([new_intag])
    _grid.total_size = _grid.total_size + _count
    s.add_all([_grid])

    try:
        s.commit()
    except pymysql.err.IntegrityError as e:
        s.rollback()
    except exc.IntegrityError as e:
        s.rollback()
    except Exception as e:
        s.rollback()

    s.close()

    return jsonify({
      'status': return_value,
      'message': return_message,
    })


# create grid data table
@createTable.route("/createGrid", methods=['POST'])
def create_grid():
  print("createGrid....")

  request_data = request.get_json()
  _spindle_type = request_data['grid_type']
  _spindle_cat = request_data['grid_cat']
  _station = request_data['grid_station']
  _layout = request_data['grid_layout']
  _grid_max_size = request_data['grid_max_size']

  return_value = True
  s = Session()

  existing_grid = s.query(Grid).filter_by(station=_station, layout=_layout).first()
  if existing_grid:
    print("Grid already exists with the same station and layout.")
    return_value = False
  else:
    new_grid = Grid(station=_station, layout=_layout)
    s.add(new_grid)
    s.flush()
    existing_spindle = s.query(Spindle).filter_by(spindle_type=_spindle_type, spindle_cat=_spindle_cat).first()
    if existing_spindle:
      new_grid.isAll = False    #2024-03-30 add
      new_grid._spindles.extend([existing_spindle])
      s.add_all([new_grid])
      #s.commit() #2024-03-30 mark
      print("Existing spindles associated with grid9.")
    else:
      print("No spindle created and associated with new_grid.")
      #return_value = False #2024-03-30 mark
    s.commit()  #2024-03-30 add
  s.close()

  return jsonify({
      'status': return_value
  })
'''

# create process data table
@createTable.route("/createProcess", methods=['POST'])
def create_process():
  print("createProcess....")

  request_data = request.get_json()
  print("request_data:", request_data)

  _begin_time = request_data['begin_time']
  _end_time = request_data['end_time']
  _period_time = request_data['periodTime']
  _user_id = request_data['user_id']
  _order_num = request_data['order_num']
  _id = request_data['id']
  _process_type= request_data['process_type']
  _process_work_time_qty = request_data.get('process_work_time_qty')
  _normal_work_time = request_data.get('normal_work_time')

  print("id:", _id, type(_id))

  s = Session()

  material = s.query(Material).filter(Material.id == _id).first()

  if not material:
    print("error, order_num 不存在!")
    return jsonify({"error": "order_num 不存在"}), 400  # 找不到對應的 Material 記錄
  print("step1...", material.id)

  # 計算期間時間
  time_diff = datetime.strptime(_end_time, "%Y-%m-%d %H:%M:%S") - datetime.strptime(_begin_time, "%Y-%m-%d %H:%M:%S")
  period_time = str(time_diff).split('.')[0]  # 去除微秒，格式為 'HH:MM:SS'
  print("step2-1...")

  # 3️⃣ 直接新增 process 記錄（無論是否已存在）
  new_process = Process(
    material_id = _id,
    user_id = _user_id,
    begin_time = _begin_time,
    end_time = _end_time,
    period_time = period_time,  # 計算期間時間
    process_type = _process_type,
    normal_work_time = _normal_work_time,
    process_work_time_qty = _process_work_time_qty,
  )
  print("step3...")

  s.add(new_process)
  print("step4...")
  s.commit()
  print("step5...")

  s.close()

  return jsonify({
    'status': True,
  })


# copy assemble data table
@createTable.route("/copyAssemble", methods=['POST'])
def copy_assemble():
  print("copyAssemble....")

  request_data = request.get_json()
  print("request_data:", request_data)

  _copy_id = request_data['copy_id']
  _must_qty = request_data.get('must_receive_qty')
  #_show2_ok = request_data['show2_ok']

  print("_copy_id, _must_qty", _copy_id, _must_qty)

  return_value = True
  s = Session()

  # 根據 copy_id 尋找現有的 Material 資料
  #exist = s.query(Assemble).filter_by(id = _copy_id).first()

  # 1. 取得原始 assemble 記錄
  source_assemble = s.query(Assemble).get(_copy_id)

  # 2. 找出符合複製條件的所有 assemble 記錄
  matching_assembles = s.query(Assemble).filter(
      Assemble.material_id == source_assemble.material_id,
      Assemble.process_step_code <= source_assemble.process_step_code
  ).all()

  # 3. 複製這些記錄（排除 id）並新增到 DB
  new_ids = []
  for record in matching_assembles:
    new_record = Assemble(
      material_id=record.material_id,
      material_num=record.material_num,
      material_comment=record.material_comment,
      seq_num=record.seq_num,
      work_num=record.work_num,
      process_step_code=record.process_step_code,
      must_receive_qty = _must_qty,     #應領取數量
      ask_qty=0,

      show1_ok = record.show1_ok,
      show2_ok = 3,   #等待組裝作業
      show3_ok = record.show3_ok,

      update_time= datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      is_copied_from_id=record.id,
    )
    s.add(new_record)
    s.flush()  # 先 flush 以取得新 ID
    new_ids.append(new_record.id)
  # end for loop

  try:
    s.commit()
    print("Process data create successfully.")
  except Exception as e:
    s.rollback()
    print("Error:", str(e))
    return_message = '錯誤! 資料新增複製沒有成功...'
    return_value = False

  s.close()

  return jsonify({
    'assemble_data': new_ids,
  })


# copy assemble data table
@createTable.route("/copyNewAssemble", methods=['POST'])
def copy_new_assemble():
  print("copyNewAssemble....")

  request_data = request.get_json()
  print("request_data:", request_data)

  _copy_id = request_data['copy_id']
  _must_qty = request_data.get('must_receive_qty')

  print("_copy_id, _must_qty", _copy_id, _must_qty)

  return_value = True
  s = Session()

  # 根據 copy_id 尋找現有的 Material 資料
  #exist = s.query(Assemble).filter_by(id = _copy_id).first()

  # 1. 取得原始 assemble 記錄
  source_assemble = s.query(Assemble).get(_copy_id)

  # 2. 找出符合複製條件的所有 assemble 記錄
  matching_assembles = s.query(Assemble).filter(
      Assemble.material_id == source_assemble.material_id,
      Assemble.must_receive_qty == source_assemble.must_receive_qty,
      #Assemble.process_step_code <= source_assemble.process_step_code
  ).all()

  # 3. 複製這些記錄（排除 id）並新增到 DB
  new_ids = []
  for record in matching_assembles:
    abnormal_field=False
    if record.work_num == 'B109':
      process_step_code =3
      #abnormal_field=True            # 2025-07-31 mark
    if record.work_num == 'B110':
      process_step_code =2
    if record.work_num == 'B106':
      process_step_code =1

    new_record = Assemble(
      material_id=record.material_id,
      material_num=record.material_num,
      material_comment=record.material_comment,
      seq_num=record.seq_num,
      work_num=record.work_num,
      process_step_code=process_step_code,
      must_receive_qty = _must_qty,     #應領取數量
      input_disable =False,
      input_end_disable =False,
      input_abnormal_disable = abnormal_field,
      completed_qty = 0,                    #完成數量
      total_completed_qty = 0,
      ask_qty=0,
      update_time= datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      is_copied_from_id=record.id,
    )
    s.add(new_record)
    s.flush()  # 先 flush 以取得新 ID
    new_ids.append(new_record.id)
  # end for loop

  try:
    s.commit()
    print("Process data create successfully.")
  except Exception as e:
    s.rollback()
    print("Error:", str(e))
    return_message = '錯誤! 資料新增複製沒有成功...'
    return_value = False

  s.close()

  return jsonify({
    'assemble_data': new_ids,
  })


# copy material data table when 檢料完成但缺料的情形
@createTable.route("/copyMaterialAndBom", methods=['POST'])
def copy_material_and_bom():
  print("copyMaterialAndBom....")

  request_data = request.get_json()
  print("request_data:", request_data)

  _copy_id = request_data['copy_id']
  _delivery_qty = 0
  _total_delivery_qty = request_data.get('total_delivery_qty')
  _allOk_qty = request_data.get('allOk_qty')
  _show2_ok = request_data['show2_ok']
  _shortage_note = request_data['shortage_note']

  s = Session()

  try:
    # 根據 copy_id 尋找現有的 Material 資料
    existing_material = s.query(Material).filter_by(id=_copy_id).first()
    if not existing_material:
      raise ValueError(f"找不到 ID 為 {_copy_id} 的資料")

    # 建立一個新的 Material 資料，並從現有的資料中複製數據
    new_material = Material(
      abnormal_cause_id=existing_material.abnormal_cause_id,
      order_num=existing_material.order_num,
      material_num=existing_material.material_num,
      material_comment=existing_material.material_comment,
      material_qty=existing_material.material_qty,                        #訂單數量
      material_date = existing_material.material_date,                    #建置日期
      material_delivery_date = existing_material.material_delivery_date,  #交期
      show2_ok = _show2_ok,

      total_delivery_qty = _total_delivery_qty if _total_delivery_qty is not None and _allOk_qty is None else existing_material.total_delivery_qty,
      assemble_qty = _allOk_qty if _allOk_qty is not None and _total_delivery_qty is None else 0,

      shortage_note = _shortage_note,

      update_time= datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      is_copied_from_id=existing_material.id,  # ✅ 設定來源
    )

    s.add(new_material)   # 加入新的 Material 資料紀錄
    s.flush()             # 獲取新的 Material ID (new_id)

    print(f"Duplicated assemble: new_id={new_material.id} from original_id={existing_material.id}")

    # 複製 receive=True 的 Bom 資料
    for bom in [b for b in existing_material._bom if not b.receive]:
      new_bom = Bom(
        material_id=new_material.id,  # 關聯到新的 Material ID
        seq_num=bom.seq_num,
        material_num=bom.material_num,
        material_comment=bom.material_comment,
        req_qty=bom.req_qty,
        pick_qty=bom.pick_qty,
        non_qty=bom.non_qty,
        lack_qty=bom.lack_qty,
        lack=bom.lack,
        start_date=bom.start_date,
        lack_bom_qty=bom.lack_bom_qty,

        receive= bom.receive,

      )
      s.add(new_bom)

    # 複製 Assemble
    for asm in existing_material._assemble:
      new_asm = Assemble(
          material_id=new_material.id,
          material_num=asm.material_num,
          material_comment=asm.material_comment,
          seq_num=asm.seq_num,
          work_num=asm.work_num,
          process_step_code=asm.process_step_code,
          must_receive_qty = _total_delivery_qty,
          user_id='',
      )
      s.add(new_asm)

      # 修改原資料的 must_receive_qty 減去 _delivery_qty
      if asm.must_receive_qty is not None:
        asm.must_receive_qty = _delivery_qty

    s.commit()
    print("Process data create successfully.")

    #_object = {
    #  'id': new_material.id,
    #}

    return jsonify({
      #'material_data': _object,
      'material_data': new_material.to_dict(),
    })

  except Exception as e:
    s.rollback()
    print("Error:", str(e))
    return jsonify({
        'material_data': {},
        'error': '錯誤! 資料新增複製沒有成功...',
        'detail': str(e)
    }), 500
  finally:
    s.close()


# copy material data table
@createTable.route("/copyMaterial", methods=['POST'])
def copy_material():
  print("copyMaterial....")

  request_data = request.get_json()
  print("request_data:", request_data)

  _copy_id = request_data['copy_id']
  _delivery_qty = request_data.get('delivery_qty')
  _total_delivery_qty = request_data.get('total_delivery_qty')
  _allOk_qty = request_data.get('allOk_qty')
  _show2_ok = request_data['show2_ok']
  _shortage_note = request_data['shortage_note']

  return_value = True
  s = Session()

  # 根據 copy_id 尋找現有的 Material 資料
  existing_material = s.query(Material).filter_by(id=_copy_id).first()

  # 建立一個新的 Material 資料，並從現有的資料中複製數據
  new_material = Material(
    abnormal_cause_id=existing_material.abnormal_cause_id,
    order_num=existing_material.order_num,
    material_num=existing_material.material_num,
    material_comment=existing_material.material_comment,
    material_qty=existing_material.material_qty,
    material_date = existing_material.material_date,
    material_delivery_date = existing_material.material_delivery_date,
    isTakeOk = True,  # 已經檢料
    show2_ok = _show2_ok,

    total_delivery_qty = _total_delivery_qty if _total_delivery_qty is not None and _allOk_qty is None else existing_material.total_delivery_qty,
    assemble_qty = _allOk_qty if _allOk_qty is not None and _total_delivery_qty is None else 0,

    shortage_note = _shortage_note,

    update_time= datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    is_copied_from_id=existing_material.id,  # ✅ 設定來源
  )

  # 將新的 Material 資料添加到會話中
  s.add(new_material)
  s.flush()  # 暫存以獲取新的 Material ID (new_id)

  print(f"Duplicated assemble: new_id={new_material.id} from original_id={existing_material.id}")

  # 複製相關的 Bom 資料並將其關聯到新的 Material 資料
  for bom in existing_material._bom:
    new_bom = Bom(
      material_id=new_material.id,  # 關聯到新的 Material ID
      seq_num=bom.seq_num,
      material_num=bom.material_num,
      material_comment=bom.material_comment,
      req_qty=bom.req_qty,
      pick_qty=bom.pick_qty,
      non_qty=bom.non_qty,
      lack_qty=bom.lack_qty,
      receive=bom.receive,
      lack=bom.lack,
      isPickOK=bom.isPickOK,
      start_date=bom.start_date,
    )
    s.add(new_bom)

    # 複製 Assemble

  for asm in existing_material._assemble:
    new_asm = Assemble(
        material_id=new_material.id,
        material_num=asm.material_num,
        material_comment=asm.material_comment,
        seq_num=asm.seq_num,
        work_num=asm.work_num,
        process_step_code=asm.process_step_code,
        must_receive_qty = _total_delivery_qty,
        #ask_qty=asm.ask_qty,
        #total_ask_qty=asm.total_ask_qty,
        #total_ask_qty_end=asm.total_ask_qty_end,
        user_id='',
        #writer_id=asm.writer_id,
        #write_date=asm.write_date,
        #good_qty=asm.good_qty,
        #total_good_qty=asm.total_good_qty,
        #non_good_qty=asm.non_good_qty,
        #meinh_qty=asm.meinh_qty,
        #completed_qty=asm.completed_qty,
        #total_completed_qty=asm.total_completed_qty,
        #reason=asm.reason,
        #confirm_comment=asm.confirm_comment,
        #is_assemble_ok=asm.is_assemble_ok,
        #currentStartTime=asm.currentStartTime
    )
    s.add(new_asm)

    # 修改原資料的 must_receive_qty 減去 _delivery_qty
    if asm.must_receive_qty is not None:
      asm.must_receive_qty = _delivery_qty

  ## 複製異常原因的關聯 (Many-to-Many)
  #for cause in existing_material._abnormal_cause:
  #  new_material._abnormal_cause.append(cause)

  _object = {
    'id': new_material.id,
  }

  try:
    s.commit()
    print("Process data create successfully.")
  except Exception as e:
    s.rollback()
    print("Error:", str(e))
    return_message = '錯誤! 資料新增複製沒有成功...'
    return_value = False

  s.close()

  return jsonify({
    #'status': return_value,
    'material_data': _object,
  })


'''
# create stockout data into table
@createTable.route("/createStockOutGrids", methods=['POST'])
def create_stockout_grids():
    print("createStockOutGrids....")

    request_data = request.get_json()
    print("request_data: ", request_data)

    _work_id = request_data['work_id']    #製令單號
    _empID = request_data['empID']        #員工編號
    _stockout_date = request_data['stockout_date']        #出庫日

    return_value = True  # true: 資料正確
    return_message='資料ok!'

    return_array = []
    return_value = True  # true: 資料正確

    s = Session()

    _user = s.query(User).filter_by(emp_id=_empID).first()
    _intag = s.query(InTag).filter_by(work_id=_work_id).first()

    if (not _user) or ( not _intag):
        return_value = False
        return_message='找不到資料!'

    _intag.isRemoved = False
    #s.query(InTag).filter_by(work_id=_work_id).update(
    #    {'items_per_page': newSetting})

    new_outtag = OutTag(
      intag_id=_intag.id,
      user_id=_user.id,
      date=_stockout_date,
    )

    _intag._outstocks.append(new_outtag)

    s.add(new_outtag)

    try:
        s.commit()
    except pymysql.err.IntegrityError as e:
        s.rollback()
    except exc.IntegrityError as e:
        s.rollback()
    except Exception as e:
        s.rollback()

    s.close()

    print(return_message)

    return jsonify({
        'status': return_value,
    })
'''