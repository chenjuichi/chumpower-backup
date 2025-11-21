import re

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash
from database.tables import User, Material, Assemble, Bom, Agv, Permission, Process, AbnormalCause, Setting, Session
from sqlalchemy import and_, or_, not_, func

from flask_cors import CORS

from operator import itemgetter

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

getTable = Blueprint('getTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------

'''
# list user, department, permission and setting table all data
@getTable.route('/reLogin', methods=['POST'])
def reLogin():
    print("reLogin....")

    request_data = request.get_json()
    userID = (request_data['empID'] or '')
    password = (request_data['password'] or '')

    s = Session()

    _user_object = {}
    user = s.query(User).filter_by(emp_id=userID).first()
    if user and user.isRemoved:
        if user.isOnline:   # 強迫下線（若已上線）
            s.query(User).filter_by(emp_id=userID).update({'isOnline': False})
            s.commit()

        # 驗證密碼
        if not check_password_hash(user.password, password):
          s.close()
          return jsonify({
            'status': False,          # false: 資料錯誤
            'message': '密碼錯誤!',
            'user': {},
          })

        # 取得 permission 和 setting
        perm_item = s.query(Permission).filter_by(id=user.perm_id).first()
        setting_item = s.query(Setting).filter_by(id=user.setting_id).first()

        # 登入：設定 isOnline = True
        s.query(User).filter(User.emp_id == userID).update({'isOnline': True})   # true: user已經上線
        s.commit()

        # 返回使用者資料
        _user_object = {
          'empID': user.emp_id,
          'name': user.emp_name,
          'dep': user.dep_name,
          'perm_name': perm_item.auth_name,
          'perm': perm_item.auth_code,
          'password': password,
          'isOnline': True,
          'setting_items_per_page': setting_item.items_per_page,
          'setting_isSee': setting_item.isSee,
          'setting_message': setting_item.message,
          'setting_routingPriv': setting_item.routingPriv,
          'setting_lastRoutingName': setting_item.lastRoutingName,
        }
    else:
      s.close()
      return jsonify({
        'status': False,                        # false: 資料錯誤
        'message': '錯誤! 找不到工號' + userID,
        'user': {},
      })

    s.close()

    return jsonify({
      'status': True,
      'message': '',
      'user': _user_object,
    })
'''


TPE = ZoneInfo("Asia/Taipei")
FMT = "%Y-%m-%d %H:%M:%S"

def now_tpe_aware():
    return datetime.now(TPE).replace(microsecond=0)

def now_tpe_str():
    return now_tpe_aware().strftime(FMT)

def parse_tpe_str(s: str):
    """把 'yyyy-mm-dd hh:mm:ss'（台北時區）轉成 aware datetime"""
    if not s:
        return None
    return datetime.strptime(s, FMT).replace(tzinfo=TPE)

def attach_tpe(dt: datetime):
    """把 DB 撈出的 DATETIME（多半 naive）視為台北時間並補上 tzinfo"""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=TPE)

def fmt_hhmmss(seconds: int):
    seconds = max(0, int(seconds or 0))
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def seconds_to_hms_str(seconds: int) -> str:
    """將秒數轉換成 hh:mm:ss"""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:02}"

def parse_dt_maybe(v):
    """把 v 轉成 datetime；支援 'YYYY-MM-DD HH:MM:SS[.ffffff]'、'YYYY-MM-DDTHH:MM:SS[.ffffff]'、結尾 'Z'。失敗回 None。"""
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip().replace('T', ' ')
    if s.endswith('Z'):
        s = s[:-1]  # 你資料看起來沒時區，先移除 'Z'
    try:
        return datetime.fromisoformat(s)  # 可吃微秒
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

def fmt_dt(v):
    dt = parse_dt_maybe(v)
    return None if dt is None else dt.strftime("%Y-%m-%d %H:%M:%S")

def _to_aware(dt):
    #把 DB 撈出的 begin_time / pause_started_at 轉成 aware(UTC)。可吃 datetime 或 'YYYY-MM-DD HH:MM:SS' 字串。
    if not dt:
        return None
    if isinstance(dt, datetime):
        base = dt if dt.tzinfo else dt.replace(tzinfo=TPE)  # ⬅️ naive 視為台北
        return base.astimezone(timezone.utc)
    if isinstance(dt, str):
        from datetime import datetime as _dt
        try:
            base = _dt.fromisoformat(dt.replace('T', ' '))  # 可吃微秒
        except Exception:
            return None
        base = base if base.tzinfo else base.replace(tzinfo=TPE)  # ⬅️ naive 視為台北
        return base.astimezone(timezone.utc)
    return None

def parse_dt_maybe_aw(value):
    """
    把 value(可能是 str/datetime/None) 轉成 Asia/Taipei 的 aware datetime。
    若無法解析回傳 None。
    """
    if value in (None, "", "None"):
        return None

    # 已是 datetime
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        dt = None

        # 常見格式先試
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                pass

        # 仍然不行再用 dateutil
        if dt is None:
            try:
                from dateutil import parser as dateparser
                dt = dateparser.parse(s)
            except Exception:
                return None

    # 補上/轉成 TPE 時區
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TPE)
    else:
        return dt.astimezone(TPE)


# ------------------------------------------------------------------


"""0917
def _to_aware(dt):
    #將 DB 取出的 begin_time / pause_started_at 轉成 aware datetime（UTC）。字串/None 也可安全處理。
    if not dt:
        return None
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if isinstance(dt, str):
        # 盡量吃 ISO 格式；'Z' 視為 UTC
        try:
            return datetime.fromisoformat(dt.replace('Z', '+00:00')).astimezone(timezone.utc)
        except Exception:
            return None
    return None
"""


def _live_elapsed_seconds(log) -> int:
    begin = _to_aware(getattr(log, 'begin_time', None))
    if not begin:
        # 後備：讀不到 begin，就用已存的數值
        return int(getattr(log, 'elapsedActive_time', 0) or 0)

    pause_total = int(getattr(log, 'pause_time', 0) or 0)

    ps = _to_aware(getattr(log, 'pause_started_at', None))
    if bool(getattr(log, 'is_pause', False)) and ps:
        end = ps  # 暫停中 → 固定到暫停那一刻
    else:
        end = datetime.now(timezone.utc)

    return max(0, int((end - begin).total_seconds()) - pause_total)


"""0917
def _live_elapsed_seconds(log) -> int:
    #動態計算：從 begin_time 到現在的總秒數，扣掉所有暫停秒數。
    #若目前處於暫停且 pause_started_at 有值，會把「正在暫停中的這段」一併扣掉。

    begin = _to_aware(getattr(log, 'begin_time', None))
    if not begin:
        return 0

    now = datetime.now(timezone.utc)
    pause_total = int(getattr(log, 'pause_time', 0) or 0)

    # ★ 無論 is_pause True/False，都把「正在暫停段」扣掉
    ps = _to_aware(getattr(log, 'pause_started_at', None))
    if ps and ps <= now:
        # 目前正在暫停中，把這段暫停秒數也算進去
        pause_total += max(0, int((now - ps).total_seconds()))

    return max(0, int((now - begin).total_seconds()) - pause_total)
"""


# 將 step code 轉成製程代號
def map_pt_from_step_code(step_code: int) -> str:
    # 3 => 21（組裝）, 2 => 22（檢驗），其它 => 23（雷射）
    return '21' if step_code == 3 else '22' if step_code == 2 else '23'

def pick_user_list(bucket, pt: str, mid: str):
    """從 user_ids_by_type 取出該製程/料號的名單（兼容 list 或字串）"""
    val = (bucket.get(pt) or {}).get(mid)
    if val is None:
        return []
    # 目前 user_ids_by_type(as_string=False) 回 list，若未來改成字串也可相容
    if isinstance(val, str):
        return [u.strip() for u in val.split(',') if u.strip()]
    return list(val)


def build_active_process_query(
      s,
      material_ids,
      process_types,
      include_paused=True,
      only_user_id=None,              # 可選的使用者過濾
      has_started=None,               # None=不過濾 / True=只要已開始 / False=只要未開始
      null_as_not_started=True,       # False 時才有用；True=把 NULL 視為「未開始」
  ):
      """
      include_paused:
          True  -> 只要未結束就算（含暫停）
          False -> 只算正在跑（不含暫停）
      has_started:
          None  -> 不過濾
          True  -> 只要 has_started=True
          False -> 只要 has_started=False（可選擇是否把 NULL 視為未開始）
      """
      q = (
          s.query(Process)
          .filter(Process.material_id.in_(material_ids))
          .filter(Process.process_type.in_(process_types))
          .filter(Process.end_time.is_(None))   # 只算未結束
      )

      if not include_paused:
          q = q.filter(or_(Process.is_pause.is_(False), Process.is_pause.is_(None)))

      if only_user_id:
          q = q.filter(Process.user_id == only_user_id)

      # 處理 has_started 過濾
      if has_started is True:
          q = q.filter(Process.has_started.is_(True))
      elif has_started is False:
          if null_as_not_started:
              q = q.filter(or_(Process.has_started.is_(False), Process.has_started.is_(None)))
          else:
              q = q.filter(Process.has_started.is_(False))

      return q


def active_count_map_by_material_multi(
    s,
    material_ids,
    process_types=(21, 22, 23),
    include_paused=True,
    only_user_id=None,
    has_started=None,
    null_as_not_started=True,
):
    """
    回傳格式：
    {
      "21": { "101": 2, "103": 1 },
      "22": { "101": 1 },
      "23": {}
    }
    include_paused: True → 只要未結束就算（包含暫停）
                     False → 只算「正在跑」（不含暫停）
    """

    result = {str(pt): {} for pt in process_types}
    if not material_ids:
        return result

    q = build_active_process_query(
        s, material_ids, process_types,
        include_paused=include_paused,
        only_user_id=only_user_id,
        has_started=has_started,
        null_as_not_started=null_as_not_started,
    )

    rows = q.with_entities(Process.process_type, Process.material_id).all()

    for pt, mid in rows:
        pt_str, mid_str = str(pt), str(mid)
        result[pt_str][mid_str] = result[pt_str].get(mid_str, 0) + 1

    return result


def active_user_ids_by_material_multi(
    s,
    material_ids,
    process_types=(21, 22, 23),
    include_paused=True,
    has_started=None,
    null_as_not_started=True,
    only_user_id=None,
    as_string=False,                # 預設 False（回 list）
    sep=', '
):
    result = {str(pt): {} for pt in process_types}
    if not material_ids:
        return result

    q = build_active_process_query(
        s, material_ids, process_types,
        include_paused=include_paused,
        only_user_id=only_user_id,
        has_started=has_started,
        null_as_not_started=null_as_not_started,
    )

    rows = q.with_entities(
        Process.process_type,
        Process.material_id,
        Process.user_id
    ).all()

    buckets = {}                  # (pt_str, mid_str) -> set(uids)
    for pt, mid, uid in rows:
        if uid is None:
            continue
        k = (str(pt), str(mid))
        buckets.setdefault(k, set()).add(str(uid))

    for (pt_str, mid_str), uids in buckets.items():
        ulist = sorted(uids)
        result[pt_str][mid_str] = sep.join(ulist) if as_string else ulist

    return result


"""
def active_user_ids_by_material_multi(
    s,
    material_ids,
    process_types=(21, 22, 23),
    include_paused=True,
    as_string=True,        # True: "00008241, 01012002"；False: ["00008241", "01012002"]
    sep=', '
):
    '''
    回傳格式：
    {
      "21": { "101": "00008241, 01012002", "103": "00008241" },
      "22": { "101": "00008241" },
      "23": {}
    }
    '''

    result = {str(pt): {} for pt in process_types}

    if not material_ids:
        return result

    # --- 依現有 Process schema 與條件來query ---
    q = (
        s.query(
            Process.process_type,
            Process.material_id,
            Process.user_id,
            Process.is_pause
        )
        .filter(Process.material_id.in_(material_ids))
        .filter(Process.process_type.in_(process_types))
        .filter(Process.end_time.is_(None))                 # 只算尚未結束
    )

    # 若「還在跑 / 未結束」有其他條件（例如 end_time is NULL），則加上
    # q = q.filter(Process.end_time.is_(None))   # 若有 end_time 欄位才加

    if include_paused:
        # 包含暫停：不過濾 is_pause
        pass
    else:
        # 只算正在跑：is_pause 為 False 或 None 視你的定義
        q = q.filter(or_(Process.is_pause.is_(False), Process.is_pause.is_(None)))
        #q = q.filter(or_(Process.is_pause.is_(False), Process.is_pause.is_(None)), Process.is_pause == 0)

    rows = q.all()

    # 蒐集每個 (pt, mid) 的 user_id（去重、排序）
    buckets = {}  # key: (pt_str, mid_str) -> set(user_id)
    #for pt, mid, uid, _is_pause in rows:
    for pt, mid, uid in rows:
        if uid is None:
            continue
        pt_str = str(pt)
        mid_str = str(mid)
        key = (pt_str, mid_str)
        if key not in buckets:
            buckets[key] = set()
        buckets[key].add(str(uid))

    # 填回結果
    for (pt_str, mid_str), uids in buckets.items():
        if as_string:
            result[pt_str][mid_str] = sep.join(sorted(uids))
        else:
            result[pt_str][mid_str] = sorted(uids)

    return result


def active_count_map_by_material_multi(session, material_ids, process_types=(21,22,23), include_paused=True):
    '''
    回傳格式：
    {
      "21": { "101": 2, "103": 1 },
      "22": { "101": 1 },
      "23": {}
    }
    include_paused: True → 只要未結束就算（包含暫停）
                     False → 只算「正在跑」（不含暫停）
    '''
    if not material_ids:
      return {str(pt): {} for pt in process_types}

    q = (session.query(
            Process.material_id,
            Process.process_type,
            func.count(Process.id))
         .filter(Process.material_id.in_(material_ids))
         .filter(Process.process_type.in_(list(process_types)))
         .filter(Process.end_time.is_(None)))

    # 不要把暫停算進去 → 再加 is_paused = false 的條件
    if not include_paused:
        q = q.filter(or_(Process.is_pause.is_(False), Process.is_pause == 0, Process.is_pause.is_(None)))

    rows = q.group_by(Process.material_id, Process.process_type).all()

    result = {str(pt): {} for pt in process_types}
    for mid, ptype, cnt in rows:
        result[str(int(ptype))][str(int(mid))] = int(cnt)
    return result
"""


def end_ok_flag(s, material_id: int, process_step_code: int) -> bool:
    """
    等價於 getEndOkByMaterialIdAndStepCode 的 True/False 判斷，
    直接在伺服器內部呼叫，不走 HTTP。
    """
    row = (
        s.query(Assemble)
         .filter(Assemble.material_id == material_id)
         .filter(Assemble.process_step_code == process_step_code)
         .first()
    )
    if not row:
        return False

    return True


# ------------------------------------------------------------------


@getTable.route('/reLogin', methods=['POST'])
def reLogin():
  print("reLogin....")

  request_data = request.get_json()
  userID = request_data.get('empID', '')
  print("login, userID:", userID)
  password = request_data.get('password', '')

  current_ip = request.remote_addr
  print("current_ip:",current_ip)
  #local_ip = request.json.get('local_ip', '0.0.0.0')
  #print("前端傳來的 local IP:", local_ip)

  local_ip = request.json.get('local_ip')
  user_agent = request.json.get('user_agent')
  device_id = request.json.get('device_id')

  print("登入來源 IP:", local_ip)
  print("瀏覽器裝置資訊:", user_agent)
  print("裝置識別碼:", device_id)



  s = Session()
  try:
    user = s.query(User).filter_by(emp_id=userID).first()

    if not user or not user.isRemoved:
      print("找不到工號!")
      return jsonify({
          'status': False,
          'message': f'錯誤! 找不到工號 {userID}',
          #'user': {}
      })

    # 驗證密碼
    if not check_password_hash(user.password, password):
      return jsonify({
          'status': False,
          'message': '密碼錯誤!',
          #'user': {}
      })

    #status = True
    forceLogoutRequired = False

    # ✅ 若已經登入且 IP 不同，禁止登入（或選擇強制登出）
    #if user.isOnline and user.last_login_ip != current_ip:
    #if user.isOnline and user.last_login_ip != local_ip:
    if user.isOnline and user.last_login_ip and user.last_login_ip.strip() and user.last_login_ip != local_ip:
    #if user.isOnline:
      #status = False
      forceLogoutRequired = True
      #print(f"⚠️ 此帳號已在線上且 IP 不同: {user.last_login_ip} ≠ {local_ip}")
      print(f"⚠️ 此帳號已在線上")
      #user_data = {
      #  'empID': user.emp_id,
      #  'name': user.emp_name,
      #}

      #return jsonify({
      #    'status': False,
      #    'message': f'此帳號已從其他位置登入（{user.last_login_ip}），請先登出。',
      #    'user': user_data,
      #    'forceLogoutRequired': True  # 前端可用來決定是否提示強制登出
      #})

    # 強迫登出（如果已上線）
    #if user.isOnline:
    #  user.isOnline = False
    #  s.commit()

    ## 驗證密碼
    #if not check_password_hash(user.password, password):
    #  return jsonify({
    #      'status': False,
    #      'message': '密碼錯誤!',
    #      'user': {}
    #  })

    # 登入：設定 isOnline = True
    user.isOnline = True
    user.last_login_ip = local_ip
    user.last_login_time = datetime.now()
    #user.forceLogoutRequired = forceLogoutRequired
    s.commit()

    # 取得權限與設定資料
    perm = s.query(Permission).filter_by(id=user.perm_id).first()
    setting = s.query(Setting).filter_by(id=user.setting_id).first()

    user_data = {
        'empID': user.emp_id,
        'name': user.emp_name,
        'dep': user.dep_name,
        'perm_name': perm.auth_name,
        'perm': perm.auth_code,
        'isOnline': True,
        'setting_items_per_page': setting.items_per_page,
        'setting_isSee': setting.isSee,
        'setting_message': setting.message,
        'setting_routingPriv': setting.routingPriv,
        'setting_lastRoutingName': setting.lastRoutingName,

    }

    return jsonify({
      'status': True,
      'forceLogoutRequired': forceLogoutRequired,
      'message': '',
      'user': user_data
    })

  finally:
    s.close()


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
        #print("login user: ", user)

        if user.isOnline:
          #print("step1...")
          s.close()
          return jsonify({
            'status': False,          # false: 資料錯誤
            'message': '使用者已上線!'
          })

        if not check_password_hash(user.password, password):
          #print("step2...")
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
      #print("step3...")
      s.close()
      return jsonify({
        'status': False,                        # false: 資料錯誤
        'message': '錯誤! 找不到工號' + userID
      })

    #print("step4...")
    s.close()

    return jsonify({
      'status': True,
      'user': _user_object,
    })


@getTable.route('/login2', methods=['POST'])
def login2():
    print("login2....")

    request_data = request.get_json()
    userID = (request_data['empID'] or '')
    password = (request_data['password'] or '')
    print("step1...", userID,password)

    s = Session()
    user = s.query(User).filter_by(emp_id=userID).first()
    if user and user.isRemoved:
      print("step2...")
      if not check_password_hash(user.password, password):
        s.close()
        print("密碼錯誤...")
        return jsonify({
          'status': False,          # false: 資料錯誤
        })
    else:
      s.close()
      print("員工編號錯誤...")
      return jsonify({
        'status': False,            # false: 資料錯誤
      })

    s.close()

    return jsonify({
      'status': True,
    })





'''
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
'''

# list all bom
@getTable.route("/getBoms", methods=['POST'])
def get_boms():
  print("getBoms....")

  request_data = request.get_json()
  #_order_num = request_data['order_num']
  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  #print("_order_num:", _order_num)
  return_value = True
  s = Session()


  # 檢查傳入的參數，選擇查詢條件
  material_record = None
  if _order_num is not None:  # 如果傳入了 order_num
    #print("step for order_num")
    material_record = s.query(Material).filter_by(order_num=_order_num).first()
  elif _id is not None:       # 如果傳入了 id
    #print("step for id")
    material_record = s.query(Material).filter_by(id=_id).first()

  #if material_record is None:
  #  return_value = False
  #else:
  boms = material_record._bom


  # 查詢 Material，根據 order_num 取得對應的 Material 資料
  #material = s.query(Material).filter(Material.order_num == _order_num).first()
  #print("material:", material)
  #boms = material._bom  # 透過關聯屬性取得所有 bom
  #print("boms:", boms)

  # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
  results = [
    {
      'id': bom.id,
      'order_num': material_record.order_num,
      'seq_num': bom.seq_num,           # 項目編號
      'material_num': bom.material_num,     # 物料編號
      'mtl_comment': bom.material_comment,  # 物料說明
      'qty': bom.req_qty,                   # 數量
      'date': material_record.material_date,       # 日期
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
  #print("getBoms: ", results)
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'boms': results
  })

'''
# list all bom
@getTable.route("/getAbnormalCauses", methods=['POST'])
def get_abnormal_causes():
  print("getAbnormalCauses....")

  request_data = request.get_json()
  #_order_num = request_data['order_num']
  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  #print("_order_num:", _order_num)
  return_value = True
  s = Session()


  # 檢查傳入的參數，選擇查詢條件
  material_record = None
  if _order_num is not None:  # 如果傳入了 order_num
    #print("step for order_num")
    material_record = s.query(Material).filter_by(order_num=_order_num).first()
  elif _id is not None:       # 如果傳入了 id
    #print("step for id")
    material_record = s.query(Material).filter_by(id=_id).first()
  # 下面代處理:
  boms = material_record._bom


  # 查詢 Material，根據 order_num 取得對應的 Material 資料
  #material = s.query(Material).filter(Material.order_num == _order_num).first()
  #print("material:", material)
  #boms = material._bom  # 透過關聯屬性取得所有 bom
  #print("boms:", boms)

  # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
  results = [
    {
      'id': bom.id,
      'order_num': material_record.order_num,
      'seq_num': bom.seq_num,           # 項目編號
      'material_num': bom.material_num,     # 物料編號
      'mtl_comment': bom.material_comment,  # 物料說明
      'qty': bom.req_qty,                   # 數量
      'date': material_record.material_date,       # 日期
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
  #print("getBoms: ", results)
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'boms': results
  })
'''

'''
# list detail information by order_num
@getTable.route("/getInformationDetails", methods=['POST'])
def get_information_details():
  print("getInformationDetails....")

  request_data = request.get_json()
  _order_num = request_data['order_num']
  print("order_num:", _order_num)

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
      'receive_qty': information_details.ask_qty,           # 領取數量
      'delivery_date': material.material_delivery_date,     # 交期
      #'actual_spent_time':  spent,
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
'''

@getTable.route("/dialog2StartProcess", methods=['POST'])
def start_process():
    print("dialog2StartProcess API....")

    data = request.json
    material_id = data["material_id"]
    user_id = data["user_id"]
    process_type = data.get("process_type", 1)
    assemble_id = data.get("assemble_id")

    s = Session()

    material_record = s.query(Material).filter_by(id=material_id).first()


    '''
    # 找到最後一筆紀錄
    log = (s.query(Process)
           .filter_by(material_id=material_id,
                      user_id=user_id,
                      process_type=process_type)
           .filter(Process.end_time.is_(None))
           .order_by(Process.begin_time.desc())
           .first())

    if not log or log.end_time is not None:
        print("step1...")
        # 🚩 新建一筆
        log = Process(
            material_id=material_id,
            user_id=user_id,
            #
            #begin_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            begin_time=None,
            end_time=None,
            elapsedActive_time=0,
            is_pause=True,        # 進入後顯示"開始"
            #is_pause=False,
            has_started=False,    # 尚未按開始
            #
            pause_time=0,
            pause_started_at=None,
            process_type=process_type
        )
        s.add(log)
        s.commit()  # 需要 commit 以拿到 id
    else:
        print("step2...")

        ## 🚩 延續紀錄
        #if log.is_pause :
        #    log.is_pause = False
        #    # 可以記錄 resume_time (若有欄位)
        ## 若已在計時中就不動

        # 不做自動恢復/暫停；只在「暫停但未記起點」時補上，方便之後恢復時計算段長
        if log.is_pause and log.pause_started_at is None:
            log.pause_started_at = datetime.utcnow()
            s.commit()
    '''

    # 1) 先找「同工單(同製程)、尚未結束」的最後一筆（不帶 user 條件）
    log = (
        s.query(Process)
        # .filter_by(material_id=material_id, process_type=process_type, user_id=user_id)
        .filter_by(material_id=material_id, process_type=process_type, user_id=user_id)
        .filter(Process.end_time.is_(None))
        .order_by(Process.id.desc())
        .first()
    )


    if log:
      # 回傳動態 live elapsed，和你現行邏輯一致
      live = _live_elapsed_seconds(log)
      return jsonify(success=True,
                      process_id=log.id,
                      begin_time=log.begin_time,
                      elapsed_time=int(live),
                      is_paused=bool(log.is_pause),
                      pause_time=int(log.pause_time or 0),
                      has_started=bool(getattr(log, "has_started", True)),

                      isOpen=getattr(material_record, "isOpen", None) if material_record else None,
                      hasStarted=getattr(material_record, "hasStarted", None) if material_record else None,
                      startStatus=getattr(material_record, "startStatus", None) if material_record else None,
                      isOpenEmpId=getattr(material_record, "isOpenEmpId", None) if material_record else None,
                    )

    # 2) 沒有未結束流程 → 幫當前 user 新建
    new_log = Process(
        material_id=material_id,
        user_id=user_id,
        process_type=process_type,
        begin_time=None,               # 由「開始」時再補
        end_time=None,
        elapsedActive_time=0,
        is_pause=True,                 # 進入即顯示「開始」
        has_started=False,
        pause_time=0,
        pause_started_at=None,
        # assemble_id=assemble_id,     # 若有此欄位再放
    )
    s.add(new_log)

    # 同步 Material（若前端有用到這些欄位）
    if material_record:
        material_record.isOpen = True
        material_record.isOpenEmpId = user_id

    s.commit()
    '''
    else:
      # 幫這位 user 新建一筆
      log = Process(
          material_id=material_id,
          user_id=user_id,
          process_type=process_type,
          begin_time=None,
          end_time=None,
          elapsedActive_time=0,
          is_pause=True,
          has_started=False,
          pause_time=0,
          pause_started_at=None,
          # 若你有打算存組裝站 id，就加上：
          # assemble_id=assemble_id,
      )
      s.add(log)
      s.commit()
      '''


    '''
    # 2) 若已存在未結束流程，但擁有者不是當前 user，維持「同一筆必須同一個人」規則 → 不處理
    if log and log.user_id != user_id:
      # 不要改動原資料，直接告知前端目前由誰計時中
      return jsonify({
          "success": False,
          "message": "此工單的計時正在由其他人進行中，無法接手。",
      }), 409

    # 3) 若存在未結束流程且擁有者就是當前 user → 直接回傳該筆（不自動切換暫停/恢復狀態）
    if log and log.user_id == user_id:
      live = _live_elapsed_seconds(log)  # 動態計算
      return jsonify({
          "success": True,
          "process_id": log.id,
          "begin_time": log.begin_time,
          #"elapsed_time": int(log.elapsedActive_time or 0),
          "elapsed_time": int(live),                 # 使用live
          "is_paused": bool(log.is_pause),
          "pause_time": int(log.pause_time or 0),

          "has_started": bool(getattr(log, "has_started", True)),

          "isOpen": getattr(material_record, "isOpen", None) if material_record else None,
          "hasStarted": getattr(material_record, "hasStarted", None) if material_record else None,
          "startStatus": getattr(material_record, "startStatus", None) if material_record else None,
          "isOpenEmpId": getattr(material_record, "isOpenEmpId", None) if material_record else None,
      })

    # 4) 沒有未結束流程 → 新建一筆（屬於當前 user）
    log = Process(
      material_id=material_id,
      user_id=user_id,
      process_type=process_type,
      begin_time=None,                # 讓前端按「開始」時再決定
      end_time=None,
      elapsedActive_time=0,
      is_pause=True,                  # 進入後顯示「開始」
      pause_time=0,
      has_started=False,              # 尚未按開始
      pause_started_at=None,
    )
    s.add(log)

    s.flush()   # 立刻取得 log.id

    # 同步 Material 狀態（若你前端有依賴這些欄位，再保留；沒有就拿掉下面三行）
    if material_record:
      material_record.isOpen = True
      material_record.isOpenEmpId = user_id
      # material_record.hasStarted = False            # 有需要再打開
      # material_record.startStatus = "not_started"  # 有需要再打開

    s.commit()
    '''

    '''
    return jsonify({
        "success": True,
        "process_id": log.id,
        "begin_time": log.begin_time,
        "elapsed_time": int(log.elapsedActive_time or 0),
        "is_paused": bool(log.is_pause),
        "pause_time": int(log.pause_time or 0),
        "has_started": bool(log.has_started),

        "isOpen": material_record.isOpen,
        "hasStarted": material_record.hasStarted,
        "startStatus": material_record.startStatus,
        "isOpenEmpId": material_record.isOpenEmpId,
    })

    '''
    return jsonify(
        success=True,
        process_id=new_log.id,
        begin_time=new_log.begin_time,
        elapsed_time=0,                     # 新建當然是 0
        is_paused=True,
        pause_time=0,
        has_started=False,

        isOpen=getattr(material_record, "isOpen", None) if material_record else None,
        hasStarted=getattr(material_record, "hasStarted", None) if material_record else None,
        startStatus=getattr(material_record, "startStatus", None) if material_record else None,
        isOpenEmpId=getattr(material_record, "isOpenEmpId", None) if material_record else None,
    )


@getTable.route("/dialog2UpdateProcess", methods=['POST'])
def update_process():
    print("dialog2UpdateProcess API....")

    data = request.json
    process_id = data["process_id"]
    new_secs   = int(data.get("elapsed_time", 0) or 0)

    s = Session()

    #log = s.query(Process).get(process_id)
    # 確保結果「最多只會有一筆」,
    # 回傳值:
    # 有一筆資料 → 回傳那筆物件
    # 沒有資料 → 回傳 None
    # 異常:
    # 超過一筆 → 丟 MultipleResultsFound 例外
    q = s.query(Process).filter_by(id=process_id).with_for_update()   # 鎖定該行後再更新, 避免 pause_started_at/pause_time 在同一瞬間被兩支 API 互相覆寫
    log = q.one_or_none()

    if not log:
        print("error, process not found!")
        return jsonify(success=False, message="process not found"), 404
    if log.end_time is not None:
        print("error, process already closed!")
        return jsonify(success=False, message="process already closed"), 400

    cur = int(log.elapsedActive_time or 0)

    # 取「想要的暫停狀態」：若前端沒傳，就用目前 DB 狀態
    want_pause = data.get("is_paused")
    if want_pause is None:
        want_pause = bool(log.is_pause)
    else:
        want_pause = bool(want_pause)


    # 🚧 夾擋：暫停中不得把有效秒數加大
    if want_pause and new_secs > cur:
        new_secs = cur

    # 仍保留「不回退」
    if new_secs < cur:
        new_secs = cur

    log.elapsedActive_time = new_secs

    # 正確維護 pause 欄位
    now = datetime.now(timezone.utc)

    print(f"[upd] cur={cur}, new={int(data.get('elapsed_time',0) or 0)}, want_pause={want_pause}, saved={log.elapsedActive_time}")

    if want_pause:
        # 進入/維持暫停：確保有起點
        if not log.is_pause:
            log.is_pause = True
            log.pause_started_at = now
        else:
            if not getattr(log, "pause_started_at", None):
                log.pause_started_at = now
    else:
        # 從暫停→恢復：補上這段暫停的秒數
        if log.is_pause:
            ps = getattr(log, "pause_started_at", None)
            if ps:
                if ps.tzinfo is None:
                    ps = ps.replace(tzinfo=timezone.utc)
                delta = max(0, int((now - ps).total_seconds()))
                log.pause_time = int(log.pause_time or 0) + delta
            log.pause_started_at = None
            log.is_pause = False

    s.commit()

    return jsonify(
        success=True,
        is_paused=bool(log.is_pause),
        elapsed_time=int(log.elapsedActive_time or 0),
        pause_time=int(log.pause_time or 0),
        pause_started_at=log.pause_started_at.isoformat() if log.pause_started_at else None,
    )



"""0917
@getTable.route("/dialog2UpdateProcess", methods=['POST'])
def update_process():
    print("dialog2UpdateProcess API....")

    data = request.json
    process_id   = data["process_id"]
    elapsed_time = int(data.get("elapsed_time", 0) or 0)
    want_pause   = bool(data.get("is_paused", False))

    s = Session()
    log = s.query(Process).get(process_id)
    if not log:
        return jsonify(success=False, message="process not found"), 404
    if log.end_time is not None:
        return jsonify(success=False, message="process already closed"), 400

    cur = int(log.elapsedActive_time or 0)

    # 🚫 暫停狀態：不允許把 elapsedActive_time 變大
    if want_pause and elapsed_time > cur:
        elapsed_time = cur

    # ✅ 仍保留「不回退」
    if  elapsed_time < cur:
         elapsed_time = cur

    # 你原本更新 elapsedActive_time 的邏輯保留
    log.elapsedActive_time = elapsed_time

    # ★ 關鍵保險：正確處理 pause_started_at 與 pause_time
    now = datetime.now(timezone.utc)

    if want_pause:
        # 維持/進入暫停
        if not log.is_pause:
            # 從運行 -> 暫停，起一個新暫停段
            log.is_pause = True
            if not getattr(log, "pause_started_at", None):
              log.pause_started_at = now
        else:
            # 已是暫停 → 確保有起點（有些路徑沒設到）
            if not getattr(log, "pause_started_at", None):
                log.pause_started_at = now
    else:
        # 維持/進入運行
        if log.is_pause:
            # 從暫停 -> 運行，結算暫停段長
            ps = getattr(log, "pause_started_at", None)
            if ps:
                # ps 可能是 naive；視為 UTC
                if ps.tzinfo is None:
                    ps = ps.replace(tzinfo=timezone.utc)
                delta = max(0, int((now - ps).total_seconds()))
                log.pause_time = int(log.pause_time or 0) + delta
            log.pause_started_at = None
            log.is_pause = False

    s.commit()

    # 回傳最新狀態（可讓前端對齊）
    return jsonify(
        success=True,
        is_paused=bool(log.is_pause),
        elapsed_time=int(log.elapsedActive_time or 0),
        pause_time=int(log.pause_time or 0),
        pause_started_at=log.pause_started_at.isoformat() if log.pause_started_at else None,
    )
"""


'''
@getTable.route("/dialog2UpdateProcess", methods=['POST'])
def update_process():
    print("dialog2UpdateProcess API....")

    data = request.json
    process_id = data["process_id"]

    if not process_id:
      return jsonify(success=False, message="missing process_id"), 400

    # 允許前端傳秒或毫秒（可選）
    elapsed_time = data.get("elapsed_time")   # 期望：秒（int）
    #elapsed_ms   = data.get("elapsed_ms")    # 如果你想直接帶毫秒也可以（可選）
    is_paused_in = data.get("is_paused")      #是否暫停

    s = Session()

    log = s.query(Process).get(process_id)
    if not log:
        return jsonify(success=False, message="process not found"), 404
    #if log.end_time is not None:
    #    return jsonify(success=False, message="process already closed"), 400

    try:
        if elapsed_time is not None:
            new_secs = int(elapsed_time)
            elapsed_sec = max(int(elapsed_time), 0)

            cur_secs = int(log.elapsedActive_time or 0)
            if new_secs < cur_secs:
                # 不回退；直接採用目前資料庫的值
                new_secs = cur_secs

            log.elapsedActive_time = new_secs

        else:
            elapsed_sec = None
    except Exception:
        return jsonify(success=False, message="invalid elapsed_time"), 400


    # 已結束(已經按確定鍵), 不可更新
    if log.end_time is not None:
        print("step5...")
        print("log.end_time:", log.end_time)
    #    # 已經關閉就不再更新
        return jsonify(success=False, message="process already closed"), 400

    # ✅ 只更新「有效計時」，不碰 pause_time
    if elapsed_sec is not None:
        print("step6...")
        log.elapsedActive_time = elapsed_sec
        try:
            # 若你有這個欄位（原本就有）
            log.str_elapsedActive_time = seconds_to_hms_str(int(log.elapsedActive_time))
        except Exception:
            # 忽略格式錯誤
            pass

    if log and log.end_time is None:  # 確保作業還在進行
        print("step7...")
        log.elapsedActive_time = data.get("elapsed_time", log.elapsedActive_time)
        log.str_elapsedActive_time = seconds_to_hms_str(int(log.elapsedActive_time))
        log.is_pause = data.get("is_paused", log.is_pause)
        s.commit()

    # 可選：同步 is_paused（不影響 pause_time 的累加，累加只在 toggle/close 做）
    # 2) 暫停/繼續狀態
    if is_paused_in is not None:
        log.is_pause = bool(is_paused_in)

    s.commit()

    return jsonify(
        success=True,
        process_id=log.id,
        elapsed_time=log.elapsedActive_time or 0,
        is_paused=log.is_pause,
        pause_time=log.pause_time or 0, # 只是回報；不在此路由更動
        #hasStarted,
    )

    #return jsonify(success=True)
'''

@getTable.route("/dialog2ToggleProcess", methods=['POST'])
def toggle_process():
    print("dialog2ToggleProcess API....")

    #
    #切換暫停/恢復：
    #  - is_paused=True  → 進入暫停狀態：只記下 pause_started_at（若當前不是暫停）
    #  - is_paused=False → 恢復：把 (now - pause_started_at) 累加到 pause_time，並清空 pause_started_at
    #

    data = request.json
    process_id = data["process_id"]
    want_pause = bool(data["is_paused"])

    s = Session()

    log = s.query(Process).get(process_id)
    q = s.query(Process).filter_by(id=process_id).with_for_update()   # 鎖定該行後再更新, 避免 pause_started_at/pause_time 在同一瞬間被兩支 API 互相覆寫
    log = q.one_or_none()

    if not log:
        return jsonify(success=False, message="process not found"), 404
    if log.end_time is not None:
        return jsonify(success=False, message="process already closed"), 400

    # 目前時刻（台北 aware）；用來算差、也用來存 begin_time 字串
    now_tpe_aw = datetime.now(TPE).replace(microsecond=0)
    now_tpe_str = now_tpe_aw.strftime(FMT)

    if want_pause:
        # → 要暫停
        if not log.is_pause:
            # 只有從「非暫停」→「暫停」時，才記錄起點
            log.is_pause = True

            log.pause_started_at = now_tpe_aw.replace(tzinfo=None)

        else:
            if not log.pause_started_at:
                log.pause_started_at = now_tpe_aw.replace(tzinfo=None)
    else:
        # → 要恢復
        if log.is_pause:
            # 從「暫停」→「恢復」時，把這段暫停秒數累加到 pause_time
            if log.pause_started_at:
                #delta = int((now - log.pause_started_at).total_seconds())

                #
                ps = log.pause_started_at
                # DB 撈出的 DATETIME 多為 naive；視為台北本地時間並補 tzinfo
                ps_aw = ps if ps.tzinfo else ps.replace(tzinfo=TPE)
                delta = int((now_tpe_aw - ps_aw).total_seconds())
                log.pause_time = (log.pause_time or 0) + max(0, delta)
            log.pause_started_at = None
            log.is_pause = False

        # 第一次開始時，標記 has_started=True，並補 begin_time
        if not getattr(log, "has_started", False):
            # 若你的模型已有 has_started 欄位，這裡會生效
            try:
                log.has_started = True
            except AttributeError:
                # 若模型尚未加欄位，就忽略，不影響既有邏輯
                pass

            if not log.begin_time:
                #log.begin_time = now
                log.begin_time = now_tpe_str


    s.commit()

    return jsonify(
        success=True,
        is_paused=log.is_pause,
        elapsed_time=int(log.elapsedActive_time or 0),
        pause_time=log.pause_time or 0,
        pause_started_at=log.pause_started_at.isoformat() if log.pause_started_at else None,
        # 回傳 has_started 讓前端可用（即使沒有欄位也安全處理）
        #has_started=getattr(log, "has_started", None),
        has_started=bool(log.has_started),
    )

    '''
    if log and log.end_time is None:
        is_paused = data["is_paused"]
        log.is_pause = is_paused

        if is_paused:
            # 🚩暫停：紀錄暫停開始時間 (若需要，可加欄位 pause_start_time)
            pass
        else:
            # 🚩恢復：累加 pause_time
            # 這裡需要在前端或後端計算 pause 時長，再加總
            pass

        s.commit()

    return jsonify(success=True)
    '''

''' for ready
@getTable.route("/dialog2CloseProcess", methods=['POST'])
def close_process():
    print("dialog2CloseProcess API....")

    data = request.json
    process_id = data["process_id"]
    elapsed_time  = data.get("elapsed_time")

    print("process_id:", process_id)

    s = Session()

    log = s.query(Process).get(process_id)

    if not log:
      return jsonify(success=False, message="process not found"), 404

    if log and log.end_time is None:
        now = datetime.now()

        # 1) 「暫停中」，先把最後這段暫停秒數補進 pause_time
        if getattr(log, "is_pause", False) and getattr(log, "pause_started_at", None):
            try:
                # pause_started_at 可能是字串或 datetime，視你的欄位型別而定
                if isinstance(log.pause_started_at, str):
                    # 若你資料庫存字串，請依你的格式解析；以下示範 ISO 格式
                    pause_start_dt = datetime.fromisoformat(log.pause_started_at)
                else:
                    pause_start_dt = log.pause_started_at

                delta = int((now - pause_start_dt).total_seconds())
                log.pause_time = (log.pause_time or 0) + max(delta, 0)
            except Exception as e:
                print("close_process: pause_time accumulate failed:", e)
            finally:
                # 清掉起點
                log.pause_started_at = None

        # 2) 把『有效計時秒數』覆蓋進去（獨立統計，不與 pause_time 相減）
        # 做單向遞增校正
        if elapsed_time is not None:
            try:
                last_secs = int(elapsed_time)
                log.elapsedActive_time = max(int(elapsed_time), 0)
            except Exception:
                pass  # 忽略格式錯誤，保留原值

            cur_secs = int(log.elapsedActive_time or 0)
            if last_secs < cur_secs:
                last_secs = cur_secs
            log.elapsedActive_time = last_secs

        # 3) 可選：產生 HH:MM:SS 文字（若你原本就有）
        try:
            log.str_elapsedActive_time = seconds_to_hms_str(int(log.elapsedActive_time or 0))
        except Exception:
            pass

        # 4) 關閉狀態
        log.is_pause = True
        log.end_time = now.strftime("%Y-%m-%d %H:%M:%S")  # 你原本用字串就維持一致

        s.commit()

        return jsonify(
            success=True,
            elapsed_time=log.elapsedActive_time or 0,
            pause_time=log.pause_time or 0,
            end_time=log.end_time
        )

    return jsonify(success=False, message="process not found or already closed"), 400
'''


'''
        log.elapsedActive_time = data.get("elapsed_time", log.elapsedActive_time)
        log.str_elapsedActive_time = seconds_to_hms_str(int(log.elapsedActive_time))
        log.is_pause = True
        log.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s.commit()

    return jsonify(success=True)
'''


@getTable.route("/dialog2CloseProcess", methods=['POST'])
def close_process():
    print("dialog2CloseProcess API....")

    data = request.json
    process_id   = data["process_id"]
    elapsed_time = data.get("elapsed_time")
    # ✅ 新增：本次完成數量與對應的 assemble 列
    receive_qty  = data.get("receive_qty", 0)
    assemble_id  = data.get("assemble_id", None)

    print("process_id:", process_id, "receive_qty:", receive_qty, "assemble_id:", assemble_id)

    s = Session()

    log = s.query(Process).get(process_id)
    if not log:
        return jsonify(success=False, message="process not found"), 404

    if log.end_time is not None:
        return jsonify(success=False, message="already closed"), 400

    now = datetime.now()

    # 1) 若暫停中，先把最後一段暫停秒數補進 pause_time
    if getattr(log, "is_pause", False) and getattr(log, "pause_started_at", None):
        try:
            if isinstance(log.pause_started_at, str):
                # 依你的實際格式調整；若你存 "%Y-%m-%d %H:%M:%S"，改用 datetime.strptime
                pause_start_dt = datetime.fromisoformat(log.pause_started_at)
            else:
                pause_start_dt = log.pause_started_at
            delta = int((now - pause_start_dt).total_seconds())
            log.pause_time = (log.pause_time or 0) + max(delta, 0)
        except Exception as e:
            print("close_process: pause_time accumulate failed:", e)
        finally:
            log.pause_started_at = None

    # 2) 校正『有效計時秒數』：採單向遞增（避免寫回比現值還小）
    if elapsed_time is not None:
        try:
            last_secs = int(elapsed_time)
        except Exception:
            last_secs = int(log.elapsedActive_time or 0)
        cur_secs = int(log.elapsedActive_time or 0)
        if last_secs < cur_secs:
            last_secs = cur_secs
        log.elapsedActive_time = max(int(last_secs), 0)

    # 3) 可選：更新 HH:MM:SS 文字欄（若模型有此欄位）
    try:
        log.str_elapsedActive_time = seconds_to_hms_str(int(log.elapsedActive_time or 0))
    except Exception:
        pass

    # 4) 關閉狀態
    log.is_pause = True
    log.end_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # 5)（重點）若有傳 assemble_id + receive_qty，更新該站完成數
    is_completed   = False
    total_completed = None
    must_qty       = None

    try:
        rq = int(receive_qty or 0)
    except Exception:
        rq = 0

    if assemble_id is not None and rq > 0:
        try:
            asm = s.query(Assemble).get(int(assemble_id))
        except Exception:
            asm = None

        if asm:
            # 依你的實際欄位名調整：
            # 假設：must_receive_end_qty = 應完成數量、total_ask_qty_end = 已完成總數
            must_qty = int(asm.must_receive_end_qty or 0)
            cur_total = int(asm.total_ask_qty_end or 0)
            new_total = cur_total + rq

            asm.total_ask_qty_end = new_total
            total_completed = new_total
            is_completed = (must_qty > 0 and new_total >= must_qty)

            s.add(asm)

    s.add(log)
    s.commit()

    return jsonify(
        success=True,
        end_time=log.end_time,
        elapsed_time=int(log.elapsedActive_time or 0),
        pause_time=int(log.pause_time or 0),
        # ✅ 前端可用來鎖定 Begin/End 的開始/結束鍵
        is_completed=is_completed,
        total_completed=total_completed,
        must_qty=must_qty
    )


'''
# get all processes data by order number
@getTable.route("/getProcessesByOrderNum", methods=['POST'])
def get_processes_by_order_num():
    print("getProcessesByOrderNum....")

    request_data = request.get_json()
    _order_num = request_data['order_num']
    print("order_num:", _order_num)

    code_to_name = {
      1 : '備料',
      19: '等待AGV(備料區)',
      2: 'AGV運行(備料區->組裝區)',
      23: '雷射',
      21: '組裝',
      22: '檢驗',
      29: '等待AGV(組裝區)',
      3: 'AGV運行(組裝區->成品區)',
      31: '成品入庫',

      5: '堆高機運行(備料區->組裝區)',
      6: '堆高機運行(組裝區->成品區)',
    }
    _results = []

    s = Session()

    material = s.query(Material).filter(Material.order_num == _order_num).first()
    work_qty = material.total_delivery_qty
    seq_num =0
    for record in material._process:
      status = code_to_name.get(record.process_type, '空白')
      temp_period_time =''
      print("!!!!record.begin_time:", record.begin_time, record.process_type)

      if record.process_type != 6 and record.process_type != 5:
        # 轉換為 datetime 物件
        #start_time = datetime.strptime(record.begin_time, "%Y-%m-%d %H:%M:%S")
        start_time = parse_dt_maybe(record.begin_time)
        print("!!!!start_time, record.begin_time:", record.begin_time)
        #end_time = datetime.strptime(record.end_time, "%Y-%m-%d %H:%M:%S")
        end_time = parse_dt_maybe(record.end_time)
        # 計算時間差
        time_diff = end_time - start_time

        # 轉換為分鐘數（小數點去掉）
        period_time = int(time_diff.total_seconds() // 60)

        # 轉換為 hh:mm:ss 格式字串
        total_seconds = int(time_diff.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_diff_str_format = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        work_time = period_time / work_qty
        work_time = round(period_time / work_qty, 1)  # 取小數點後 1 位


        # 轉換為字串格式
        time_diff_str = str(time_diff)
        #period_time_str = str(period_time)
        period_time_str = record.period_time
        work_time_str = str(work_time)  if (record.process_type == 21 or record.process_type == 22 or record.process_type == 23) else ''
        single_std_time_str = ''
        if record.process_type == 22:
          single_std_time_str = str(material.sd_time_B110)  #檢驗
        if record.process_type == 23:
          single_std_time_str = str(material.sd_time_B106)  #雷射
        if record.process_type == 21:
          single_std_time_str = str(material.sd_time_B109)  #組裝

        if record.process_type == 31:                       #成品入庫
          single_std_time_str = str(material.sd_time_B110)

        print("period_time:",period_time_str)

        temp_period_time = time_diff_str_format
        if record.process_type == 1:
          temp_period_time = record.period_time
        if record.process_type == 31:
          temp_period_time = ''
        print("temp_period_time:", temp_period_time, record.process_type)

      print("name:", record.user_id)
      name = record.user_id.lstrip("0")
      if record.process_type == 1 or record.process_type == 5 or record.process_type == 6 or record.process_type == 21 or record.process_type == 22 or record.process_type == 23 or record.process_type == 31:
        user = s.query(User).filter_by(emp_id=record.user_id).first()
        status = status + '(' + name + user.emp_name + ')'
      #if not record.normal_work_time:
      #  status = status + ' - 異常整修'
      print("status:", status)
      print("222!!!!start_time, record.begin_time:", record.begin_time)

      seq_num = seq_num + 1
      _object = {
          'seq_num': seq_num,
          'id': material.id,
          'order_num': material.order_num,
          #'total_delivery_qty': material.total_delivery_qty,
          #'process_work_time_qty': '' if (record.process_type == 2 or record.process_type == 3 or record.process_type == 19 or record.process_type == 29) else record.process_work_time_qty,
          'process_work_time_qty': record.process_work_time_qty if (record.process_type !=19 and record.process_type !=29 and record.process_type !=2 and record.process_type !=3 and record.process_type !=5 and record.process_type !=6) else '',
          'sd_time_B109': material.sd_time_B109,
          'sd_time_B106': material.sd_time_B106,
          'sd_time_B110': material.sd_time_B110,
          'user_id': name,
          'begin_time': record.begin_time,
          'end_time': record.end_time if record.process_type != 31 else '',
          #'period_time': period_time_str if record.process_type != 31 else '',
          'period_time': temp_period_time if record.process_type != 1 else record.str_elapsedActive_time,
          'work_time': work_time_str if record.process_type != 31 else '',
          'single_std_time': single_std_time_str if record.process_type != 31 else '',
          'process_type': status,
          'normal_type': ' - 異常整修' if not record.normal_work_time else '',
          'user_comment': '',
          'create_at': record.create_at
      }
      _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("getProcessesByOrderNum, 總數: ", temp_len)
    print("_results:",_results)

    # 根據 create_at 屬性的值進行排序
    _results = sorted(_results, key=lambda x: x['create_at'])

    return jsonify({

      'processes': _results
    })
'''


# get all processes data by order number
@getTable.route("/getProcessesByOrderNum", methods=['POST'])
def get_processes_by_order_num():
    print("getProcessesByOrderNum....")

    request_data = request.get_json()
    _order_num = request_data['order_num']
    print("order_num:", _order_num)

    code_to_name = {
        1:  '備料',
        19: '等待AGV(備料區)',
        2:  'AGV運行(備料區->組裝區)',
        23: '雷射',
        21: '組裝',
        22: '檢驗',
        29: '等待AGV(組裝區)',
        3:  'AGV運行(組裝區->成品區)',
        31: '成品入庫',
        5:  '堆高機運行(備料區->組裝區)',
        6:  '堆高機運行(組裝區->成品區)',
    }

    _results = []
    s = Session()

    material = s.query(Material).filter(Material.order_num == _order_num).first()
    if not material:
        s.close()
        return jsonify(success=False, message="order not found"), 404

    work_qty = material.total_delivery_qty or 0
    now_tpe_aw = datetime.now(TPE).replace(microsecond=0)

    seq_num = 0
    for record in material._process:
        seq_num += 1

        status = code_to_name.get(record.process_type, '空白')

        # ---- 使用者名稱附註（若有） ----
        name_core = (record.user_id or "").lstrip("0")
        if record.process_type in {1, 5, 6, 21, 22, 23, 31}:
            user = s.query(User).filter_by(emp_id=record.user_id).first()
            emp_name = user.emp_name if user and getattr(user, "emp_name", None) else ""
            status = f"{status}({name_core}{emp_name})"

        # ---- 計算時長（非 5/6 流動段才算）----
        temp_period_time = ""
        work_time_str = ""
        single_std_time_str = ""

        if record.process_type not in {5, 6}:
            #start_time = parse_dt_maybe(record.begin_time)
            #end_time = parse_dt_maybe(record.end_time)
            start_time = parse_dt_maybe_aw(record.begin_time)
            end_time   = parse_dt_maybe_aw(record.end_time)

            # 設定各製程標準單件工時字串
            if record.process_type == 22:   # 檢驗
                single_std_time_str = str(material.sd_time_B110)
            elif record.process_type == 23: # 雷射
                single_std_time_str = str(material.sd_time_B106)
            elif record.process_type == 21: # 組裝
                single_std_time_str = str(material.sd_time_B109)
            elif record.process_type == 31: # 成品入庫
                single_std_time_str = str(material.sd_time_B110)

            if start_time:
                if end_time:
                    # 已結束：用結束時間 - 開始時間
                    total_seconds = int((end_time - start_time).total_seconds())
                else:
                    # 未結束：依目前狀態計算有效作業秒數
                    pause_total = int(record.pause_time or 0)

                    #if getattr(record, "is_pause", False) and record.pause_started_at:
                    if getattr(record, "is_pause", False) and getattr(record, "pause_started_at", None):
                        #ps_aw = attach_tpe(record.pause_started_at)
                        ps_aw = parse_dt_maybe_aw(record.pause_started_at)
                        if ps_aw:
                            #pause_total += max(0, int((now_tpe_aw - ps_aw).total_seconds()))
                            # 若 DB 時間不小心比現在還未來，多餘負值做保護
                            extra_pause = int((now_tpe_aw - ps_aw).total_seconds())
                            pause_total += max(0, extra_pause)
                        # end if
                    # end if

                    # 這裡兩邊皆為 aware
                    total_seconds = int((now_tpe_aw - start_time).total_seconds()) - pause_total

                total_seconds = max(0, total_seconds)
                time_diff_str_format = fmt_hhmmss(total_seconds)

                # 你的原始需求：製程 1（備料）顯示 front-end 的 str_elapsedActive_time 優先
                if record.process_type == 1:
                    temp_period_time = record.str_elapsedActive_time or record.period_time or time_diff_str_format
                elif record.process_type == 31:
                    temp_period_time = ""  # 入庫不顯示
                else:
                    # 若 DB 已有 period_time 就沿用；否則用動態計算
                    temp_period_time = record.period_time or time_diff_str_format

                # 分/單件（只對 21/22/23/31 有意義，其它依你原本邏輯空白）
                if record.process_type in {21, 22, 23} and work_qty > 0:
                    minutes_total = total_seconds // 60
                    work_time = round(minutes_total / work_qty, 1)
                    work_time_str = str(work_time)
                elif record.process_type == 31:
                    work_time_str = ""
            else:
                # 沒開始時間
                temp_period_time = record.period_time or ""
        # else: 5/6 不計時長

        _object = {
            'seq_num': seq_num,
            'id': material.id,
            'order_num': material.order_num,
            'process_work_time_qty': (
                record.process_work_time_qty
                if record.process_type not in {19, 29, 2, 3, 5, 6}
                else ''
            ),
            'sd_time_B109': material.sd_time_B109,
            'sd_time_B106': material.sd_time_B106,
            'sd_time_B110': material.sd_time_B110,
            'user_id': name_core,
            'begin_time': record.begin_time,
            'end_time': record.end_time if record.process_type != 31 else '',
            'period_time': temp_period_time if record.process_type != 1 else (record.str_elapsedActive_time or temp_period_time),
            'work_time': work_time_str if record.process_type != 31 else '',
            'single_std_time': single_std_time_str if record.process_type != 31 else '',
            'process_type': status,
            'normal_type': ' - 異常整修' if not getattr(record, "normal_work_time", True) else '',
            'user_comment': '',
            'create_at': record.create_at,
        }
        _results.append(_object)

    s.close()

    # 依 create_at 排序
    _results = sorted(_results, key=lambda x: x['create_at'])

    return jsonify({'processes': _results})


# # get all all Warehouse For Assemble
@getTable.route("/getAbnormalCausesByHistory", methods=['POST'])
def get_abnormal_causes_by_history():
    print("getAbnormalCausesByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True

    materials = [u.__dict__ for u in s.query(Material).all()]

    # 過濾 isAssembleAlarm 為 True 的資料
    filtered_materials = [record for record in materials if record['isAssembleAlarm']]
    for record in filtered_materials:
      #包含歷史檔：_history_flag=true
      #不包含歷史檔:_history_flag=false and record['isAssembleAlarmRpt']=false
      if not (_history_flag==True or (record['isAssembleAlarmRpt']==False and _history_flag==False)):
        continue


# # get all all Warehouse For Assemble
@getTable.route("/getWarehouseForAssembleByHistory", methods=['POST'])
def get_Warehouse_For_assemble_by_history():
    print("getWarehouseForAssembleByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True

    materials = [u.__dict__ for u in s.query(Material).all()]
    #processed_order_nums = set()

    # 過濾掉 isAssembleStationShow 為 True 的資料
    filtered_materials = [record for record in materials if record['isAssembleStationShow']]
    for record in filtered_materials:
      #包含歷史檔：_history_flag=true
      #不包含歷史檔:_history_flag=false and record['isAllOk']=false
      if not (_history_flag==True or (record['isAllOk']==False and _history_flag==False)):
        continue
      cleaned_comment = record['material_comment'].strip()  # 刪除 material_comment 字串前後的空白

      _object = {
        'id': record['id'],
        'order_num': record['order_num'],                   #訂單編號
        'material_num': record['material_num'],             #物料編號
        'req_qty': record['material_qty'],                  #訂單數量
        'date': record['material_delivery_date'],           #交期
        'delivery_qty': record['assemble_qty'],             #組裝完成數量(到庫數量)
        'allOk_qty': record['allOk_qty'],                   #確認完成數量
        'total_allOk_qty': record['total_allOk_qty'],
        'must_allOk_qty': record['must_allOk_qty'],         #應入庫數量
        'input_disable': record['input_disable'],
        'delivery_date':record['material_delivery_date'],   #交期
        'shortage_note': record['shortage_note'],           #缺料註記 '元件缺料'
        'comment': cleaned_comment,                         #說明
        'isTakeOk' : record['isAllOk'],                     #true:成品已入庫
        'isShow' : record['isAssembleStationShow'],         #false:歷史檔案
        'isLackMaterial' : record['isLackMaterial'],
        'isBatchFeeding' :  record['isBatchFeeding'],
        'whichStation' : record['whichStation'],
        'show1_ok' : record['show1_ok'],
        'show2_ok' : record['show2_ok'],
        'show3_ok' : record['show3_ok'],
        'Incoming2_Abnormal': record['Incoming2_Abnormal'] == ''
      }

      _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("getWarehouseForAssembleByHistory, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 isTakeOk 屬性的值進行排序
    _results = sorted(_results, key=lambda x: not x['isTakeOk'])

    return jsonify({
      'status': return_value,
      'warehouse_for_assemble': _results
    })

'''
@getTable.route("/getInformationsForAssembleErrorByHistory", methods=['POST'])
def get_informations_for_assemble_error_by_history():
    print("getInformationsForAssembleErrorByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True
    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                3              4             5           6             7            8             9           10                 11           12            13          14                15            16          17
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)    16(agv_start)
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業',  'agv Start']

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for material_record in _objects:    # for loop a
      #包含歷史檔：_history_flag=true
      #不包含歷史檔:_history_flag=false and record['isAssembleAlarmRpt']=false
      if not (_history_flag==True or (material_record.isAssembleAlarm==False and material_record.isAssembleAlarmRpt==False and _history_flag==False)):
        continue

      skip_material = False   # 標誌變數，預設為 False
      assemble_ok = False
      assemble_users = []               # 用於存儲處理後的 user_id
      assemble_work_nums = []           # 用於存儲處理後的 user_id
      for assemble_record in material_record._assemble:   # for loop b
        if assemble_record.alarm_enable:   #False:異常
          continue

        assemble_ok = True

        user_id = assemble_record.user_id.lstrip('0')       # 去除前導的 0
        writer_id = assemble_record.writer_id.lstrip('0')   # 去除前導的 0

        #if user_id not in assemble_user_ids: # 於 user_ids 中, 檢查 user_id
        assemble_users.append(user_id)
        assemble_work_nums.append(assemble_record.work_num)
      #end for loop b

      temp_alarm_message=assemble_record.alarm_message.strip()
      temp_alarm_enable=assemble_record.alarm_enable

      user = ', '.join(assemble_users)        # 將列表轉換為以逗號分隔的字符串
      work =  ', '.join(assemble_work_nums)

      abnormal_cause_ids = [str(abnormal.id) for abnormal in material_record._abnormal_cause]       # 轉換為字串列表
      abnormal_cause_id_str = ",".join(abnormal_cause_ids) if len(abnormal_cause_ids) > 0 else ''   # 用逗號合併

      # 取得 material_record 關聯的 AbnormalCause
      abnormal_cause_strs = [
          f"{abnormal.message}({abnormal.number})" for abnormal in material_record._abnormal_cause
      ]
      abnormal_cause_message_str = ",".join(abnormal_cause_strs)  if len(abnormal_cause_strs) > 0 else '' #用逗號連接所有字串

      print("abnormal_cause_id_str:", len(abnormal_cause_ids), abnormal_cause_id_str)
      print("abnormal_cause_message_str:",len(abnormal_cause_strs), abnormal_cause_message_str)

      print("user:", user)
      print("work:", work)
      print("material order num:", material_record.order_num)
      cleaned_comment = material_record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

      temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
      temp_show2_ok = int(material_record.show2_ok)
      if (temp_show2_ok == 1):
        temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note

      _object = {
        'id': material_record.id,                                # 訂單編號的 table id
        'order_num': material_record.order_num,                  # 訂單編號
        'material_num': material_record.material_num,            # 物料編號
        'isTakeOk': material_record.isTakeOk,
        'whichStation': material_record.whichStation,
        'req_qty': material_record.material_qty,                 # 需求數量
        'delivery_date': material_record.material_delivery_date, # 交期
        'delivery_qty': material_record.delivery_qty,            # 現況數量
        'comment': cleaned_comment,                              # 說明
        'show1_ok': str1[int(material_record.show1_ok) - 1],     # 現況進度
        'show2_ok': temp_temp_show2_ok_str,
        'show3_ok': str3[int(material_record.show3_ok)],         # 現況備註
        'user': user,
        'work': work,
        #**abnormal_cause                                         # 將 cause_id, cause_number, cause_message 展開加入字典
        #'cause_number': '',
        'cause_id': abnormal_cause_id_str,
        'cause_message': abnormal_cause_message_str,
        #'assemble_id': assemble_record.id,
      }

      _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listInformationsForAssembleError, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 'order_num' 排序
    _results = sorted(_results, key=lambda x: x['order_num'])

    return jsonify({
      'status': return_value,
      'informations_for_assemble_error': _results
    })
'''

# 取得訂單「組裝異常」相關的歷史資訊清單
@getTable.route("/getInformationsForAssembleErrorByHistory", methods=['POST'])
def get_informations_for_assemble_error_by_history():
    print("getInformationsForAssembleErrorByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)   # 是否包含歷史資料
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True

    code_to_name = {
      '106': '雷射',  #第3個動作
      '109': '組裝',  #第1個動作
      '110': '檢驗'   #第2個動作
    }

    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                3              4             5           6             7            8             9           10                 11           12            13          14                15            16          17
    #str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '檢驗進行中', '00/00/00',  '雷射進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']

    #       0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)    16(agv_start)
    #str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業',  'agv Start']
    str3=['',       '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '檢驗進行中', '檢驗已結束', '雷射進行中', '雷射已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業',  'agv Start']

    _alarm_objects = s.query(AbnormalCause).all()  # 取得所有 AbnormalCause 物件

    _alarm_objects_list = [
      {"id": item.id, "message": f"{item.message}({item.number})"}
      for item in _alarm_objects
    ]
    print("_alarm_objects_list: ", _alarm_objects_list)

    _alarm_objects_dict = {
      str(item.id): f"{item.message}({item.number})"
      for item in _alarm_objects
    }
    print("_alarm_objects_dict: ", _alarm_objects_dict)

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    index = 0

    for material_record in _objects:    # for loop a
      #包含歷史檔：_history_flag=true
      #不包含歷史檔:_history_flag=false and record['isAssembleAlarmRpt']=false
      if not (_history_flag==True or (material_record.isAssembleAlarm==False and material_record.isAssembleAlarmRpt==False and _history_flag==False)):
        continue

      skip_material = False             # 標誌變數，預設為 False
      assemble_ok = False
      assemble_users = []               # 用於存儲處理後的 user_id
      assemble_work_nums = []           # 用於存儲處理後的 user_id

      temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
      temp_show2_ok = int(material_record.show2_ok)

      for assemble_record in material_record._assemble:   # for loop b
        #if assemble_record.alarm_enable:   #False:異常
        if assemble_record.alarm_enable and assemble_record.isAssembleFirstAlarm:   #False:異常
          continue

        assemble_ok = True

        #user_id = assemble_record.user_id.lstrip('0')       # 去除前導的 0
        user = s.query(User).filter_by(emp_id=assemble_record.user_id).first()
        #writer_id = assemble_record.writer_id.lstrip('0') if assemble_record.writer_id else ''
        if assemble_record.writer_id:
          writer = s.query(User).filter_by(emp_id=assemble_record.writer_id).first()
          writerName = writer.emp_name
        else:
          writerName = ''

        #從 assemble_record 中取得 alarm_message 欄位，這個欄位是以逗號與空白分隔的字串（例如 "異常1, 異常2, 異常3"）。
        temp_alarm_message = assemble_record.alarm_message
        print("temp_alarm_message:", temp_alarm_message)

        # 解析字串(非 None 或空字串, 且以', '作為分隔符號)轉成 ID list，例如 ['1', '3', '4'], "" 或 None → []
        alarm_id_list = temp_alarm_message.split(', ')  if temp_alarm_message else []
        print("alarm_id_list:", alarm_id_list)

        # 對應出異常訊息文字，並過濾掉找不到的 id
        temp_alarm_message_list = [
          _alarm_objects_dict.get(alarm_id) for alarm_id in alarm_id_list
          if _alarm_objects_dict.get(alarm_id)
        ]
        print("temp_alarm_message_list:", temp_alarm_message_list)

        #說明: 進一步過濾 temp_alarm_message_list 中的元素，只保留非空字串（msg 為 True）。
        #      這是為了避免有空的異常訊息（例如 "異常1, , 異常3"）也被加入。
        filtered_list = [msg for msg in temp_alarm_message_list if msg]
        print("filtered_list:", filtered_list)

        temp_alarm_enable = assemble_record.alarm_enable

        #abnormal_cause_ids = [str(abnormal.id) for abnormal in material_record._abnormal_cause]       # 轉換為字串列表
        #abnormal_cause_id_str = ",".join(abnormal_cause_ids) if len(abnormal_cause_ids) > 0 else ''   # 用逗號合併

        # 取得 material_record 關聯的 AbnormalCause
        #abnormal_cause_strs = [
        #    f"{abnormal.message}({abnormal.number})" for abnormal in material_record._abnormal_cause
        #]
        #abnormal_cause_message_str = ",".join(abnormal_cause_strs)  if len(abnormal_cause_strs) > 0 else '' #用逗號連接所有字串

        cleaned_comment = material_record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

        code = assemble_record.work_num[1:]                           # 取得字串中的代碼 (去掉字串中的第一個字元)
        work = code_to_name.get(code, '')                             # 查找對應的中文名稱
        '''
        temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
        temp_show2_ok = int(material_record.show2_ok)

        if (temp_show2_ok == 1):
          temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note
        '''

        # 處理 show2_ok 的情況
        if temp_show2_ok == 5 or temp_show2_ok == 7 or temp_show2_ok == 9:
          for _record in material_record._assemble:
            # 如果 `total_ask_qty_end` 為 1, 2 或 3，替換 `00/00/00` 的相應部分
            if _record.total_ask_qty_end in [1, 2, 3]:
              completed_qty = str(_record.completed_qty)  # 將數值轉換為字串
              date_parts = temp_temp_show2_ok_str.split('/')  # 分割 `00/00/00` 為 ['00', '00', '00']
              date_parts[_record.total_ask_qty_end - 1] = completed_qty  # 替換對應位置
              temp_temp_show2_ok_str = '/'.join(date_parts)  # 合併回字串

        if (temp_show2_ok == 1):
          temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note

        #temp_temp_show2_ok_str = re.sub(r'\b00\b', 'na', temp_temp_show2_ok_str)
        temp_temp_show2_ok_str = re.sub(r'\b00\b', '', temp_temp_show2_ok_str)

        index += 1

        _object = {
          'index': index,
          'id': material_record.id,                                # 訂單編號的 table id
          'assemble_id': assemble_record.id,
          'order_num': material_record.order_num,                  # 訂單編號
          'material_num': material_record.material_num,            # 物料編號
          'isTakeOk': material_record.isTakeOk,
          'whichStation': material_record.whichStation,
          'req_qty': material_record.material_qty,                  # 需求數量
          'delivery_date': material_record.material_delivery_date,  # 交期
          'delivery_qty': material_record.delivery_qty,             # 現況數量
          'comment': cleaned_comment,                               # 說明
          'show1_ok': str1[int(material_record.show1_ok) - 1],      # 現況進度
          'show2_ok' : temp_temp_show2_ok_str,                      #現況進度(途程)
          'show3_ok': str3[int(material_record.show3_ok)],          # 現況備註
          'cause_user': writerName,   #填寫人員
          'user': user.emp_name,      #檢點人員
          #'work_num'
          #'user': user_id,
          'work': work,
          #**abnormal_cause                                         # 將 cause_id, cause_number, cause_message 展開加入字典
          #'cause_number': '',
          #'cause_id': abnormal_cause_id_str,
          #'cause_message': abnormal_cause_message_str,
          'cause_message':filtered_list,
          #'assemble_id': assemble_record.id,
        }

        _results.append(_object)
        #end loop b
    #end loop a
    s.close()

    temp_len = len(_results)
    print("getInformationsForAssembleErrorByHistory, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 'order_num' 排序
    _results = sorted(_results, key=lambda x: x['order_num'])

    return jsonify({
      'status': return_value,
      'informations_for_assemble_error': _results,
      'alarm_objects_list': _alarm_objects_list,
    })


# 取得訂單「組裝異常」相關的歷史資訊清單
@getTable.route("/getSchedulesForAssembleError", methods=['POST'])
def get_schedule_for_assemble_error():
    print("getScheduleForAssembleError....")

    data = request.json
    _history_flag = data.get('history_flag', False)   # 是否包含歷史資料
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True

    code_to_name = {
      '106': '雷射',  #第3個動作
      '109': '組裝',  #第1個動作
      '110': '檢驗'   #第2個動作
    }

    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                 3              4            5           6             7            8             9           10                 11           12            13          14                15            16          17
    #str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '檢驗進行中', '00/00/00',  '雷射進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']

    #       0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)   8(開始鍵)     9(結束鍵)    10(agv_begin)      11(agv_end)   12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)    16(agv_start)
    #str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業',  'agv Start']
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '檢驗進行中', '檢驗已結束', '雷射進行中', '雷射已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業',  'agv Start']

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for material_record in _objects:    # for loop a
      #包含歷史檔：_history_flag=true
      #不包含歷史檔:_history_flag=false and record['isAssembleAlarmRpt']=false
      if not (_history_flag==True or (material_record.isAssembleAlarm==False and material_record.isAssembleAlarmRpt==False and _history_flag==False)):
        continue

      temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
      temp_show2_ok = int(material_record.show2_ok)

      for assemble_record in material_record._assemble:   # for loop b
        if assemble_record.alarm_enable:   #False:異常
          continue

        code = assemble_record.work_num[1:]                           # 取得字串中的代碼 (去掉字串中的第一個字元)
        work = code_to_name.get(code, '')                             # 查找對應的中文名稱

        # 處理 show2_ok 的情況
        if temp_show2_ok == 5 or temp_show2_ok == 7 or temp_show2_ok == 9:
          for _record in material_record._assemble:
            # 如果 `total_ask_qty_end` 為 1, 2 或 3，替換 `00/00/00` 的相應部分
            if _record.total_ask_qty_end in [1, 2, 3]:
              completed_qty = str(_record.completed_qty)  # 將數值轉換為字串
              date_parts = temp_temp_show2_ok_str.split('/')  # 分割 `00/00/00` 為 ['00', '00', '00']
              date_parts[_record.total_ask_qty_end - 1] = completed_qty  # 替換對應位置
              temp_temp_show2_ok_str = '/'.join(date_parts)  # 合併回字串

        if (temp_show2_ok == 1):
          temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note

        #temp_temp_show2_ok_str = re.sub(r'\b00\b', 'na', temp_temp_show2_ok_str)
        temp_temp_show2_ok_str = re.sub(r'\b00\b', '', temp_temp_show2_ok_str)

        _object = {
          'id': material_record.id,                                # 訂單編號的 table id
          'assemble_id': assemble_record.id,
          'order_num': material_record.order_num,                  # 訂單編號
          'material_num': material_record.material_num,            # 物料編號
          'isTakeOk': material_record.isTakeOk,
          'whichStation': material_record.whichStation,
          'show1_ok': str1[int(material_record.show1_ok) - 1],      # 現況進度
          'show2_ok' : temp_temp_show2_ok_str,                      #現況進度(途程)
          'show3_ok': str3[int(material_record.show3_ok)],          # 現況備註
          'work': work,
        }

        _results.append(_object)
        #end loop b
    #end loop a
    s.close()

    temp_len = len(_results)
    print("getScheduleForAssembleError, 總數: ", temp_len)
    if (temp_len == 0):
      return_value = False

    # 根據 'order_num' 排序
    _results = sorted(_results, key=lambda x: x['order_num'])

    return jsonify({
      'status': return_value,
      'schedules_for_assemble_error': _results,
    })

'''
# get all assemble error information by history
@getTable.route("/getInformationsForAssembleErrorByHistory", methods=['POST'])
def get_2_informations_for_assemble_error_by_history():
    print("2 getInformationsForAssembleErrorByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True
    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                3              4             5           6             7            8             9           10                 11           12            13          14                15            16          17
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)    16(agv_start)
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業',  'agv Start']

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for material_record in _objects:
      #print("material id:", material_record.id)
      skip_material = False  # 標誌變數，預設為 False
      user_ids = []  # 用於存儲處理後的 user_id
      #print("step a...", material_record.id)
      assemble_ok = False
      for assemble_record in material_record._assemble:
        if assemble_record.material_id != material_record.id:
          skip_material = True
        if assemble_record.alarm_enable == False:
          continue

        assemble_ok = True
        #print("assemble id:", assemble_record.id)
        user_id = assemble_record.user_id.lstrip('0')  # 去除前導的 0
        #user_ids.append(user_id)  # 將處理後的值加入列表
        # 檢查 user_id 是否已存在於 user_ids 中
        if user_id not in user_ids:
          user_ids.append(user_id)  # 如果不存在，則插入列表

      if skip_material or not assemble_ok:
          continue                # 跳過當前 material_record，進入下一個 _objects 的迴圈

      #print("material id:", material_record.id)

      temp_alarm_message=assemble_record.alarm_message.strip()
      temp_alarm_enable=assemble_record.alarm_enable
      if not _history_flag and temp_alarm_enable and temp_alarm_message:
        continue
      print("temp_alarm_message:",temp_alarm_message)

      user = ', '.join(user_ids)  # 將列表轉換為以逗號分隔的字符串
      print("user:", user)
      print("material order num:", material_record.order_num)
      cleaned_comment = material_record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

      temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
      temp_show2_ok = int(material_record.show2_ok)
      if (temp_show2_ok == 1):
        temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note

      ## 取得所有相關聯的 AbnormalCause 資料
      #abnormal_cause = (
      #  {
      #    "cause_id": material_record._abnormal_cause[0].id,
      #    "cause_number": material_record._abnormal_cause[0].number,
      #    "cause_message": material_record._abnormal_cause[0].message,
      #  }
      #  if material_record._abnormal_cause and len(material_record._abnormal_cause) > 0
      #  else {
      #    "cause_id": '',
      #    "cause_number": '',
      #    "cause_message": '',
      #  }
      #)


      temp_list = [x.strip("'") for x in temp_alarm_message.split(",")] if temp_alarm_message else []
      _object = {
        'id': material_record.id,                                # 訂單編號的 table id
        'order_num': material_record.order_num,                  # 訂單編號
        'material_num': material_record.material_num,            # 物料編號
        'isTakeOk': material_record.isTakeOk,
        'whichStation': material_record.whichStation,
        'req_qty': material_record.material_qty,                 # 需求數量
        'delivery_date': material_record.material_delivery_date, # 交期
        'delivery_qty': material_record.delivery_qty,            # 現況數量
        'comment': cleaned_comment,                              # 說明
        'show1_ok': str1[int(material_record.show1_ok) - 1],     # 現況進度
        'show2_ok': temp_temp_show2_ok_str,
        'show3_ok': str3[int(material_record.show3_ok)],         # 現況備註
        'user': user,
        #**abnormal_cause                                         # 將 cause_id, cause_number, cause_message 展開加入字典
        #'cause_number': '',
        'cause_message': temp_list,
        'assemble_id': assemble_record.id,
      }

      _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listInformationsForAssembleError, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 'order_num' 排序
    _results = sorted(_results, key=lambda x: x['order_num'])

    return jsonify({
      'status': return_value,
      'informations_for_assemble_error': _results
    })
'''


"""
# list all materials and assemble data by current user
@getTable.route("/getMaterialsAndAssemblesByUser", methods=['POST'])
def get_materials_and_assembles_by_user():
    print("getMaterialsAndAssemblesByUser....")

    request_data = request.get_json()

    _user_id = request_data['user_id']

    s = Session()

    _results = []
    return_value = True
    code_to_name = {'106':'雷射', '109':'組裝', '110':'檢驗'}

    code_to_assembleStep = {    #組裝區工作順序, 3:最優先
      '109': 3, '106': 1, '110': 2, }

    #       0         1       2            3              4            5           6            7           8            9           10             11            12
    #str2=['未備料', '備料中', '備料完成',   '等待組裝作業', '組裝進行中', '00/00/00', '雷射進行中', '00/00/00', '檢驗進行中', '00/00/00', '等待入庫作業', '入庫進行中',  '入庫完成']
    str2=['未備料', '備料中', '備料完成',   '等待組裝作業', '組裝進行中', '00/00/00', '檢驗進行中', '00/00/00', '雷射進行中', '00/00/00', '等待入庫作業', '入庫進行中',  '入庫完成']

    _objects = s.query(Material).all()

    # 初始化一個 set 來追蹤已處理的 (order_num_id, format_name)
    processed_records = set()

    # 初始化一個暫存字典來存放每個 order_num_id 下的最大 process_step_code
    max_step_code_per_order = {}

    # 搜尋所有紀錄，找出每個訂單下最大的 process_step_code
    '''
    for material_record in _objects:    # loop_1
      for assemble_record in material_record._assemble:   # loop_2

        # 檢查員工編號是否符合, 且生產報工的已領取總數是否為0
        #if assemble_record.user_id != _user_id or assemble_record.total_ask_qty == 0:
        if assemble_record.user_id != _user_id or assemble_record.ask_qty == 0:
          continue  # 如果不符合，跳過這筆紀錄

        #code = assemble_record.work_num[1:]                  # 取得字串中的代碼 (去掉字串中的第一個字元)
        #step_code = code_to_assembleStep.get(code, 0)        # 取得對應的 step code
        step_code = assemble_record.process_step_code         # 直接使用資料中的 step_code

        #order_num = material_record.order_num                 # 訂單編號
        #order_num_id = material_record.id                     # 該筆訂單編號的table id
        order_num_id = assemble_record.id                     # 該筆訂單編號的table id

        ## 設定或更新該 order_num_id 下的最大 step code
        #if order_num_id not in max_step_code_per_order:
        #    max_step_code_per_order[order_num_id] = step_code
        #else:
        #    max_step_code_per_order[order_num_id] = max(max_step_code_per_order[order_num_id], step_code)

        #    print(f"Processing material id={order_num_id}, assemble work_num={assemble_record.work_num}, step_code={step_code}")

        # 設定或更新該 order_num_id 下的最大 step code
        if order_num_id not in max_step_code_per_order:
            max_step_code_per_order[order_num_id] = step_code
            print(f"Set initial max step_code for id={order_num_id}: {step_code}")
        else:
            current_max = max_step_code_per_order[order_num_id]
            max_step_code_per_order[order_num_id] = max(current_max, step_code)
            print(f"Updated max step_code for id={order_num_id}: {current_max} -> {max_step_code_per_order[order_num_id]}")
      # end loop_2
    # end loop_1
    '''
    for material_record in _objects:
      for assemble_record in material_record._assemble:
        step_code = assemble_record.process_step_code   # 直接使用資料中的 step_code
        order_num_id = material_record.id               # 該筆訂單編號的table id

        # 設定或更新該 order_num_id 下的最大 step code
        if order_num_id not in max_step_code_per_order:
          max_step_code_per_order[order_num_id] = step_code
        else:
          current_max = max_step_code_per_order[order_num_id]
          max_step_code_per_order[order_num_id] = max(current_max, step_code)

    print("Final max_step_code_per_order:", max_step_code_per_order)

    #流程追蹤與狀態管理：
    #根據工序代碼（如 '106', '109', '110'）判斷當前流程階段，並匹配對應的名稱和步驟。
    #追蹤每個訂單的最大進度階段，確保顯示的資料反映正確的流程狀態。

    # 在此期間，_objects 中的資料會被鎖定，其他進程或交易無法修改這些資料, 但自己可以執行你需要的操作，如更新或處理資料
    #_objects = s.query(Material).all()
    index = 0
    for material_record in _objects:
      assemble_records = material_record._assemble
      for assemble_record in material_record._assemble:

        # 檢查員工編號是否符合及生產報工的已領取總數不為0
        #if assemble_record.user_id != _user_id or assemble_record.total_ask_qty == 0 or material_record.isAssembleStationShow:
        #if assemble_record.user_id != _user_id or assemble_record.ask_qty == 0 or material_record.isAssembleStationShow:

        '''
        print("判斷")
        print("material_record.id:",material_record.id)
        print("assemble_record.id:",assemble_record.id)
        print("assemble_record.user_id, _user_id:",assemble_record.user_id, _user_id)
        print("assemble_record.input_end_disable", assemble_record.input_end_disable)

        print("assemble_record.ask_qty", assemble_record.ask_qty)
        print("material_record.isAssembleStationShow:", material_record.isAssembleStationShow)
        print("assemble_record.isAssembleStationShow:",assemble_record.isAssembleStationShow)
        '''

        '''
        if (assemble_record.user_id != _user_id or
            assemble_record.ask_qty == 0 or
            assemble_record.input_end_disable or
            material_record.isAssembleStationShow or
            assemble_record.isAssembleStationShow
           ):
        '''
        if (assemble_record.user_id != _user_id):   # 相同登入者
          continue

        #print("1. :", assemble_record.input_disable, assemble_record.input_end_disable, assemble_record.isAssembleStationShow)
        if not ((assemble_record.input_disable and not assemble_record.input_end_disable) or
                assemble_record.isAssembleStationShow):
        #   ):

        #print("1. :", assemble_record.input_end_disable, assemble_record.isAssembleStationShow)
        #if not (assemble_record.input_end_disable and assemble_record.isAssembleStationShow):
          continue
        print("2. :", assemble_record.input_disable, assemble_record.input_end_disable, assemble_record.isAssembleStationShow)

        code = assemble_record.work_num[1:]                 # 取得字串中的代碼 (去掉字串中的第一個字元)
        name = code_to_name.get(code, '')                   # 查找對應的中文名稱
        format_name = f"{assemble_record.work_num}({name})"
        #print("format_name:", format_name)
        #order_num_id = material_record.id                   # 該筆訂單編號的table id
        order_num_id  = assemble_record.material_id
        #print("order_num_id:", assemble_record.id, order_num_id)
        #print("processed_records:", processed_records)
        # 如果 (order_num_id, format_name) 組合已經存在，則跳過
        #if (order_num_id, format_name) in processed_records:
        #  continue

        # 比較該筆記錄的 step_code 是否為該訂單下最大的
        '''
        max_step_code = max_step_code_per_order.get(order_num_id, 0)
        step_code = assemble_record.process_step_code
        step_enable = (step_code == max_step_code and material_record.whichStation==2)  # 如果是最大值，則啟用
        '''
        order_num_id = material_record.id                   # 該筆訂單編號的table id
        step_code = assemble_record.process_step_code
        max_step_code = max_step_code_per_order.get(order_num_id, 0)
        step_enable = (step_code == max_step_code and material_record.whichStation==2)

        num = int(material_record.show2_ok)
        #print("bug num:", num)
        cleaned_comment = material_record.material_comment.strip()          # 刪除 material_comment 字串前後的空白

        temp_assemble_process_str = str2[num]

        temp_assemble_process_str = str2[num]
        temp_show2_ok = int(material_record.show2_ok)
        temp_assemble_show2_ok = assemble_record.show2_ok

        #if (num == 1):
        #if temp_show2_ok == 1:
        if temp_show2_ok == 1 or temp_assemble_show2_ok == 1:
          temp_assemble_process_str = temp_assemble_process_str + material_record.shortage_note

        index += 1

        #
        # 處理 show2_ok 的情況

        #if temp_show2_ok in [5, 7, 9]:
        if temp_show2_ok in [5, 7, 9] or temp_assemble_show2_ok in [5, 7, 9]:
          for temp2_assemble_record in assemble_records:
            if temp2_assemble_record.total_ask_qty_end in [1, 2, 3]:
              completed_qty = str(temp2_assemble_record.completed_qty)                  # 將數值轉換為字串
              date_parts = temp_assemble_process_str.split('/')                         # 分割 00/00/00 為 ['00', '00', '00']
              date_parts[temp2_assemble_record.total_ask_qty_end - 1] = completed_qty   # 替換對應位置
              temp_assemble_process_str = '/'.join(date_parts)                          # 合併回字串
        #

        _object = {
          'index': index,                                   #agv送料序號
          'id': material_record.id,                         #訂單編號
          'order_num': material_record.order_num,           #訂單編號
          'assemble_work': format_name,                     #工序
          'material_num': material_record.material_num,     #物料編號
          #'assemble_process': '' if (num > 2 and not step_enable) else str2[num],       #途程目前狀況 isTakeOk & step_enable
          'assemble_process': '' if (num > 2 and not step_enable) else temp_assemble_process_str,
          'assemble_process_num': num,
          'assemble_id': assemble_record.id,
          'req_qty': material_record.material_qty,                                         #需求數量(作業數量)
          #'total_ask_qty': assemble_record.total_ask_qty,
          'total_ask_qty': assemble_record.ask_qty,
          'total_ask_qty_end': assemble_record.total_ask_qty_end,
          'process_step_code': assemble_record.process_step_code,

          'total_receive_qty_num': assemble_record.total_ask_qty,                       #領取總數量
          'total_receive_qty': f"({assemble_record.total_completed_qty})",              # 已完成總數量
          'total_receive_qty_num': assemble_record.total_completed_qty,

          'must_receive_end_qty': assemble_record.ask_qty,                              #應完成數量
          'abnormal_qty': assemble_record.abnormal_qty,                                 #組裝區異常數量

          'receive_qty': assemble_record.completed_qty,                                 #組裝區領料完成數量
          'delivery_date': material_record.material_delivery_date,                      #交期
          'delivery_qty': material_record.delivery_qty,                                 #現況數量
          #'assemble_qty': material_record.assemble_qty,                                 #(組裝）完成數量
          'abnormal_qty': assemble_record.isAssembleFirstAlarm_qty if code == '109' else assemble_record.abnormal_qty,

          'total_assemble_qty': material_record.total_assemble_qty,                     #已(組裝）完成總數量

          'comment': cleaned_comment,                                                   #說明
          'isAssembleAlarm' : material_record.isAssembleAlarm,

          'isAssembleFirstAlarm' : assemble_record.isAssembleFirstAlarm,                # 2025-07-24
          'isAssembleFirstAlarm_qty' : assemble_record.isAssembleFirstAlarm_qty,

          'alarm_enable' : assemble_record.alarm_enable,
          'whichStation' : material_record.whichStation,
          'isTakeOk': material_record.isAssembleStation3TakeOk,                         # true:組裝站製程3完成(最後製程)
          'isLackMaterial': material_record.isLackMaterial,
          'shortage_note': material_record.shortage_note,

          'isShow': assemble_record.isAssembleStationShow,
          'currentStartTime': assemble_record.currentStartTime,
          'tooltipVisible': False,
                                                                                                                      #顯示數字輸入欄位alarm
          'abnormal_tooltipVisible': False,
                                                                                                                    #顯示數字輸入欄位alarm
          'input_end_disable': assemble_record.input_end_disable,
          'input_abnormal_disable': assemble_record.input_abnormal_disable,
          'process_step_enable': step_enable,

          'code': code,

          'assemble_count': len(material_record._assemble),

          'is_copied_from_id': assemble_record.is_copied_from_id,
        }

        processed_records.add((order_num_id, format_name))
        _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("getMaterialsAndAssemblesByUser, 總數: ", temp_len)
    if (temp_len == 0):
      return_value = False

    return jsonify({
      'status': return_value,
      'materials_and_assembles_by_user': _results
    })
"""



# get all materials and assemble count by current user
@getTable.route("/getCountMaterialsAndAssemblesByUser", methods=['POST'])
def get_count_materials_and_assembles_by_user():
    print("getCountMaterialsAndAssemblesByUser....")

    request_data = request.get_json()

    _user_id = request_data['user_id']

    s = Session()

    _objects = s.query(Material).all()
    material_ids_all = [m.id for m in _objects]

    counts_by_type = active_count_map_by_material_multi(
        s, material_ids_all,
        process_types=(21, 22, 23),
        include_paused=True,
        # only_user_id=None             # 全員
        only_user_id=_user_id,          # 只算該使用者本人（看你要哪種）
        has_started=True,               # 只找 has_started=True
    )

    total_active_records = sum(
        1 for m in counts_by_type.values() for c in m.values() if c > 0
    )
    print("end_count, total_active_records:", total_active_records)

    return jsonify({
      'end_count': total_active_records
    })


# get all materials and assemble count by current user
@getTable.route("/getCountMaterialsAndAssemblesByUser2", methods=['POST'])
def get_count_materials_and_assembles_by_user2():
    print("getCountMaterialsAndAssemblesByUser2....")

    request_data = request.get_json()

    _user_id = request_data['user_id']

    s = Session()

    _objects = s.query(Material).all()
    material_ids_all = [m.id for m in _objects]

    counts_by_type = active_count_map_by_material_multi(
        s, material_ids_all,
        process_types=(21, 22, 23),
        include_paused=False,          # 只算正在跑
        # only_user_id=None            # ← 全員
        only_user_id=_user_id,          # ← 只算該使用者本人（看你要哪種）
        has_started=True,               # 只找 has_started=True
    )

    total_active_records = sum(
        1 for m in counts_by_type.values() for c in m.values() if c > 0
    )
    print("end_count, total_active_records:", total_active_records)

    return jsonify({
      'end_count': total_active_records
    })


# list all materials and assemble data by current user
@getTable.route("/getMaterialsAndAssemblesByUser", methods=['POST'])
def get_materials_and_assembles_by_user():
    print("getMaterialsAndAssemblesByUser....")

    request_data = request.get_json()

    _user_id = request_data['user_id']

    s = Session()

    _results = []
    return_value = True
    code_to_name = {'106':'雷射', '109':'組裝', '110':'檢驗'}    # 組裝區工作代號
    code_to_assembleStep = { '109': 3, '106': 1, '110': 2, }    # 組裝區工作順序, 3:最優先

    #       0         1       2            3              4            5           6            7           8            9           10             11            12
    str2=['未備料', '備料中', '備料完成',   '等待組裝作業', '組裝進行中', '00/00/00', '檢驗進行中', '00/00/00', '雷射進行中', '00/00/00', '等待入庫作業', '入庫進行中',  '入庫完成']

    _objects = s.query(Material).all()
    material_ids_all = [m.id for m in _objects]

    # 1) 只撈「該使用者、且 has_started=True」的未結束 Process 名單/計數
    counts_by_type = active_count_map_by_material_multi(
        s, material_ids_all,
        process_types=(21, 22, 23),
        include_paused=False,           # 是否把暫停算在「未結束」內，False:不包括
        # only_user_id=None            # ← 全員
        only_user_id=_user_id,          # ← 只算該使用者本人（看你要哪種）
        has_started=True,               # 只找 has_started=True
    )

    # 查「誰」正在該料號/該製程上有未結束(進行中或暫停中)的流程, 並將結果依「製程別(21/22/23) → 料號ID」分組，回傳每一組底下的使用者ID清單。
    user_ids_by_type = active_user_ids_by_material_multi(
        s, material_ids_all,
        process_types=(21, 22, 23),
        include_paused=True,
        # only_user_id=None,           # 全員名單
        only_user_id=_user_id,          # 僅該使用者的名單
        as_string=False,                # 建議回 list
        has_started=True,               # 只找 has_started=True
    )

    # 初始化一個 set 來追蹤已處理的 (order_num_id, format_name)
    processed_records = set()

    # 初始化一個暫存字典來存放每個 order_num_id 下的最大 process_step_code
    max_step_code_per_order = {}

    # 搜尋所有紀錄，找出每個訂單下最大的 process_step_code
    for material_record in _objects:
      for assemble_record in material_record._assemble:
        step_code = assemble_record.process_step_code   # 直接使用資料中的 step_code
        order_num_id = material_record.id               # 該筆訂單編號的table id

        # 設定或更新該 order_num_id 下的最大 step code
        if order_num_id not in max_step_code_per_order:
          max_step_code_per_order[order_num_id] = step_code
        else:
          current_max = max_step_code_per_order[order_num_id]
          max_step_code_per_order[order_num_id] = max(current_max, step_code)

    print("Final max_step_code_per_order:", max_step_code_per_order)

    #流程追蹤與狀態管理：
    #根據工序代碼（如 '106', '109', '110'）判斷當前流程階段，並匹配對應的名稱和步驟。
    #追蹤每個訂單的最大進度階段，確保顯示的資料反映正確的流程狀態。

    # 在此期間，_objects 中的資料會被鎖定，其他進程或交易無法修改這些資料, 但自己可以執行你需要的操作，如更新或處理資料
    index = 0
    for material_record in _objects:                      # loop_m_rec
      assemble_records = material_record._assemble
      for assemble_record in material_record._assemble:   # loop_a_rec

        ### 相同登入者 ###
        #if (assemble_record.user_id != _user_id):   # 相同登入者
        #  continue
        ###

        #if not ((assemble_record.input_disable and not assemble_record.input_end_disable) or
        #        assemble_record.isAssembleStationShow):
        #  continue

        code = assemble_record.work_num[1:]                 # 取得字串中的代碼 (去掉字串中的第一個字元)
        name = code_to_name.get(code, '')                   # 查找對應的中文名稱
        format_name = f"{assemble_record.work_num}({name})"
        order_num_id = material_record.id                   # 該筆訂單編號的table id
        step_code = assemble_record.process_step_code
        max_step_code = max_step_code_per_order.get(order_num_id, 0)
        step_enable = (step_code == max_step_code and material_record.whichStation==2)

        num = int(material_record.show2_ok)
        cleaned_comment = material_record.material_comment.strip()          # 刪除 material_comment 字串前後的空白

        temp_assemble_process_str = str2[num]
        temp_show2_ok = int(material_record.show2_ok)
        temp_assemble_show2_ok = assemble_record.show2_ok

        if temp_show2_ok == 1 or temp_assemble_show2_ok == 1:
          temp_assemble_process_str = temp_assemble_process_str + material_record.shortage_note

        index += 1

        #
        # 處理 show2_ok 的情況
        if temp_show2_ok in [5, 7, 9] or temp_assemble_show2_ok in [5, 7, 9]:
          for temp2_assemble_record in assemble_records:
            if temp2_assemble_record.total_ask_qty_end in [1, 2, 3]:
              completed_qty = str(temp2_assemble_record.completed_qty)                  # 將數值轉換為字串
              date_parts = temp_assemble_process_str.split('/')                         # 分割 00/00/00 為 ['00', '00', '00']
              date_parts[temp2_assemble_record.total_ask_qty_end - 1] = completed_qty   # 替換對應位置
              temp_assemble_process_str = '/'.join(date_parts)                          # 合併回字串
        #

        _object = {
          'index': index,                                   #agv送料序號
          'id': material_record.id,                         #訂單編號
          'order_num': material_record.order_num,           ## 訂單編號
          'material_num': material_record.material_num,     ## 物料編號
          'req_qty': material_record.material_qty,          ## 組裝區需求數量(訂單數量)
          'ask_qty': assemble_record.ask_qty,         ## 組裝區領取數量

          'assemble_work': format_name,                     #工序
          'assemble_process': '' if (num > 2 and not step_enable) else temp_assemble_process_str,
          'assemble_process_num': num,
          'assemble_id': assemble_record.id,
          'total_ask_qty_end': assemble_record.total_ask_qty_end,
          'process_step_code': assemble_record.process_step_code,

          #'total_receive_qty_num': assemble_record.total_ask_qty,                       # 領取總數量
          'total_receive_qty': f"({assemble_record.total_completed_qty})",
          'total_receive_qty_num': assemble_record.total_completed_qty,     ## 組裝區完成數量的總數

          'must_receive_end_qty': assemble_record.ask_qty,                  ## 組裝區應完成數量
          'abnormal_qty': assemble_record.abnormal_qty,                     ## 組裝區異常數量

          #'receive_qty': assemble_record.completed_qty,                     ## 組裝區完成數量
          'receive_qty': 0,                                                 ## 組裝區完成數量
          'delivery_date': material_record.material_delivery_date,                      # 交期
          'delivery_qty': material_record.delivery_qty,                                 # 現況數量
          'abnormal_qty': assemble_record.isAssembleFirstAlarm_qty if code == '109' else assemble_record.abnormal_qty,

          'total_assemble_qty': material_record.total_assemble_qty,                     # 已(組裝）完成總數量

          'comment': cleaned_comment,                                                   # 說明
          'isAssembleAlarm' : material_record.isAssembleAlarm,

          'isAssembleFirstAlarm' : assemble_record.isAssembleFirstAlarm,                # 2025-07-24
          'isAssembleFirstAlarm_qty' : assemble_record.isAssembleFirstAlarm_qty,

          'alarm_enable' : assemble_record.alarm_enable,
          'whichStation' : material_record.whichStation,
          'isTakeOk': material_record.isAssembleStation3TakeOk,                         # true:組裝站製程3完成(最後製程)
          'isLackMaterial': material_record.isLackMaterial,
          'shortage_note': material_record.shortage_note,

          'isShow': assemble_record.isAssembleStationShow,
          'currentStartTime': assemble_record.currentStartTime,
          'tooltipVisible': False,
                                                                                                                      #顯示數字輸入欄位alarm
          'abnormal_tooltipVisible': False,
                                                                                                                    #顯示數字輸入欄位alarm
          'input_end_disable': assemble_record.input_end_disable,
          'input_abnormal_disable': assemble_record.input_abnormal_disable,
          'process_step_enable': step_enable,

          'code': code,

          'assemble_count': len(material_record._assemble),

          'is_copied_from_id': assemble_record.is_copied_from_id,
        }

        processed_records.add((order_num_id, format_name))
        _results.append(_object)

      # end loop_a_rec
    # end loop_m_rec

    ###
    # 2) 加上 end_ok 的過濾
    filtered_results = []
    for row in _results:  # 假設 results 是你前面已經算好的 list[dict]
        ptype = map_pt_from_step_code(int(row['process_step_code']))  # 21/22/23
        mid   = str(row['id'])

        # 該製程/料的使用者名單（list），挑出是否包含 _user_id
        ulist = pick_user_list(user_ids_by_type, ptype, mid)
        if _user_id not in ulist:
            continue  # 不是該 user 的「已開始」紀錄 → 略過

        # 3) 再套 end_ok 條件（必須 True 才留下）
        if not end_ok_flag(s, material_id=row['id'], process_step_code=int(row['process_step_code'])):
            continue

        filtered_results.append(row)
    ###

    s.close()
    """
    filtered_results = []
    for row in _results:
        try:
            pt  = map_pt_from_step_code(row.get('process_step_code', 0))
            mid = str(row.get('id'))

            ulist = pick_user_list(user_ids_by_type, pt, mid)
            if _user_id in ulist:
                filtered_results.append(row)
        except Exception as e:
            print('getMaterialsAndAssemblesByUser: skip row due to error =>', e, row)
            continue
    """
    # 只回傳符合該 user 的 rows
    _results = filtered_results

    temp_len = len(_results)
    print("getMaterialsAndAssemblesByUser, 總數: ", temp_len)
    print("materials_and_assembles_by_user:", _results)
    print("active_counts_all:", counts_by_type)
    print("active_user_ids_all:", user_ids_by_type)

    if (temp_len == 0):
      return_value = False

    return jsonify({
      'status': return_value,
      'materials_and_assembles_by_user': _results,
      'active_counts_all': counts_by_type,
      'active_user_ids_all': user_ids_by_type,
    })


# get agv status by id
@getTable.route("/getAGV", methods=['POST'])
def get_agv():
  print("getAGV....")

  request_data = request.get_json()
  #_id = request_data['id']
  _id = request_data.get('agv_id')
  #print("request_data", request_data, _id)
  s = Session()

  myAgv = s.query(Agv).filter(Agv.id == _id).first()
  #print("myAgv", myAgv, myAgv.station)
  _object = {
    #'id': myAgv.id,
    'status': myAgv.status,
    'station': myAgv.station
  }

  s.close()

  return jsonify({
    'agv_data': _object
  })


@getTable.route("/getActiveCountMap", methods=['POST'])
def active_count_map():
    print("getActiveCountMap...")

    #data = request.get_json(silent=True) or {}
    data = request.get_json()

    print("data:", data)
    key = data.get("key", "material")
    print("stepaa")
    # ---- 解析 groups（新格式），或回退到舊格式 ----
    groups = data.get("groups")
    print("step0")
    if not groups:
        ids = data.get("ids", [])
        pt = int(data.get("process_type") or 21)
        groups = {str(pt): ids}
    print("step1")
    # 正規化：鍵轉字串、值轉 set[int]
    norm_groups = {}
    for k, v in groups.items():
        try:
            pt = str(int(k))
        except Exception:
            continue
        if not isinstance(v, (list, tuple, set)):
            continue
        try:
            norm_groups[pt] = {int(x) for x in v if x is not None}
        except Exception:
            return jsonify(success=False, message="ids must be numbers"), 400
    print("step2")
    # 若所有組都空 → 回空
    if not any(norm_groups.values()):
        return jsonify(success=True, counts={pt:{} for pt in norm_groups.keys()})
    print("step3")
    # 集合總 ids 與 types
    all_ids = sorted({i for s in norm_groups.values() for i in s})
    types = sorted({int(pt) for pt, s in norm_groups.items() if s})

    # 欄位選擇
    group_col = Process.assemble_id if key == "assemble" else Process.material_id

    s = Session()
    # 一次查：WHERE id IN all_ids AND process_type IN types AND end_time IS NULL
    rows = (
        s.query(group_col, Process.process_type, func.count(Process.id))
         .filter(group_col.in_(all_ids))
         .filter(Process.process_type.in_(types))
         .filter(Process.end_time.is_(None))
         .group_by(group_col, Process.process_type)
         .all()
    )
    print("step4", rows)
    # 轉為 { "21": { "101": 2, ... }, "22": {...}, ... }
    result = {str(pt): {} for pt in norm_groups.keys()}
    for id_, pt, cnt in rows:
        result[str(int(pt))][str(int(id_))] = int(cnt)

    print("result:", result)

    return jsonify({
      'status':True,
      'counts': result,
    })


@getTable.route("/getEndOkByMaterialIdAndStepCode", methods=['POST'])
def get_end_ok_by_material_id_and_step_code():
    print("getEndOkByMaterialIdAndStepCode()...")

    """
    需求：
      針對相同工單(相同 material_id, process_step_code, ask_qty)，計算：
        t1 = sum(completed_qty)
        t2 = sum(abnormal_qty)
        t3 = ask_qty（由前端傳入，且以此等值過濾）
      判斷：若 t1 >= t3 - t2 -> end_assemble_ok = True，否則 False
    請求 JSON：
      {
        "material_id": <int>,
        "process_step_code": <int>,
        "ask_qty": <int>
      }
    回傳 JSON：
      {
        "status": True/False,
        "message": "...",
        "data": {
          "material_id": ...,
          "process_step_code": ...,
          "ask_qty": ...,
          "t1_total_completed_qty": ...,
          "t2_total_abnormal_qty": ...,
          "t3_should_complete_qty": ...,
          "threshold": <t3 - t2>,
          "end_assemble_ok": True/False,
          "matched_rows": <int>   # 符合條件的筆數（可用來排查）
        }
      }
    """
    payload = request.get_json()

    material_id = payload.get("material_id")
    process_step_code = payload.get("process_step_code")
    ask_qty = payload.get("ask_qty")

    # 基本參數檢查
    missing = []
    if material_id is None: missing.append("material_id")
    if process_step_code is None: missing.append("process_step_code")
    if ask_qty is None: missing.append("ask_qty")

    if missing:
      return jsonify({
        "status": False,
        "message": f"缺少必要參數：{', '.join(missing)}",
        "data": {},
      })

    material_id = int(material_id)
    process_step_code = int(process_step_code)
    ask_qty = int(ask_qty)

    s = Session()

    # 以相同 material_id、process_step_code、ask_qty 篩選
    q = (s
      .query(
        func.coalesce(func.sum(Assemble.completed_qty), 0),
        func.coalesce(func.sum(Assemble.abnormal_qty), 0),
        func.count(Assemble.id))
      .filter(Assemble.material_id == material_id)
      .filter(Assemble.process_step_code == process_step_code)
      .filter(Assemble.ask_qty == ask_qty)
    )

    t1_sum, t2_sum, row_count = q.one()   # 回傳 (sum_completed, sum_abnormal, count)

    t1 = int(t1_sum or 0)
    t2 = int(t2_sum or 0)
    t3 = int(ask_qty)

    threshold = t3 - t2
    end_ok = t1 >= threshold

    s.close()

    print("material_id", material_id)
    print("process_step_code", process_step_code)
    print("ask_qty", t3)
    print( "t1_total_completed_qty", t1)
    print("t2_total_abnormal_qty", t2)
    print("t3_should_complete_qty", t3)
    print("threshold", threshold)
    print("end_assemble_ok", end_ok)
    print("matched_rows", int(row_count or 0))

    return jsonify({
      "status": True,
      "message": "計算成功",
      "data": {
        "material_id": material_id,
        "process_step_code": process_step_code,
        "ask_qty": t3,
        "t1_total_completed_qty": t1,
        "t2_total_abnormal_qty": t2,
        "t3_should_complete_qty": t3,
        "threshold": threshold,
        "end_assemble_ok": end_ok,
        "matched_rows": int(row_count or 0),
      }
    })

