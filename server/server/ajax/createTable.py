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
#from sqlalchemy import exc
from sqlalchemy import func

from .helper import (
  sync_b110_remaining_qty,
  _normalize_bool
)

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


# 20260807版
# 1. type=2/5/19 短時間重複呼叫防護
# 2. type=3/6 搬運紀錄防重複
# 3. 使用 material row lock，避免多人同時 INSERT
# 4. type=2/5 確認非重複後才釋放到 Begin
# 5. 保留 type=21/22/23 工序計時防重複
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
    '''
    def get_or_create_prepare_to_assemble_transport(
        session,
        material_id,
        user_id,
        transport_type,
        now,
    ):

        # 建立「備料區 -> 組裝區」搬運紀錄。
        #
        # transport_type:
        #     2 = AGV 備料區 -> 組裝區
        #     5 = 堆高機備料區 -> 組裝區
        #
        # 同一個 material 只能存在一筆 2 或 5，
        # 避免 AGV / 堆高機重複建立。

        if transport_type not in (2, 5):
            raise ValueError(
                "transport_type 必須為 2 或 5"
            )

        # --------------------------------------------------------
        # 1. 鎖定 material。
        #
        # 第二個同時進來的 request 必須等待第一個 transaction
        # commit，之後才會繼續執行。
        # --------------------------------------------------------
        material = (
            session.query(Material)
            .filter(Material.id == material_id)
            .with_for_update()
            .one_or_none()
        )

        if material is None:
            raise ValueError(
                f"找不到 material_id={material_id}"
            )

        # --------------------------------------------------------
        # 2. 同一 material 的「備料區 -> 組裝區」只能有一筆。
        #
        # 這裡同時檢查 type 2 與 type 5，
        # 避免先建立 AGV，之後又建立堆高機。
        # --------------------------------------------------------
        existing = (
            session.query(Process)
            .filter(
                Process.material_id == material_id,
                Process.process_type.in_([2, 5]),
            )
            .order_by(
                Process.create_at.asc(),
                Process.id.asc(),
            )
            .first()
        )

        if existing is not None:
            return existing, False

        # --------------------------------------------------------
        # 3. 確定不存在後才建立。
        # --------------------------------------------------------
        process = Process(
            material_id=material_id,
            assemble_id=0,
            has_started=False,
            user_id=str(user_id or "").strip(),
            user_delegate_id="",
            begin_time=now,
            end_time=None,
            period_time="",
            pause_time=0,
            pause_started_at=None,
            elapsedActive_time=0,
            str_elapsedActive_time=None,
            is_pause=False,
            process_type=transport_type,
            process_work_time_qty=0,
            must_allOk_qty=0,
            allOk_qty=0,
            isAllOk=False,
            normal_work_time=1,
            abnormal_cause_message="",
            create_at=now,
        )

        session.add(process)
        session.flush()

        return process, True
        #
    '''
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

        '''
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
        '''

        '''
        #
        # --------------------------------------------------------
        # type=2 / 5 / 19 搬運紀錄防重複
        #
        # 2  = AGV 備料區 -> 組裝區
        # 5  = 堆高機 備料區 -> 組裝區
        # 19 = 等待 AGV（備料區）
        #
        # 防止：
        # 1. 使用者重複點擊
        # 2. Socket 重送
        # 3. 前端短時間內重複呼叫 API
        #
        # 注意：
        # 不可單純用 end_time IS NULL 判斷，
        # 因為舊批次若漏補 end_time，會把後續正常批次也擋住。
        #
        # 判斷規則：
        # 同 material + 同 type + 同 user，
        # 且 begin_time 相差 30 秒以內，視為同一次重送。
        # --------------------------------------------------------
        if process_type_int in {2, 5, 19}:

            def parse_transport_datetime(value):
                """
                將前端或資料庫的時間轉成 datetime。

                支援：
                - datetime
                - YYYY-MM-DD HH:MM:SS
                - YYYY-MM-DDTHH:MM:SS
                - 含微秒格式
                """

                if value in (None, "", "None"):
                    return None

                if isinstance(value, datetime):
                    return value

                text = str(value).strip()

                if text.endswith("Z"):
                    text = text[:-1]

                text = text.replace("T", " ")

                try:
                    return datetime.fromisoformat(text)
                except (TypeError, ValueError):
                    pass

                for fmt in (
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                ):
                    try:
                        return datetime.strptime(text, fmt)
                    except (TypeError, ValueError):
                        continue

                return None

            incoming_begin_dt = parse_transport_datetime(_begin_time)

            # ----------------------------------------------------
            # 1. 先檢查完全相同的 begin_time
            # ----------------------------------------------------
            exact_duplicate = None

            if incoming_begin_dt is not None:
                exact_duplicate = (
                    s.query(Process)
                    .filter(
                        Process.material_id == material_id_int,
                        Process.process_type == process_type_int,
                        Process.begin_time == _begin_time,
                    )
                    .order_by(Process.id.asc())
                    .first()
                )

            if exact_duplicate:
                s.commit()

                print(
                    "[createProcess] exact duplicate transport skipped:",
                    {
                        "material_id": material_id_int,
                        "process_type": process_type_int,
                        "process_id": exact_duplicate.id,
                        "begin_time": _begin_time,
                    }
                )

                return jsonify({
                    "status": True,
                    "created": False,
                    "process_id": exact_duplicate.id,
                    "skipped": True,
                    "duplicate": True,
                    "message": "相同搬運紀錄已存在，不重複新增",
                }), 200

            # ----------------------------------------------------
            # 2. 找相同 material / type / user 最近一筆
            #
            # 只找同一位操作人員，避免不同人員在真正不同批次
            # 進行搬運時被錯誤攔截。
            # ----------------------------------------------------
            latest_transport = (
                s.query(Process)
                .filter(
                    Process.material_id == material_id_int,
                    Process.process_type == process_type_int,
                    Process.user_id == _user_id,
                )
                .order_by(
                    Process.begin_time.desc(),
                    Process.id.desc(),
                )
                .first()
            )

            if latest_transport and incoming_begin_dt is not None:

                latest_begin_dt = parse_transport_datetime(
                    latest_transport.begin_time
                )

                if latest_begin_dt is not None:
                    diff_seconds = abs(
                        (
                            incoming_begin_dt
                            - latest_begin_dt
                        ).total_seconds()
                    )

                    # --------------------------------------------
                    # 30 秒內視為重複送出
                    # --------------------------------------------
                    if diff_seconds <= 30:
                        s.commit()

                        print(
                            "[createProcess] near duplicate "
                            "transport skipped:",
                            {
                                "material_id": material_id_int,
                                "process_type": process_type_int,
                                "user_id": _user_id,
                                "existing_process_id":
                                    latest_transport.id,
                                "existing_begin_time":
                                    str(latest_transport.begin_time),
                                "incoming_begin_time":
                                    str(_begin_time),
                                "diff_seconds":
                                    diff_seconds,
                            }
                        )

                        return jsonify({
                            "status": True,
                            "created": False,
                            "process_id":
                                latest_transport.id,
                            "skipped": True,
                            "duplicate": True,
                            "message":
                                "短時間內已有相同搬運紀錄，"
                                "本次重複呼叫已忽略",
                            "diff_seconds":
                                diff_seconds,
                        }), 200
        # end if process_type_int in {2, 5, 19}:
        '''
        #
        # --------------------------------------------------------
        # type=2 / 5：
        # 備料區 -> 組裝區，只允許一種搬運方式、一筆紀錄
        #
        # 2 = AGV
        # 5 = 堆高機
        #
        # material 已在前面 with_for_update() 鎖定，
        # 因此兩個 request 同時進入時：
        #
        # request A：取得鎖並新增
        # request B：等待 A commit，之後查到既有資料並略過
        # --------------------------------------------------------
        if process_type_int in (2, 5):

            #existed_inbound_transport = (
            #    s.query(Process)
            #    .filter(
            #        Process.material_id == material_id_int,
            #
            #        # AGV 與堆高機互斥
            #        Process.process_type.in_([2, 5])
            #    )
            #    .order_by(
            #        Process.create_at.asc(),
            #        Process.id.asc()
            #    )
            #    .first()
            #)
            # 20260817版
            existed_inbound_transport = (
                s.query(Process)
                .filter(
                    Process.material_id == material_id_int,
                    Process.process_type.in_([2, 5])
                )
                .order_by(
                    Process.create_at.asc(),
                    Process.id.asc()
                )
                .with_for_update()
                .first()
            )
            #

            if existed_inbound_transport is not None:
                s.commit()

                print(
                    "[createProcess] inbound transport "
                    "duplicate skipped:",
                    {
                        "material_id":
                            material_id_int,

                        "incoming_process_type":
                            process_type_int,

                        "existing_process_id":
                            existed_inbound_transport.id,

                        "existing_process_type":
                            existed_inbound_transport.process_type,

                        "existing_begin_time":
                            str(
                                existed_inbound_transport.begin_time
                            ),
                    }
                )

                return jsonify({
                    "status": True,
                    "created": False,

                    "process_id":
                        existed_inbound_transport.id,

                    "process_type":
                        existed_inbound_transport.process_type,

                    "skipped": True,
                    "duplicate": True,

                    "message":
                        "此批工單已有備料區到組裝區搬運紀錄，"
                        "不重複新增"
                }), 200

        # --------------------------------------------------------
        # type=19：
        # 等待 AGV（備料區）
        #
        # 同一 material 只保留一筆等待 AGV。
        # 不能和 type 2 / 5 共用同一判斷，
        # 因為正常流程可能是：
        #
        # type 19 等待 AGV
        #       ↓
        # type 2 AGV 運行
        # --------------------------------------------------------
        if process_type_int == 19:

            existed_waiting_agv = (
                s.query(Process)
                .filter(
                    Process.material_id == material_id_int,
                    Process.process_type == 19
                )
                .order_by(
                    Process.create_at.asc(),
                    Process.id.asc()
                )
                .first()
            )

            if existed_waiting_agv is not None:
                s.commit()

                print(
                    "[createProcess] waiting AGV "
                    "duplicate skipped:",
                    {
                        "material_id":
                            material_id_int,

                        "existing_process_id":
                            existed_waiting_agv.id,

                        "existing_begin_time":
                            str(
                                existed_waiting_agv.begin_time
                            ),
                    }
                )

                return jsonify({
                    "status": True,
                    "created": False,

                    "process_id":
                        existed_waiting_agv.id,

                    "process_type": 19,

                    "skipped": True,
                    "duplicate": True,

                    "message":
                        "此批工單已有等待 AGV 紀錄，"
                        "不重複新增"
                }), 200

        # 20260818版
        # ========================================================
        # 20260818
        # process_type=29：
        # 等待 AGV（組裝區）
        #
        # 同一 material 只允許一筆 type=29。
        #
        # 防止：
        #   1. station2_agv_ready Socket 重送
        #   2. 前端重複呼叫 createProcess
        #   3. 多台電腦同時收到 Socket
        #
        # material 已在前面 with_for_update() 鎖定，
        # 所以可避免同時 INSERT。
        # ========================================================
        if process_type_int == 29:

            # ----------------------------------------------------
            # 1. 已完成入庫，不再建立等待 AGV
            # ----------------------------------------------------
            has_stockin = (
                s.query(Process.id)
                .filter(
                    Process.material_id
                    == material_id_int,

                    Process.process_type
                    == 31
                )
                .first()
            )

            if has_stockin:

                s.commit()

                return jsonify({
                    "status": True,
                    "created": False,

                    "process_id": None,
                    "process_type": 29,

                    "skipped": True,
                    "duplicate": False,

                    "message":
                        "此工單已完成入庫，"
                        "不再建立等待AGV(組裝區)紀錄"
                }), 200


            # ----------------------------------------------------
            # 2. 同一 material 已存在 type=29
            #    → 不再建立第二筆
            # ----------------------------------------------------
            existed_type29 = (
                s.query(Process)
                .filter(
                    Process.material_id
                    == material_id_int,

                    Process.process_type
                    == 29
                )
                .order_by(
                    Process.create_at.asc(),
                    Process.id.asc()
                )
                .first()
            )

            if existed_type29 is not None:

                s.commit()

                return jsonify({
                    "status": True,
                    "created": False,

                    "process_id":
                        existed_type29.id,

                    "process_type": 29,

                    "skipped": True,
                    "duplicate": True,

                    "message":
                        "此工單已有等待AGV(組裝區)紀錄，"
                        "不重複新增"
                }), 200
        #

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
            #assemble_id=assemble_id_int,
            # 20260807版
            assemble_id=(
                0
                if process_type_int in (
                    1,   # 備料
                    2,   # AGV 備料 -> 組裝
                    5,   # 堆高機 備料 -> 組裝
                    19,  # 等待 AGV 備料區
                    29,  # 等待 AGV 組裝區
                    31,  # 入庫
                )
                else assemble_id_int
            ),
            #
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


"""
# 20260731版
@createTable.route("/copyAssembleForDifference", methods=['POST'])
def copy_assemble_for_difference():
  print("copyAssembleForDifference....")

  data = request.get_json() or {}

  copy_id = data.get('copy_id')
  abnormal_qty = data.get('must_receive_qty')
  pre_must_qty = data.get('pre_must_receive_qty')

  # 按下異常鍵的員工工號
  current_user_id = str(data.get('user_id') or '').strip()

  s = Session()

  try:
    copy_id = int(copy_id)
    abnormal_qty = int(abnormal_qty or 0)
    pre_must_qty = int(pre_must_qty or 0)

    #
    if not current_user_id:
      return jsonify({
        'status': False,
        'message': '缺少按異常鍵的員工工號 user_id',
        'assemble_data': []
      }), 400
    #

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

    #
    current_user = (
      s.query(User)
      .filter(User.emp_id == current_user_id)
      .first()
    )

    if not current_user:
      return jsonify({
        'status': False,
        'message': f'找不到員工工號 {current_user_id}',
        'assemble_data': []
      }), 400
    #

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    #
    source.abnormal_qty = abnormal_qty
    source.input_abnormal_disable = True
    source.alarm_enable = False
    source.alarm_message = data.get('alarm_message') or source.alarm_message or ''

    # 記錄實際按下異常鍵的點檢人員
    source.user_id = current_user_id

    source.update_time = now_str

    print(
      "copyAssembleForDifference:",
      "source_id=", source.id,
      "user_id=", source.user_id,
      "user_name=", current_user.emp_name,
      "abnormal_qty=", abnormal_qty
    )

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
    #if pre_must_qty > 0:
    #  remain_qty = pre_must_qty
    #else:
    #  remain_qty = max(0, int(source.must_receive_qty or 0) - abnormal_qty)
    #
    # 原工序剩餘數量
    if pre_must_qty >= 0:
        remain_qty = pre_must_qty
    else:
        remain_qty = max(
            0,
            int(source.must_receive_qty or 0) - abnormal_qty
        )

    #source.must_receive_qty = remain_qty
    #source.ask_qty = remain_qty
    #source.total_ask_qty = remain_qty
    #source.must_receive_end_qty = remain_qty

    material_id = source.material_id

    #
    sync_b110_remaining_qty(
        s=s,
        material_id=material_id,
        remain_qty=remain_qty,
        now_str=now_str,
    )
    #

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
"""


'''
重點修正：

先取得 material_id / schedule_id / release_batch_no，再呼叫 helper。
只有 B110 發生異常時，同步同批正常 b1/b2/b3。
B109 發生異常時，只修改目前來源 B109，不會誤改 B110。
使用 release_batch_no，不使用 schedule_id 同步。
正確處理 pre_must_receive_qty=0。
保留點檢人員 source.user_id。
保留你目前的 B109/B110 異常返工父子關係。原始版本可對照你上傳檔案。
'''
# 20260731版, past
# 20260731版
@createTable.route("/copyAssembleForDifference", methods=['POST'])
def copy_assemble_for_difference():
    print("copyAssembleForDifference....")

    data = request.get_json(silent=True) or {}

    copy_id = data.get('copy_id')
    abnormal_qty_raw = data.get('must_receive_qty')
    pre_must_qty_raw = data.get('pre_must_receive_qty')

    # 按下異常鍵的員工工號
    current_user_id = str(
        data.get('user_id') or ''
    ).strip()

    s = Session()

    try:
        # ------------------------------------------------------------
        # 1. 基本參數轉換與檢查
        # ------------------------------------------------------------
        try:
            copy_id = int(copy_id)
        except (TypeError, ValueError):
            return jsonify({
                'status': False,
                'message': 'copy_id 格式錯誤',
                'assemble_data': []
            }), 400

        try:
            abnormal_qty = int(abnormal_qty_raw or 0)
        except (TypeError, ValueError):
            abnormal_qty = 0

        # pre_must_receive_qty 可能合法為 0，
        # 因此不能使用 int(value or 0) 判斷是否有傳入。
        pre_must_qty = None

        if pre_must_qty_raw is not None:
            try:
                pre_must_qty = int(pre_must_qty_raw)
            except (TypeError, ValueError):
                pre_must_qty = None

        if not current_user_id:
            return jsonify({
                'status': False,
                'message': '缺少按異常鍵的員工工號 user_id',
                'assemble_data': []
            }), 400

        if abnormal_qty <= 0:
            return jsonify({
                'status': False,
                'message': '異常數量必須大於 0',
                'assemble_data': []
            }), 400

        # ------------------------------------------------------------
        # 2. 鎖定來源 assemble
        # ------------------------------------------------------------
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

        source_work_num = (
            source.work_num or ''
        ).strip()

        if source_work_num not in ('B109', 'B110'):
            return jsonify({
                'status': False,
                'message': (
                    '目前只支援 B109/B110 異常返工，'
                    f'來源 work_num={source_work_num}'
                ),
                'assemble_data': []
            }), 400

        # ------------------------------------------------------------
        # 3. 檢查按異常鍵的人員
        # ------------------------------------------------------------
        current_user = (
            s.query(User)
            .filter(User.emp_id == current_user_id)
            .first()
        )

        if not current_user:
            return jsonify({
                'status': False,
                'message': f'找不到員工工號 {current_user_id}',
                'assemble_data': []
            }), 400

        now_str = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ------------------------------------------------------------
        # 4. 先取得來源識別資料
        #
        # 必須放在 sync_b110_remaining_qty() 前面。
        # ------------------------------------------------------------
        material_id = int(source.material_id)
        schedule_id = int(
            source.schedule_id or 0
        )
        release_batch_no = int(
            getattr(
                source,
                'release_batch_no',
                0
            ) or 0
        )

        material = (
            s.query(Material)
            .filter(Material.id == material_id)
            .with_for_update()
            .first()
        )

        if not material:
            return jsonify({
                'status': False,
                'message': (
                    f'找不到 material_id={material_id}'
                ),
                'assemble_data': []
            }), 404

        # ------------------------------------------------------------
        # 5. 記錄來源工序異常狀態
        # ------------------------------------------------------------
        source.abnormal_qty = abnormal_qty
        source.input_abnormal_disable = True
        source.alarm_enable = False

        source.alarm_message = (
            data.get('alarm_message')
            or source.alarm_message
            or ''
        )

        # 實際按下異常鍵的點檢人員
        source.user_id = current_user_id
        source.update_time = now_str

        print(
            "copyAssembleForDifference:",
            "source_id=", source.id,
            "material_id=", material_id,
            "schedule_id=", schedule_id,
            "release_batch_no=", release_batch_no,
            "work_num=", source_work_num,
            "user_id=", source.user_id,
            "user_name=", current_user.emp_name,
            "abnormal_qty=", abnormal_qty
        )

        rework_alarm_message = (
            data.get('alarm_message')
            or source.alarm_message
            or source.Incoming1_Abnormal
            or source.confirm_comment
            or ''
        )

        # B109 異常時，Error.vue 目前讀取此欄位
        if source_work_num == 'B109':
            source.isAssembleFirstAlarm = False
            source.isAssembleFirstAlarm_qty = (
                abnormal_qty
            )

        # ------------------------------------------------------------
        # 6. 計算正常工序剩餘數量
        #
        # 前端若有傳 pre_must_receive_qty：
        #   直接視為扣除異常後剩餘量。
        #
        # 前端若沒有傳：
        #   由來源目前應完成量 - abnormal_qty 計算。
        # ------------------------------------------------------------
        source_current_qty = max(
            int(source.must_receive_qty or 0),
            int(source.ask_qty or 0),
            int(source.must_receive_end_qty or 0),
            0
        )

        if pre_must_qty is not None:
            remain_qty = max(
                min(
                    int(pre_must_qty),
                    source_current_qty
                ),
                0
            )
        else:
            remain_qty = max(
                source_current_qty - abnormal_qty,
                0
            )

        # 防止異常數量超過目前正常數量
        if abnormal_qty > source_current_qty:
            return jsonify({
                'status': False,
                'message': (
                    f'異常數量 {abnormal_qty} '
                    f'不可大於目前應完成數量 '
                    f'{source_current_qty}'
                ),
                'assemble_data': []
            }), 400

        # ------------------------------------------------------------
        # 7. 更新來源正常工序的剩餘量
        # ------------------------------------------------------------
        source.must_receive_qty = remain_qty
        source.ask_qty = remain_qty
        source.total_ask_qty = remain_qty
        source.must_receive_end_qty = remain_qty

        updated_b110_rows = []

        # ------------------------------------------------------------
        # 8. 只有 B110 發生異常時，才同步同一批正常 B110
        #
        # 例如：
        #   b1/b2/b3 = 72
        #   b1 異常 10
        #
        # 結果：
        #   b1/b2/b3 = 62
        #
        # B109 異常不可在此同步 B110。
        # ------------------------------------------------------------
        if source_work_num == 'B110':
            updated_b110_rows = (
                sync_b110_remaining_qty(
                    s=s,
                    material_id=material_id,
                    release_batch_no=release_batch_no,
                    remain_qty=remain_qty,
                    now_str=now_str
                )
            )

        print(
            "[SYNC NORMAL REMAINING QTY]",
            {
                "source_id": source.id,
                "source_work_num": source_work_num,
                "material_id": material_id,
                "schedule_id": schedule_id,
                "release_batch_no": release_batch_no,
                "source_current_qty": source_current_qty,
                "abnormal_qty": abnormal_qty,
                "remain_qty": remain_qty,
                "updated_b110_rows": [
                    {
                        "id": row.id,
                        "schedule_id": row.schedule_id,
                        "release_batch_no": (
                            getattr(
                                row,
                                'release_batch_no',
                                0
                            )
                        ),
                        "qty": row.must_receive_qty
                    }
                    for row in updated_b110_rows
                ]
            }
        )

        # ------------------------------------------------------------
        # 9. 若來源沒有 schedule_id，尋找可用 schedule_id
        # ------------------------------------------------------------
        if schedule_id <= 0:
            schedule_id = (
                s.query(Assemble.schedule_id)
                .filter(
                    Assemble.material_id
                    == material_id
                )
                .filter(
                    Assemble.schedule_id.isnot(None)
                )
                .filter(
                    Assemble.schedule_id > 0
                )
                .order_by(
                    Assemble.id.desc()
                )
                .scalar()
            ) or 0

        # ------------------------------------------------------------
        # 10. 防止同一來源、同一異常量重複建立返工列
        # ------------------------------------------------------------
        existed = (
            s.query(Assemble)
            .filter(
                Assemble.material_id == material_id
            )
            .filter(
                Assemble.is_copied_from_id
                == source.id
            )
            .filter(
                Assemble.must_receive_qty
                == abnormal_qty
            )
            .filter(
                Assemble.work_num.in_([
                    'B109',
                    'B110'
                ])
            )
            .filter(
                Assemble.reason == '異常返工'
            )
            .order_by(
                Assemble.id.asc()
            )
            .all()
        )

        if existed:
            s.commit()

            return jsonify({
                'status': True,
                'message': '返工列已存在，不重複建立',
                'assemble_data': [
                    row.id for row in existed
                ],
                'remain_qty': remain_qty
            }), 200

        # ------------------------------------------------------------
        # 11. 建立異常返工列共用函式
        # ------------------------------------------------------------
        def make_rework_row(
            work_num,
            step_code,
            show_code,
            show_in_begin=True,
            target_schedule_id=None,
            parent_id=None
        ):
            new_row = Assemble(
                material_id=source.material_id,
                material_num=source.material_num,
                material_comment=(
                    source.material_comment
                ),
                seq_num=source.seq_num,

                work_num=work_num,
                process_step_code=step_code,

                Incoming1_Abnormal=(
                    rework_alarm_message
                ),

                schedule_id=(
                    target_schedule_id
                    if target_schedule_id is not None
                    else schedule_id
                ),

                must_receive_qty=abnormal_qty,
                must_receive_end_qty=abnormal_qty,
                ask_qty=abnormal_qty,
                total_ask_qty=abnormal_qty,
                total_ask_qty_end=0,

                abnormal_qty=0,

                completed_qty=0,
                total_completed_qty=0,
                allOk_qty=0,

                # 返工列尚未開始，未來操作員可能不同
                user_id='',
                writer_id=None,
                write_date=None,

                good_qty=0,
                total_good_qty=0,
                non_good_qty=0,
                meinh_qty=0,

                reason='異常返工',
                confirm_comment=(
                    rework_alarm_message
                ),
                is_assemble_ok=False,

                currentStartTime=None,
                currentEndTime=None,

                input_disable=False,
                input_end_disable=False,
                input_allOk_disable=False,
                input_abnormal_disable=False,

                isAssembleStationShow=(
                    show_in_begin
                ),
                isWarehouseStationShow=False,

                # 返工列本身不是 Error.vue 原始異常來源
                alarm_enable=True,
                alarm_message=(
                    rework_alarm_message
                ),

                isAssembleFirstAlarm=False,
                isAssembleFirstAlarm_message='',
                isAssembleFirstAlarm_qty=0,

                whichStation=1,

                show1_ok=1,
                show2_ok=show_code,
                show3_ok=show_code,

                update_time=now_str,
                create_at=now_str,

                is_copied_from_id=(
                    parent_id
                    if parent_id is not None
                    else source.id
                ),

                # 異常返工列獨立處理，不加入正常 release batch
                release_batch_no=0
            )

            s.add(new_row)
            s.flush()

            return new_row

        new_rows = []

        # ------------------------------------------------------------
        # 12. 解析 material.process_steps
        # ------------------------------------------------------------
        raw_steps = material.process_steps

        try:
            if isinstance(raw_steps, str):
                process_steps = json.loads(
                    raw_steps or "{}"
                )

            elif isinstance(raw_steps, dict):
                process_steps = raw_steps

            else:
                process_steps = (
                    default_process_steps()
                )

        except Exception:
            process_steps = (
                default_process_steps()
            )

        assemble_checked_ids = [
            int(step.get("id"))
            for step in (
                process_steps.get("assemble")
                or []
            )
            if step.get("checked")
            and not step.get("deleted", False)
            and step.get("id") is not None
        ]

        check_checked_ids = [
            int(step.get("id"))
            for step in (
                process_steps.get("check")
                or []
            )
            if step.get("checked")
            and not step.get("deleted", False)
            and step.get("id") is not None
        ]

        has_assemble_selected = (
            len(assemble_checked_ids) > 0
        )

        # ------------------------------------------------------------
        # 13. B109 異常
        #
        # 組裝異常：
        # 只建立一筆新的 B109 異常返工列。
        # ------------------------------------------------------------
        if source_work_num == 'B109':
            new_rows.append(
                make_rework_row(
                    work_num='B109',
                    step_code=3,
                    show_code=3,
                    show_in_begin=True,
                    target_schedule_id=schedule_id,
                    parent_id=source.id
                )
            )

        # ------------------------------------------------------------
        # 14. B110 異常
        # ------------------------------------------------------------
        elif source_work_num == 'B110':
            if has_assemble_selected:
                # ----------------------------------------------------
                # 有組裝工序：
                #
                # b1 發生異常
                #   ↓
                # 建立 a1-異常，立即顯示
                #   ↓
                # 建立 b1-異常，先隱藏
                #   ↓
                # a1-異常完成後再開啟 b1-異常
                # ----------------------------------------------------
                first_assemble_schedule_id = min(
                    assemble_checked_ids
                )

                new_b109 = make_rework_row(
                    work_num='B109',
                    step_code=3,
                    show_code=3,
                    show_in_begin=True,
                    target_schedule_id=(
                        first_assemble_schedule_id
                    ),
                    parent_id=source.id
                )

                new_rows.append(new_b109)

                new_b110 = make_rework_row(
                    work_num='B110',
                    step_code=2,
                    show_code=5,
                    show_in_begin=False,
                    target_schedule_id=schedule_id,

                    # B110 異常返工列指向 B109 異常返工列
                    parent_id=new_b109.id
                )

                new_rows.append(new_b110)

            else:
                # ----------------------------------------------------
                # 工單只有檢驗工序：
                # 直接建立原檢驗工序的異常返工列。
                # ----------------------------------------------------
                new_rows.append(
                    make_rework_row(
                        work_num='B110',
                        step_code=2,
                        show_code=5,
                        show_in_begin=True,
                        target_schedule_id=schedule_id,
                        parent_id=source.id
                    )
                )

        # ------------------------------------------------------------
        # 15. Material 回到 Begin 可操作狀態
        # ------------------------------------------------------------
        material.process_step_enable = True
        material.hasStarted = False
        material.startStatus = False

        material.isOpen = False
        material.isOpenEmpId = ''

        material.isAssembleStationShow = True
        material.isAssembleStation3TakeOk = False
        material.whichStation = 2

        if source_work_num == 'B109':
            material.show1_ok = 1
            material.show2_ok = 3
            material.show3_ok = 3

        else:
            # B110 異常後回 B109 異常返工
            if has_assemble_selected:
                material.show1_ok = 1
                material.show2_ok = 3
                material.show3_ok = 3
            else:
                material.show1_ok = 1
                material.show2_ok = 5
                material.show3_ok = 5

        # ------------------------------------------------------------
        # 16. 寫入資料庫
        # ------------------------------------------------------------
        s.commit()

        return jsonify({
            'status': True,
            'message': '異常返工流程已建立',

            'source_id': source.id,
            'source_work_num': source_work_num,

            'material_id': material_id,
            'schedule_id': schedule_id,
            'release_batch_no': release_batch_no,

            'abnormal_qty': abnormal_qty,
            'remain_qty': remain_qty,

            'synced_b110_ids': [
                row.id
                for row in updated_b110_rows
            ],

            'assemble_data': [
                row.id for row in new_rows
            ]
        }), 200

    except Exception as e:
        s.rollback()

        print(
            "copyAssembleForDifference ERROR:",
            repr(e)
        )

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


# 20260811版
# ------------------------------------------------------------
# 檢料完成但仍有缺料：
#
# 1. 將 receive=False 的 BOM 搬到新的 Material copy
# 2. 原 Material 保留 receive=True 的 BOM
# 3. copy 繼承原工單的應備數量
# 4. 絕對不可把原 Assemble.must_receive_qty 清成 0
# 5. copy 繼承 merge_enabled
# 6. 防止同一來源重複建立缺料 copy
# ------------------------------------------------------------
@createTable.route("/copyMaterialAndBom", methods=["POST"])
def copy_material_and_bom():

    print("copyMaterialAndBom....")

    request_data = (request.get_json(silent=True) or {})

    print("request_data:", request_data)

    # --------------------------------------------------------
    # 1. 取得參數
    # --------------------------------------------------------
    try:
        _copy_id = int(
            request_data.get("copy_id")
            or 0
        )

        # 前端目前有傳 delivery_qty
        _delivery_qty = int(
            request_data.get("delivery_qty")
            or 0
        )

        _total_delivery_qty_raw = (
            request_data.get(
                "total_delivery_qty"
            )
        )

        _allOk_qty_raw = (
            request_data.get(
                "allOk_qty"
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return jsonify({
            "success": False,
            "material_data": {},
            "message":
                "copy_id / delivery_qty 格式錯誤",
        }), 400

    _show2_ok = int(request_data.get("show2_ok", 2) or 2)

    _shortage_note = str(
        request_data.get(
            "shortage_note",
            "",
        )
        or ""
    )

    _merge_enabled = _normalize_bool(
        request_data.get(
            "merge_enabled",
            True,
        ),
        default=True,
    )

    if _copy_id <= 0:
        return jsonify({
            "success": False,
            "material_data": {},
            "message":
                "copy_id 不可為 0",
        }), 400

    s = Session()

    try:

        # ----------------------------------------------------
        # 2. 鎖定來源 Material
        # ----------------------------------------------------
        existing_material = (
            s.query(Material)
            .filter(
                Material.id
                == _copy_id
            )
            .with_for_update()
            .one_or_none()
        )

        if not existing_material:
            s.rollback()

            return jsonify({
                "success": False,
                "material_data": {},
                "message":
                    f"找不到 Material "
                    f"id={_copy_id}",
            }), 404

        # ----------------------------------------------------
        # 3. 本工單真正的應備數量
        #
        # 前端目前 copyMaterialAndBom 沒有固定傳
        # total_delivery_qty，所以：
        #
        # request 有傳 -> 優先使用
        # request 沒傳 -> 使用來源 Material.total_delivery_qty
        #
        # 缺料 copy 是 BOM 拆分，
        # 不是一般數量拆批，因此不能直接使用
        # material_qty - delivery_qty。
        # ----------------------------------------------------
        if (
            _total_delivery_qty_raw
            not in (
                None,
                "",
            )
        ):
            copy_required_qty = int(
                _total_delivery_qty_raw
            )
        else:
            copy_required_qty = int(
                existing_material
                .total_delivery_qty
                or existing_material
                .material_qty
                or 0
            )

        copy_required_qty = max(
            copy_required_qty,
            0,
        )

        # ----------------------------------------------------
        # 4. allOk_qty
        # ----------------------------------------------------
        if (
            _allOk_qty_raw
            not in (
                None,
                "",
            )
        ):
            _allOk_qty = int(
                _allOk_qty_raw
            )
        else:
            _allOk_qty = None

        # ----------------------------------------------------
        # 5. 找出真正缺料的 BOM
        # ----------------------------------------------------
        missing_boms = (
            s.query(Bom)
            .filter(
                Bom.material_id
                == existing_material.id,
                Bom.receive.is_(
                    False
                ),
            )
            .order_by(
                Bom.seq_num.asc(),
                Bom.id.asc(),
            )
            .all()
        )

        if not missing_boms:
            s.rollback()

            return jsonify({
                "success": False,
                "material_data": {},
                "message": (
                    "目前已無缺料 BOM，"
                    "不建立新的 Material copy"
                ),
            }), 200

        # ----------------------------------------------------
        # 6. 防止重複建立 copy
        # ----------------------------------------------------
        existing_copy = (
            s.query(Material)
            .filter(
                Material.is_copied_from_id
                == existing_material.id
            )
            .order_by(
                Material.id.asc()
            )
            .first()
        )

        if existing_copy:
            s.rollback()

            return jsonify({
                "success": False,
                "return_value": False,
                "material_data":
                    existing_copy.to_dict(),
                "message": (
                    f"來源 Material"
                    f"({existing_material.id}) "
                    f"已存在缺料 copy"
                    f"({existing_copy.id})，"
                    "不重複建立。"
                ),
            }), 200

        # ----------------------------------------------------
        # 7. 建立缺料 Material copy
        #
        # copy 仍留在備料區。
        # 不要複製來源 Material 已經進站之後的流程狀態。
        # ----------------------------------------------------
        new_material = Material(

            abnormal_cause_id=
                existing_material
                .abnormal_cause_id,

            order_num=
                existing_material
                .order_num,

            material_num=
                existing_material
                .material_num,

            material_comment=
                existing_material
                .material_comment,

            # 訂單原始數量保留
            material_qty=
                existing_material
                .material_qty,

            material_date=
                existing_material
                .material_date,

            material_delivery_date=
                existing_material
                .material_delivery_date,

            # ---------------------------------------------
            # copy 是尚待後續補料，
            # 所以本批實際送料量先為 0
            # ---------------------------------------------
            delivery_qty=0,

            total_delivery_qty=
                copy_required_qty,

            assemble_qty=(
                _allOk_qty
                if _allOk_qty
                is not None
                else 0
            ),

            # ---------------------------------------------
            # copy 留在備料區
            # ---------------------------------------------
            isTakeOk=False,
            isShow=False,
            isAssembleStationShow=False,

            whichStation=1,

            show1_ok=1,
            show2_ok=_show2_ok,
            show3_ok=0,

            shortage_note=
                _shortage_note,

            # 缺料 copy
            isLackMaterial=0,

            # ---------------------------------------------
            # 併單設定直接繼承
            # 不必再靠前端補一次才正確
            # ---------------------------------------------
            #merge_enabled=
            #    _merge_enabled,
            # 20260812版
            merge_enabled=_normalize_bool(
                existing_material.merge_enabled,
                default=True,
            ),
            # 20260812版 remove
            #merge_enable=
            #    bool(
            #        existing_material
            #        .merge_enabled
            #    ),

            move_by_automatic_or_manual=
                existing_material
                .move_by_automatic_or_manual,

            move_by_automatic_or_manual_2=
                existing_material
                .move_by_automatic_or_manual_2,

            move_by_process_type=
                existing_material
                .move_by_process_type,

            process_steps=
                existing_material
                .process_steps,

            process_step_enable=
                existing_material
                .process_step_enable,

            isOpen=False,
            isOpenEmpId="",
            hasStarted=False,
            startStatus=0,

            update_time=
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            # 關鍵：
            # 記住來源 parent
            is_copied_from_id=
                existing_material.id,
        )

        s.add(
            new_material
        )

        # 先取得 new material id
        s.flush()

        print(
            "[copyMaterialAndBom]",
            "new_id=",
            new_material.id,
            "source_id=",
            existing_material.id,
            "delivery_qty=",
            _delivery_qty,
            "copy_required_qty=",
            copy_required_qty,
        )

        # ----------------------------------------------------
        # 8. 將缺料 BOM 複製到新 material
        # ----------------------------------------------------
        missing_bom_ids = []

        for bom in missing_boms:

            new_bom = Bom(

                material_id=
                    new_material.id,

                seq_num=
                    bom.seq_num,

                material_num=
                    bom.material_num,

                material_comment=
                    bom.material_comment,

                req_qty=
                    bom.req_qty,

                pick_qty=
                    bom.pick_qty,

                non_qty=
                    bom.non_qty,

                lack_qty=
                    bom.lack_qty,

                lack=
                    bom.lack,

                lack_bom_qty=
                    bom.lack_bom_qty,

                receive=
                    bom.receive,

                isPickOK=
                    bom.isPickOK,

                start_date=
                    bom.start_date,
            )

            s.add(
                new_bom
            )

            missing_bom_ids.append(
                bom.id
            )

        # flush 新 BOM
        s.flush()

        # ----------------------------------------------------
        # 9. 從 parent 刪掉已搬走的 receive=False BOM
        #
        # 用 ID 精確刪除，
        # 不要再次用模糊條件刪除。
        # ----------------------------------------------------
        if missing_bom_ids:

            (
                s.query(Bom)
                .filter(
                    Bom.id.in_(
                        missing_bom_ids
                    )
                )
                .delete(
                    synchronize_session=False
                )
            )

        # ----------------------------------------------------
        # 10. 複製 Assemble 到缺料 copy
        #
        # ★ 重要：
        # copy 的 must_receive_qty 使用應備數量。
        #
        # ★ 更重要：
        # 絕對不要在這裡修改原 asm.must_receive_qty。
        #
        # 舊程式：
        #
        #   asm.must_receive_qty = _delivery_qty
        #
        # 會造成原本 479/480 被清成 0。
        # ----------------------------------------------------
        source_assemble_rows = (
            s.query(Assemble)
            .filter(
                Assemble.material_id
                == existing_material.id
            )
            .order_by(
                Assemble.id.asc()
            )
            .all()
        )

        for asm in source_assemble_rows:

            new_asm = Assemble(

                material_id=
                    new_material.id,

                material_num=
                    asm.material_num,

                material_comment=
                    asm.material_comment,

                seq_num=
                    asm.seq_num,

                work_num=
                    asm.work_num,

                process_step_code=
                    asm.process_step_code,

                # -----------------------------------------
                # 缺料 copy 的應領量
                # -----------------------------------------
                must_receive_qty=
                    copy_required_qty,

                user_id="",

                # copy 尚未送到 Begin
                isAssembleStationShow=False,
                isWarehouseStationShow=False,

                whichStation=1,

                show1_ok=1,
                show2_ok=0,
                show3_ok=0,

                # copy 尚未排程
                schedule_id=0,

                release_batch_no=0,
            )

            s.add(
                new_asm
            )

            # ------------------------------------------------
            # ★★★ 不要再有下面這段 ★★★
            #
            # if asm.must_receive_qty is not None:
            #     asm.must_receive_qty = _delivery_qty
            #
            # parent Assemble 的狀態完全不動。
            # ------------------------------------------------

        # ----------------------------------------------------
        # 11. 最後提交
        # ----------------------------------------------------
        s.commit()

        print(
            "[copyMaterialAndBom] success:",
            {
                "source_material_id":
                    existing_material.id,

                "new_material_id":
                    new_material.id,

                "delivery_qty":
                    _delivery_qty,

                "copy_required_qty":
                    copy_required_qty,

                "missing_bom_count":
                    len(
                        missing_bom_ids
                    ),

                "assemble_count":
                    len(
                        source_assemble_rows
                    ),
            }
        )

        return jsonify({
            "success": True,
            "return_value": True,

            "material_data":
                new_material.to_dict(),

            "source_material_id":
                existing_material.id,

            "new_material_id":
                new_material.id,

            "delivery_qty":
                _delivery_qty,

            "copy_required_qty":
                copy_required_qty,

            "missing_bom_count":
                len(
                    missing_bom_ids
                ),

            "message":
                "缺料 Material copy 建立成功",
        }), 200

    except Exception as e:

        s.rollback()

        print(
            "copyMaterialAndBom Error:",
            str(e),
        )

        logger.exception(
            "copyMaterialAndBom failed"
        )

        return jsonify({
            "success": False,
            "return_value": False,
            "material_data": {},
            "error":
                "錯誤! 資料新增複製沒有成功...",
            "detail":
                str(e),
        }), 500

    finally:
        s.close()


"""
# 20260810版
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

  _merge_enabled = request_data['merge_enabled']

  s = Session()

  try:
    # 根據 copy_id 尋找現有的 Material 資料
    existing_material = s.query(Material).filter_by(id=_copy_id).first()
    if not existing_material:
      raise ValueError(f"找不到 ID 為 {_copy_id} 的資料")

    # 20260810版 add
    # ------------------------------------------------------------
    # 只有真正存在 receive=False 的 BOM，才允許建立缺料 copy
    # ------------------------------------------------------------
    missing_boms = (
        s.query(Bom)
        .filter(
            Bom.material_id == existing_material.id,
            Bom.receive.is_(False),
        )
        .all()
    )

    if not missing_boms:
        s.rollback()

        return jsonify({
            "success": False,
            "material_data": {},
            "message": (
                "目前已無缺料 BOM，"
                "不建立新的 Material copy"
            ),
        }), 200
    # 20260810版 add
    # =====================================================
    # ② 檢查是否已經存在缺料 copy
    # =====================================================

    existing_copy = (
        s.query(Material)
        .filter(
            Material.is_copied_from_id == existing_material.id
        )
        .first()
    )

    if existing_copy:
        s.rollback()

        return jsonify({
            "return_value": False,
            "material_data": existing_copy.to_dict(),
            "message":
                f"來源 Material({existing_material.id}) "
                f"已存在缺料 copy({existing_copy.id})，"
                "不重複建立。"
        }), 200
    #

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

      # 新資料繼承主資料的併單設定, 20260806版 add
      #merge_enabled=bool(existing_material.merge_enabled),
      #merge_enabled=_normalize_bool(
      #    existing_material.merge_enabled,
      #    default=True,
      #),

      is_copied_from_id=existing_material.id,  # ✅ 設定來源
    )

    s.add(new_material)   # 加入新的 Material 資料紀錄
    s.flush()             # 獲取新的 Material ID (new_id)

    print(f"Duplicated assemble: new_id={new_material.id} from original_id={existing_material.id}")

    # 複製 receive=True 的 Bom 資料
    #for bom in [b for b in existing_material._bom if not b.receive]:
    # 20260810版
    # ------------------------------------------------------------
    # 將真正缺料的 BOM 搬到新 material
    # ------------------------------------------------------------
    for bom in missing_boms:
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
"""


"""
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
"""


# 20260806版
# copy material data table
@createTable.route(
    "/copyMaterial",
    methods=["POST"]
)
def copy_material():
    print("copyMaterial....")

    request_data = (
        request.get_json(silent=True)
        or {}
    )

    print(
        "request_data:",
        request_data
    )

    try:
        _copy_id = int(
            request_data.get(
                "copy_id"
            )
            or 0
        )

        _delivery_qty = int(
            request_data.get(
                "delivery_qty"
            )
            or 0
        )

        raw_total_delivery_qty = (
            request_data.get(
                "total_delivery_qty"
            )
        )

        _total_delivery_qty = (
            int(
                raw_total_delivery_qty
                or 0
            )
            if raw_total_delivery_qty
            is not None
            else None
        )

        raw_all_ok_qty = (
            request_data.get(
                "allOk_qty"
            )
        )

        _allOk_qty = (
            int(
                raw_all_ok_qty
                or 0
            )
            if raw_all_ok_qty
            is not None
            else None
        )

        _show2_ok = int(
            request_data.get(
                "show2_ok"
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        return jsonify({
            "status": False,
            "message":
                "copy_id / 數量格式錯誤",
        }), 400

    _shortage_note = str(
        request_data.get(
            "shortage_note"
        )
        or ""
    )

    if _copy_id <= 0:
        return jsonify({
            "status": False,
            "message":
                "copy_id 不正確",
        }), 400

    return_value = True
    s = Session()

    try:
        # ----------------------------------------------------
        # 1. 鎖定來源 Material
        #
        # 避免 A、B 電腦或雙擊同時建立子批次。
        # ----------------------------------------------------
        existing_material = (
            s.query(Material)
            .filter(
                Material.id ==
                _copy_id
            )
            .with_for_update()
            .one_or_none()
        )

        if not existing_material:
            return jsonify({
                "status": False,
                "message":
                    f"找不到 material_id={_copy_id}",
            }), 404

        # ----------------------------------------------------
        # 2. 剩餘批次模式
        #
        # 前端傳入：
        # delivery_qty       = 本批已送數量
        # total_delivery_qty = 剩餘數量
        #
        # 剩餘量 <= 0 時，禁止建立 copy。
        # ----------------------------------------------------
        is_remaining_batch = (
            _total_delivery_qty
            is not None
            and
            _allOk_qty is None
        )

        if (
            is_remaining_batch
            and
            _total_delivery_qty <= 0
        ):
            existing_material.show2_ok = 3

            s.commit()

            return jsonify({
                "status": True,
                "created": False,
                "duplicate": False,
                "material_data": {
                    "id":
                        existing_material.id,
                },
                "remaining_qty": 0,
                "message":
                    "剩餘數量為0，不建立新批次",
            }), 200

        # ----------------------------------------------------
        # 3. 防止同一來源重複建立子批次
        #
        # 只針對剩餘批次模式判斷。
        # 異常、返工等其他 copy 用途不受影響。
        # ----------------------------------------------------
        if is_remaining_batch:
            existing_child = (
                s.query(Material)
                .filter(
                    Material
                    .is_copied_from_id ==
                    existing_material.id
                )
                .filter(
                    Material.isAllOk
                    .isnot(True)
                )
                .order_by(
                    Material.id.asc()
                )
                .first()
            )

            if existing_child:
                s.commit()

                print(
                    "[copyMaterial] "
                    "duplicate child skipped:",
                    {
                        "source_id":
                            existing_material.id,
                        "existing_child_id":
                            existing_child.id,
                    }
                )

                return jsonify({
                    "status": True,
                    "created": False,
                    "duplicate": True,
                    "material_data": {
                        "id":
                            existing_child.id,
                    },
                    "remaining_qty":
                        int(
                            existing_child
                            .total_delivery_qty
                            or 0
                        ),
                    "message":
                        "此來源工單已建立剩餘批次",
                }), 200

        # ----------------------------------------------------
        # 4. 決定新批次數量
        # ----------------------------------------------------
        if is_remaining_batch:
            new_batch_qty = int(
                _total_delivery_qty
                or 0
            )
        elif _allOk_qty is not None:
            new_batch_qty = int(
                _allOk_qty
                or 0
            )
        else:
            new_batch_qty = int(
                existing_material
                .material_qty
                or 0
            )

        if new_batch_qty <= 0:
            return jsonify({
                "status": False,
                "message":
                    "新批次數量不可小於等於0",
            }), 400

        # ----------------------------------------------------
        # 5. 建立新 Material
        # ----------------------------------------------------
        new_material = Material(
            abnormal_cause_id=
                existing_material
                .abnormal_cause_id,

            order_num=
                existing_material
                .order_num,

            material_num=
                existing_material
                .material_num,

            material_comment=
                existing_material
                .material_comment,

            # 關鍵修正：
            # 剩餘批次不可照抄原始完整數量。
            material_qty=
                new_batch_qty,

            # 建議一併填入，避免新批次 delivery_qty
            # 仍為 NULL 或沿用錯誤值。
            delivery_qty=
                new_batch_qty,

            material_date=
                existing_material
                .material_date,

            material_delivery_date=
                existing_material
                .material_delivery_date,

            isTakeOk=True,

            show2_ok=
                _show2_ok,

            total_delivery_qty=(
                _total_delivery_qty
                if is_remaining_batch
                else
                existing_material
                .total_delivery_qty
            ),

            assemble_qty=(
                _allOk_qty
                if (
                    _allOk_qty
                    is not None
                    and
                    _total_delivery_qty
                    is None
                )
                else 0
            ),

            shortage_note=
                _shortage_note,

            update_time=
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            is_copied_from_id=
                existing_material.id,
        )

        s.add(new_material)
        s.flush()

        print(
            "Duplicated material:",
            {
                "new_id":
                    new_material.id,
                "source_id":
                    existing_material.id,
                "new_batch_qty":
                    new_batch_qty,
            }
        )

        # ----------------------------------------------------
        # 6. 複製 BOM
        # ----------------------------------------------------
        for bom in (
            existing_material._bom
            or []
        ):
            new_bom = Bom(
                material_id=
                    new_material.id,

                seq_num=
                    bom.seq_num,

                material_num=
                    bom.material_num,

                material_comment=
                    bom.material_comment,

                req_qty=
                    bom.req_qty,

                pick_qty=
                    bom.pick_qty,

                non_qty=
                    bom.non_qty,

                lack_qty=
                    bom.lack_qty,

                receive=
                    bom.receive,

                lack=
                    bom.lack,

                isPickOK=
                    bom.isPickOK,

                start_date=
                    bom.start_date,
            )

            s.add(new_bom)

        # ----------------------------------------------------
        # 7. 複製 Assemble
        # ----------------------------------------------------
        for asm in (
            existing_material._assemble
            or []
        ):
            new_asm = Assemble(
                material_id=
                    new_material.id,

                material_num=
                    asm.material_num,

                material_comment=
                    asm.material_comment,

                seq_num=
                    asm.seq_num,

                work_num=
                    asm.work_num,

                process_step_code=
                    asm.process_step_code,

                # 關鍵修正：
                # 新批次應領量使用新批次數量。
                must_receive_qty=
                    new_batch_qty,

                user_id="",
            )

            s.add(new_asm)

            # 原資料改成本批實際送料數量
            if (
                asm.must_receive_qty
                is not None
            ):
                asm.must_receive_qty = (
                    _delivery_qty
                )

        s.commit()

        print(
            "Material copy successfully."
        )

        return jsonify({
            "status": True,
            "created": True,
            "duplicate": False,
            "material_data": {
                "id":
                    new_material.id,
            },
            "remaining_qty":
                new_batch_qty,
        }), 200

    except Exception as error:
        s.rollback()

        print(
            "copyMaterial Error:",
            repr(error)
        )

        return_value = False

        return jsonify({
            "status":
                return_value,

            "created":
                False,

            "duplicate":
                False,

            "message":
                "錯誤! 資料新增複製沒有成功...",

            "detail":
                str(error),
        }), 500

    finally:
        s.close()

"""
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

            # 20260809版

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
"""


# 20260809版
@createTable.route("/createProduct", methods=["POST"])
def create_product():

    # ============================================================
    # 組裝線成品入庫
    #
    # 一般工單：
    #   1 material
    #   1 assemble
    #   1 process_type=31
    #   1 Product
    #
    # 缺料、不併單、多批 material：
    #
    #   material 152
    #   material 160
    #   material 161
    #
    #   Warehouse 顯示前已合併成：
    #
    #   group_material_ids = [152,160,161]
    #   group_assemble_ids = [395,398,399]
    #
    # 入庫時：
    #
    #   process_type=31 只建立 1 筆
    #   Product         只建立 1 筆
    #
    # 但：
    #
    #   material 152 / 160 / 161
    #   assemble 相關列
    #
    # 全部同步成入庫完成。
    #
    # 歷史 material / assemble / process 不刪除。
    # ============================================================

    print("createProduct...")

    def safe_int(value):
        try:
            return int(value or 0)
        except (
            TypeError,
            ValueError,
        ):
            return 0


    def safe_bool(value):
        if isinstance(value, bool):
            return value

        if isinstance(value, int):
            return value == 1

        if isinstance(value, str):
            return (
                value.strip().lower()
                in (
                    "1",
                    "true",
                    "yes",
                    "y",
                )
            )

        return False


    s = Session()

    try:

        payload = (
            request.get_json(
                silent=True
            )
            or {}
        )


        # ========================================================
        # 1. 支援單筆 / 批次
        # ========================================================
        raw_items = payload.get(
            "items"
        )

        if raw_items is None:
            raw_items = [
                payload
            ]

        if (
            not isinstance(
                raw_items,
                list
            )
            or not raw_items
        ):
            return jsonify({
                "status": False,
                "error": (
                    "payload 應為物件或 "
                    "{'items': [...]}，"
                    "且不可為空"
                )
            }), 400


        # ========================================================
        # 2. Normalize + 驗證輸入
        # ========================================================
        errors = []

        normalized_items = []


        for idx, item in enumerate(
            raw_items
        ):

            if not isinstance(
                item,
                dict
            ):
                errors.append({
                    "index": idx,
                    "error":
                        "每一筆 items 必須是物件"
                })
                continue


            material_id = (
                _normalize_int(
                    item.get(
                        "material_id"
                    ),
                    0
                )
            )

            assemble_id = (
                _normalize_int(
                    item.get(
                        "assemble_id"
                    ),
                    0
                )
            )

            process_id = (
                _normalize_int(
                    item.get(
                        "process_id"
                    ),
                    0
                )
            )

            all_ok_qty = (
                _normalize_int(
                    item.get(
                        "allOk_qty"
                    ),
                    0
                )
            )


            if material_id <= 0:
                errors.append({
                    "index": idx,
                    "error":
                        "material_id 必須是大於 0 的整數"
                })


            if all_ok_qty <= 0:
                errors.append({
                    "index": idx,
                    "error":
                        "allOk_qty 入庫數量必須大於 0"
                })


            # ----------------------------------------------------
            # group_material_ids
            # ----------------------------------------------------
            raw_group_material_ids = (
                item.get(
                    "group_material_ids"
                )
            )

            group_material_ids = []


            if isinstance(
                raw_group_material_ids,
                list
            ):

                for value in (
                    raw_group_material_ids
                ):

                    mid = (
                        _normalize_int(
                            value,
                            0
                        )
                    )

                    if (
                        mid > 0
                        and mid
                        not in group_material_ids
                    ):
                        group_material_ids.append(
                            mid
                        )


            # 一般工單 fallback
            if not group_material_ids:
                group_material_ids = [
                    material_id
                ]


            # representative 一定包含
            if (
                material_id
                not in group_material_ids
            ):
                group_material_ids.insert(
                    0,
                    material_id
                )


            # ----------------------------------------------------
            # group_assemble_ids
            # ----------------------------------------------------
            raw_group_assemble_ids = (
                item.get(
                    "group_assemble_ids"
                )
            )

            group_assemble_ids = []


            if isinstance(
                raw_group_assemble_ids,
                list
            ):

                for value in (
                    raw_group_assemble_ids
                ):

                    aid = (
                        _normalize_int(
                            value,
                            0
                        )
                    )

                    if (
                        aid > 0
                        and aid
                        not in group_assemble_ids
                    ):
                        group_assemble_ids.append(
                            aid
                        )


            # ----------------------------------------------------
            # merged shortage
            # ----------------------------------------------------
            is_merged_shortage_order = (
                safe_bool(
                    item.get(
                        "is_merged_shortage_order"
                    )
                )
                and len(
                    group_material_ids
                ) > 1
            )


            normalized_items.append({
                "index":
                    idx,

                "raw":
                    item,

                "material_id":
                    material_id,

                "assemble_id":
                    assemble_id,

                "process_id":
                    process_id,

                "allOk_qty":
                    all_ok_qty,

                "is_merged_shortage_order":
                    is_merged_shortage_order,

                "group_material_ids":
                    group_material_ids,

                "group_assemble_ids":
                    group_assemble_ids,
            })


        if errors:
            return jsonify({
                "status": False,
                "errors": errors
            }), 400


        # ========================================================
        # 3. 驗證所有 material 存在
        # ========================================================
        material_ids = sorted({
            mid
            for row
            in normalized_items
            for mid
            in row.get(
                "group_material_ids",
                [
                    row[
                        "material_id"
                    ]
                ]
            )
        })


        existing_material_ids = {
            int(row[0])
            for row in (
                s.query(
                    Material.id
                )
                .filter(
                    Material.id.in_(
                        material_ids
                    )
                )
                .all()
            )
        }


        for row in (
            normalized_items
        ):

            missing_ids = [
                mid
                for mid
                in row.get(
                    "group_material_ids",
                    [
                        row[
                            "material_id"
                        ]
                    ]
                )
                if mid
                not in existing_material_ids
            ]

            if missing_ids:
                errors.append({
                    "index":
                        row["index"],

                    "error": (
                        "找不到 material_id："
                        f"{missing_ids}"
                    )
                })


        if errors:
            return jsonify({
                "status": False,
                "errors": errors
            }), 400


        # ========================================================
        # 4. 開始處理
        # ========================================================
        created_products = []

        result_items = []


        # 同一 merged group 不可在同一 request
        # 重複處理
        processed_merged_groups = set()


        now_dt = datetime.now()

        now_str = (
            now_dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )


        for row in normalized_items:

            idx = row["index"]

            item = row["raw"]

            material_id = (
                row["material_id"]
            )

            assemble_id = (
                row["assemble_id"]
            )

            process_id_to_use = (
                row["process_id"]
            )

            add_qty = (
                row["allOk_qty"]
            )


            is_merged_shortage_order = (
                bool(
                    row.get(
                        "is_merged_shortage_order",
                        False
                    )
                )
            )


            group_material_ids = sorted({
                int(mid)
                for mid
                in row.get(
                    "group_material_ids",
                    [
                        material_id
                    ]
                )
                if int(
                    mid or 0
                ) > 0
            })


            if not group_material_ids:
                group_material_ids = [
                    material_id
                ]


            group_assemble_ids = sorted({
                int(aid)
                for aid
                in row.get(
                    "group_assemble_ids",
                    []
                )
                if int(
                    aid or 0
                ) > 0
            })


            # ----------------------------------------------------
            # merged group 只處理一次
            # ----------------------------------------------------
            if is_merged_shortage_order:

                merge_key = tuple(
                    group_material_ids
                )

                if (
                    merge_key
                    in processed_merged_groups
                ):
                    print(
                        "[createProduct] "
                        "skip duplicated merged group:",
                        merge_key
                    )
                    continue

                processed_merged_groups.add(
                    merge_key
                )


            user_id = str(
                item.get(
                    "user_id"
                )
                or "system"
            ).strip() or "system"


            delivery_qty = (
                _normalize_int(
                    item.get(
                        "delivery_qty"
                    ),
                    0
                )
            )

            assemble_qty = (
                _normalize_int(
                    item.get(
                        "assemble_qty"
                    ),
                    0
                )
            )

            good_qty = (
                _normalize_int(
                    item.get(
                        "good_qty"
                    ),
                    0
                )
            )

            non_good_qty = (
                _normalize_int(
                    item.get(
                        "non_good_qty"
                    ),
                    0
                )
            )

            line_difference = (
                _normalize_int(
                    item.get(
                        "line_difference"
                    ),
                    0
                )
            )


            reason = (
                str(
                    item.get(
                        "reason"
                    )
                ).strip()
                if item.get(
                    "reason"
                ) is not None
                else None
            )


            confirm_comment = (
                str(
                    item.get(
                        "confirm_comment"
                    )
                ).strip()
                if item.get(
                    "confirm_comment"
                ) is not None
                else None
            )


            # ====================================================
            # 4-1. 一次鎖定整組 Material
            # ====================================================
            group_material_rows = (
                s.query(
                    Material
                )
                .filter(
                    Material.id.in_(
                        group_material_ids
                    )
                )
                .order_by(
                    Material.id.asc()
                )
                .with_for_update()
                .all()
            )


            group_material_map = {
                int(m.id): m
                for m
                in group_material_rows
            }


            if (
                len(
                    group_material_rows
                )
                != len(
                    group_material_ids
                )
            ):
                raise ValueError(
                    "合併入庫 material 數量不一致；"
                    f"要求={group_material_ids}，"
                    "找到="
                    f"{sorted(group_material_map.keys())}"
                )


            # ----------------------------------------------------
            # representative material
            #
            # merged：
            #   固定使用最小 material_id
            #
            # normal：
            #   使用傳入 material_id
            # ----------------------------------------------------
            if is_merged_shortage_order:

                representative_material_id = (
                    min(
                        group_material_ids
                    )
                )

            else:

                representative_material_id = (
                    material_id
                )


            material = (
                group_material_map.get(
                    representative_material_id
                )
            )


            if material is None:
                raise ValueError(
                    "找不到代表 material_id="
                    f"{representative_material_id}"
                )


            # ====================================================
            # 4-1-1.
            # merged shortage 安全驗證
            # ====================================================
            if is_merged_shortage_order:

                representative_order_num = (
                    str(
                        getattr(
                            material,
                            "order_num",
                            ""
                        )
                        or ""
                    ).strip()
                )


                # -----------------------------------------------
                # A. group 全部必須同 order_num
                # -----------------------------------------------
                invalid_order_material_ids = [
                    int(m.id)
                    for m
                    in group_material_rows
                    if str(
                        getattr(
                            m,
                            "order_num",
                            ""
                        )
                        or ""
                    ).strip()
                    != representative_order_num
                ]


                if invalid_order_material_ids:

                    raise ValueError(
                        "group_material_ids "
                        "包含不同訂單資料；"
                        "代表 order_num="
                        f"{representative_order_num}，"
                        "異常 material_id="
                        f"{sorted(invalid_order_material_ids)}"
                    )


                # -----------------------------------------------
                # B. 全部 material 都必須到 Warehouse
                # -----------------------------------------------
                warehouse_ready_rows = (
                    s.query(
                        Assemble.material_id
                    )
                    .filter(
                        Assemble.material_id.in_(
                            group_material_ids
                        ),

                        Assemble.work_num
                        == "B110",

                        Assemble.process_step_code
                        == 0,

                        Assemble.isWarehouseStationShow
                        .is_(True),

                        Assemble.show2_ok.in_(
                            [9, 10]
                        ),
                    )
                    .distinct()
                    .all()
                )


                warehouse_ready_material_ids = {
                    int(r[0])
                    for r
                    in warehouse_ready_rows
                    if r[0] is not None
                }


                missing_warehouse_ids = (
                    set(
                        group_material_ids
                    )
                    - warehouse_ready_material_ids
                )


                print(
                    "[createProduct]"
                    "[merged shortage validation]",
                    {
                        "order_num":
                            representative_order_num,

                        "group_material_ids":
                            group_material_ids,

                        "warehouse_ready_material_ids":
                            sorted(
                                warehouse_ready_material_ids
                            ),

                        "missing_warehouse_ids":
                            sorted(
                                missing_warehouse_ids
                            ),
                    }
                )


                if missing_warehouse_ids:
                    raise ValueError(
                        "缺料分批尚未全部送到 Warehouse；"
                        "不可進行合併入庫。"
                        "尚缺 material_id="
                        f"{sorted(missing_warehouse_ids)}"
                    )


            # ====================================================
            # 4-2. 找本次 assemble
            #
            # merged shortage：
            #   不再依單一 assemble 決定入庫。
            #   backing rows 由 group_assemble_ids 控制。
            # ====================================================
            assemble_record = None


            if (
                not is_merged_shortage_order
            ):

                if assemble_id > 0:

                    assemble_record = (
                        s.query(
                            Assemble
                        )
                        .filter(
                            Assemble.id
                            == assemble_id,

                            Assemble.material_id
                            == material_id
                        )
                        .with_for_update()
                        .one_or_none()
                    )


                    if (
                        assemble_record
                        is None
                    ):
                        raise ValueError(
                            f"第 {idx + 1} 筆找不到 "
                            f"assemble_id={assemble_id}，"
                            "或不屬於 "
                            f"material_id={material_id}"
                        )


                else:

                    assemble_record = (
                        s.query(
                            Assemble
                        )
                        .filter(
                            Assemble.material_id
                            == material_id,

                            Assemble.isWarehouseStationShow
                            .is_(True)
                        )
                        .order_by(
                            Assemble.id.asc()
                        )
                        .with_for_update()
                        .first()
                    )


                    if (
                        assemble_record
                        is None
                    ):

                        assemble_record = (
                            s.query(
                                Assemble
                            )
                            .filter(
                                Assemble.material_id
                                == material_id,

                                Assemble.process_step_code
                                == 0
                            )
                            .order_by(
                                Assemble.id.desc()
                            )
                            .with_for_update()
                            .first()
                        )


                    if (
                        assemble_record
                        is not None
                    ):
                        assemble_id = int(
                            assemble_record.id
                        )


            # ====================================================
            # 4-3. 計算 old_total
            # ====================================================
            old_total = (
                _normalize_int(
                    getattr(
                        material,
                        "total_allOk_qty",
                        0
                    ),
                    0
                )
            )


            # merged：各 copy 是同一整單累計，
            # 不可 SUM
            if is_merged_shortage_order:

                old_total = max(
                    [
                        _normalize_int(
                            getattr(
                                m,
                                "total_allOk_qty",
                                0
                            ),
                            0
                        )
                        for m
                        in group_material_rows
                    ]
                    or [0]
                )


            # ====================================================
            # 4-3-1. must_qty
            # ====================================================
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


            # 一般工單才依單 material assemble
            # 補候選數量
            assemble_qty_candidates = []


            if not is_merged_shortage_order:

                warehouse_rows = (
                    s.query(
                        Assemble
                    )
                    .filter(
                        Assemble.material_id
                        == material_id
                    )
                    .filter(
                        or_(
                            Assemble.isWarehouseStationShow
                            .is_(True),

                            Assemble.process_step_code
                            == 0
                        )
                    )
                    .with_for_update()
                    .all()
                )


                for warehouse_row in (
                    warehouse_rows
                ):

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


            # ----------------------------------------------------
            # merged shortage：
            #
            # 152 = 20
            # 160 = 20
            # 161 = 20
            #
            # 不是 60
            # ----------------------------------------------------
            if is_merged_shortage_order:

                group_order_qty = max(
                    [
                        _normalize_int(
                            getattr(
                                group_material,
                                "material_qty",
                                0
                            ),
                            0
                        )
                        for group_material
                        in group_material_rows
                    ]
                    or [0]
                )


                if group_order_qty > 0:
                    must_qty = (
                        group_order_qty
                    )


                print(
                    "[createProduct]"
                    "[merged shortage qty]",
                    {
                        "order_num":
                            material.order_num,

                        "group_material_ids":
                            group_material_ids,

                        "group_order_qty":
                            group_order_qty,

                        "must_qty":
                            must_qty,

                        "old_total":
                            old_total,

                        "add_qty":
                            add_qty,
                    }
                )


            # ----------------------------------------------------
            # 一般工單數量上限
            # ----------------------------------------------------
            material_delivery_qty = (
                _normalize_int(
                    getattr(
                        material,
                        "delivery_qty",
                        0
                    ),
                    0
                )
            )


            material_order_qty = (
                _normalize_int(
                    getattr(
                        material,
                        "material_qty",
                        0
                    ),
                    0
                )
            )


            if (
                not is_merged_shortage_order
                and material_delivery_qty > 0
                and material_order_qty > 0
                and material_delivery_qty
                >= material_order_qty
            ):
                must_qty = min(
                    must_qty,
                    material_delivery_qty
                )


            if (
                must_qty <= 0
                and material_order_qty > 0
            ):
                must_qty = (
                    material_order_qty
                )


            print(
                "[createProduct] "
                "stock-in quantity validation:",
                {
                    "material_id":
                        representative_material_id,

                    "order_num":
                        material.order_num,

                    "is_merged_shortage_order":
                        is_merged_shortage_order,

                    "must_qty":
                        must_qty,

                    "old_total":
                        old_total,

                    "add_qty":
                        add_qty,
                }
            )


            # ====================================================
            # 防止重複 / 超量
            # ====================================================
            if (
                must_qty > 0
                and old_total >= must_qty
            ):

                already_finished = any(
                    bool(
                        getattr(
                            m,
                            "isAllOk",
                            False
                        )
                    )
                    for m
                    in group_material_rows
                )

                if already_finished:
                    raise ValueError(
                        "此工單已全數入庫，"
                        "不可重複入庫；"
                        f"order_num="
                        f"{material.order_num}"
                    )


            if (
                must_qty > 0
                and old_total + add_qty
                > must_qty
            ):

                remain_qty = max(
                    must_qty - old_total,
                    0
                )

                raise ValueError(
                    f"第 {idx + 1} 筆"
                    "入庫數量超過剩餘數量；"
                    f"應入庫={must_qty}，"
                    f"已入庫={old_total}，"
                    f"剩餘={remain_qty}，"
                    f"本次輸入={add_qty}"
                )


            # ====================================================
            # 4-4. process_type = 31
            #
            # merged shortage：
            #
            # material_id =
            #   representative_material_id
            #
            # assemble_id = 0
            #
            # 整組只建立 1 筆。
            # ====================================================
            stockin_assemble_id = (
                0
                if is_merged_shortage_order
                else int(
                    assemble_id or 0
                )
            )


            stockin_process = None


            # ----------------------------------------------------
            # A. 檢查前端 process_id
            # ----------------------------------------------------
            if process_id_to_use > 0:

                candidate_process = (
                    s.query(
                        Process
                    )
                    .filter(
                        Process.id
                        == process_id_to_use
                    )
                    .with_for_update()
                    .one_or_none()
                )


                if (
                    candidate_process
                    is None
                ):

                    print(
                        "[createProduct] "
                        "ignore invalid process_id:",
                        process_id_to_use
                    )

                    process_id_to_use = 0


                elif (
                    int(
                        candidate_process.process_type
                        or 0
                    )
                    != 31
                ):

                    print(
                        "[createProduct] "
                        "ignore non-stockin process_id:",
                        {
                            "process_id":
                                process_id_to_use,

                            "process_type":
                                int(
                                    candidate_process.process_type
                                    or 0
                                ),
                        }
                    )

                    process_id_to_use = 0


                elif (
                    int(
                        candidate_process.material_id
                        or 0
                    )
                    != representative_material_id
                ):

                    print(
                        "[createProduct] "
                        "ignore type31 of "
                        "non representative material:",
                        {
                            "process_id":
                                process_id_to_use,

                            "process_material_id":
                                candidate_process.material_id,

                            "representative_material_id":
                                representative_material_id,
                        }
                    )

                    process_id_to_use = 0


                else:

                    stockin_process = (
                        candidate_process
                    )


            # ----------------------------------------------------
            # B. 使用既有 31
            # ----------------------------------------------------
            if stockin_process is not None:

                duplicate_product = (
                    s.query(
                        Product.id
                    )
                    .filter(
                        Product.process_id
                        == stockin_process.id
                    )
                    .first()
                )


                if duplicate_product:

                    raise ValueError(
                        "process_id="
                        f"{stockin_process.id} "
                        "已建立過入庫 Product，"
                        "不可重複送出"
                    )


                stockin_process.has_started = (
                    False
                )

                stockin_process.is_pause = (
                    True
                )

                stockin_process.pause_started_at = (
                    None
                )


                if (
                    stockin_process.begin_time
                    is None
                    or str(
                        stockin_process.begin_time
                    ).strip() == ""
                ):
                    stockin_process.begin_time = (
                        now_str
                    )


                if (
                    stockin_process.end_time
                    is None
                    or str(
                        stockin_process.end_time
                    ).strip() == ""
                ):
                    stockin_process.end_time = (
                        now_str
                    )


                stockin_process.process_work_time_qty = (
                    add_qty
                )

                stockin_process.allOk_qty = (
                    add_qty
                )

                stockin_process.must_allOk_qty = (
                    must_qty
                )

                stockin_process.isAllOk = (
                    must_qty <= 0
                    or old_total + add_qty
                    >= must_qty
                )


                process_id_to_use = int(
                    stockin_process.id
                )


            # ----------------------------------------------------
            # C. 找 / 建新的 31
            # ----------------------------------------------------
            else:

                existing_stockin_process = (
                    s.query(
                        Process
                    )
                    .filter(
                        Process.material_id
                        == representative_material_id,

                        Process.assemble_id
                        == stockin_assemble_id,

                        Process.process_type
                        == 31,

                        Process.process_work_time_qty
                        == add_qty
                    )
                    .order_by(
                        Process.id.desc()
                    )
                    .with_for_update()
                    .first()
                )


                if (
                    existing_stockin_process
                    is not None
                ):

                    duplicate_product = (
                        s.query(
                            Product.id
                        )
                        .filter(
                            Product.process_id
                            == existing_stockin_process.id
                        )
                        .first()
                    )


                    if duplicate_product:

                        raise ValueError(
                            "此工單已有相同入庫紀錄；"
                            f"material_id="
                            f"{representative_material_id}，"
                            f"入庫數量={add_qty}"
                        )


                    stockin_process = (
                        existing_stockin_process
                    )


                    stockin_process.has_started = (
                        False
                    )

                    stockin_process.is_pause = (
                        True
                    )

                    stockin_process.pause_started_at = (
                        None
                    )


                    if (
                        stockin_process.begin_time
                        is None
                        or str(
                            stockin_process.begin_time
                        ).strip() == ""
                    ):
                        stockin_process.begin_time = (
                            now_str
                        )


                    if (
                        stockin_process.end_time
                        is None
                        or str(
                            stockin_process.end_time
                        ).strip() == ""
                    ):
                        stockin_process.end_time = (
                            now_str
                        )


                    stockin_process.process_work_time_qty = (
                        add_qty
                    )

                    stockin_process.allOk_qty = (
                        add_qty
                    )

                    stockin_process.must_allOk_qty = (
                        must_qty
                    )

                    stockin_process.isAllOk = (
                        must_qty <= 0
                        or old_total + add_qty
                        >= must_qty
                    )


                else:

                    stockin_process = Process(

                        material_id=
                            representative_material_id,

                        assemble_id=
                            stockin_assemble_id,

                        has_started=False,

                        user_id=user_id,

                        user_delegate_id="",

                        begin_time=now_str,

                        end_time=now_str,

                        period_time="0:00:00",

                        pause_time=0,

                        pause_started_at=None,

                        elapsedActive_time=0,

                        str_elapsedActive_time=
                            "00:00:00",

                        is_pause=True,

                        process_type=31,

                        process_work_time_qty=
                            add_qty,

                        must_allOk_qty=
                            must_qty,

                        allOk_qty=
                            add_qty,

                        isAllOk=(
                            must_qty <= 0
                            or old_total + add_qty
                            >= must_qty
                        ),

                        normal_work_time=1,

                        abnormal_cause_message="",

                        create_at=now_dt
                    )


                    s.add(
                        stockin_process
                    )

                    s.flush()


                process_id_to_use = int(
                    stockin_process.id
                )


            # ====================================================
            # 4-5. Product
            #
            # merged shortage：
            # 只建立 1 筆
            # ====================================================
            product = Product(

                material_id=
                    representative_material_id,

                process_id=
                    process_id_to_use or None,

                line_difference=
                    line_difference,

                delivery_qty=
                    delivery_qty,

                assemble_qty=
                    assemble_qty,

                allOk_qty=
                    add_qty,

                good_qty=
                    good_qty,

                non_good_qty=
                    non_good_qty,

                reason=
                    reason,

                confirm_comment=
                    confirm_comment,
            )


            s.add(
                product
            )

            s.flush()


            created_products.append(
                product
            )


            # ====================================================
            # 4-6. Material 累計
            # ====================================================
            new_total = (
                old_total
                + add_qty
            )


            material_finished = (
                must_qty <= 0
                or new_total
                >= must_qty
            )


            target_material_ids = (
                group_material_ids
                if is_merged_shortage_order
                else [
                    material_id
                ]
            )


            target_material_rows = (
                s.query(
                    Material
                )
                .filter(
                    Material.id.in_(
                        target_material_ids
                    )
                )
                .order_by(
                    Material.id.asc()
                )
                .with_for_update()
                .all()
            )


            # merged copy 全部同步整單累計
            for target_material in (
                target_material_rows
            ):

                target_material.allOk_qty = (
                    add_qty
                )

                target_material.total_allOk_qty = (
                    new_total
                )

                if hasattr(
                    target_material,
                    "must_allOk_qty"
                ):
                    target_material.must_allOk_qty = (
                        must_qty
                    )


            # ====================================================
            # 4-7. 部分入庫
            # ====================================================
            if not material_finished:

                for target_material in (
                    target_material_rows
                ):

                    target_material.isAllOk = (
                        False
                    )

                    target_material.isAssembleStationShow = (
                        False
                    )

                    target_material.whichStation = (
                        3
                    )

                    target_material.show1_ok = (
                        3
                    )

                    target_material.show2_ok = (
                        10
                    )

                    target_material.show3_ok = (
                        11
                    )

                    target_material.isOpen = (
                        False
                    )

                    target_material.isOpenEmpId = (
                        ""
                    )

                    target_material.hasStarted = (
                        False
                    )

                    target_material.startStatus = (
                        1
                    )

                    if hasattr(
                        target_material,
                        "update_time"
                    ):
                        target_material.update_time = (
                            now_str
                        )


                # -----------------------------------------------
                # 一般工單：
                # 部分入庫只關閉本次 assemble
                #
                # merged：
                # backing Warehouse rows 仍保留，
                # 下一次可繼續輸入剩餘量。
                # -----------------------------------------------
                if (
                    not is_merged_shortage_order
                    and assemble_record
                    is not None
                ):

                    assemble_record.allOk_qty = (
                        add_qty
                    )

                    assemble_record.process_step_code = (
                        0
                    )

                    assemble_record.isAssembleStationShow = (
                        False
                    )

                    assemble_record.isWarehouseStationShow = (
                        False
                    )

                    assemble_record.input_disable = (
                        True
                    )

                    assemble_record.input_end_disable = (
                        True
                    )

                    assemble_record.input_abnormal_disable = (
                        True
                    )

                    assemble_record.input_allOk_disable = (
                        True
                    )

                    assemble_record.currentStartTime = (
                        None
                    )

                    assemble_record.currentEndTime = (
                        None
                    )

                    assemble_record.whichStation = (
                        3
                    )

                    assemble_record.show1_ok = (
                        3
                    )

                    assemble_record.show2_ok = (
                        12
                    )

                    assemble_record.show3_ok = (
                        13
                    )

                    if hasattr(
                        assemble_record,
                        "update_time"
                    ):
                        assemble_record.update_time = (
                            now_str
                        )


            # ====================================================
            # 4-8. 全數入庫
            # ====================================================
            else:

                # -----------------------------------------------
                # A. 所有 Material 完成
                # -----------------------------------------------
                for target_material in (
                    target_material_rows
                ):

                    target_material.isAllOk = (
                        True
                    )

                    target_material.isShow = (
                        True
                    )

                    target_material.isTakeOk = (
                        True
                    )

                    target_material.isAssembleStationShow = (
                        False
                    )

                    target_material.isAssembleStation3TakeOk = (
                        True
                    )

                    target_material.whichStation = (
                        3
                    )

                    target_material.show1_ok = (
                        3
                    )

                    target_material.show2_ok = (
                        12
                    )

                    target_material.show3_ok = (
                        13
                    )

                    target_material.isOpen = (
                        False
                    )

                    target_material.isOpenEmpId = (
                        ""
                    )

                    target_material.hasStarted = (
                        False
                    )

                    target_material.startStatus = (
                        1
                    )

                    target_material.allOk_qty = (
                        add_qty
                    )

                    target_material.total_allOk_qty = (
                        new_total
                    )

                    if hasattr(
                        target_material,
                        "must_allOk_qty"
                    ):
                        target_material.must_allOk_qty = (
                            must_qty
                        )

                    if hasattr(
                        target_material,
                        "update_time"
                    ):
                        target_material.update_time = (
                            now_str
                        )


                # -----------------------------------------------
                # B. 所有 Assemble 退出
                # Begin / End / Warehouse
                # -----------------------------------------------
                all_assemble_rows = (
                    s.query(
                        Assemble
                    )
                    .filter(
                        Assemble.material_id.in_(
                            target_material_ids
                        )
                    )
                    .order_by(
                        Assemble.material_id.asc(),
                        Assemble.id.asc()
                    )
                    .with_for_update()
                    .all()
                )


                for assemble_row in (
                    all_assemble_rows
                ):

                    assemble_row.process_step_code = (
                        0
                    )

                    assemble_row.isAssembleStationShow = (
                        False
                    )

                    assemble_row.isWarehouseStationShow = (
                        False
                    )

                    assemble_row.input_disable = (
                        True
                    )

                    assemble_row.input_end_disable = (
                        True
                    )

                    assemble_row.input_abnormal_disable = (
                        True
                    )

                    assemble_row.input_allOk_disable = (
                        True
                    )

                    assemble_row.currentStartTime = (
                        None
                    )

                    assemble_row.currentEndTime = (
                        None
                    )

                    assemble_row.whichStation = (
                        3
                    )

                    assemble_row.show1_ok = (
                        3
                    )

                    assemble_row.show2_ok = (
                        12
                    )

                    assemble_row.show3_ok = (
                        13
                    )


                    if (
                        is_merged_shortage_order
                        and int(
                            assemble_row.id
                            or 0
                        )
                        in group_assemble_ids
                    ):
                        assemble_row.allOk_qty = (
                            add_qty
                        )


                    elif (
                        not is_merged_shortage_order
                        and int(
                            assemble_row.id
                            or 0
                        )
                        == int(
                            assemble_id
                            or 0
                        )
                    ):
                        assemble_row.allOk_qty = (
                            add_qty
                        )


                    if hasattr(
                        assemble_row,
                        "update_time"
                    ):
                        assemble_row.update_time = (
                            now_str
                        )


                # -----------------------------------------------
                # C. 關閉整組殘留 21/22/23
                # -----------------------------------------------
                active_process_rows = (
                    s.query(
                        Process
                    )
                    .filter(
                        Process.material_id.in_(
                            target_material_ids
                        ),

                        Process.process_type.in_(
                            [
                                21,
                                22,
                                23,
                            ]
                        ),

                        or_(
                            Process.end_time
                            .is_(None),

                            Process.end_time
                            == "",

                            Process.has_started
                            .is_(True)
                        )
                    )
                    .with_for_update()
                    .all()
                )


                for process_row in (
                    active_process_rows
                ):

                    if (
                        process_row.end_time
                        is None
                        or str(
                            process_row.end_time
                        ).strip() == ""
                    ):
                        process_row.end_time = (
                            now_str
                        )

                    process_row.has_started = (
                        False
                    )

                    process_row.is_pause = (
                        True
                    )

                    process_row.pause_started_at = (
                        None
                    )


                print(
                    "[createProduct] "
                    "fully stocked in:",
                    {
                        "order_num":
                            material.order_num,

                        "representative_material_id":
                            representative_material_id,

                        "is_merged_shortage_order":
                            is_merged_shortage_order,

                        "group_material_ids":
                            target_material_ids,

                        "group_assemble_ids":
                            group_assemble_ids,

                        "process_id":
                            process_id_to_use,

                        "product_id":
                            product.id,

                        "must_qty":
                            must_qty,

                        "old_total":
                            old_total,

                        "add_qty":
                            add_qty,

                        "new_total":
                            new_total,

                        "assemble_closed":
                            len(
                                all_assemble_rows
                            ),

                        "active_process_closed":
                            len(
                                active_process_rows
                            ),
                    }
                )


            # ====================================================
            # Result
            # ====================================================
            result_items.append({

                "index":
                    idx,

                "material_id":
                    representative_material_id,

                "assemble_id":
                    (
                        None
                        if is_merged_shortage_order
                        else (
                            assemble_id
                            or None
                        )
                    ),

                "process_id":
                    process_id_to_use,

                "product_id":
                    product.id,

                "allOk_qty":
                    add_qty,

                "old_total_allOk_qty":
                    old_total,

                "new_total_allOk_qty":
                    new_total,

                "must_allOk_qty":
                    must_qty,

                "material_finished":
                    material_finished,

                "is_merged_shortage_order":
                    is_merged_shortage_order,

                "group_material_ids":
                    target_material_ids,

                "group_assemble_ids":
                    group_assemble_ids,
            })


        # ========================================================
        # 5. 全部成功才 commit
        # ========================================================
        s.commit()


        response_products = []


        for product in (
            created_products
        ):

            response_products.append({

                "id":
                    product.id,

                "material_id":
                    product.material_id,

                "process_id":
                    product.process_id,

                "delivery_qty":
                    product.delivery_qty,

                "assemble_qty":
                    product.assemble_qty,

                "allOk_qty":
                    product.allOk_qty,

                "good_qty":
                    product.good_qty,

                "non_good_qty":
                    product.non_good_qty,

                "reason":
                    product.reason,

                "confirm_comment":
                    product.confirm_comment,

                "create_at":
                    (
                        product.create_at
                        .isoformat()
                        if getattr(
                            product,
                            "create_at",
                            None
                        )
                        else None
                    ),
            })


        return jsonify({
            "status": True,
            "created":
                len(
                    response_products
                ),

            "items":
                response_products,

            "results":
                result_items
        }), 200


    except ValueError as e:

        s.rollback()

        print(
            "[createProduct] "
            "validation error:",
            str(e)
        )

        return jsonify({
            "status": False,
            "error": str(e)
        }), 400


    except SQLAlchemyError as e:

        s.rollback()

        print(
            "[createProduct] "
            "SQLAlchemy error:",
            repr(e)
        )

        return jsonify({
            "status": False,
            "error": str(e)
        }), 500


    except Exception as e:

        s.rollback()

        print(
            "[createProduct] "
            "unexpected error:",
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

