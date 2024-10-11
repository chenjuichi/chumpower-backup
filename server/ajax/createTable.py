import math

from flask import Blueprint, jsonify, request
from sqlalchemy import func
from database.tables import User, Process, Permission, Setting, Session
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

import pymysql
from sqlalchemy import exc

createTable = Blueprint('createTable', __name__)

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
  #print("request_data: ", request_data)

  _begin_time = request_data['begin_time']
  _end_time = request_data['end_time']
  _period_time = request_data['periodTime']
  _user_id = request_data['user_id']
  _order_num = request_data['order_num']
  _process_type= request_data['process_type']
  #_process_status = request_data['process_status']

  return_value = True
  return_message = ''
  s = Session()

  record = Process(
    order_num = _order_num,
    user_id = _user_id,
    begin_time = _begin_time,
    end_time = _end_time,
    process_type = _process_type,
    #process_status = _process_status,
  )

  s.add(record)

  try:
    s.commit()
    print("Process data create successfully.")
  except Exception as e:
    s.rollback()
    print("Error:", str(e))
    return_message = '錯誤! 資料新增沒有成功...'
    return_value = False

  s.close()

  return jsonify({
    'status': return_value,
    #'message': return_message,
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