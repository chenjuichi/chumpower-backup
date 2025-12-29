import math
from datetime import datetime

from flask import Blueprint, jsonify, request

from database.tables import User, UserDelegate, Process, Agv, Material, Assemble, Bom, Permission, Product, Process, Setting, Session
from database.p_tables import P_Material, P_Assemble,  P_AbnormalCause, P_Process, P_Product, P_Part

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect
from werkzeug.security import generate_password_hash

from datetime import datetime, timezone

import pymysql
from sqlalchemy import exc
from sqlalchemy import func

createTable = Blueprint('createTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


def _normalize_int(value, default=0):
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
def create_user():
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


@createTable.route('/createDelegate', methods=['POST'])
def create_delegate():
    print("createDelegate....")

    data = request.json
    user_id = data.get('user_id')
    delegate_emp_id = data.get('delegate_emp_id').strip()
    start_date = datetime.fromisoformat(data.get('start_date').replace('Z','')) if data.get('start_date') else None
    end_date = datetime.fromisoformat(data.get('end_date').replace('Z','')) if data.get('end_date') else None
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

  _begin_time = request_data.get('begin_time')
  _end_time = request_data.get('end_time')
  _period_time = request_data.get('periodTime')
  _period_time2 = request_data.get('periodTime2')
  _process_work_time_qty = request_data.get('process_work_time_qty')

  _normal_work_time = request_data.get('normal_work_time')
  _assemble_id = request_data.get('assemble_id')
  _has_started = bool(request_data.get('has_started'))

  _user_id = request_data['user_id']
  _id = request_data['id']
  _process_type= request_data['process_type']

  print("process_type:", _process_type)
  print("id:", _id)
  print("assemble_id:", _assemble_id)
  print("has_started:", _has_started)
  print("begin_time:", _begin_time)
  print("end_time:", _end_time)

  s = Session()

  material = s.query(Material).filter(Material.id == _id).first()

  if not material:
    print("error, order_num 不存在!")
    return jsonify({"error": "order_num 不存在"}), 400  # 找不到對應的 Material 記錄
  print("step1...", material.id)

  if _process_type != 6 and _process_type != 5:
    # 計算期間時間
    if _period_time2:
      period_time = _period_time2
    else:
      time_diff = datetime.strptime(_end_time, "%Y-%m-%d %H:%M:%S") - datetime.strptime(_begin_time, "%Y-%m-%d %H:%M:%S")
      period_time = str(time_diff).split('.')[0]  # 去除微秒，格式為 'HH:MM:SS'
    print("step2-1...", period_time)

  # 3️⃣ 直接新增 process 記錄（無論是否已存在）
  new_process = Process(
    material_id = _id,
    assemble_id = _assemble_id,
    has_started = _has_started,
    user_id = _user_id,
    process_type = _process_type,
    normal_work_time = _normal_work_time,

    begin_time = _begin_time if _process_type != 6 and _process_type != 5 else '',
    end_time = _end_time if _process_type != 6 and _process_type != 5 else '',
    period_time = period_time if _process_type != 6 and _process_type != 5 else '',
    process_work_time_qty = _process_work_time_qty if _process_type != 6 and _process_type != 5 else 0,
  )
  print("step3...")

  s.add(new_process)
  print("step4...")

  s.flush()  # ← 立刻送出 INSERT 並回填自增 id（未提交交易）

  new_process_id = new_process.id  # ← 這裡就拿得到主鍵 id
  print("new_process_id:", new_process_id)

  s.commit()
  print("step5...")

  s.close()

  return jsonify({
    'status': True,
    'process_id': new_process_id
  })


@createTable.route("/createProcessP", methods=['POST'])
def create_process_p():
  print("createProcessP....")

  request_data = request.get_json()
  print("request_data:", request_data)

  _begin_time = request_data.get('begin_time')
  _end_time = request_data.get('end_time')
  _period_time = request_data.get('periodTime')
  _period_time2 = request_data.get('periodTime2')
  _process_work_time_qty = request_data.get('process_work_time_qty')

  _normal_work_time = request_data.get('normal_work_time')
  _assemble_id = request_data.get('assemble_id')
  _has_started = bool(request_data.get('has_started'))

  _user_id = request_data['user_id']
  _id = request_data['id']
  _process_type= request_data['process_type']

  print("process_type:", _process_type)
  print("id:", _id)
  print("assemble_id:", _assemble_id)
  print("has_started:", _has_started)
  print("begin_time:", _begin_time)
  print("end_time:", _end_time)

  s = Session()

  material = s.query(P_Material).filter(P_Material.id == _id).first()

  if not material:
    print("error, order_num 不存在!")
    return jsonify({"error": "order_num 不存在"}), 400  # 找不到對應的 Material 記錄
  print("step1...", material.id)

  if _process_type != 6 and _process_type != 5:
    # 計算期間時間
    if _period_time2:
      period_time = _period_time2
    else:
      time_diff = datetime.strptime(_end_time, "%Y-%m-%d %H:%M:%S") - datetime.strptime(_begin_time, "%Y-%m-%d %H:%M:%S")
      period_time = str(time_diff).split('.')[0]  # 去除微秒，格式為 'HH:MM:SS'
    print("step2-1...", period_time)

  # 3️⃣ 直接新增 P_Process 記錄（無論是否已存在）
  new_process = P_Process(
    material_id = _id,
    assemble_id = _assemble_id,
    has_started = _has_started,
    user_id = _user_id,
    process_type = _process_type,
    normal_work_time = _normal_work_time,

    begin_time = _begin_time if _process_type != 6 and _process_type != 5 else '',
    end_time = _end_time if _process_type != 6 and _process_type != 5 else '',
    period_time = period_time if _process_type != 6 and _process_type != 5 else '',
    process_work_time_qty = _process_work_time_qty if _process_type != 6 and _process_type != 5 else 0,
  )
  print("step3...")

  s.add(new_process)
  print("step4...")

  s.flush()  # ← 立刻送出 INSERT 並回填自增 id（未提交交易）

  new_process_id = new_process.id  # ← 這裡就拿得到主鍵 id
  print("new_process_id:", new_process_id)

  s.commit()
  print("step5...")

  s.close()

  return jsonify({
    'status': True,
    'process_id': new_process_id
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


@createTable.route("/copyAssembleForDifference", methods=['POST'])
def copy_assemble_for_difference():
  print("copyAssembleForDifference....")

  request_data = request.get_json()
  print("request_data:", request_data)

  _copy_id = request_data['copy_id']
  _must_qty = request_data.get('must_receive_qty')
  _pre_must_qty = request_data.get('pre_must_receive_qty')

  print("_copy_id, _must_qty", _copy_id, _must_qty)

  return_value = True
  s = Session()

  # 根據 copy_id 尋找現有的 Material 資料
  #exist = s.query(Assemble).filter_by(id = _copy_id).first()


  # 1. 取得原始 assemble 記錄
  source_assemble = s.query(Assemble).get(_copy_id)

  """
  # 2. 找出符合複製條件的所有 assemble 記錄
  matching_assembles = s.query(Assemble).filter(
      Assemble.material_id == source_assemble.material_id,
      Assemble.must_receive_qty == source_assemble.must_receive_qty,
      #Assemble.process_step_code <= source_assemble.process_step_code
  ).all()
  """
  k = _copy_id
  h = k + 1
  m = k + 2  # 若之後也要用，可以一起放進 IN

  ids = [k, h]            # 只要 k、h
  matching_assembles = (
    s.query(Assemble)
     .filter(
        Assemble.material_id == source_assemble.material_id,
        Assemble.update_time == source_assemble.update_time,
        Assemble.id.in_(ids)          # 「包含 k 或 h」
     )
     .order_by(Assemble.id.asc())
     .all()
  )
  print("matching_assembles:",matching_assembles)

  # 2-1. 先更新這些舊紀錄的 must_receive_end_qty = pre_must_receive_qty
  #      （如果 pre_must_receive_qty 有帶進來）
  if _pre_must_qty is not None:
    try:
      pre_must_val = int(_pre_must_qty)
    except (TypeError, ValueError):
      pre_must_val = 0

    for rec in matching_assembles:
      print(f"update old rec(id={rec.id}) must_receive_end_qty ->", pre_must_val)
      rec.must_receive_end_qty = pre_must_val

  # 3. 複製這些記錄（排除 id）並新增到 DB
  print("len(matching_assembles):", len(matching_assembles))
  new_ids = []
  for record in matching_assembles:
    #abnormal_field=False
    """
    if record.work_num == 'B109':
      process_step_code =3
      ok2=3
      ok3=3
    if record.work_num == 'B110':
      process_step_code =2
      ok2=5
      ok3=5
    if record.work_num == 'B106':
      process_step_code =1
      ok2=7
      ok3=7
    else:
      # 如果不是這三種工作中心，就略過，不新增
      print("skip record.id =", record.id, "work_num =", record.work_num)
      continue
    """

    if record.work_num == 'B109':
        process_step_code = 3
        ok2 = 3
        ok3 = 3
    elif record.work_num == 'B110':
        process_step_code = 2
        ok2 = 5
        ok3 = 5
    elif record.work_num == 'B106':
        process_step_code = 1
        ok2 = 7
        ok3 = 7
    else:
        # 如果不是這三種工作中心，就略過，不新增
        print("skip record.id =", record.id, "work_num =", record.work_num)
        continue

    abnormal_field=False

    new_record = Assemble(
      material_id=record.material_id,
      material_num=record.material_num,
      material_comment=record.material_comment,
      seq_num=record.seq_num,
      work_num=record.work_num,
      process_step_code=process_step_code,
      must_receive_qty = _must_qty,     #應領取數量
      must_receive_end_qty=_must_qty,
      input_disable =False,
      input_end_disable =False,
      input_abnormal_disable = abnormal_field,
      completed_qty = 0,                    #完成數量
      total_completed_qty = 0,
      ask_qty=0,
      update_time= datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      is_copied_from_id=record.id,
      show2_ok=ok2,
      show3_ok=ok3,
    )
    s.add(new_record)
    s.flush()  # 先 flush 以取得新 ID
    print("new_record.id:", new_record.id)
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

  matching_assembles = []
  """
  bb = source_assemble
  while True:
      aa = s.get(Assemble, bb.id + 1)  # 下一筆（相鄰 id）
      if not aa:
          break
      if (aa.material_id == source_assemble.material_id) and (aa.update_time == source_assemble.update_time):
        matching_assembles.append(aa)
        bb = aa   # 往下一筆繼續找
      else:
        break
  """

  """
    # 2. 找出符合複製條件的所有 assemble 記錄
    matching_assembles = s.query(Assemble).filter(
        Assemble.material_id == source_assemble.material_id,
        Assemble.must_receive_qty == source_assemble.must_receive_qty,
        #Assemble.process_step_code <= source_assemble.process_step_code
    ).all()
  """


  k = _copy_id
  h = k - 1
  m = k + 1  # 若之後也要用，可以一起放進 IN

  ids = [k, h, m]            # 只要 k、h
  matching_assembles = (
    s.query(Assemble)
     .filter(
        Assemble.material_id == source_assemble.material_id,
        #Assemble.is_copied_from_id == source_assemble.update_time,
        Assemble.id.in_(ids)          # 「包含 k 或 h」
     )
     #.order_by(Assemble.id.asc())
     .all()
  )

  print("matching_assembles:",matching_assembles)

  # 3. 複製這些記錄（排除 id）並新增到 DB
  new_ids = []
  for record in matching_assembles:
    abnormal_field=False
    if record.work_num == 'B109':
      process_step_code =3
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
      isAssembleStationShow=False,
      must_receive_qty = _must_qty,         #應領取數量
      must_receive_end_qty = _must_qty,     #應完成數量
      input_disable =False,
      input_end_disable =False,

      alarm_enable=False,
      isAssembleFirstAlarm=False,

      input_abnormal_disable = abnormal_field,
      completed_qty = 0,                    #完成數量
      total_completed_qty = 0,
      ask_qty=0,
      update_time= datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      is_copied_from_id=record.id,
      show2_ok=3 if (record.work_num=='109') else (5 if (record.work_num=='110') else 7),
      show3_ok=3 if (record.work_num=='109') else (5 if (record.work_num=='110') else 7),
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


@createTable.route("/createProduct", methods=["POST"])
def create_product():
    """
    支援：
    1) 單筆：JSON 直接是一個物件
    2) 多筆：{"items": [ {...}, {...} ]}
    欄位（每筆 item）：
      - material_id (必填, int, 必須存在於 material)
      - delivery_qty (選填, int, default 0)
      - assemble_qty (選填, int, default 0)
      - allOk_qty (選填, int, default 0)
      - good_qty (選填, int, default 0)
      - non_good_qty (選填, int, default 0)
      - reason (選填, str)
      - confirm_comment (選填, str)
    批次語意：任何一筆驗證錯誤 → 整批 rollback。
    回傳：{ status, created, items: [ {id, material_id, ...} ] }
    """
    s = Session()
    try:
        #payload = request.get_json(silent=True) or {}
        payload = request.get_json()

        # 兼容兩種型態：物件 or {items: [..]}
        raw_items = payload.get("items", None)
        if raw_items is None:
            # 當作單筆物件
            raw_items = [payload]

        # 基本型態檢查
        if not isinstance(raw_items, list) or len(raw_items) == 0:
            return jsonify({"status": False, "error": "payload 應為物件或 {items: [...]}，且不可為空"}), 400

        # 先做前置驗證（material 存在性），有任何錯誤→直接 400
        errors = []
        material_ids = [it.get("material_id") for it in raw_items]
        # 必須都是 int
        try:
            material_ids_int = [int(mid) for mid in material_ids]
        except (TypeError, ValueError):
            return jsonify({"status": False, "error": "material_id 必須是整數"}), 400

        # 查詢存在的 materials
        exist_mid_set = set([m.id for m in s.query(Material.id).filter(Material.id.in_(material_ids_int)).all()])
        for idx, it in enumerate(raw_items):
            mid = it.get("material_id")
            if mid is None:
                errors.append({"index": idx, "error": "material_id 為必填"})
                continue
            if int(mid) not in exist_mid_set:
                errors.append({"index": idx, "error": f"material_id {mid} 不存在"})

        if errors:
            return jsonify({"status": False, "errors": errors}), 400

        # 通過驗證 → 建立資料
        created_rows = []
        for it in raw_items:
            p = Product(
                material_id      = int(it.get("material_id")),
                process_id       = int(it.get("process_id")),
                delivery_qty     = _normalize_int(it.get("delivery_qty"), 0),
                assemble_qty     = _normalize_int(it.get("assemble_qty"), 0),
                allOk_qty        = _normalize_int(it.get("allOk_qty"), 0),
                good_qty         = _normalize_int(it.get("good_qty"), 0),
                non_good_qty     = _normalize_int(it.get("non_good_qty"), 0),
                reason           = (it.get("reason") or None),
                confirm_comment  = (it.get("confirm_comment") or None),
            )
            s.add(p)
            created_rows.append(p)

        s.commit()

        # 組回傳（expire_on_commit=False，id 可直接讀）
        items = []
        for p in created_rows:
            items.append({
                "id": p.id,
                "material_id": p.material_id,
                "delivery_qty": p.delivery_qty,
                "assemble_qty": p.assemble_qty,
                "allOk_qty": p.allOk_qty,
                "good_qty": p.good_qty,
                "non_good_qty": p.non_good_qty,
                "reason": p.reason,
                "confirm_comment": p.confirm_comment,
                "create_at": getattr(p, "create_at", None).isoformat() if getattr(p, "create_at", None) else None,
            })

        return jsonify({
           "status": True,
           "created": len(items),
           "items": items
        })
        #}) , 201

    except SQLAlchemyError as e:
        s.rollback()
        return jsonify({"status": False, "error": str(e)}), 500
    except Exception as e:
        s.rollback()
        return jsonify({"status": False, "error": str(e)}), 500
    finally:
        s.close()


def _int_or_error(value, name):
    try:
        iv = int(value)
        if iv < 0:
            raise ValueError
        return iv
    except Exception:
        raise ValueError(f"{name} 必須是非負整數")


@createTable.route("/copyNewIdAssemble", methods=['POST'])
def copy_new_id_assemble():
    """
    POST JSON:
    {
        "copy_assemble_id": 123,
        "copy_assemble_must_receive_qty": 10,
        "copy_assemble_process_step_code": 21
    }
    """
    payload = request.get_json(silent=True) or {}
    #payload = request.get_json()

    try:
        src_id = _int_or_error(payload.get("copy_assemble_id"), "copy_assemble_id")
        new_must_qty = _int_or_error(payload.get("copy_assemble_must_receive_qty"), "copy_assemble_must_receive_qty")
        new_step_code = _int_or_error(payload.get("copy_assemble_process_step_code"), "copy_assemble_process_step_code")
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    s = Session()
    try:
        # 1) 讀來源
        src: Assemble | None = s.query(Assemble).filter(Assemble.id == src_id).one_or_none()
        if not src:
            return jsonify({"ok": False, "error": f"來源 assemble id {src_id} 不存在"}), 404

        # 2) 建立新物件：先將來源轉 dict，再挑欄位
        #    只複製普通欄位；不帶入主鍵 id / 自動時間 / 關聯 backref
        #    下列欄位名稱以你的 tables.py 為準
        clone_fields = {
            "material_id": src.material_id,
            "material_num": src.material_num,
            "material_comment": src.material_comment,
            "seq_num": src.seq_num,
            "work_num": src.work_num,

            # 保留原本數值（你有需要可改成重置 0）
            "Incoming1_Abnormal": src.Incoming1_Abnormal,
            #"ask_qty": 0,
            #"total_ask_qty": 0,
            #"total_ask_qty_end": 0,
            #"abnormal_qty": 0,
            "user_id": '',
            "writer_id": src.writer_id,
            "write_date": src.write_date,
            "good_qty": src.good_qty,
            "total_good_qty": src.total_good_qty,
            "non_good_qty": src.non_good_qty,
            "meinh_qty": src.meinh_qty,
            #"completed_qty": 0,
            "total_completed_qty": src.total_completed_qty,
            "reason": src.reason,
            "confirm_comment": src.confirm_comment,
            "is_assemble_ok": src.is_assemble_ok,
            #"currentStartTime": src.currentStartTime,
            #"currentEndTime": src.currentEndTime,
            #"input_disable": src.input_disable,
            #"input_end_disable": src.input_end_disable,
            "input_abnormal_disable": src.input_abnormal_disable,
            "isAssembleStationShow": src.isAssembleStationShow,
            "isWarehouseStationShow": getattr(src, "isWarehouseStationShow", False),
            "alarm_enable": src.alarm_enable,
            "alarm_message": src.alarm_message,
            "isAssembleFirstAlarm": src.isAssembleFirstAlarm,
            "isAssembleFirstAlarm_message": src.isAssembleFirstAlarm_message,
            "isAssembleFirstAlarm_qty": src.isAssembleFirstAlarm_qty,
            "whichStation": src.whichStation,
            "show1_ok": src.show1_ok,
            "show2_ok": 3 if (src.work_num=='109') else (5 if (src.work_num=='110') else 7),
            "show3_ok": 3 if (src.work_num=='109') else (5 if (src.work_num=='110') else 7),

            # 會在下方覆寫的新值
            # "process_step_code": src.process_step_code,
            # "must_receive_qty": src.must_receive_qty,
            # "must_receive_end_qty": src.must_receive_end_qty,

            # 溯源
            "is_copied_from_id": src.id,

            # 時間戳（若你有 middleware 統一寫入可拿掉）
            #"update_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 3) 覆寫需求欄位
        clone_fields["process_step_code"] = new_step_code
        clone_fields["must_receive_qty"] = new_must_qty
        clone_fields["must_receive_end_qty"] = new_must_qty

        # 4) 生成並寫入
        new_rec = Assemble(**clone_fields)
        s.add(new_rec)
        s.commit()

        # 5) 取新 id 與內容
        new_id = new_rec.id
        # expire_on_commit=False 已設定，直接可取
        return jsonify({
            "ok": True,
            "new_assemble_id": new_id,
            "data": new_rec.get_dict()
        #}), 201
        })

    except Exception as e:
        s.rollback()
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
    finally:
        s.close()


@createTable.route("/copyDeliveryRecord", methods=['POST'])
def copy_delivery_record():
    print("copyDeliveryRecord....")

    request_data = request.get_json() or {}
    print("request_data:", request_data)

    assemble_id = request_data.get("assemble_id")           # 要複製哪一筆 assemble.id
    new_total_completed = request_data.get("total_completed_qty")
    new_completed = request_data.get("completed_qty")

    # 參數檢查
    if assemble_id is None:
        return jsonify({
            "return_value": False,
            "message": "缺少 assemble_id 參數"
        }), 400

    try:
        new_total_completed = int(new_total_completed)
        new_completed = int(new_completed)
    except (TypeError, ValueError):
        return jsonify({
            "return_value": False,
            "message": "total_completed_qty / completed_qty 必須是整數"
        }), 400

    s = Session()
    try:
        with s.begin():
            # 1. 取得原始 assemble 記錄
            assemble = s.get(Assemble, assemble_id)
            if not assemble:
                return jsonify({
                    "return_value": False,
                    "message": f"找不到 assemble.id = {assemble_id}"
                }), 404

            # 先記錄原始值，避免被覆蓋之後無法計算差額
            orig_total_completed = assemble.total_completed_qty or 0
            orig_completed = assemble.completed_qty or 0

            # 檢查拆分數量是否合理
            if new_total_completed < 0 or new_completed < 0:
                return jsonify({
                    "return_value": False,
                    "message": "total_completed_qty / completed_qty 不可為負數"
                }), 400

            if new_total_completed > orig_total_completed or new_completed > orig_completed:
                return jsonify({
                    "return_value": False,
                    "message": "拆分數量不可大於原本的 total_completed_qty / completed_qty"
                }), 400

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 2. 建立「新紀錄」
            #    其他欄位都沿用原資料，只調整指定欄位：
            #    new_assemble.total_completed_qty = 原本 - 傳入 total_completed_qty
            #    new_assemble.completed_qty       = 原本 - 傳入 completed_qty
            #    new_assemble.isAssembleStationShow = False
            #    new_assemble.is_copied_from_id = 原始 id (方便追蹤來源)
            remain_total_completed = orig_total_completed - new_total_completed
            remain_completed = orig_completed - new_completed

            # 3. 建立「新紀錄」，先複製所有欄位
            mapper = inspect(Assemble)

            new_assemble = Assemble()
            for col in mapper.columns:
                col_name = col.key
                # 不要複製主鍵＆create_at，讓 DB 自己長
                if col_name in ("id", "create_at"):
                    continue
                setattr(new_assemble, col_name, getattr(assemble, col_name))

            # 4. 接著覆寫指定要改的欄位
            new_assemble.total_completed_qty = remain_total_completed
            new_assemble.completed_qty = remain_completed
            new_assemble.isAssembleStationShow = False
            new_assemble.is_copied_from_id = assemble.id
            new_assemble.update_time = now_str

            s.add(new_assemble)
            # with s.begin(): 會自動 commit

        return jsonify({
            "return_value": True,
            "message": "ok",
            "source_id": assemble_id,
            "new_id": new_assemble.id,
        })

    except Exception as e:
        s.rollback()
        print("copyDeliveryRecord error:", e)
        return jsonify({
            "return_value": False,
            "message": f"copyDeliveryRecord 發生錯誤: {e}"
        }), 500
    finally:
        s.close()

