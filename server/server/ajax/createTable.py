import math

import json

from datetime import datetime

from flask import Blueprint, jsonify, request

from database.tables import default_process_steps
from database.tables import User, UserDelegate, Process, Agv, Material, Assemble, Bom, Permission, Product, Process, Setting, Session
from database.p_tables import P_Material, P_Assemble,  P_AbnormalCause, P_Process, P_Product, P_Part

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect
from werkzeug.security import generate_password_hash
from sqlalchemy import func, or_

from datetime import datetime, timezone

#import pymysql
from sqlalchemy import exc
from sqlalchemy import func

createTable = Blueprint('createTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


def _int_or_error(value, name):
  try:
    iv = int(value)
    if iv < 0:
      raise ValueError
    return iv
  except Exception:
    raise ValueError(f"{name} 必須是非負整數")


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


# 20260722版
# createProcess：
# 1. type=6 空白堆高機紀錄防重複
# 2. 使用 material row lock，避免多人同時 INSERT
# 3. 保留 type=2/3/5 與 21/22/23 原有流程
@createTable.route("/createProcess", methods=['POST'])
def create_process():
    print("createProcess....")

    request_data = request.get_json(silent=True) or {}

    _begin_time = request_data.get('begin_time')
    _end_time = request_data.get('end_time')
    _period_time = request_data.get('periodTime')
    _period_time2 = request_data.get('periodTime2')
    _process_work_time_qty = request_data.get('process_work_time_qty')

    _normal_work_time = request_data.get('normal_work_time')

    _assemble_id = request_data.get('assemble_id')
    _has_started = bool(request_data.get('has_started'))

    _user_id = str(request_data.get('user_id') or '').strip()

    _id = request_data.get('id')
    _process_type = request_data.get('process_type')

    #print("process_type:", _process_type)
    #print("id:", _id)
    #print("assemble_id:", _assemble_id)
    #print("has_started:", _has_started)
    #print("begin_time:", _begin_time)
    #print("end_time:", _end_time)

    # ------------------------------------------------------------
    # AGV / 堆高機送達組裝區後，釋放到 Begin
    # ------------------------------------------------------------
    def release_to_assemble_begin(session, material):
        #AGV / 堆高機送達組裝區後，將 material 與 assemble
        #同步釋放到 Begin.vue。

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # --------------------------------------------------------
        # 1. material：進入組裝區
        # --------------------------------------------------------
        material.isShow = True
        material.isTakeOk = True
        material.isAssembleStationShow = True
        material.whichStation = 2

        material.show1_ok = 2
        material.show2_ok = 3
        material.show3_ok = 3

        material.isOpen = False
        material.isOpenEmpId = ''
        material.hasStarted = False
        material.startStatus = 1

        material.update_time = now_str

        # 尚未設定工序時，Begin 顯示 B109 樣板及「+工序」
        has_scheduled_rows = (session.query(Assemble.id)
            .filter(
                Assemble.material_id == material.id,
                Assemble.schedule_id.isnot(None),
                Assemble.schedule_id > 0
            )
            .first()
            is not None
        )

        material.process_step_enable = has_scheduled_rows

        # --------------------------------------------------------
        # 2. assemble：同步釋放到 Begin
        # --------------------------------------------------------
        assemble_rows = (session.query(Assemble)
            .filter(Assemble.material_id == material.id)
            .filter(
                or_(
                    Assemble.reason.is_(None),
                    Assemble.reason != 'B110_DONE_COPY'
                )
            )
            .order_by(Assemble.id.asc())
            .all()
        )

        # 有排程時，只開啟 schedule_id > 0 的工序列。
        # 尚未排程時，只開啟一筆 B109 樣板列。
        template_opened = False

        for row in assemble_rows:
            work_num = (row.work_num or '').strip()
            schedule_id = int(row.schedule_id or 0)
            step = int(row.process_step_code or 0)

            # 已送入庫、待入庫或已完成的歷史列不可重新開啟
            if bool(row.isWarehouseStationShow):
                continue

            if int(row.show2_ok or 0) >= 9:
                continue

            should_show = False

            if has_scheduled_rows:
                # 已設定工序，只顯示有效排程列
                should_show = (
                    schedule_id > 0
                    and step > 0
                    and work_num in ('B109', 'B110')
                )
            else:
                # 尚未按 +工序，只顯示唯一一筆 B109 樣板
                if (
                    not template_opened
                    and work_num == 'B109'
                    and schedule_id == 0
                ):
                    should_show = True
                    template_opened = True

                    # 樣板列必須保留正確 step，Begin 才不會排除
                    if step <= 0:
                        row.process_step_code = 3

            if not should_show:
                row.isAssembleStationShow = False
                row.isWarehouseStationShow = False
                continue

            row.isAssembleStationShow = True
            row.isWarehouseStationShow = False

            row.whichStation = 2
            row.show1_ok = 2

            if work_num == 'B110':
                row.show2_ok = 5
                row.show3_ok = 5
            else:
                row.show2_ok = 3
                row.show3_ok = 3

            row.input_disable = False
            row.input_end_disable = False
            row.input_abnormal_disable = False
            row.input_allOk_disable = False

            row.currentStartTime = None
            row.currentEndTime = None
            row.update_time = now_str

        print(
            '[release_to_assemble_begin]',
            {
                'material_id': material.id,
                'has_scheduled_rows': has_scheduled_rows,
                'assemble_count': len(assemble_rows),
            }
        )

    # ------------------------------------------------------------
    # 參數檢查
    # ------------------------------------------------------------
    if (not _user_id or _id is None or _process_type is None):
        return jsonify({
            "status": False,
            "message":
                "missing params: user_id / id / process_type"
        }), 400

    try:
        material_id_int = int(_id)
        process_type_int = int(_process_type)
        assemble_id_int = int(_assemble_id or 0)

        process_work_time_qty_int = int(_process_work_time_qty or 0)

    except (TypeError, ValueError):
        return jsonify({
            "status": False,
            "message":
                "invalid params: id / process_type / "
                "assemble_id / process_work_time_qty"
        }), 400

    period_time = ''

    s = Session()

    try:
        # --------------------------------------------------------
        # 鎖定 material
        #
        # 防止 A、B 電腦同時對同一 material 建立 type=6。
        # --------------------------------------------------------
        material = (s.query(Material)
            .filter(Material.id == material_id_int)
            .with_for_update()
            .one_or_none()
        )

        if not material:
            s.rollback()

            print("error, material 不存在:", material_id_int)

            return jsonify({
                "status": False,
                "message":
                    f"material_id={material_id_int} 不存在"
            }), 400

        print("[createProcess] material locked:", material.id)

        # --------------------------------------------------------
        # type=2 / 5 / 19
        # 同一開始時間只建立一次
        # --------------------------------------------------------
        if process_type_int in {2, 5, 19}:

            has_begin_time = bool(str(_begin_time or "").strip())

            if has_begin_time:
                existed_transport = (s.query(Process)
                    .filter(
                        Process.material_id == material_id_int,
                        Process.process_type == process_type_int,
                        Process.begin_time == _begin_time
                    )
                    .order_by(Process.id.asc())
                    .first()
                )

                if existed_transport:
                    s.commit()

                    print("[createProcess] duplicate transport skipped:", existed_transport.id)

                    return jsonify({
                        "status": True,
                        "created": False,
                        "process_id": existed_transport.id,
                        "skipped": True,
                        "duplicate": True,
                        "message": "相同搬運開始時間已存在，不重複新增"
                    }), 200

        # --------------------------------------------------------
        # process_type=6：
        # 堆高機運行（組裝區 -> 成品區）
        # --------------------------------------------------------
        if process_type_int == 6:
            # ----------------------------------------------------
            # 已經有成品入庫紀錄，不再補 type=6
            # ----------------------------------------------------
            has_stockin = (s.query(Process.id)
                .filter(
                    Process.material_id
                    == material_id_int,

                    Process.process_type == 31
                )
                .first()
            )

            if has_stockin:
                s.commit()

                print("[createProcess] type=6 skipped, stockin already exists:", material_id_int)

                return jsonify({
                    "status": True,
                    "created": False,
                    "process_id": None,
                    "skipped": True,
                    "duplicate": False,
                    "message":
                        "此工單已成品入庫，"
                        "不再建立 process_type=6"
                }), 200

            # ----------------------------------------------------
            # 已有尚未執行的空白 type=6，保留最早一筆
            # ----------------------------------------------------
            existed_type6 = (s.query(Process)
                .filter(
                    Process.material_id == material_id_int,
                    Process.process_type == 6,

                    or_(Process.begin_time.is_(None), Process.begin_time == ''),

                    or_(Process.end_time.is_(None), Process.end_time == ''),

                    func.coalesce(Process.elapsedActive_time, 0) == 0,

                    or_(
                        Process.has_started.is_(False),
                        Process.has_started.is_(None)
                    )
                )
                .order_by(Process.create_at.asc(), Process.id.asc())
                .first()
            )

            if existed_type6:
                s.commit()

                print(
                    "[createProcess] duplicate type=6 "
                    "skipped:",
                    {
                        "material_id": material_id_int,
                        "existing_process_id":
                            existed_type6.id
                    }
                )

                return jsonify({
                    "status": True,
                    "created": False,
                    "process_id":
                        existed_type6.id,
                    "skipped": True,
                    "duplicate": True,
                    "message":
                        "已有堆高機運行"
                        "(組裝區->成品區)紀錄，"
                        "不重複新增"
                }), 200

        # --------------------------------------------------------
        # process_type=2：
        # AGV 備料區 -> 組裝區
        #
        # process_type=5：
        # 堆高機 備料區 -> 組裝區
        # --------------------------------------------------------
        if process_type_int in (2, 5):
            release_to_assemble_begin(
                session=s,
                material=material
            )

        # --------------------------------------------------------
        # process_type=3：
        # AGV 組裝區 -> 成品區防重複
        #
        # station3_agv_end 可能因 Socket 重送而執行多次。
        # 同一 material 原則上只允許一筆 type=3。
        # --------------------------------------------------------
        if process_type_int == 3:

            if assemble_id_int <= 0:
                s.rollback()

                return jsonify({
                    "status": False,
                    "created": False,
                    "message":
                        "process_type=3 必須提供 assemble_id"
                }), 400

            # 已經入庫，不再建立 AGV 搬運
            has_stockin = (
                s.query(Process.id)
                .filter(
                    Process.material_id == material_id_int,
                    Process.process_type == 31
                )
                .first()
            )

            if has_stockin:
                s.commit()

                return jsonify({
                    "status": True,
                    "created": False,
                    "process_id": None,
                    "skipped": True,
                    "duplicate": False,
                    "message":
                        "此工單已完成入庫，不再建立 process_type=3"
                }), 200

            # 同 material 已有 type=3，不重複建立
            existed_type3 = (s.query(Process)
                .filter(
                    Process.material_id == material_id_int,
                    Process.process_type == 3
                )
                .order_by(Process.id.asc())
                .first()
            )

            if existed_type3:
                s.commit()

                print(
                    "[createProcess] duplicate type=3 skipped:",
                    {
                        "material_id": material_id_int,
                        "assemble_id": assemble_id_int,
                        "existing_process_id":
                            existed_type3.id,
                    }
                )

                return jsonify({
                    "status": True,
                    "created": False,
                    "process_id":
                        existed_type3.id,
                    "skipped": True,
                    "duplicate": True,
                    "message":
                        "此工單已有AGV運行"
                        "(組裝區->成品區)紀錄，不重複新增"
                }), 200

        # --------------------------------------------------------
        # 計算 period_time
        #
        # type=5 要保留時間與 period_time
        # type=6 為空白搬運通知，不計算
        # --------------------------------------------------------
        if process_type_int != 6:
            if _period_time2:
                period_time = str(
                    _period_time2
                )

            elif _period_time:
                period_time = str(_period_time)

            elif _begin_time and _end_time:
                begin_dt = datetime.strptime(str(_begin_time),  "%Y-%m-%d %H:%M:%S")

                end_dt = datetime.strptime(str(_end_time),  "%Y-%m-%d %H:%M:%S")

                time_diff = end_dt - begin_dt

                period_time = str(time_diff).split('.')[0]

            else:
                #period_time = '00:00:00'
                # 只有開始時間(尚未結束)
                period_time = ''

            print("period_time:", period_time)

        # --------------------------------------------------------
        # 不重複建立同一員工、同 assemble、同製程的
        # active process
        # --------------------------------------------------------
        if (
            process_type_int in (21, 22, 23)
            and _has_started
        ):
            existed_active = (s.query(Process)
                .filter(
                    Process.material_id
                    == material_id_int,

                    Process.assemble_id
                    == assemble_id_int,

                    Process.process_type
                    == process_type_int,

                    Process.user_id
                    == _user_id,

                    Process.has_started.is_(True),

                    Process.end_time.is_(None)
                )
                .order_by(
                    Process.id.asc()
                )
                .first()
            )

            if existed_active:
                s.commit()

                print(
                    "[createProcess] active duplicate "
                    "skipped:",
                    existed_active.id
                )

                return jsonify({
                    "status": True,
                    "created": False,
                    "process_id":
                        existed_active.id,
                    "skipped": True,
                    "duplicate": True,
                    "message":
                        "此員工此工序已開始，"
                        "不重複新增"
                }), 200

        # --------------------------------------------------------
        # 新增 process
        #
        # type=5：
        # 保留 begin/end/period_time
        #
        # type=6：
        # begin_time/end_time 使用 NULL
        # --------------------------------------------------------
        '''
        new_process = Process(
            material_id=material_id_int,
            assemble_id=assemble_id_int,
            has_started=_has_started,
            user_id=_user_id,
            process_type=process_type_int,
            normal_work_time=_normal_work_time,

            begin_time=(
                _begin_time
                if process_type_int != 6
                else None
            ),

            end_time=(
                _end_time
                if process_type_int != 6
                else None
            ),

            period_time=(
                period_time
                if process_type_int != 6
                else ''
            ),

            process_work_time_qty=(
                process_work_time_qty_int
                if process_type_int != 6
                else 0
            ),
        )
        '''
        #
        new_process = Process(
            material_id=material_id_int,
            assemble_id=assemble_id_int,

            has_started=(
                False
                if process_type_int in (2, 3, 5)
                and _end_time
                else _has_started
            ),

            user_id=_user_id,
            process_type=process_type_int,
            normal_work_time=_normal_work_time,

            begin_time=(
                _begin_time
                if process_type_int != 6
                else None
            ),

            end_time=(
                _end_time
                if process_type_int != 6
                else None
            ),

            period_time=(
                period_time
                if process_type_int != 6
                else ''
            ),

            process_work_time_qty=(
                process_work_time_qty_int
                if process_type_int != 6
                else 0
            ),

            is_pause=(
                True
                if process_type_int in (2, 3, 5)
                and _end_time
                else False
            ),

            pause_started_at=None,
        )
        #

        s.add(new_process)
        s.flush()

        new_process_id = new_process.id

        print("[createProcess] new_process_id:", new_process_id)

        '''
        # --------------------------------------------------------
        # AGV 組裝區 -> 成品區
        # 送達後開啟 Warehouse 待入庫
        # --------------------------------------------------------
        if (
            process_type_int == 3
            and assemble_id_int > 0
        ):
            updated = (
                s.query(Assemble)
                .filter(
                    Assemble.id
                    == assemble_id_int,

                    Assemble.material_id
                    == material_id_int,

                    Assemble.process_step_code == 0,

                    Assemble.isAssembleStationShow
                    .is_(True),

                    Assemble.isWarehouseStationShow
                    .is_(False),

                    Assemble.show2_ok.in_(
                        [9, 10]
                    )
                )
                .update({
                    Assemble.isWarehouseStationShow:
                        True,

                    Assemble.input_allOk_disable:
                        False,

                    Assemble.update_time:
                        datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                }, synchronize_session=False)
            )

            print(
                "[createProcess] AGV2 -> "
                "Warehouse update rows =",
                updated
            )
        '''
        #
        if process_type_int == 3:
            print(
                "[createProcess] AGV2 arrived:",
                {
                    "material_id":
                        material_id_int,
                    "assemble_id":
                        assemble_id_int,
                    "process_id":
                        new_process_id,
                    "begin_time":
                        _begin_time,
                    "end_time":
                        _end_time,
                    "period_time":
                        period_time,
                }
            )
        #

        s.commit()

        print(
            "createProcess done:",
            {
                "process_id": new_process_id,
                "material_id": material_id_int,
                "process_type": process_type_int,
            }
        )

        return jsonify({
            "status": True,
            "created": True,
            "process_id": new_process_id,
            "skipped": False,
            "duplicate": False
        }), 200

    except Exception as e:
        s.rollback()

        print(
            "createProcess ERROR:",
            repr(e)
        )

        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:
        s.close()


# copy assemble data table
@createTable.route("/copyAssemble", methods=['POST'])
def copy_assemble():
  print("copyAssemble....")

  request_data = request.get_json()
  #print("request_data:", request_data)

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
      #
      schedule_id=record.schedule_id,
      #
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

  data = request.get_json() or {}

  copy_id = data.get('copy_id')
  abnormal_qty = data.get('must_receive_qty')
  pre_must_qty = data.get('pre_must_receive_qty')

  s = Session()

  try:
    copy_id = int(copy_id)
    abnormal_qty = int(abnormal_qty or 0)
    pre_must_qty = int(pre_must_qty or 0)

    if abnormal_qty <= 0:
      return jsonify({
        'status': False,
        'message': '異常數量必須大於 0',
        'assemble_data': []
      }), 400

    source = (
      s.query(Assemble)
       .filter(Assemble.id == copy_id)
       .with_for_update()
       .first()
    )

    if not source:
      return jsonify({
        'status': False,
        'message': f'找不到來源 assemble_id={copy_id}',
        'assemble_data': []
      }), 404

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    #
    source.abnormal_qty = abnormal_qty
    source.input_abnormal_disable = True
    source.alarm_enable = False
    source.alarm_message = data.get('alarm_message') or source.alarm_message or ''
    source.update_time = now_str

    rework_alarm_message = (
        data.get('alarm_message')
        or source.alarm_message
        or source.Incoming1_Abnormal
        or source.confirm_comment
        or ''
    )

    # B109 異常時，Error.vue 目前看這個欄位
    if source.work_num == 'B109':
      source.isAssembleFirstAlarm = False
      source.isAssembleFirstAlarm_qty = abnormal_qty

    '''
    if pre_must_qty > 0:
      source.must_receive_end_qty = pre_must_qty
    '''
    #
    # ✅ 原工序扣掉異常數量
    if pre_must_qty > 0:
      remain_qty = pre_must_qty
    else:
      remain_qty = max(0, int(source.must_receive_qty or 0) - abnormal_qty)

    source.must_receive_qty = remain_qty
    source.ask_qty = remain_qty
    source.total_ask_qty = remain_qty
    source.must_receive_end_qty = remain_qty
    #

    material_id = source.material_id
    schedule_id = int(source.schedule_id or 0)


    material = s.query(Material).filter(Material.id == material_id).first()

    # ✅ 若來源沒有 schedule_id，從同 material 找一個可用 schedule_id
    if schedule_id <= 0:
      schedule_id = (
        s.query(Assemble.schedule_id)
         .filter(Assemble.material_id == material_id)
         .filter(Assemble.schedule_id.isnot(None))
         .filter(Assemble.schedule_id > 0)
         .order_by(Assemble.id.desc())
         .scalar()
      ) or 0

    existed = (
      s.query(Assemble)
       .filter(Assemble.material_id == material_id)
       .filter(Assemble.is_copied_from_id == source.id)
       .filter(Assemble.must_receive_qty == abnormal_qty)
       .filter(Assemble.work_num.in_(['B109', 'B110']))
       .order_by(Assemble.id.asc())
       .all()
    )

    if existed:
      s.commit()
      return jsonify({
        'status': True,
        'message': '返工列已存在，不重複建立',
        'assemble_data': [r.id for r in existed]
      })

    #def make_rework_row(work_num, step_code, show_code, show_in_begin):
    #def make_rework_row(work_num, step_code, show_code, show_in_begin=True, target_schedule_id=None):
    def make_rework_row(work_num, step_code, show_code, show_in_begin=True, target_schedule_id=None, parent_id=None):
        new_row = Assemble(
            material_id=source.material_id,
            material_num=source.material_num,
            material_comment=source.material_comment,
            seq_num=source.seq_num,

            work_num=work_num,
            process_step_code=step_code,
            Incoming1_Abnormal=rework_alarm_message,
            #schedule_id=schedule_id,
            schedule_id=target_schedule_id if target_schedule_id is not None else schedule_id,

            must_receive_qty=abnormal_qty,
            must_receive_end_qty=abnormal_qty,
            ask_qty=abnormal_qty,
            total_ask_qty=abnormal_qty,
            total_ask_qty_end=0,

            abnormal_qty=0,
            completed_qty=0,
            total_completed_qty=0,
            allOk_qty=0,

            user_id='',
            writer_id=None,
            write_date=None,

            good_qty=0,
            total_good_qty=0,
            non_good_qty=0,
            meinh_qty=0,

            #reason='',
            reason='異常返工',
            #confirm_comment='',
            confirm_comment=rework_alarm_message,
            is_assemble_ok=False,

            currentStartTime=None,
            currentEndTime=None,

            input_disable=False,
            input_end_disable=False,
            input_allOk_disable=False,
            input_abnormal_disable=False,

            isAssembleStationShow=show_in_begin,
            isWarehouseStationShow=False,

            # ✅ 返工列不是 Error.vue 異常來源
            alarm_enable=True,
            #alarm_message='',
            alarm_message=rework_alarm_message,
            isAssembleFirstAlarm=False,
            isAssembleFirstAlarm_message='',
            isAssembleFirstAlarm_qty=0,

            whichStation=1,
            show1_ok=1,
            show2_ok=show_code,
            show3_ok=show_code,

            update_time=now_str,
            create_at=now_str,
            #is_copied_from_id=source.id,
            is_copied_from_id=parent_id if parent_id is not None else source.id,
        )

        s.add(new_row)
        s.flush()
        return new_row

    new_rows = []

    raw_steps = material.process_steps if material else None
    try:
        if isinstance(raw_steps, str):
            process_steps = json.loads(raw_steps or "{}")
        elif isinstance(raw_steps, dict):
            process_steps = raw_steps
        else:
            process_steps = default_process_steps()
    except Exception:
        process_steps = default_process_steps()

    assemble_checked_ids = [
        int(x.get("id"))
        for x in (process_steps.get("assemble") or [])
        if x.get("checked") and x.get("id") is not None
    ]

    check_checked_ids = [
        int(x.get("id"))
        for x in (process_steps.get("check") or [])
        if x.get("checked") and x.get("id") is not None
    ]

    has_assemble_selected = len(assemble_checked_ids) > 0

    if source.work_num == 'B109':
        # 組裝異常：只產生新的 B109 返工列
        new_rows.append(make_rework_row(
          work_num='B109',
          step_code=3,
          show_code=3,
          show_in_begin=True
        ))

    elif source.work_num == 'B110':
        if has_assemble_selected:
            # 有組裝 + 檢驗：
            # 檢驗異常 → 回組裝製程第 1 個組裝工序
            first_assemble_schedule_id = min(assemble_checked_ids)

            '''
            new_rows.append(make_rework_row(
                work_num='B109',
                step_code=3,
                show_code=3,
                show_in_begin=True,
                target_schedule_id=first_assemble_schedule_id
            ))

            # 後續檢驗先隱藏，等組裝返工完成後再釋放
            new_rows.append(make_rework_row(
                work_num='B110',
                step_code=2,
                show_code=5,
                show_in_begin=False
            ))
            '''
            #
            new_b109 = make_rework_row(
                work_num='B109',
                step_code=3,
                show_code=3,
                show_in_begin=True,
                target_schedule_id=first_assemble_schedule_id,
                parent_id=source.id
            )
            new_rows.append(new_b109)

            new_b110 = make_rework_row(
                work_num='B110',
                step_code=2,
                show_code=5,
                show_in_begin=False,
                target_schedule_id=schedule_id,
                parent_id=new_b109.id
            )
            new_rows.append(new_b110)
            #

        else:
            # 只有檢驗：
            # 檢驗異常 → 回原檢驗工序
            new_rows.append(make_rework_row(
                work_num='B110',
                step_code=2,
                show_code=5,
                show_in_begin=True,
                target_schedule_id=schedule_id
            ))

    else:
        return jsonify({
          'status': False,
          'message': f'目前只支援 B109/B110 異常返工，來源 work_num={source.work_num}',
          'assemble_data': []
        }), 400

    if material:
        material.process_step_enable = True
        material.hasStarted = False
        material.startStatus = False
        material.isOpen = False
        material.isOpenEmpId = ''

    s.commit()

    return jsonify({
      'status': True,
      'message': '異常返工流程已建立',
      'assemble_data': [r.id for r in new_rows],
    })

  except Exception as e:
    s.rollback()
    print("copyAssembleForDifference ERROR:", repr(e))
    return jsonify({
      'status': False,
      'message': str(e),
      'assemble_data': []
    }), 500

  finally:
    s.close()


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

      schedule_id=record.schedule_id,
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

    # ✅ 方案 B：已複製到新單後，把舊單的缺料 BOM 刪掉
    s.query(Bom)\
    .filter(Bom.material_id == existing_material.id)\
    .filter(Bom.receive.is_(False))\
    .delete(synchronize_session=False)

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


# 20260722版
@createTable.route("/createProduct", methods=["POST"])
def create_product():

    # 組裝線成品入庫。
    #
    # 支援：
    # 1. 單筆：
    #    {
    #        "material_id": 123,
    #        "assemble_id": 456,
    #        "allOk_qty": 10,
    #        ...
    #    }
    #
    # 2. 批次：
    #    {
    #        "items": [
    #            {...},
    #            {...}
    #        ]
    #    }
    #
    # 主要規則：
    # 1. allOk_qty 必須大於 0。
    # 2. 若未傳 process_id，自動建立 process_type=31 入庫紀錄。
    # 3. 建立 Product。
    # 4. 更新 Material 入庫累計。
    # 5. 部分入庫時，只關閉本次入庫的 assemble。
    # 6. 全數入庫時，關閉同 material 的所有 assemble。
    # 7. 全數入庫時，關閉殘留的 process_type 21/22/23 計時。
    # 8. 組裝線 Assemble 沒有 isStockIn，不可使用該欄位。

    print("createProduct...")

    def safe_int(value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    s = Session()

    try:
        payload = request.get_json(silent=True) or {}

        # --------------------------------------------------------
        # 1. 支援單筆或批次
        # --------------------------------------------------------
        raw_items = payload.get("items")

        if raw_items is None:
            raw_items = [payload]

        if not isinstance(raw_items, list) or not raw_items:
            return jsonify({
                "status": False,
                "error": "payload 應為物件或 {'items': [...]}，且不可為空"
            }), 400

        # --------------------------------------------------------
        # 2. 先完整驗證所有輸入
        # 任一筆錯誤，整批不處理
        # --------------------------------------------------------
        errors = []
        normalized_items = []

        for idx, item in enumerate(raw_items):
            if not isinstance(item, dict):
                errors.append({
                    "index": idx,
                    "error": "每一筆 items 必須是物件"
                })
                continue

            material_id = _normalize_int(
                item.get("material_id"),
                0
            )

            assemble_id = _normalize_int(
                item.get("assemble_id"),
                0
            )

            process_id = _normalize_int(
                item.get("process_id"),
                0
            )

            all_ok_qty = _normalize_int(
                item.get("allOk_qty"),
                0
            )

            if material_id <= 0:
                errors.append({
                    "index": idx,
                    "error": "material_id 必須是大於 0 的整數"
                })

            if all_ok_qty <= 0:
                errors.append({
                    "index": idx,
                    "error": "allOk_qty 入庫數量必須大於 0"
                })

            normalized_items.append({
                "index": idx,
                "raw": item,
                "material_id": material_id,
                "assemble_id": assemble_id,
                "process_id": process_id,
                "allOk_qty": all_ok_qty,
            })

        if errors:
            return jsonify({
                "status": False,
                "errors": errors
            }), 400

        # --------------------------------------------------------
        # 3. 確認 material 全部存在
        # --------------------------------------------------------
        material_ids = sorted({
            row["material_id"]
            for row in normalized_items
        })

        existing_material_ids = {
            int(row[0])
            for row in (
                s.query(Material.id)
                .filter(Material.id.in_(material_ids))
                .all()
            )
        }

        for row in normalized_items:
            if row["material_id"] not in existing_material_ids:
                errors.append({
                    "index": row["index"],
                    "error": (
                        f"material_id={row['material_id']} 不存在"
                    )
                })

        if errors:
            return jsonify({
                "status": False,
                "errors": errors
            }), 400

        created_products = []
        result_items = []

        now_dt = datetime.now()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

        # --------------------------------------------------------
        # 4. 逐筆處理
        # --------------------------------------------------------
        for row in normalized_items:
            idx = row["index"]
            item = row["raw"]

            material_id = row["material_id"]
            assemble_id = row["assemble_id"]
            process_id_to_use = row["process_id"]
            add_qty = row["allOk_qty"]

            user_id = str(
                item.get("user_id") or "system"
            ).strip() or "system"

            delivery_qty = _normalize_int(
                item.get("delivery_qty"),
                0
            )

            assemble_qty = _normalize_int(
                item.get("assemble_qty"),
                0
            )

            good_qty = _normalize_int(
                item.get("good_qty"),
                0
            )

            non_good_qty = _normalize_int(
                item.get("non_good_qty"),
                0
            )

            line_difference = _normalize_int(
                item.get("line_difference"),
                0
            )

            reason = (
                str(item.get("reason")).strip()
                if item.get("reason") is not None
                else None
            )

            confirm_comment = (
                str(item.get("confirm_comment")).strip()
                if item.get("confirm_comment") is not None
                else None
            )

            # ----------------------------------------------------
            # 4-1. 鎖定 material
            # 避免兩台電腦同時入庫造成累計錯誤
            # ----------------------------------------------------
            material = (
                s.query(Material)
                .filter(Material.id == material_id)
                .with_for_update()
                .one_or_none()
            )

            if material is None:
                raise ValueError(
                    f"第 {idx + 1} 筆找不到 material_id={material_id}"
                )

            # ----------------------------------------------------
            # 4-2. 找本次要入庫的 assemble
            # ----------------------------------------------------
            assemble_record = None

            if assemble_id > 0:
                assemble_record = (
                    s.query(Assemble)
                    .filter(
                        Assemble.id == assemble_id,
                        Assemble.material_id == material_id
                    )
                    .with_for_update()
                    .one_or_none()
                )

                if assemble_record is None:
                    raise ValueError(
                        f"第 {idx + 1} 筆找不到 "
                        f"assemble_id={assemble_id}，"
                        f"或不屬於 material_id={material_id}"
                    )

            else:
                # 前端沒有傳 assemble_id 時：
                # 優先找 Warehouse 正在等待入庫的完成列
                assemble_record = (
                    s.query(Assemble)
                    .filter(
                        Assemble.material_id == material_id,
                        Assemble.isWarehouseStationShow.is_(True)
                    )
                    .order_by(Assemble.id.asc())
                    .with_for_update()
                    .first()
                )

                # 找不到 Warehouse 列，再找最新完成列
                if assemble_record is None:
                    assemble_record = (
                        s.query(Assemble)
                        .filter(
                            Assemble.material_id == material_id,
                            Assemble.process_step_code == 0
                        )
                        .order_by(Assemble.id.desc())
                        .with_for_update()
                        .first()
                    )

                if assemble_record is not None:
                    assemble_id = int(assemble_record.id)
            '''
            # ----------------------------------------------------
            # 4-3. 檢查是否已經完全入庫
            # ----------------------------------------------------
            old_total = _normalize_int(
                getattr(material, "total_allOk_qty", 0),
                0
            )

            must_qty = _normalize_int(
                getattr(material, "must_allOk_qty", 0),
                0
            )

            # must_allOk_qty 為 0 時，使用其他數量欄位推估
            if must_qty <= 0:
                must_qty = _normalize_int(
                    getattr(material, "total_assemble_qty", 0),
                    0
                )

            if must_qty <= 0:
                must_qty = _normalize_int(
                    getattr(material, "assemble_qty", 0),
                    0
                )

            if must_qty <= 0:
                must_qty = _normalize_int(
                    getattr(material, "total_delivery_qty", 0),
                    0
                )

            if must_qty <= 0:
                must_qty = _normalize_int(
                    getattr(material, "delivery_qty", 0),
                    0
                )

            if must_qty <= 0:
                must_qty = _normalize_int(
                    getattr(material, "material_qty", 0),
                    0
                )
            '''
            #
            # ----------------------------------------------------
            # 4-3. 檢查是否已經完全入庫
            # ----------------------------------------------------
            old_total = _normalize_int(
                getattr(
                    material,
                    "total_allOk_qty",
                    0
                ),
                0
            )

            # ----------------------------------------------------
            # 不能只依賴 material.must_allOk_qty。
            #
            # 某些工單的 material.must_allOk_qty 可能只記錄
            # 最後一批或最後一個工序數量，例如 22，
            # 但整張工單實際應入庫量可能是 72。
            #
            # 因此同時參考：
            # 1. material 各數量欄位
            # 2. Warehouse 待入庫 assemble
            # 3. 已完成 B110 / B109 的累計數量
            # ----------------------------------------------------

            material_qty_candidates = [
                _normalize_int(
                    getattr(
                        material,
                        "must_allOk_qty",
                        0
                    ),
                    0
                ),
                _normalize_int(
                    getattr(
                        material,
                        "total_assemble_qty",
                        0
                    ),
                    0
                ),
                _normalize_int(
                    getattr(
                        material,
                        "assemble_qty",
                        0
                    ),
                    0
                ),
                _normalize_int(
                    getattr(
                        material,
                        "total_delivery_qty",
                        0
                    ),
                    0
                ),
                _normalize_int(
                    getattr(
                        material,
                        "delivery_qty",
                        0
                    ),
                    0
                ),
                _normalize_int(
                    getattr(
                        material,
                        "material_qty",
                        0
                    ),
                    0
                ),
            ]

            # 找出同一 material 目前位於 Warehouse
            # 或已完成的 assemble 列
            warehouse_rows = (
                s.query(Assemble)
                .filter(
                    Assemble.material_id == material_id
                )
                .filter(
                    or_(
                        Assemble.isWarehouseStationShow.is_(True),
                        Assemble.process_step_code == 0
                    )
                )
                .with_for_update()
                .all()
            )

            assemble_qty_candidates = []

            for warehouse_row in warehouse_rows:
                assemble_qty_candidates.extend([
                    _normalize_int(
                        getattr(
                            warehouse_row,
                            "allOk_qty",
                            0
                        ),
                        0
                    ),
                    _normalize_int(
                        getattr(
                            warehouse_row,
                            "total_completed_qty",
                            0
                        ),
                        0
                    ),
                    _normalize_int(
                        getattr(
                            warehouse_row,
                            "completed_qty",
                            0
                        ),
                        0
                    ),
                    _normalize_int(
                        getattr(
                            warehouse_row,
                            "total_ask_qty",
                            0
                        ),
                        0
                    ),
                    _normalize_int(
                        getattr(
                            warehouse_row,
                            "must_receive_qty",
                            0
                        ),
                        0
                    ),
                ])

            must_qty = max(
                material_qty_candidates
                + assemble_qty_candidates
                + [0]
            )
            '''
            # 工單應交數量可作為上限，避免異常累計超過訂單數量
            material_delivery_qty = _normalize_int(
                getattr(
                    material,
                    "delivery_qty",
                    0
                ),
                0
            )

            if material_delivery_qty > 0:
                must_qty = min(
                    must_qty,
                    material_delivery_qty
                )

            print(
                "[createProduct] stock-in quantity validation:",
                {
                    "material_id": material_id,
                    "order_num": getattr(
                        material,
                        "order_num",
                        ""
                    ),
                    "material_candidates":
                        material_qty_candidates,
                    "assemble_candidates":
                        assemble_qty_candidates,
                    "must_qty": must_qty,
                    "old_total": old_total,
                    "add_qty": add_qty,
                }
            )
            '''
            #
            # ----------------------------------------------------
            # 工單數量上限判斷
            #
            # 注意：
            # material.delivery_qty 有時只是本批數量，
            # 例如 delivery_qty=22，
            # 但整張工單 material_qty=72。
            #
            # 因此不可直接用：
            #     must_qty = min(must_qty, delivery_qty)
            #
            # 否則 72 會被錯誤截成 22。
            # ----------------------------------------------------
            material_delivery_qty = _normalize_int(
                getattr(
                    material,
                    "delivery_qty",
                    0
                ),
                0
            )

            material_order_qty = _normalize_int(
                getattr(
                    material,
                    "material_qty",
                    0
                ),
                0
            )

            # 只有 delivery_qty 大於等於整張工單數量時，
            # 才可作為 must_qty 上限。
            #
            # 若 delivery_qty < material_qty，
            # 代表 delivery_qty 很可能只是分批數量，
            # 不可以拿來限制整張工單入庫量。
            if (
                material_delivery_qty > 0
                and material_order_qty > 0
                and material_delivery_qty >= material_order_qty
            ):
                must_qty = min(
                    must_qty,
                    material_delivery_qty
                )

            # 若目前還算不到應入庫量，
            # 至少使用整張工單數量作為 fallback
            if must_qty <= 0 and material_order_qty > 0:
                must_qty = material_order_qty

            print(
                "[createProduct] stock-in quantity validation:",
                {
                    "material_id": material_id,
                    "order_num": getattr(
                        material,
                        "order_num",
                        ""
                    ),
                    "material_candidates":
                        material_qty_candidates,
                    "assemble_candidates":
                        assemble_qty_candidates,

                    "material_delivery_qty":
                        material_delivery_qty,

                    "material_order_qty":
                        material_order_qty,

                    "must_qty": must_qty,
                    "old_total": old_total,
                    "add_qty": add_qty,
                }
            )
            #

            # 已經完成全部入庫，不允許再次新增
            if (
                bool(getattr(material, "isAllOk", False))
                and must_qty > 0
                and old_total >= must_qty
            ):
                raise ValueError(
                    f"material_id={material_id} 已全數入庫，"
                    "不可重複入庫"
                )

            # 防止累計超過應入庫數量
            if must_qty > 0 and old_total + add_qty > must_qty:
                remain_qty = max(must_qty - old_total, 0)

                raise ValueError(
                    f"第 {idx + 1} 筆入庫數量超過剩餘數量；"
                    f"應入庫={must_qty}，"
                    f"已入庫={old_total}，"
                    f"剩餘={remain_qty}，"
                    f"本次輸入={add_qty}"
                )
            '''
            # ----------------------------------------------------
            # 4-4. 準備或建立 process_type=31
            # ----------------------------------------------------
            stockin_process = None

            if process_id_to_use > 0:
                stockin_process = (
                    s.query(Process)
                    .filter(
                        Process.id == process_id_to_use,
                        Process.material_id == material_id
                    )
                    .with_for_update()
                    .one_or_none()
                )

                if stockin_process is None:
                    raise ValueError(
                        f"process_id={process_id_to_use} 不存在，"
                        f"或不屬於 material_id={material_id}"
                    )

                if int(stockin_process.process_type or 0) != 31:
                    raise ValueError(
                        f"process_id={process_id_to_use} "
                        "不是成品入庫 process_type=31"
                    )
            '''

            '''
            # ----------------------------------------------------
            # 4-4. 準備或建立 process_type=31
            # ----------------------------------------------------
            stockin_process = None

            if process_id_to_use > 0:
                candidate_process = (
                    s.query(Process)
                    .filter(
                        Process.id == process_id_to_use,
                        Process.material_id == material_id
                    )
                    .with_for_update()
                    .one_or_none()
                )

                # ------------------------------------------------
                # 前端可能傳入 Warehouse 列上的搬運 process_id，
                # 例如：
                # process_type=3  AGV 組裝區 -> 成品區
                # process_type=6  堆高機組裝區 -> 成品區
                #
                # 這些都不是入庫 process_type=31，
                # 不可直接拿來建立 Product。
                #
                # 若不是 type=31，就清除 process_id，
                # 讓後端在下面自動建立新的入庫 Process。
                # ------------------------------------------------
                if candidate_process is None:
                    print(
                        "[createProduct] ignore invalid process_id:",
                        {
                            "material_id": material_id,
                            "process_id": process_id_to_use,
                            "reason": "process 不存在或不屬於此 material",
                        }
                    )

                    process_id_to_use = 0

                elif int(candidate_process.process_type or 0) != 31:
                    print(
                        "[createProduct] ignore non-stockin process_id:",
                        {
                            "material_id": material_id,
                            "process_id": process_id_to_use,
                            "process_type":
                                int(candidate_process.process_type or 0),
                            "reason": "不是 process_type=31",
                        }
                    )

                    process_id_to_use = 0

                else:
                    stockin_process = candidate_process

                # 同一 process_id 不可重複建立 Product
                duplicate_product = (
                    s.query(Product.id)
                    .filter(
                        Product.process_id == process_id_to_use
                    )
                    .first()
                )

                if duplicate_product:
                    raise ValueError(
                        f"process_id={process_id_to_use} "
                        "已建立過入庫 Product，不可重複送出"
                    )

                # 確保入庫 process 已結束
                stockin_process.has_started = False
                stockin_process.is_pause = True
                stockin_process.pause_started_at = None

                if (
                    stockin_process.begin_time is None
                    or str(stockin_process.begin_time).strip() == ""
                ):
                    stockin_process.begin_time = now_str

                if (
                    stockin_process.end_time is None
                    or str(stockin_process.end_time).strip() == ""
                ):
                    stockin_process.end_time = now_str

                stockin_process.process_work_time_qty = add_qty
                stockin_process.allOk_qty = add_qty
                stockin_process.must_allOk_qty = must_qty
                stockin_process.isAllOk = (
                    must_qty <= 0
                    or old_total + add_qty >= must_qty
                )

            else:
                # 防止同一 assemble、同數量的重複入庫請求
                existing_stockin_process = (
                    s.query(Process)
                    .filter(
                        Process.material_id == material_id,
                        Process.assemble_id == (assemble_id or 0),
                        Process.process_type == 31,
                        Process.process_work_time_qty == add_qty
                    )
                    .order_by(Process.id.desc())
                    .first()
                )

                if existing_stockin_process is not None:
                    duplicate_product = (
                        s.query(Product.id)
                        .filter(
                            Product.process_id
                            == existing_stockin_process.id
                        )
                        .first()
                    )

                    if duplicate_product:
                        raise ValueError(
                            f"material_id={material_id}、"
                            f"assemble_id={assemble_id}、"
                            f"入庫數量={add_qty} "
                            "已有入庫紀錄，不可重複送出"
                        )

                    stockin_process = existing_stockin_process

                else:
                    stockin_process = Process(
                        material_id=material_id,
                        assemble_id=assemble_id or 0,
                        has_started=False,
                        user_id=user_id,
                        user_delegate_id="",

                        begin_time=now_str,
                        end_time=now_str,

                        period_time="0:00:00",
                        pause_time=0,
                        pause_started_at=None,

                        elapsedActive_time=0,
                        str_elapsedActive_time="00:00:00",
                        is_pause=True,

                        process_type=31,
                        process_work_time_qty=add_qty,

                        must_allOk_qty=must_qty,
                        allOk_qty=add_qty,
                        isAllOk=(
                            must_qty <= 0
                            or old_total + add_qty >= must_qty
                        ),

                        normal_work_time=1,
                        abnormal_cause_message="",
                        create_at=now_dt
                    )

                    s.add(stockin_process)
                    s.flush()

                process_id_to_use = int(stockin_process.id)
            '''
            #
            # ----------------------------------------------------
            # 4-4. 準備或建立 process_type=31
            # ----------------------------------------------------
            stockin_process = None

            # ----------------------------------------------------
            # A. 檢查前端傳入的 process_id
            #
            # Warehouse 畫面傳來的 process_id 可能是：
            # 3  = AGV 組裝區 -> 成品區
            # 6  = 堆高機組裝區 -> 成品區
            #
            # 只有 process_type=31 才能當作成品入庫紀錄。
            # ----------------------------------------------------
            if process_id_to_use > 0:
                candidate_process = (
                    s.query(Process)
                    .filter(
                        Process.id == process_id_to_use,
                        Process.material_id == material_id
                    )
                    .with_for_update()
                    .one_or_none()
                )

                if candidate_process is None:
                    print(
                        "[createProduct] ignore invalid process_id:",
                        {
                            "material_id": material_id,
                            "process_id": process_id_to_use,
                            "reason": (
                                "process 不存在，"
                                "或不屬於此 material"
                            ),
                        }
                    )

                    process_id_to_use = 0

                elif int(candidate_process.process_type or 0) != 31:
                    print(
                        "[createProduct] ignore non-stockin process_id:",
                        {
                            "material_id": material_id,
                            "process_id": process_id_to_use,
                            "process_type": int(
                                candidate_process.process_type or 0
                            ),
                            "reason": "不是 process_type=31",
                        }
                    )

                    # 清除搬運 process_id，
                    # 後面自動建立新的入庫 process
                    process_id_to_use = 0

                else:
                    stockin_process = candidate_process


            # ----------------------------------------------------
            # B. 前端傳入的確實是 process_type=31
            # ----------------------------------------------------
            if stockin_process is not None:

                duplicate_product = (
                    s.query(Product.id)
                    .filter(
                        Product.process_id
                        == stockin_process.id
                    )
                    .first()
                )

                if duplicate_product:
                    raise ValueError(
                        f"process_id={stockin_process.id} "
                        "已建立過入庫 Product，不可重複送出"
                    )

                # 確保入庫 process 已結束
                stockin_process.has_started = False
                stockin_process.is_pause = True
                stockin_process.pause_started_at = None

                if (
                    stockin_process.begin_time is None
                    or str(
                        stockin_process.begin_time
                    ).strip() == ""
                ):
                    stockin_process.begin_time = now_str

                if (
                    stockin_process.end_time is None
                    or str(
                        stockin_process.end_time
                    ).strip() == ""
                ):
                    stockin_process.end_time = now_str

                stockin_process.process_work_time_qty = add_qty
                stockin_process.allOk_qty = add_qty
                stockin_process.must_allOk_qty = must_qty

                stockin_process.isAllOk = (
                    must_qty <= 0
                    or old_total + add_qty >= must_qty
                )

                process_id_to_use = int(
                    stockin_process.id
                )


            # ----------------------------------------------------
            # C. 沒有可用的 process_type=31
            # 自動尋找或建立新的入庫 process
            # ----------------------------------------------------
            else:
                existing_stockin_process = (
                    s.query(Process)
                    .filter(
                        Process.material_id == material_id,
                        Process.assemble_id
                        == (assemble_id or 0),
                        Process.process_type == 31,
                        Process.process_work_time_qty
                        == add_qty
                    )
                    .order_by(Process.id.desc())
                    .with_for_update()
                    .first()
                )

                if existing_stockin_process is not None:
                    duplicate_product = (
                        s.query(Product.id)
                        .filter(
                            Product.process_id
                            == existing_stockin_process.id
                        )
                        .first()
                    )

                    if duplicate_product:
                        raise ValueError(
                            f"material_id={material_id}、"
                            f"assemble_id={assemble_id}、"
                            f"入庫數量={add_qty} "
                            "已有入庫紀錄，不可重複送出"
                        )

                    stockin_process = (
                        existing_stockin_process
                    )

                    # 補齊既有但尚未建立 Product 的
                    # process_type=31 狀態
                    stockin_process.has_started = False
                    stockin_process.is_pause = True
                    stockin_process.pause_started_at = None

                    if (
                        stockin_process.begin_time is None
                        or str(
                            stockin_process.begin_time
                        ).strip() == ""
                    ):
                        stockin_process.begin_time = now_str

                    if (
                        stockin_process.end_time is None
                        or str(
                            stockin_process.end_time
                        ).strip() == ""
                    ):
                        stockin_process.end_time = now_str

                    stockin_process.process_work_time_qty = (
                        add_qty
                    )
                    stockin_process.allOk_qty = add_qty
                    stockin_process.must_allOk_qty = must_qty

                    stockin_process.isAllOk = (
                        must_qty <= 0
                        or old_total + add_qty >= must_qty
                    )

                else:
                    stockin_process = Process(
                        material_id=material_id,
                        assemble_id=assemble_id or 0,

                        has_started=False,
                        user_id=user_id,
                        user_delegate_id="",

                        begin_time=now_str,
                        end_time=now_str,

                        period_time="0:00:00",
                        pause_time=0,
                        pause_started_at=None,

                        elapsedActive_time=0,
                        str_elapsedActive_time="00:00:00",
                        is_pause=True,

                        process_type=31,
                        process_work_time_qty=add_qty,

                        must_allOk_qty=must_qty,
                        allOk_qty=add_qty,

                        isAllOk=(
                            must_qty <= 0
                            or old_total + add_qty >= must_qty
                        ),

                        normal_work_time=1,
                        abnormal_cause_message="",
                        create_at=now_dt
                    )

                    s.add(stockin_process)
                    s.flush()

                process_id_to_use = int(
                    stockin_process.id
                )
            #

            # ----------------------------------------------------
            # 4-5. 建立 Product
            # ----------------------------------------------------
            product = Product(
                material_id=material_id,
                process_id=process_id_to_use or None,

                line_difference=line_difference,
                delivery_qty=delivery_qty,
                assemble_qty=assemble_qty,

                allOk_qty=add_qty,
                good_qty=good_qty,
                non_good_qty=non_good_qty,

                reason=reason,
                confirm_comment=confirm_comment,
            )

            s.add(product)
            s.flush()

            created_products.append(product)

            # ----------------------------------------------------
            # 4-6. 更新 Material 入庫累計
            # ----------------------------------------------------
            new_total = old_total + add_qty

            material.allOk_qty = add_qty
            material.total_allOk_qty = new_total

            # 是否已完成全部入庫
            material_finished = (
                must_qty <= 0
                or new_total >= must_qty
            )

            # ----------------------------------------------------
            # 4-7. 部分入庫
            #
            # 只關閉本次入庫的 assemble，
            # 其他 Warehouse 列仍可繼續入庫。
            # ----------------------------------------------------
            if not material_finished:
                material.isAllOk = False
                material.isAssembleStationShow = False

                material.whichStation = 3
                material.show1_ok = 3
                material.show2_ok = 10
                material.show3_ok = 11

                material.isOpen = False
                material.isOpenEmpId = ""
                material.hasStarted = False
                material.startStatus = 1

                if hasattr(material, "update_time"):
                    material.update_time = now_str

                if assemble_record is not None:
                    assemble_record.allOk_qty = add_qty

                    assemble_record.process_step_code = 0
                    assemble_record.isAssembleStationShow = False
                    assemble_record.isWarehouseStationShow = False

                    assemble_record.input_disable = True
                    assemble_record.input_end_disable = True
                    assemble_record.input_abnormal_disable = True
                    assemble_record.input_allOk_disable = True

                    assemble_record.currentStartTime = None
                    assemble_record.currentEndTime = None

                    assemble_record.whichStation = 3
                    assemble_record.show1_ok = 3
                    assemble_record.show2_ok = 12
                    assemble_record.show3_ok = 13

                    if hasattr(assemble_record, "update_time"):
                        assemble_record.update_time = now_str

            # ----------------------------------------------------
            # 4-8. 全數入庫完成
            # ----------------------------------------------------
            else:
                material.isAllOk = True
                material.isShow = True
                material.isTakeOk = True

                material.isAssembleStationShow = False
                material.isAssembleStation3TakeOk = True

                material.whichStation = 3
                material.show1_ok = 3
                material.show2_ok = 12
                material.show3_ok = 13

                material.isOpen = False
                material.isOpenEmpId = ""
                material.hasStarted = False
                material.startStatus = 1

                if hasattr(material, "update_time"):
                    material.update_time = now_str

                # ------------------------------------------------
                # 同 material 所有 assemble 全部退出：
                # Begin / End / Warehouse
                #
                # 組裝線 Assemble 沒有 isStockIn，
                # 不可設定 Assemble.isStockIn。
                # ------------------------------------------------
                all_assemble_rows = (
                    s.query(Assemble)
                    .filter(
                        Assemble.material_id == material_id
                    )
                    .with_for_update()
                    .all()
                )

                for assemble_row in all_assemble_rows:
                    assemble_row.process_step_code = 0

                    assemble_row.isAssembleStationShow = False
                    assemble_row.isWarehouseStationShow = False

                    assemble_row.input_disable = True
                    assemble_row.input_end_disable = True
                    assemble_row.input_abnormal_disable = True
                    assemble_row.input_allOk_disable = True

                    assemble_row.currentStartTime = None
                    assemble_row.currentEndTime = None

                    assemble_row.whichStation = 3
                    assemble_row.show1_ok = 3
                    assemble_row.show2_ok = 12
                    assemble_row.show3_ok = 13

                    if (
                        int(assemble_row.id)
                        == int(assemble_id or 0)
                    ):
                        assemble_row.allOk_qty = add_qty

                    if hasattr(assemble_row, "update_time"):
                        assemble_row.update_time = now_str

                # ------------------------------------------------
                # 關閉殘留的組裝／檢驗／雷射 Process
                #
                # 只修改尚未結束或 has_started=1 的紀錄。
                # 已正常結束的歷史紀錄不動。
                # ------------------------------------------------
                active_process_rows = (
                    s.query(Process)
                    .filter(
                        Process.material_id == material_id,
                        Process.process_type.in_([21, 22, 23]),
                        or_(
                            Process.end_time.is_(None),
                            Process.end_time == "",
                            Process.has_started.is_(True)
                        )
                    )
                    .with_for_update()
                    .all()
                )

                for process_row in active_process_rows:
                    if (
                        process_row.end_time is None
                        or str(process_row.end_time).strip() == ""
                    ):
                        process_row.end_time = now_str

                    process_row.has_started = False
                    process_row.is_pause = True
                    process_row.pause_started_at = None

                print(
                    "[createProduct] material fully stocked in:",
                    {
                        "material_id": material_id,
                        "order_num": material.order_num,
                        "must_qty": must_qty,
                        "old_total": old_total,
                        "add_qty": add_qty,
                        "new_total": new_total,
                        "assemble_closed": len(
                            all_assemble_rows
                        ),
                        "active_process_closed": len(
                            active_process_rows
                        ),
                    }
                )

            result_items.append({
                "index": idx,
                "material_id": material_id,
                "assemble_id": assemble_id or None,
                "process_id": process_id_to_use,
                "product_id": product.id,
                "allOk_qty": add_qty,
                "old_total_allOk_qty": old_total,
                "new_total_allOk_qty": new_total,
                "must_allOk_qty": must_qty,
                "material_finished": material_finished,
            })

        # --------------------------------------------------------
        # 5. 整批成功才 commit
        # --------------------------------------------------------
        s.commit()

        response_products = []

        for product in created_products:
            response_products.append({
                "id": product.id,
                "material_id": product.material_id,
                "process_id": product.process_id,
                "delivery_qty": product.delivery_qty,
                "assemble_qty": product.assemble_qty,
                "allOk_qty": product.allOk_qty,
                "good_qty": product.good_qty,
                "non_good_qty": product.non_good_qty,
                "reason": product.reason,
                "confirm_comment": product.confirm_comment,
                "create_at": (
                    product.create_at.isoformat()
                    if getattr(product, "create_at", None)
                    else None
                ),
            })

        return jsonify({
            "status": True,
            "created": len(response_products),
            "items": response_products,
            "results": result_items
        }), 200

    except ValueError as e:
        s.rollback()

        print(
            "[createProduct] validation error:",
            str(e)
        )

        return jsonify({
            "status": False,
            "error": str(e)
        }), 400

    except SQLAlchemyError as e:
        s.rollback()

        print(
            "[createProduct] SQLAlchemy error:",
            repr(e)
        )

        return jsonify({
            "status": False,
            "error": str(e)
        }), 500

    except Exception as e:
        s.rollback()

        print(
            "[createProduct] unexpected error:",
            repr(e)
        )

        return jsonify({
            "status": False,
            "error": str(e)
        }), 500

    finally:
        s.close()


@createTable.route("/copyNewIdAssemble", methods=['POST'])
def copy_new_id_assemble():
    # POST JSON:
    # {
    #     "copy_assemble_id": 123,
    #     "copy_assemble_must_receive_qty": 10,
    #     "copy_assemble_process_step_code": 21
    # }

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

