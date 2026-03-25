import re
import random
from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import check_password_hash
from server.database.x_tables import User, Material, Assemble, Bom, Agv, Permission, Process, AbnormalCause, Setting, Session
from database.p_tables import P_Material, P_Assemble, P_Process, P_Part,P_AbnormalCause
from sqlalchemy import and_, or_, not_, func
#from sqlalchemy.orm import joinedload
from sqlalchemy import func, cast, Integer

from collections import defaultdict

#from flask_cors import CORS
#from operator import itemgetter

from datetime import datetime, timezone, timedelta
from datetime import datetime as dt

from zoneinfo import ZoneInfo

getTable = Blueprint('getTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


def read_all_p_part_process_code_p():
    """
    從 p_part 資料表讀取所有製程資料，組出：

        code_to_assembleStep = { '100-01': step_code, '100-02': step_code, ... }

    規則：
      - 使用 P_Part.part_code 當 key 的來源，例如 'B100-01'
      - 若 part_code 以 'B' 開頭，就去掉 'B'，變成 '100-01' 當 dict 的 key
      - value 直接使用 P_Part.process_step_code
    """

    session = Session()
    code_to_assembleStep = {}

    try:
        parts = session.query(P_Part).order_by(P_Part.id).all()
        print(f"read_all_p_part_process_code_p(): 從 p_part 讀到 {len(parts)} 筆資料")

        for part in parts:
            raw_code = (part.part_code or "").strip()
            if not raw_code:
                continue

            # 去掉開頭 'B'，跟原本 Excel 版的行為一致
            if raw_code.startswith("B"):
                key = raw_code[1:]   # 'B100-01' -> '100-01'
            else:
                key = raw_code

            step = part.process_step_code or 0
            if not step:
                # 若 process_step_code 為 0 或 None，就略過（必要時可以改成保留）
                continue

            # 若同一個 key 被多筆覆蓋，印出提示（最後一筆會生效）
            if key in code_to_assembleStep and code_to_assembleStep[key] != step:
                print(
                    f"  ⚠️ key={key} 已有 step={code_to_assembleStep[key]}，"
                    f"這筆 part_code={raw_code} 的 step={step} 會覆蓋前一筆"
                )

            code_to_assembleStep[key] = step

    finally:
        session.close()

    print("read_all_p_part_process_code_p(), 從 p_part 組完，總筆數:", len(code_to_assembleStep))
    return code_to_assembleStep


# ------------------------------------------------------------------


def map_pt(row):
    """
    3 -> 21, 2 -> 22, 1 -> 23，其餘預設 23。
    支援欄位名：process_step_code / process_step / step_code
    row 可為 dict 或 ORM 物件。
    """
    code = get_val(row, 'process_step_code')
    if code is None:
        code = get_val(row, 'process_step')
    if code is None:
        code = get_val(row, 'step_code')

    try:
        code = int(code) if code is not None else None
    except Exception:
        code = None

    if code == 3:
        return 21
    if code == 2:
        return 22
    if code == 1:
        return 23
    return 23


def get_val(row, key, default=None):
    """同時支援 dict 與 ORM 物件取值。"""
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


# ------------------------------------------------------------------


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


def active_count_map_by_assemble_multi(
    s,
    assemble_ids,
    process_types=(21, 22, 23),
    include_paused=True,
    only_user_id=None,
    has_started=None,
    null_as_not_started=True,
):
    """
    回傳：
    { "21": { "6": 1, "38": 0 }, "22": {...}, "23": {...} }
    以「製程別 → assemble_id」分組計數
    """
    from server.database.x_tables import Process
    result = {str(pt): {} for pt in process_types}
    if not assemble_ids:
        return result

    q = (
        s.query(Process)
         .filter(Process.assemble_id.in_(assemble_ids))
         .filter(Process.process_type.in_(process_types))
         .filter(Process.end_time.is_(None))  # 未結束
    )
    if not include_paused:
        from sqlalchemy import or_
        q = q.filter(or_(Process.is_pause.is_(False), Process.is_pause.is_(None)))
    if only_user_id:
        q = q.filter(Process.user_id == only_user_id)
    if has_started is True:
        q = q.filter(Process.has_started.is_(True))
    elif has_started is False:
        if null_as_not_started:
            from sqlalchemy import or_
            q = q.filter(or_(Process.has_started.is_(False), Process.has_started.is_(None)))
        else:
            q = q.filter(Process.has_started.is_(False))

    rows = q.with_entities(Process.process_type, Process.assemble_id).all()
    for pt, asm_id in rows:
        pt_str, asm_str = str(pt), str(asm_id)
        result[pt_str][asm_str] = result[pt_str].get(asm_str, 0) + 1
    return result


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



def active_count_map_by_material_multi_P(
    s,
    material_ids,
    process_types,
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
    process_types = list(process_types)             # 確保是可迭代序列

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

    rows = q.with_entities(P_Process.process_type, P_Process.material_id).all()

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
    print("active_user_ids_by_material_multi(), start....", result)
    if not material_ids:
        return result
    print("active_user_ids_by_material_multi()....",only_user_id, include_paused,has_started,)

    q = build_active_process_query(
        s, material_ids, process_types,
        include_paused=include_paused,
        only_user_id=only_user_id,
        has_started=has_started,
        null_as_not_started=null_as_not_started,
    )

    #print("q:", q)

    rows = q.with_entities(
        Process.process_type,
        Process.material_id,
        Process.user_id
    ).all()
    print("active_user_ids_by_material_multi(), rows:", rows)
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


def need_more_assemble_abnormal_qty(k1: int, s=None):
    close_after = False
    if s is None:
        from server.database.x_tables import Session  # 若你的檔名不同請調整
        s = Session()
        close_after = True

    try:
        total = (
            s.query(func.coalesce(func.sum(Assemble.abnormal_qty), 0))
             .filter(Assemble.material_id == k1)
             .filter(Assemble.user_id != '')
             .scalar()
        ) or 0

        total = int(total)
        return total
    finally:
        if close_after:
            s.close()


def need_more_process_qty(k1: int, a1: int, t1: int, must_qty: int, s=None):
    #print("need_more_process_qty()...")

    """
    回傳 (is_insufficient, process_total)
    is_insufficient: True 表示加總 < must_qty；False 表示 >= must_qty
    process_total  : 依條件加總後的數量（int）
    """
    # 允許外部傳入 session；若沒傳就自行建立並在結尾關閉

    #print(k1, t1, must_qty)

    close_after = False
    if s is None:
        from server.database.x_tables import Session  # 若你的檔名不同請調整
        s = Session()
        close_after = True

    try:
        # end_time 欄位在你的 schema 是 String(30)，因此除了 not NULL，也一併排除空字串
        total = (
            s.query(func.coalesce(func.sum(Process.process_work_time_qty), 0))
             .filter(Process.material_id == k1)
             .filter(Process.assemble_id == a1)
             .filter(Process.process_type == t1)
             .filter(Process.has_started.is_(True))
             .filter(Process.end_time.isnot(None))
             .filter(Process.end_time != '')
             .scalar()
        ) or 0

        total = int(total)
        #print("total, must_qty:", total, must_qty)
        return (total < int(must_qty), total)
    finally:
        if close_after:
            s.close()


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
    material_record = s.query(Material).filter_by(order_num=_order_num).first()
  elif _id is not None:       # 如果傳入了 id
    material_record = s.query(Material).filter_by(id=_id).first()

  boms = material_record._bom

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
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'boms': results
  })


@getTable.route("/getBomsP", methods=['POST'])
def get_boms_p():
  print("getBomsP....")

  request_data = request.get_json()
  #_order_num = request_data['order_num']
  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  return_value = True
  s = Session()

  # 檢查傳入的參數，選擇查詢條件
  material_record = None
  if _order_num is not None:  # 如果傳入了 order_num
    material_record = s.query(P_Material).filter_by(order_num=_order_num).first()
  elif _id is not None:       # 如果傳入了 id
    material_record = s.query(P_Material).filter_by(id=_id).first()

  boms = material_record._bom

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
      #'receive': bom.receive,               #領取
      'lack': bom.lack,                     #缺料
      'isPickOK': bom.isPickOK
    }
    for bom in boms if not bom.isPickOK
  ]

  s.close()

  temp_len = len(results)
  print("getBoms, 總數: ", temp_len)
  print("getBoms: ", results)
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'boms': results
  })


# -----dialog2~ for 前端 MaterialListForAssem.vue -------------------------------------------------------------


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
      live = _live_elapsed_seconds(log)
      return jsonify(
        success=True,
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
        begin_time=None,                # 由「開始」時再補
        end_time=None,
        elapsedActive_time=0,
        is_pause=True,                  # 進入即顯示「開始」
        has_started=False,
        pause_time=0,
        pause_started_at=None,
        #assemble_id=assemble_id,        # 若有此欄位再放
    )
    s.add(new_log)

    # 同步 Material（若前端有用到這些欄位）
    if material_record:
        material_record.isOpen = True
        material_record.isOpenEmpId = user_id

    s.commit()

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
    q = s.query(Process).filter_by(id=process_id).with_for_update()   # 鎖定該行後再更新, 避免 pause_started_at/pause_time 在同一瞬間被兩支 API 互相覆寫
    log = q.one_or_none()

    if not log:
        return jsonify(success=False, message="process not found"), 404
    if log.end_time is not None:
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

                ps = log.pause_started_at
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
                log.begin_time = now_tpe_str

    s.commit()

    return jsonify(
        success=True,
        is_paused=log.is_pause,
        elapsed_time=int(log.elapsedActive_time or 0),
        pause_time=log.pause_time or 0,
        pause_started_at=log.pause_started_at.isoformat() if log.pause_started_at else None,
        # 回傳 has_started 讓前端可用（即使沒有欄位也安全處理）
        has_started=bool(log.has_started),
    )


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


# -----dialog2~Begin for 前端 PickReportForAssembleBegin.vue 及 PickReportForAssembleEnd.vue -------------------------------------------------------------


@getTable.route("/dialog2StartProcessBegin", methods=['POST'])
def start_process_begin():
    print("dialog2StartProcessBegin API....")

    data = request.json
    material_id = data["material_id"]
    user_id = data["user_id"]
    process_type = data.get("process_type", 1)
    assemble_id = data.get("assemble_id")

    s = Session()

    material_record = s.query(Material).filter_by(id=material_id).first()

    # 1) 先找「同工單(同製程)、尚未結束」的最後一筆（不帶 user 條件）
    log = (
        s.query(Process)
        .filter_by(material_id=material_id, assemble_id=assemble_id, process_type=process_type, user_id=user_id)
        #.filter_by(material_id=material_id, process_type=process_type, user_id=user_id)
        .filter(Process.end_time.is_(None))
        .order_by(Process.id.desc())
        .first()
    )

    if log:
      # 回傳動態 live elapsed，和你現行邏輯一致
      live = _live_elapsed_seconds(log)
      return jsonify(
        success=True,
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
        assemble_id=assemble_id,
        user_id=user_id,
        process_type=process_type,
        begin_time=None,               # 由「開始」時再補
        end_time=None,
        elapsedActive_time=0,
        is_pause=True,                 # 進入即顯示「開始」
        has_started=False,
        pause_time=0,
        pause_started_at=None,
    )
    s.add(new_log)

    # 同步 Material（若前端有用到這些欄位）
    if material_record:
        material_record.isOpen = True
        material_record.isOpenEmpId = user_id

    s.commit()

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


@getTable.route("/dialog2UpdateProcessBegin", methods=['POST'])
def update_process_begin():
    print("dialog2UpdateProcessBegin API....")

    data = request.json
    process_id = data["process_id"]
    new_secs   = int(data.get("elapsed_time", 0) or 0)

    s = Session()

    # 確保結果「最多只會有一筆」,
    # 回傳值:
    # 有一筆資料 → 回傳那筆物件
    # 沒有資料 → 回傳 None
    # 異常:
    # 超過一筆 → 丟 MultipleResultsFound 例外
    print("process_id:", process_id)
    log = s.query(Process).filter_by(id=process_id).with_for_update().one_or_none()   # 鎖定該行後再更新, 避免 pause_started_at/pause_time 在同一瞬間被兩支 API 互相覆寫

    if not log:
        print("error, process not found!")
        return jsonify(success=False, message="process not found"), 404

    if log.end_time is not None:
        print("error, process already closed!")

        return jsonify(
                success=True,
                message="process already closed",
                is_paused=bool(log.is_pause),
                elapsed_time=int(log.elapsedActive_time or 0),
                pause_time=int(log.pause_time or 0)
            ), 200

    cur = int(log.elapsedActive_time or 0)

    # 取「想要的暫停狀態」：若前端沒傳，就用目前 DB 狀態
    want_pause = data.get("is_paused")
    #if want_pause is None:
    #    want_pause = bool(log.is_pause)
    #else:
    #    want_pause = bool(want_pause)
    want_pause = bool(log.is_pause) if want_pause is None else bool(want_pause)

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
        elif not getattr(log, "pause_started_at", None):
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


@getTable.route("/dialog2ToggleProcessBegin", methods=['POST'])
def toggle_process_begin():
    print("dialog2ToggleProcessBegin API....")

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
            ps = log.pause_started_at
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


@getTable.route("/dialog2CloseProcessBegin", methods=['POST'])
def close_process_begin():
    print("dialog2CloseProcessBegin API....")

    data = request.json
    process_id   = data["process_id"]
    elapsed_time = data.get("elapsed_time")
    receive_qty  = data.get("receive_qty", 0)
    alarm_enable = data.get("alarm_enable")
    alarm_message = data.get("alarm_message")
    isAssembleFirstAlarm = data.get("isAssembleFirstAlarm")
    #assemble_id  = data.get("assemble_id", None)
    assemble_id  = data.get("assemble_id")

    print("process_id:", process_id, "receive_qty:", receive_qty, "alarm_enable:", alarm_enable, "assemble_id:", assemble_id)
    print("alarm_enable data type:",alarm_enable, type(alarm_enable))
    print("isAssembleFirstAlarm data type:",isAssembleFirstAlarm, type(isAssembleFirstAlarm))

    myTest  = data.get("test")
    print("test, qty:", myTest, receive_qty)

    s = Session()

    #log = s.query(Process).get(process_id)
    log = s.query(Process).filter_by(id=process_id).first()

    if not log:
      return jsonify(success=False, message="process not found"), 404

    if (log.end_time is not None) and (log.process_work_time_qty !=0):
      print("@@close_process_begin step1..")
      return jsonify(
        success=True,
        message="already closed",
        elapsed_time=int(log.elapsedActive_time or 0),
        pause_time=int(log.pause_time or 0),
        end_time=log.end_time,
      ), 200

    TPE = ZoneInfo("Asia/Taipei")
    now_aw = datetime.now(TPE).replace(microsecond=0)

    # 1) 若暫停中，先把最後一段暫停秒數補進 pause_time
    if getattr(log, "is_pause", False) and getattr(log, "pause_started_at", None):
      print("@@close_process_begin step2..")

      try:
        ps = log.pause_started_at
        if isinstance(ps, str):
          # 依你的實際格式調整；若你存 "%Y-%m-%d %H:%M:%S"，改用 datetime.strptime
          ps = datetime.fromisoformat(ps)
        if ps.tzinfo is None:
          ps = ps.replace(tzinfo=TPE)

        delta = int((now_aw - ps).total_seconds())
        log.pause_time = (log.pause_time or 0) + max(delta, 0)
      except Exception as e:
        print("close_process: pause_time accumulate failed:", e)
      finally:
        log.pause_started_at = None

    # 2) 校正『有效計時秒數』：採單向遞增（避免寫回比現值還小）
    if elapsed_time is not None:
      print("@@close_process_begin step3..")

      try:
        last_secs = int(elapsed_time)
      except Exception:
        last_secs = int(log.elapsedActive_time or 0)
      cur_secs = int(log.elapsedActive_time or 0)

      log.elapsedActive_time = max(cur_secs, last_secs)

    # 3) 可選：更新 HH:MM:SS 文字欄（若模型有此欄位）
    try:
      print("@@close_process_begin step4..")

      log.str_elapsedActive_time = seconds_to_hms_str(int(log.elapsedActive_time or 0))
    except Exception:
      pass

    # 4) 關閉狀態
    print("@@close_process_begin step5..")

    log.is_pause = True
    log.end_time = now_aw.strftime("%Y-%m-%d %H:%M:%S")
    print("log.process_work_time_qty:", receive_qty)
    log.process_work_time_qty = receive_qty

    if alarm_enable:
      print("@@close_process_begin step5a..")
      log.normal_work_time = 1
      log.abnormal_cause_message=''
    if not alarm_enable and isAssembleFirstAlarm:
      print("@@close_process_begin step5b..")
      log.normal_work_time = 1
      log.abnormal_cause_message=''
    if not alarm_enable and not isAssembleFirstAlarm:
      print("@@close_process_begin step5c..")
      log.normal_work_time = 0
      log.abnormal_cause_message=alarm_message

    log.must_allOk_qty = receive_qty

    # 5)（重點）若有傳 assemble_id + receive_qty，更新該站完成數
    # 也就是說, 處理 receive_qty / assemble_id 之類的寫回，都在此處補充
    is_completed   = False
    total_completed = None
    must_qty       = None

    try:
      print("@@close_process_begin step6..")
      rq = int(receive_qty or 0)
    except Exception:
      rq = 0

    print("@@close_process_begin step7..")
    if assemble_id is not None and rq > 0:
      try:
        asm = s.query(Assemble).get(int(assemble_id))
        print("@@close_process_begin step8..")
      except Exception:
        asm = None

      print("@@close_process_begin step9..")
      if asm:
        print("@@close_process_begin step10..")
        # 依你的實際欄位名調整：
        # 假設：must_receive_end_qty = 應完成數量、total_ask_qty_end = 已完成總數
        must_qty = int(asm.must_receive_end_qty or 0)
        cur_total = int(asm.total_ask_qty_end or 0)
        new_total = cur_total + rq

        asm.total_ask_qty_end = new_total
        total_completed = new_total
        is_completed = (must_qty > 0 and new_total >= must_qty)

        s.add(asm)

    print("@@close_process_begin step11..")
    s.add(log)

    s.commit()

    return jsonify(
      success=True,
      end_time=log.end_time,
      elapsed_time=int(log.elapsedActive_time or 0),
      pause_time=int(log.pause_time or 0),
      # 待確定
      # ✅ 前端可用來鎖定 Begin/End 的開始/結束鍵
      is_completed=is_completed,
      total_completed=total_completed,
      must_qty=must_qty
    )


# -----dialog2~MP for 前端 MaterialListForProcess.vue -------------------------------------------------------------

#
#table:P_Material, P_Process
#
@getTable.route("/dialog2StartProcessMP", methods=['POST'])
def start_process_mp():
    print("dialog2StartProcessBegin API....")

    data = request.json
    material_id = data["material_id"]
    user_id = data["user_id"]
    process_type = data.get("process_type", 1)
    assemble_id = data.get("assemble_id")

    s = Session()

    material_record = s.query(P_Material).filter_by(id=material_id).first()

    # 1) 先找「同工單(同製程)、尚未結束」的最後一筆（不帶 user 條件）
    log_query = (
    #log = (
        s.query(P_Process)
        .filter_by(
           material_id=material_id,
           #assemble_id=assemble_id,
           process_type=process_type,
           user_id=user_id)
        .filter(P_Process.end_time.is_(None)
        )
        #.order_by(P_Process.id.desc())
        #.first()
    )

    # 只有在「傳進來有意義的 assemble_id」時才加這個條件
    if assemble_id not in (None, 0):
        log_query = log_query.filter_by(assemble_id=assemble_id)

    log = log_query.order_by(P_Process.id.desc()).first()
    print("MP dialog2StartProcess, 找到的 log.id:", log.id if log else None)

    if log:
      # 回傳動態 live elapsed，和你現行邏輯一致
      live = _live_elapsed_seconds(log)
      return jsonify(
        success=True,
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
    new_log = P_Process(
        material_id=material_id,
        assemble_id=assemble_id,
        user_id=user_id,
        process_type=process_type,
        begin_time=None,               # 由「開始」時再補
        end_time=None,
        elapsedActive_time=0,
        is_pause=True,                 # 進入即顯示「開始」
        has_started=False,
        pause_time=0,
        pause_started_at=None,
    )
    s.add(new_log)

    # 同步 Material（若前端有用到這些欄位）
    if material_record:
        material_record.isOpen = True
        material_record.isOpenEmpId = user_id

    s.commit()

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

#
#table:P_Process
#
@getTable.route("/dialog2UpdateProcessMP", methods=['POST'])
def update_process_mp():
    print("dialog2UpdateProcessBegin API....")

    data = request.json
    process_id = data["process_id"]
    new_secs   = int(data.get("elapsed_time", 0) or 0)

    s = Session()

    # 確保結果「最多只會有一筆」,
    # 回傳值:
    # 有一筆資料 → 回傳那筆物件
    # 沒有資料 → 回傳 None
    # 異常:
    # 超過一筆 → 丟 MultipleResultsFound 例外
    print("process_id:", process_id)
    log = s.query(P_Process).filter_by(id=process_id).with_for_update().one_or_none()   # 鎖定該行後再更新, 避免 pause_started_at/pause_time 在同一瞬間被兩支 API 互相覆寫

    if not log:
        print("error, p process not found!")
        return jsonify(success=False, message="p process not found"), 404

    if log.end_time is not None:
        print("error, p process already closed!")

        return jsonify(
                success=True,
                message="p process already closed",
                is_paused=bool(log.is_pause),
                elapsed_time=int(log.elapsedActive_time or 0),
                pause_time=int(log.pause_time or 0)
            ), 200

    cur = int(log.elapsedActive_time or 0)

    # 取「想要的暫停狀態」：若前端沒傳，就用目前 DB 狀態
    want_pause = data.get("is_paused")
    #if want_pause is None:
    #    want_pause = bool(log.is_pause)
    #else:
    #    want_pause = bool(want_pause)
    want_pause = bool(log.is_pause) if want_pause is None else bool(want_pause)

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
        elif not getattr(log, "pause_started_at", None):
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

#
#table:P_Process
#
@getTable.route("/dialog2ToggleProcessMP", methods=['POST'])
def toggle_process_mp():
    print("dialog2ToggleProcessBegin API....")

    #
    #切換暫停/恢復：
    #  - is_paused=True  → 進入暫停狀態：只記下 pause_started_at（若當前不是暫停）
    #  - is_paused=False → 恢復：把 (now - pause_started_at) 累加到 pause_time，並清空 pause_started_at
    #
    data = request.json
    process_id = data["process_id"]
    want_pause = bool(data["is_paused"])

    s = Session()

    log = s.query(P_Process).get(process_id)
    q = s.query(P_Process).filter_by(id=process_id).with_for_update()   # 鎖定該行後再更新, 避免 pause_started_at/pause_time 在同一瞬間被兩支 API 互相覆寫
    log = q.one_or_none()

    if not log:
        return jsonify(success=False, message="p process not found"), 404
    if log.end_time is not None:
        return jsonify(success=False, message="p process already closed"), 400

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
            ps = log.pause_started_at
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

#
#table:P_Assemble, P_Process
#
@getTable.route("/dialog2CloseProcessMP", methods=['POST'])
def close_process_mp():
    print("dialog2CloseProcessBegin API....")

    data = request.json
    process_id   = data["process_id"]
    elapsed_time = data.get("elapsed_time")
    receive_qty  = data.get("receive_qty", 0)
    alarm_enable = data.get("alarm_enable")
    alarm_message = data.get("alarm_message")
    isAssembleFirstAlarm = data.get("isAssembleFirstAlarm")
    assemble_id  = data.get("assemble_id")

    print("process_id:", process_id, "receive_qty:", receive_qty, "alarm_enable:", alarm_enable, "assemble_id:", assemble_id)
    print("alarm_enable data type:",alarm_enable, type(alarm_enable))
    print("isAssembleFirstAlarm data type:",isAssembleFirstAlarm, type(isAssembleFirstAlarm))

    myTest  = data.get("test")
    print("test, qty:", myTest, receive_qty)

    s = Session()

    log = s.query(P_Process).filter_by(id=process_id).first()

    if not log:
      return jsonify(success=False, message="p process not found"), 404

    if (log.end_time is not None) and (log.process_work_time_qty !=0):
      print("@@close_process_begin step1..")
      return jsonify(
        success=True,
        message="already closed",
        elapsed_time=int(log.elapsedActive_time or 0),
        pause_time=int(log.pause_time or 0),
        end_time=log.end_time,
      ), 200

    TPE = ZoneInfo("Asia/Taipei")
    now_aw = datetime.now(TPE).replace(microsecond=0)

    # 1) 若暫停中，先把最後一段暫停秒數補進 pause_time
    if getattr(log, "is_pause", False) and getattr(log, "pause_started_at", None):
      print("@@close_process_begin step2..")

      try:
        ps = log.pause_started_at
        if isinstance(ps, str):
          # 依你的實際格式調整；若你存 "%Y-%m-%d %H:%M:%S"，改用 datetime.strptime
          ps = datetime.fromisoformat(ps)
        if ps.tzinfo is None:
          ps = ps.replace(tzinfo=TPE)

        delta = int((now_aw - ps).total_seconds())
        log.pause_time = (log.pause_time or 0) + max(delta, 0)
      except Exception as e:
        print("close_process: pause_time accumulate failed:", e)
      finally:
        log.pause_started_at = None

    # 2) 校正『有效計時秒數』：採單向遞增（避免寫回比現值還小）
    if elapsed_time is not None:
      print("@@close_process_begin step3..")

      try:
        last_secs = int(elapsed_time)
      except Exception:
        last_secs = int(log.elapsedActive_time or 0)
      cur_secs = int(log.elapsedActive_time or 0)

      log.elapsedActive_time = max(cur_secs, last_secs)

    # 3) 可選：更新 HH:MM:SS 文字欄（若模型有此欄位）
    try:
      print("@@close_process_begin step4..")

      log.str_elapsedActive_time = seconds_to_hms_str(int(log.elapsedActive_time or 0))
    except Exception:
      pass

    # 4) 關閉狀態
    print("@@close_process_begin step5..")

    log.is_pause = True
    log.end_time = now_aw.strftime("%Y-%m-%d %H:%M:%S")
    print("log.process_work_time_qty:", receive_qty)
    log.process_work_time_qty = receive_qty

    if alarm_enable:
      print("@@close_process_begin step5a..")
      log.normal_work_time = 1
      log.abnormal_cause_message=''
    if not alarm_enable and isAssembleFirstAlarm:
      print("@@close_process_begin step5b..")
      log.normal_work_time = 1
      log.abnormal_cause_message=''
    if not alarm_enable and not isAssembleFirstAlarm:
      print("@@close_process_begin step5c..")
      log.normal_work_time = 0
      log.abnormal_cause_message=alarm_message

    log.must_allOk_qty = receive_qty

    # 5)（重點）若有傳 assemble_id + receive_qty，更新該站完成數
    # 也就是說, 處理 receive_qty / assemble_id 之類的寫回，都在此處補充
    is_completed   = False
    total_completed = None
    must_qty       = None

    try:
      print("@@close_process_begin step6..")
      rq = int(receive_qty or 0)
    except Exception:
      rq = 0

    print("@@close_process_begin step7..")
    if assemble_id is not None and rq > 0:
      try:
        asm = s.query(P_Assemble).get(int(assemble_id))
        print("@@close_process_begin step8..")
      except Exception:
        asm = None

      print("@@close_process_begin step9..")
      if asm:
        print("@@close_process_begin step10..")
        # 依你的實際欄位名調整：
        # 假設：must_receive_end_qty = 應完成數量、total_ask_qty_end = 已完成總數
        must_qty = int(asm.must_receive_end_qty or 0)
        cur_total = int(asm.total_ask_qty_end or 0)
        new_total = cur_total + rq

        asm.total_ask_qty_end = new_total
        total_completed = new_total
        is_completed = (must_qty > 0 and new_total >= must_qty)

        s.add(asm)

    print("@@close_process_begin step11..")
    s.add(log)

    s.commit()

    return jsonify(
      success=True,
      end_time=log.end_time,
      elapsed_time=int(log.elapsedActive_time or 0),
      pause_time=int(log.pause_time or 0),
      # 待確定
      # ✅ 前端可用來鎖定 Begin/End 的開始/結束鍵
      is_completed=is_completed,
      total_completed=total_completed,
      must_qty=must_qty
    )


# -----dialog2~Process for 前端 PickReportForProcessBegin.vue 及 PickReportForProcessEnd.vue -------------------------------------------------------------


#
#table:P_Material, P_Process
#
@getTable.route("/dialog2StartProcessProcess", methods=['POST'])
def start_process_process():
    print("dialog2StartProcessProcess API....")

    data = request.json
    material_id = data["material_id"]
    user_id = data["user_id"]
    process_type = data.get("process_type", 1)
    assemble_id = data.get("assemble_id")

    s = Session()

    material_record = s.query(P_Material).filter_by(id=material_id).first()

    # 1) 先找「同工單(同製程)、尚未結束」的最後一筆（不帶 user 條件）
    log = (
        s.query(P_Process)
        .filter_by(
           material_id=material_id,
           assemble_id=assemble_id,
           process_type=process_type,
           user_id=user_id
        )
        .filter(P_Process.end_time.is_(None))
        .order_by(P_Process.id.desc())
        .first()
    )

    if log:
      # 回傳動態 live elapsed，和你現行邏輯一致
      live = _live_elapsed_seconds(log)
      return jsonify(
        success=True,
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
    new_log = P_Process(
        material_id=material_id,
        assemble_id=assemble_id,
        user_id=user_id,
        process_type=process_type,
        begin_time=None,               # 由「開始」時再補
        end_time=None,
        elapsedActive_time=0,
        is_pause=True,                 # 進入即顯示「開始」
        has_started=False,
        pause_time=0,
        pause_started_at=None,
    )
    s.add(new_log)

    # 同步 P_Material（若前端有用到這些欄位）
    if material_record:
        material_record.isOpen = True
        material_record.isOpenEmpId = user_id

    s.commit()

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

#
#table:P_Process
#
@getTable.route("/dialog2UpdateProcessProcess", methods=['POST'])
def update_process_process():
    print("dialog2UpdateProcessProcess API....")

    data = request.json
    process_id = data["process_id"]
    new_secs   = int(data.get("elapsed_time", 0) or 0)

    s = Session()

    # 確保結果「最多只會有一筆」,
    # 回傳值:
    # 有一筆資料 → 回傳那筆物件
    # 沒有資料 → 回傳 None
    # 異常:
    # 超過一筆 → 丟 MultipleResultsFound 例外
    log = s.query(P_Process).filter_by(id=process_id).with_for_update().one_or_none()   # 鎖定該行後再更新, 避免 pause_started_at/pause_time 在同一瞬間被兩支 API 互相覆寫

    if not log:
        print("error, p process not found!")
        return jsonify(success=False, message="p process not found"), 404

    if log.end_time is not None:
        print("error, p process already closed!")

        return jsonify(
                success=True,
                message="p process already closed",
                is_paused=bool(log.is_pause),
                elapsed_time=int(log.elapsedActive_time or 0),
                pause_time=int(log.pause_time or 0)
            ), 200

    cur = int(log.elapsedActive_time or 0)

    # 取「想要的暫停狀態」：若前端沒傳，就用目前 DB 狀態
    want_pause = data.get("is_paused")
    #if want_pause is None:
    #    want_pause = bool(log.is_pause)
    #else:
    #    want_pause = bool(want_pause)
    want_pause = bool(log.is_pause) if want_pause is None else bool(want_pause)

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
        elif not getattr(log, "pause_started_at", None):
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

#
#table:P_Process
#
@getTable.route("/dialog2ToggleProcessProcess", methods=['POST'])
def toggle_process_process():
    print("dialog2ToggleProcessProcess API....")

    #
    #切換暫停/恢復：
    #  - is_paused=True  → 進入暫停狀態：只記下 pause_started_at（若當前不是暫停）
    #  - is_paused=False → 恢復：把 (now - pause_started_at) 累加到 pause_time，並清空 pause_started_at
    #
    data = request.json
    process_id = data["process_id"]
    want_pause = bool(data["is_paused"])

    s = Session()

    log = s.query(P_Process).get(process_id)
    q = s.query(P_Process).filter_by(id=process_id).with_for_update()   # 鎖定該行後再更新, 避免 pause_started_at/pause_time 在同一瞬間被兩支 API 互相覆寫
    log = q.one_or_none()

    if not log:
        return jsonify(success=False, message="p process not found"), 404
    if log.end_time is not None:
        return jsonify(success=False, message="p process already closed"), 400

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
            ps = log.pause_started_at
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

#
#table:P_Process
#
@getTable.route("/dialog2CloseProcessProcess", methods=['POST'])
def close_process_process():
    print("dialog2CloseProcessProcess API....")

    data = request.json
    process_id   = data["process_id"]
    elapsed_time = data.get("elapsed_time")
    receive_qty  = data.get("receive_qty", 0)
    alarm_enable = data.get("alarm_enable")
    alarm_message = data.get("alarm_message")
    isAssembleFirstAlarm = data.get("isAssembleFirstAlarm")
    #assemble_id  = data.get("assemble_id", None)
    assemble_id  = data.get("assemble_id")

    print("process_id:", process_id, "receive_qty:", receive_qty, "alarm_enable:", alarm_enable, "assemble_id:", assemble_id)
    print("alarm_enable data type:",alarm_enable, type(alarm_enable))
    print("isAssembleFirstAlarm data type:",isAssembleFirstAlarm, type(isAssembleFirstAlarm))

    myTest  = data.get("test")
    print("test, qty:", myTest, receive_qty)

    s = Session()

    log = s.query(P_Process).filter_by(id=process_id).first()

    if not log:
      return jsonify(success=False, message="p process not found"), 404

    if (log.end_time is not None) and (log.process_work_time_qty !=0):
      print("$$close_process_begin step1..")
      return jsonify(
        success=True,
        message="already closed",
        elapsed_time=int(log.elapsedActive_time or 0),
        pause_time=int(log.pause_time or 0),
        end_time=log.end_time,
      ), 200

    TPE = ZoneInfo("Asia/Taipei")
    now_aw = datetime.now(TPE).replace(microsecond=0)

    # 1) 若暫停中，先把最後一段暫停秒數補進 pause_time
    if getattr(log, "is_pause", False) and getattr(log, "pause_started_at", None):
      print("$$close_process_begin step2..")

      try:
        ps = log.pause_started_at
        if isinstance(ps, str):
          # 依你的實際格式調整；若你存 "%Y-%m-%d %H:%M:%S"，改用 datetime.strptime
          ps = datetime.fromisoformat(ps)
        if ps.tzinfo is None:
          ps = ps.replace(tzinfo=TPE)

        delta = int((now_aw - ps).total_seconds())
        log.pause_time = (log.pause_time or 0) + max(delta, 0)
      except Exception as e:
        print("close_process: pause_time accumulate failed:", e)
      finally:
        log.pause_started_at = None

    # 2) 校正『有效計時秒數』：採單向遞增（避免寫回比現值還小）
    if elapsed_time is not None:
      print("$$close_process_begin step3..")

      try:
        last_secs = int(elapsed_time)
      except Exception:
        last_secs = int(log.elapsedActive_time or 0)
      cur_secs = int(log.elapsedActive_time or 0)

      log.elapsedActive_time = max(cur_secs, last_secs)

    # 3) 可選：更新 HH:MM:SS 文字欄（若模型有此欄位）
    try:
      print("$$close_process_begin step4..")

      log.str_elapsedActive_time = seconds_to_hms_str(int(log.elapsedActive_time or 0))
    except Exception:
      pass

    # 4) 關閉狀態
    print("$$close_process_begin step5..")

    log.is_pause = True
    log.end_time = now_aw.strftime("%Y-%m-%d %H:%M:%S")
    print("log.process_work_time_qty:", receive_qty)
    log.process_work_time_qty = receive_qty

    if alarm_enable:
      print("$$close_process_begin step5a..")
      log.normal_work_time = 1
      log.abnormal_cause_message=''
    if not alarm_enable and isAssembleFirstAlarm:
      print("$$close_process_begin step5b..")
      log.normal_work_time = 1
      log.abnormal_cause_message=''
    if not alarm_enable and not isAssembleFirstAlarm:
      print("@@close_process_begin step5c..")
      log.normal_work_time = 0
      log.abnormal_cause_message=alarm_message

    log.must_allOk_qty = receive_qty

    # 5)（重點）若有傳 assemble_id + receive_qty，更新該站完成數
    # 也就是說, 處理 receive_qty / assemble_id 之類的寫回，都在此處補充
    is_completed   = False
    total_completed = None
    must_qty       = None

    try:
      print("$$close_process_begin step6..")
      rq = int(receive_qty or 0)
    except Exception:
      rq = 0

    print("$$close_process_begin step7..")
    if assemble_id is not None and rq > 0:
      try:
        asm = s.query(P_Assemble).get(int(assemble_id))
        print("$$close_process_begin step8..")
      except Exception:
        asm = None

      print("$$close_process_begin step9..")
      if asm:
        print("$$close_process_begin step10..")
        # 依你的實際欄位名調整：
        # 假設：must_receive_end_qty = 應完成數量、total_ask_qty_end = 已完成總數
        must_qty = int(asm.must_receive_end_qty or 0)
        cur_total = int(asm.total_ask_qty_end or 0)
        new_total = cur_total + rq

        asm.total_ask_qty_end = new_total
        total_completed = new_total
        is_completed = (must_qty > 0 and new_total >= must_qty)

        s.add(asm)

    print("$$close_process_begin step11..")
    s.add(log)

    s.commit()

    return jsonify(
      success=True,
      end_time=log.end_time,
      elapsed_time=int(log.elapsedActive_time or 0),
      pause_time=int(log.pause_time or 0),
      # 待確定
      # ✅ 前端可用來鎖定 Begin/End 的開始/結束鍵
      is_completed=is_completed,
      total_completed=total_completed,
      must_qty=must_qty
    )


# ------------------------------------------------------------------


@getTable.route("/getUsersDepsProcesses", methods=['POST'])
def get_users_deps_processes():
    print("getUsersDepsProcesses....")

    _user_results = []
    return_value = True
    raw_select = 0
    """
    if request.method == 'GET':
        # 從 query 取
        raw_select = request.args.get('select', 0)
    else:
    """
        # 從 JSON 取
    #data = request.get_json(silent=True) or {}
    data = request.get_json()

    raw_select = data.get('select', 0)

    try:
        # 取得 select 參數（0, 1, 3, 7），預設 0
        raw_select = request.args.get('select', '0')
        try:
            select_days = int(raw_select)
        except ValueError:
            select_days = 0

        # 只允許 0,1,3,7，其它當 0
        if select_days not in (0, 1, 3, 7):
            select_days = 0

        today = dt.now().date()

        if select_days <= 0:
            # select = 0 → 只算今天
            start_day = today
            end_day = today
        else:
            # select = 1/3/7 → 算「前 N 天」，不含今天
            # 例如 select=3：今天 11/23，範圍是 11/20 ~ 11/22
            start_day = today - timedelta(days=select_days)
            end_day = today - timedelta(days=1)

        start_str = f"{start_day.strftime('%Y-%m-%d')} 00:00:00"
        end_str   = f"{end_day.strftime('%Y-%m-%d')} 23:59:59"
        print(f"計算區間: select={select_days}, {start_str} ~ {end_str}")

        s = Session()

        _objects = s.query(User).all()
        users = [u.__dict__ for u in _objects]
        index=0
        for user in users:
            # 依你原本邏輯：只留下 isRemoved == True 的使用者
            if user['isRemoved'] == False:
                continue

            emp_id = user['emp_id']

            # 計算這段日期內的 elapsedActive_time 總和
            total_elapsed = (
                s.query(func.coalesce(func.sum(Process.elapsedActive_time), 0))
                .filter(
                    Process.user_id == emp_id,
                    Process.begin_time != '',
                    Process.end_time != '',
                    Process.begin_time >= start_str,
                    Process.begin_time <= end_str,
                    Process.end_time >= start_str,
                    Process.end_time <= end_str,
                )
                .scalar()
            ) or 0

            total_elapsed = int(total_elapsed)
            #print("total_elapsed:", total_elapsed)
            # 轉成 hh:mm:ss 文字
            h = total_elapsed // 3600
            m = (total_elapsed % 3600) // 60
            sec = total_elapsed % 60
            total_str = f"{h:02d}:{m:02d}:{sec:02d}"
            index = index + 1
            _user_object = {
              'id': index,
              'emp_id': emp_id,
              'emp_name': user['emp_name'],
              'dep_name': user['dep_name'].split('-', 1)[1],

              #'elapsedActive_range_secs':  total_elapsed,
              #'elapsedActive_range_str':  total_str,
              #'elapsedActive_select':  select_days,
              'workHours': total_str,
              'online': random.randint(0, 2),
            }

            _user_results.append(_user_object)


        temp_len = len(_user_results)
        print("getUsersDepsProcesses, 總數: ", temp_len)

        return jsonify({
          'status': return_value,
          'users_and_deps_and_process': _user_results,
        })

    except Exception as e:
        s.rollback()
        print("list_users_deps_processes error:", e)
        return jsonify({
            'status': False,
            'error': str(e),
        })
    finally:
        s.close()


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
    assemble_records=material._assemble
    for record in material._process:
        alarm_proc_record = [a for a in assemble_records if ((a.id == record.assemble_id and record.has_started))]
        if len(alarm_proc_record) == 1:
            alarm_msg_enable = alarm_proc_record[0].alarm_enable
            alarm_msg_isAssembleFirstAlarm = alarm_proc_record[0].isAssembleFirstAlarm
            if not alarm_msg_enable and not alarm_msg_isAssembleFirstAlarm:
              alarm_msg_string = (alarm_proc_record[0].alarm_message or '').strip()
            else:
              alarm_msg_string = ''

            if record.process_type == 21:
              alarm_msg_string = alarm_proc_record[0].Incoming1_Abnormal
        else:
            alarm_msg_enable = True
            alarm_msg_isAssembleFirstAlarm = True
            alarm_msg_string = ''

            if (
              material.Incoming0_Abnormal != '' and
              record.end_time !='' and
              record.begin_time !='' and
              record.assemble_id==0 and
              record.process_type in [1, 5]
            ):
              alarm_msg_string = material.Incoming0_Abnormal


        # 跳過 begin_time 為 None、空字串、只有空白、或無效預設值的紀錄
        bt = (record.begin_time or "").strip()
        if (not bt or bt == "0000-00-00 00:00:00") and record.process_type not in {5, 6}:
            continue

        seq_num += 1

        status = code_to_name.get(record.process_type, '空白')
        print("step1...", status)
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

            'normal_type': ' - 異常整修' if (not alarm_msg_enable and not alarm_msg_isAssembleFirstAlarm) else '',
            'user_comment': alarm_msg_string,

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


@getTable.route("/getWarehouseForAssembleByHistory", methods=['POST'])
def get_Warehouse_For_assemble_by_history():
    print("getWarehouseForAssembleByHistory()...")

    s = Session()
    try:
        q = (
            s.query(Material, Assemble, Process)
             .join(Process, Process.material_id == Material.id)         # Material -> Process
             .join(Assemble, Assemble.id == Process.assemble_id)        # Process -> Assemble
             .filter(Process.has_started.is_(True))
             .filter(Process.end_time.isnot(None))
             .filter(Process.end_time != '')
             .filter(Process.normal_work_time.in_([2, 3]))
        )

        # 資料是 (Material, Assemble, Process) JOIN 回來的 tuple
        rows = q.all()

        def g(obj, name, default=None):
            return getattr(obj, name, default) if obj is not None else default

        def safe_str(v, default=''):
          try:
            return '' if v is None else str(v)
          except Exception:
            return default

        results = []
        index=0
        for m, a, p in rows:
            isWarehouseStationShow = bool(g(a, "isWarehouseStationShow", 0))
            #print("isWarehouseStationShow:", isWarehouseStationShow)
            if isWarehouseStationShow:
               continue

            cleaned_comment = (g(m, "material_comment", "") or "").strip()
            material_id=g(m, "id")
            assemble_id=g(a, "id")
            input_allOk_disable=g(a, "input_allOk_disable")
            ok, process_total = need_more_process_qty(k1=material_id, a1=assemble_id, t1=31, must_qty=0, s=s)
            print("process_total:", process_total)
            index=index+1

            results.append({
                "index":  index,
                "id":                   material_id,
                "order_num":            g(m, "order_num", ""),
                "material_num":         g(m, "material_num", ""),
                "req_qty":              g(m, "material_qty", 0),
                "date":                 g(m, "material_delivery_date", ""),
                "input_allOk_disable":  input_allOk_disable,
                "allOk_disable":  g(a, "input_allOk_disable"),

                "shortage_note":        g(m, "shortage_note", ""),
                "comment":              cleaned_comment,
                "Incoming2_Abnormal":   (g(m, "Incoming2_Abnormal", "") == ""),

                "process_id":           g(p, "id"),
                "assemble_id":          assemble_id,
                "delivery_qty":         g(p, "process_work_time_qty"),    # 到庫數量
                "must_allOk_qty":       g(p, "must_allOk_qty", 0),        # 應入庫總數量
                "total_allOk_qty":      process_total,                    # 已入庫登記總數量
                #"allOk_qty":            g(p, "allOk_qty", 0),             # 入庫數量
                "allOk_qty":            g(a, "allOk_qty", 0),             # 入庫數量
                "isWarehouseStationShow": isWarehouseStationShow,

                "normal_work_time":     g(p, "normal_work_time", 0),
                "tooltipVisible":       False,
            })

        results.sort(key=lambda x: (x["material_num"] or ""), reverse=True)

        return jsonify({
            "status": len(results) > 0,
            "warehouse_for_assemble": results
        })
    finally:
        s.close()


# 取得訂單「組裝異常」相關的歷史資訊清單
@getTable.route("/getInformationsForAssembleErrorByHistory", methods=['POST'])
def get_informations_for_assemble_error_by_history():
    print("getInformationsForAssembleErrorByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)   # 是否包含歷史資料
    _userId = data.get('userId')
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

    currentUser = s.query(User).filter_by(emp_id=_userId).first()

    perm = True if currentUser.perm_id >=2 and currentUser.perm_id <=4 else False

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
        if assemble_record.abnormal_qty == 0:
           continue

        if assemble_record.user_id != _userId and not perm:
          continue

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
          #'cause_message':filtered_list,
          'cause_message': temp_alarm_message,
          #'alarm_qty': assemble_record.isAssembleFirstAlarm_qty,
          'alarm_qty': assemble_record.abnormal_qty,
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


@getTable.route("/getMaterialsAndAssemblesAndTime", methods=['POST'])
def get_materials_and_assembles_and_time():
    print("getMaterialsAndAssemblesAndTime....")

    request_data = request.get_json()

    k1 = request_data['mid']
    t1 = request_data['code']
    u1 = request_data['user_id']

    code_to_pt = {'106': 23, '109': 21, '110': 22}

    def safe_str(v, default=''):
      try:
          return '' if v is None else str(v)
      except Exception:
          return default

    pt =code_to_pt.get(t1, 0)

    s = Session()

    try:
      row = (s.query(Process).filter(
          Process.material_id == k1,
          Process.process_type == pt,
          Process.has_started.is_(True),
          Process.end_time.isnot(None),
          Process.end_time != '',
          Process.user_id == u1,
        ).first()
      )

      print("last_time:", row.str_elapsedActive_time)

      return jsonify({
        'last_time': row.str_elapsedActive_time,
        'qty': row.process_work_time_qty,
      })
    finally:
      s.close()


# list all materials and assemble data
@getTable.route("/getMaterialsAndAssembles", methods=['POST'])
def get_materials_and_assembles():
    print("getMaterialsAndAssembles....")

    request_data = request.get_json()
    _user_id = request_data['user_id']

    s = Session()
    _results = []
    _assemble_active_users = []

    def safe_str(v, default=''):
        try:
            return '' if v is None else str(v)
        except Exception:
            return default

    def safe_status_str(num, base_str, completed_qty, pos):
        """
        只在 num ∈ {5,7,9} 且 pos ∈ {1,2,3} 時，安全替換 '00/00/00' 的其中一段。
        """
        try:
            if num in (5, 7, 9) and pos in (1, 2, 3):
                parts = (base_str or '00/00/00').split('/')
                if len(parts) == 3:
                    parts[pos - 1] = safe_str(completed_qty, '00')
                    return '/'.join(parts)
        except Exception:
            pass
        return base_str or '00/00/00'

    try:
        _objects = s.query(Material).all()
        material_ids_all = [m.id for m in _objects]

        # 每個 material 的最大 step_code
        max_step_code_per_order = {}
        for material_record in _objects:
            for assemble_record in material_record._assemble:
                step_code = assemble_record.process_step_code
                order_num_id = material_record.id
                cur = max_step_code_per_order.get(order_num_id)
                max_step_code_per_order[order_num_id] = step_code if cur is None else max(cur, step_code)

        code_to_name = {'106': '雷射', '109': '組裝', '110': '檢驗'}
        str2 = ['未備料','備料中','備料完成','等待組裝作業','組裝進行中','00/00/00','檢驗進行中','00/00/00','雷射進行中','00/00/00','等待入庫作業','入庫進行中','入庫完成']
        code_to_pt = {'106': 23, '109': 21, '110': 22}

        index = 0
        test_index = 0
        for material_record in _objects:
            if not material_record.isShow:
                continue

            process_records = material_record._process
            assemble_records = material_record._assemble

            # 先算出：在同一個 material_id 裡，每個 update_time 的 max_step_code
            max_by_ut = {}  # { update_time -> max_step_code }
            for a in assemble_records:
                step = int(a.process_step_code or 0)
                if step == 0:
                    continue
                ut = a.update_time
                #if ut is None:
                #    continue  # 若你想把 NULL 當成一組可改成保留
                cur = max_by_ut.get(ut)
                if cur is None or step > cur:
                  max_by_ut[ut] = step

            for assemble_record in material_record._assemble:
                if assemble_record.must_receive_qty <= 0:
                   continue

                step = int(assemble_record.process_step_code or 0)

                # 依 work_num 判斷對應的 process_type
                work = assemble_record.work_num or ''
                target_pt = None
                if 'B109' in work:
                    target_pt = 21
                elif 'B110' in work:
                    target_pt = 22
                elif 'B106' in work:
                    target_pt = 23

                matched_count = 0
                total_work_qty = 0  # 累加 process_work_time_qty
                if target_pt is not None:
                    # 這裡一定要是 list，不是數字！
                    target_procs = [
                        p for p in process_records
                        if p.material_id == assemble_record.material_id
                        and p.process_type == target_pt
                    ]

                    matched_count = len(target_procs)
                    total_work_qty = sum((p.process_work_time_qty or 0) for p in target_procs)

                # a_statement: step != 0 且有對應 process，且已報工數量 >= 交期數量
                a_statement = (
                    step != 0
                    and matched_count > 0
                    and total_work_qty >= (material_record.delivery_qty or 0)
                )
                print("$$$ step, matched_count:", step, matched_count, total_work_qty, a_statement, assemble_record.id)
                if step == 0 or (step != 0 and matched_count == 0) or a_statement:
                #if step == 0 or assemble_record.user_id:
                  continue


                # ---- 安全取值區 ----
                cleaned_comment = safe_str(material_record.material_comment).strip()
                work_num = safe_str(assemble_record.work_num)     # 可能為 ''（避免 None）
                code = work_num[1:] if len(work_num) >= 2 else work_num
                name = code_to_name.get(code, '')
                pt =code_to_pt.get(code, 0)

                ok, process_total = need_more_process_qty(k1=assemble_record.material_id, a1=assemble_record.id, t1=pt, must_qty=assemble_record.must_receive_end_qty, s=s)

                # 找出該組(max) → 「同 material_id 且同 update_time」
                ut = assemble_record.update_time
                max_step_code = max_by_ut.get(ut)
                if max_step_code is None:
                    continue

                if step != max_step_code:
                    continue

                print("max_step_code:", max_step_code, assemble_record.id, assemble_record.material_id)

                # 缺料併單排除
                if material_record.isLackMaterial == 0 and material_record.is_copied_from_id and material_record.is_copied_from_id > 0:
                  continue

                num = int(getattr(assemble_record, 'show2_ok', 0) or 0)
                base = str2[num] if 0 <= num < len(str2) else '00/00/00'
                ##print("**********id, num, show2_ok:", assemble_record.id, num, assemble_record.show2_ok, base, len(str2))
                total_ask_end = getattr(assemble_record, 'total_ask_qty_end', None)
                completed_qty = getattr(assemble_record, 'completed_qty', 0)
                temp_temp_show2_ok_str = safe_status_str(num, base, completed_qty, total_ask_end)

                format_name = f"{work_num}({name})" if name else work_num

                index += 1
                _object = {
                    'index': index,
                    'id': material_record.id,
                    'order_num': material_record.order_num,
                    'assemble_work': format_name,
                    'material_num': material_record.material_num,
                    #'assemble_process': '' if (num > 2 and not (step_enable or sub_process_step_enable)) else temp_temp_show2_ok_str,
                    'assemble_process': '' if num > 2 else temp_temp_show2_ok_str,

                    'assemble_process_num': num,
                    'assemble_id': assemble_record.id,
                    'req_qty': material_record.material_qty,

                    'delivery_qty': material_record.delivery_qty,
                    'total_receive_qty': f"({getattr(assemble_record, 'total_ask_qty', 0)})",
                    'total_receive_qty_num': getattr(assemble_record, 'total_ask_qty', 0),
                    #'total_receive_qty_num': process_total,

                    'must_receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'must_receive_end_qty': getattr(assemble_record, 'must_receive_qty', 0),

                    'delivery_date': material_record.material_delivery_date,
                    'comment': cleaned_comment,
                    'isTakeOk': material_record.isTakeOk,
                    'whichStation': material_record.whichStation,
                    'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,
                    'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,
                    'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,
                    'currentStartTime': getattr(assemble_record, 'currentStartTime', None),
                    'tooltipVisible': False,
                    'input_disable': getattr(assemble_record, 'input_disable', False),
                    #'process_step_enable': bool(step_enable or sub_process_step_enable),
                    'process_step_code': max_step_code,
                    #'completed_qty': str(assemble_record.completed_qty),

                    'isLackMaterial': material_record.isLackMaterial,
                    'Incoming1_Abnormal': getattr(assemble_record, 'Incoming1_Abnormal', '') == '',
                    'is_copied_from_id': getattr(assemble_record, 'is_copied_from_id', None),
                    'create_at': assemble_record.create_at,
                }
                _results.append(_object)


        print("kkkkaaa _results length:", len(_results))
        # 只有在前面的 _results 成功建好後，才去算使用中人數
        #from sqlalchemy import or_ as _or
        counts_by_type = active_count_map_by_material_multi(
            s,
            material_ids=material_ids_all,
            process_types=(21, 22, 23),
            include_paused=False
        )

        ###
        def _contains_code(s: str, code: str) -> bool:
            # 嚴謹判斷，避免 '1109' 被當成 '109'
            return re.search(rf'(?<!\d){re.escape(code)}(?!\d)', str(s or "")) is not None

        def _to_qty_str(v):
            if v is None: return "0"
            try:
                if isinstance(v, float) and v.is_integer():
                    return str(int(v))
                return str(v)
            except Exception:
                return str(v)

        def _to_int_or_none(x):
            try:
                return int(x)
            except Exception:
                return None

        # ① 預取：k=row.assemble_id 的「前一筆 h=k-1 是否存在且 step==0」
        def prepare_prev_step0_flags(session, rows):
            ks = set()
            for r in rows:
                k = _to_int_or_none(r.get('assemble_id'))
                if k is not None:
                    ks.add(k)
            prev_ids = {k - 1 for k in ks if k and k > 0}
            if not prev_ids:
                return {}

            recs = (session.query(Assemble.id, Assemble.process_step_code)
                          .filter(Assemble.id.in_(prev_ids))
                          .all())
            id_to_step = {aid: step for aid, step in recs}
            # 回傳：k -> (ok, h)
            return {k: ((id_to_step.get(k - 1) == 0), (k - 1)) for k in ks}

        # ② 預取：(assemble_id=h, material_id=mid) → 最新 qty
        def prepare_latest_qty_by_pair_h_mid(session, rows, prev_ok_map):
            pairs = set()
            for r in rows:
                k = _to_int_or_none(r.get('assemble_id'))
                mid = _to_int_or_none(r.get('id'))
                num = _to_int_or_none(r.get('work_num'))
                if k is None or mid is None:
                    continue
                ok, h = prev_ok_map.get(k, (False, None))
                if not ok or h is None:
                    continue
                pairs.add((h, mid))

            if not pairs:
                return {}

            hs  = {h for h, _ in pairs}
            mids = {mid for _, mid in pairs}
            nums = {num for _, num in pairs}

            q = (session.query(
                    Process.assemble_id,         # h
                    Process.material_id,         # mid
                    Process.process_work_time_qty,
                    Process.end_time,
                    Process.id
                )
                .filter(Process.assemble_id.in_(hs),
                        Process.material_id.in_(mids))
            )

            buckets = defaultdict(list)
            for a_id, m_id, qty, end_time, pid in q:
                buckets[(a_id, m_id)].append((end_time, pid, qty))

            latest_qty = {}
            for key, items in buckets.items():
                ended = [it for it in items if it[0] is not None]
                if ended:
                    ended.sort(key=lambda t: (t[0], t[1]), reverse=True)   # end_time DESC, id DESC
                    latest_qty[key] = _to_qty_str(ended[0][2])
                else:
                    items.sort(key=lambda t: t[1], reverse=True)           # id DESC
                    latest_qty[key] = _to_qty_str(items[0][2])
            return latest_qty

        # ③ 主修補：符合條件時，把 aa/bb/cc 改為 (h, mid) 的最新 qty
        def patch_assemble_process_from_h_mid(session, rows):
            prev_ok_map = prepare_prev_step0_flags(session, rows)
            qty_map     = prepare_latest_qty_by_pair_h_mid(session, rows, prev_ok_map)
            print("prev_ok_map:",prev_ok_map)
            print("qty_map:",qty_map)
            for row in rows:
                k   = _to_int_or_none(row.get('assemble_id'))  # k = m = row.assemble_id
                mid = _to_int_or_none(row.get('id'))           # mid = row.id
                if k is None or mid is None:
                    continue

                ok, h = prev_ok_map.get(k, (False, None))
                if not ok or h is None:
                    continue  # h=k-1 不存在或 step!=0 → 不處理

                num = row.get('assemble_work') or ""               # num = assemble.work_num
                ap  = row.get('assemble_process') or ""
                print("k, mid:", k, mid)
                print("ok, h:", ok, h)

                print("ap:", ap)
                parts = ap.split('/') if ap else []
                print("parts:",parts)
                while len(parts) < 3:
                    parts.append('0')

                pair_qty = qty_map.get((k-1, mid), "0")        # (assemble_id=h, material_id=mid)
                print("pair_qty:",pair_qty)
                print("num:",num)
                # 109 → aa(0), 110 → bb(1), 106 → cc(2)
                if _contains_code(num, '109'):
                    parts[2] = pair_qty
                    print("parts[0]:", parts[0])
                if _contains_code(num, '110'):
                    parts[0] = pair_qty
                    print("parts[1]:", parts[1])
                if _contains_code(num, '106'):
                    parts[1] = pair_qty
                    print("parts[2]:", parts[2])

                row['assemble_process'] = '/'.join(parts[:3])
                print("row['assemble_process'] :", row['assemble_process'])

        ###

        #print("_results:",_results)
        # 先依「h = k-1 為 step==0」條件回填 assemble_process
        patch_assemble_process_from_h_mid(s, _results)

        # 安全讀值的 map_pt / get_val 已在檔案上方定義
        for row in _results:
            try:
                pt = str(map_pt(row))                  # '21'/'22'/'23'
                mid = str(get_val(row, 'id'))         # material_id
                temp_count = counts_by_type.get(pt, {}).get(mid, 0)
                row['active_user_count'] = temp_count
                _assemble_active_users.append(temp_count)

            except Exception as e:
                print("listMaterialsAndAssembles: skip bad row =>", e, row)
                continue

        """
        # 1) 找出需剔除的 material_id 清單
        mids_to_remove = {
            mid for (mid,) in (
                s.query(Process.material_id)
                .filter(Process.normal_work_time == 3)
                .filter(Process.end_time.isnot(None))
                .filter(Process.end_time != '')
                .distinct()
                .all()
            )
        }

        if mids_to_remove:
            mids_to_remove_str = {str(m) for m in mids_to_remove}

            # 2) _results 與 _assemble_active_users 一起過濾，保持索引一致
            _results_kept = []
            _counts_kept  = []
            for i, row in enumerate(_results):
                rid = str(row.get('id'))
                if rid not in mids_to_remove_str:
                    _results_kept.append(row)
                    # 這裡假設 _assemble_active_users 與 _results 先前是一一對應 append 的
                    if i < len(_assemble_active_users):
                        _counts_kept.append(_assemble_active_users[i])

            _results = _results_kept
            _assemble_active_users = _counts_kept
        """
        s.close()

        # 先依 id（升冪）排一次
        _results.sort(key=lambda x: x.get('id') or 0)

        # 再依 create_at（降冪）排一次 → 穩定排序會保留同日期下的 id 排序
        _results.sort(key=lambda x: x.get('create_at') or datetime.min, reverse=True)

        return jsonify({
            'status': bool(_results),
            'materials_and_assembles': _results or [],
            'assemble_active_users': _assemble_active_users or [],
        })

    except Exception as e:
        # 任何資料不乾淨都不讓它 500；記 log + 回傳空清單，避免前端炸掉
        import traceback
        print("listMaterialsAndAssembles ERROR:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("listMaterialsAndAssembles failed")
        except Exception:
            pass
        s.close()
        return jsonify({
            'status': False,
            'materials_and_assembles': [],
            'assemble_active_users': [],
        }), 200


# list all materials and assemble data by current user
@getTable.route("/getMaterialsAndAssemblesByUser", methods=['POST'])
def get_materials_and_assembles_by_user():
    print("getMaterialsAndAssemblesByUser....")

    request_data = request.get_json()

    _user_id = request_data['user_id']
    print("_user_id:", _user_id)
    s = Session()

    _results = []
    return_value = True
    code_to_name = {'106':'雷射', '109':'組裝', '110':'檢驗'}    # 組裝區工作代號
    code_to_assembleStep = { '109': 3, '106': 1, '110': 2, }    # 組裝區工作順序, 3:最優先
    code_to_pt = {'106': 23, '109': 21, '110': 22}              # process table 工序代號

    #       0         1       2            3              4            5           6            7           8            9           10             11            12
    str2=['未備料', '備料中', '備料完成',   '等待組裝作業', '組裝進行中', '00/00/00', '檢驗進行中', '00/00/00', '雷射進行中', '00/00/00', '等待入庫作業', '入庫進行中',  '入庫完成']

    def safe_str(v, default=''):
      try:
        return '' if v is None else str(v)
      except Exception:
        return default

    _objects = s.query(Material).all()
    material_ids_all = [m.id for m in _objects]

    # 1) 篩選「該使用者、且 has_started=True」的未結束 Process 名單/計數
    counts_by_type = active_count_map_by_material_multi(
        s, material_ids_all,
        process_types=(21, 22, 23),
        include_paused=False,           # 是否把暫停算在「未結束」內，False:不包括
        # only_user_id=None            # 全員
        only_user_id=_user_id,          # 只算該使用者本人（看你要哪種）
        has_started=True,               # 只找 has_started=True
    )
    print("start....")
    # 篩選「誰」正在該料號/該製程上有未結束(進行中或暫停中)的流程, 並將結果依「製程別(21/22/23) → 料號ID」分組，回傳每一組底下的使用者ID清單。
    user_ids_by_type = active_user_ids_by_material_multi(
        s, material_ids_all,
        process_types=(21, 22, 23),
        include_paused=True,
        #only_user_id=None,           # 全員名單
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
      process_records = material_record._process

      # 測適用
      #if material_record.id==4:
      #  t_user_proc_records = [p for p in process_records if ((p.user_id == _user_id and not p.end_time and p.end_time !=''))]
      #  print("t_user_proc_records:",t_user_proc_records)

      # 篩選登入者的製程紀錄
      #user_proc_records = [p for p in process_records if p.user_id == _user_id]
      #if not user_proc_records:
      #   continue

      #print("aaa step1...")
      #print("material_record id:", material_record.id, user_proc_records)
      for assemble_record in material_record._assemble:   # loop_a_rec
        # 篩選登入者的製程紀錄
        #user_proc_records = [p for p in process_records if ((p.user_id == _user_id and not p.end_time and p.end_time !='') or assemble_record.isAssembleStationShow)]
        user_proc_records = [p for p in process_records if (p.user_id == _user_id and not p.end_time or p.end_time !='')]
        #print("user_proc_records, rows:", len(user_proc_records), assemble_record.id)
        #print("s0s0s0s0s0 index:",index)
        #if not user_proc_records:
        #  continue
        #print("s1s1s1s1s1 index:",index)

        if assemble_record.process_step_code==0 and not assemble_record.isAssembleStationShow:
           continue

        ### 相同登入者 ###

        # 依 work_num 判斷對應的 process_type
        work = assemble_record.work_num or ''
        target_pt = None
        if 'B109' in work:
            target_pt = 21
        elif 'B110' in work:
            target_pt = 22
        elif 'B106' in work:
            target_pt = 23

        matched_count = 0
        if target_pt is not None:
            # 這裡一定要是 list，不是數字！
            target_procs = [
                p for p in process_records
                if p.material_id == assemble_record.material_id
                and p.assemble_id == assemble_record.id
                and p.process_type == target_pt

                and p.user_id == _user_id

                and p.begin_time
                and (not p.end_time or p.end_time !='')
            ]

            matched_count = len(target_procs)

        if matched_count == 0 and not assemble_record.isAssembleStationShow:
        #if (assemble_record.user_id != _user_id):   # 相同登入者
          continue

        ###

        #end_proc_records = [end_p for end_p in process_records if end_p.assemble_id == assemble_record.id and not end_p.end_time and end_p.begin_time]
        #print("isAssembleStationShow:",assemble_record.isAssembleStationShow)
        #print("end_proc_records:",end_proc_records)
        #if not assemble_record.isAssembleStationShow and not end_proc_records:
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
        print("sssss index:",index)
        #
        # 處理 show2_ok 的情況
        print("temp_show2_ok, temp_assemble_show2_ok:", temp_show2_ok, temp_assemble_show2_ok)
        if temp_show2_ok in [5, 7, 9] or temp_assemble_show2_ok in [5, 7, 9]:
          for temp2_assemble_record in assemble_records:
            if temp2_assemble_record.total_ask_qty_end in [1, 2, 3]:
              completed_qty = str(temp2_assemble_record.completed_qty)                  # 將數值轉換為字串
              date_parts = temp_assemble_process_str.split('/')                         # 分割 00/00/00 為 ['00', '00', '00']
              date_parts[temp2_assemble_record.total_ask_qty_end - 1] = completed_qty   # 替換對應位置
              temp_assemble_process_str = '/'.join(date_parts)                          # 合併回字串
        #

        work_num = safe_str(assemble_record.work_num)     # 可能為 ''（避免 None）
        code = work_num[1:] if len(work_num) >= 2 else work_num
        name = code_to_name.get(code, '')
        pt =code_to_pt.get(code, 0)
        #print("pt:", pt)
        #print("must_qty:", assemble_record.id, assemble_record.must_receive_end_qty)
        ok, process_total = need_more_process_qty(k1=assemble_record.material_id, a1=assemble_record.id, t1=pt, must_qty=assemble_record.must_receive_end_qty, s=s)
        # ok 為 True 代表 process_total < 50；False 代表已達標或超過
        #assemble_abnormal_total=need_more_assemble_abnormal_qty(k1=assemble_record.material_id, s=s)
        #print("id, process_total, assemble_abnormal_total:", assemble_record.id, process_total, assemble_abnormal_total)

        #print("user_proc_records:", user_proc_records)
        r = next(
            (p for p in user_proc_records
            if p.material_id == assemble_record.material_id and p.process_type == pt),
            None
        )

        def _norm_end_time(x):
          if x is None:
              return None
          if isinstance(x, str):
              x = x.strip()
              if x == "" or x == "0000-00-00 00:00:00":
                  return None
              return x
          # 若是 datetime 物件就直接回傳
          return x

        user_receive_qty = int((getattr(r, "process_work_time_qty", 0) or 0))

        _end_time = _norm_end_time(getattr(r, "end_time", None))
        user_is_show_last_time = _end_time is not None

        # 若有結束時間才顯示字串化的工時；沒有就給空字串
        user_last_time = getattr(r, "str_elapsedActive_time", "") if user_is_show_last_time else ""

        print("工序format_name:", format_name)
        print("assemble_record.input_end_disable:", assemble_record.input_end_disable)

        _object = {
          'index': index,                                   #agv送料序號
          'id': material_record.id,                         #訂單編號
          'order_num': material_record.order_num,           ## 訂單編號
          'material_num': material_record.material_num,     ## 物料編號
          'req_qty': material_record.material_qty,          ## 組裝區需求數量(訂單數量)
          'ask_qty': assemble_record.ask_qty,               ## 組裝區領取數量

          'assemble_work': format_name,                     #工序
          'assemble_process': '' if (num > 2 and not step_enable) else temp_assemble_process_str,
          'assemble_process_num': num,
          'assemble_id': assemble_record.id,
          'total_ask_qty_end': assemble_record.total_ask_qty_end,
          'process_step_code': assemble_record.process_step_code,

          'must_receive_end_qty': int(getattr(assemble_record, 'must_receive_end_qty', 0) or 0),
          'abnormal_qty': int(getattr(assemble_record, 'abnormal_qty', 0) or 0),                      ## 組裝區異常數量

          'total_completed_qty': f"({assemble_record.total_completed_qty})",
          'total_completed_qty_num': process_total,

          #'must_receive_end_qty': assemble_record.must_receive_end_qty,
          #'abnormal_qty': assemble_record.abnormal_qty,                       ## 組裝區異常數量

          'receive_qty': assemble_record.completed_qty,                       ## 組裝區完成數量

          'delivery_date': material_record.material_delivery_date,            # 交期
          'delivery_qty': material_record.delivery_qty,                       # 現況數量
          'abnormal_qty': assemble_record.isAssembleFirstAlarm_qty if code == '109' else assemble_record.abnormal_qty,

          'total_assemble_qty': material_record.total_assemble_qty,           # 已(組裝）完成總數量

          'comment': cleaned_comment,                                         # 說明
          'isAssembleAlarm' : material_record.isAssembleAlarm,

          'isAssembleFirstAlarm' : assemble_record.isAssembleFirstAlarm,
          'isAssembleFirstAlarm_qty' : assemble_record.isAssembleFirstAlarm_qty,
          'alarm_enable' : assemble_record.alarm_enable,

          'whichStation' : material_record.whichStation,
          'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,   # true:組裝站製程3完成(最後製程)
          'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,   # true:組裝站製程3完成(最後製程)
          'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,   # true:組裝站製程3完成(最後製程)
          'isLackMaterial': material_record.isLackMaterial,
          'shortage_note': material_record.shortage_note,

          'isAssembleStationShow': bool(assemble_record.isAssembleStationShow==1),         # true:完成生產報工(按結束按鍵),
          'currentStartTime': assemble_record.currentStartTime,
          'tooltipVisible': False,
                                                                                                                      #顯示數字輸入欄位alarm
          'abnormal_tooltipVisible': False,
                                                                                                                    #顯示數字輸入欄位alarm
          'input_end_disable': assemble_record.input_end_disable,
          #'input_abnormal_disable': assemble_record.isAssembleFirstAlarm_qty if code == '110' else True,
          'input_abnormal_disable': assemble_record.input_abnormal_disable,
          'alarm_enable': assemble_record.alarm_enable,

          'process_step_enable': step_enable,

          'code': code,

          'isShowLastTime': user_is_show_last_time,
          'last_time': user_last_time,

          'assemble_count': len(material_record._assemble),

          'is_copied_from_id': assemble_record.is_copied_from_id,

          'create_at': assemble_record.create_at,
        }

        processed_records.add((order_num_id, format_name))
        _results.append(_object)

      # end loop_a_rec
    # end loop_m_rec

    print("kkkkk length:", len(_results), index)

    record_sum = (
    s.query(
        Assemble.material_id,
        func.coalesce(func.sum(cast(Assemble.completed_qty, Integer)), 0).label("sum_completed_qty")
    )
    .filter(Assemble.isAssembleStationShow == 1)
    .group_by(Assemble.material_id)
    .order_by(Assemble.material_id)
    .all()
)

    #for material_id, total in record_sum:
    #  print(f"material_id={material_id}, completed_qty總和={total}")

    ###
    all_zero_by_mid = {}
    for r in _results:
        mid  = str(r['id'])
        code = int((r.get('process_step_code') or 0))
        if mid not in all_zero_by_mid:
            all_zero_by_mid[mid] = True
        if code != 0:
            all_zero_by_mid[mid] = False

        for material_id, total in record_sum:
          if r['id']==material_id:
             r['total_completed_qty_num']=total

    #print("all_zero_by_mid:", all_zero_by_mid)

    # 2) 加上 end_ok 的過濾
    filtered_results = []
    for row in _results:
        #if int(row['must_receive_end_qty'])==0:
        #   index=index-1
        #   continue
        #print("ffff.....must_receive_end_qty <> 0", row['assemble_id'], index)
        # 先處理 isAssembleStationShow==1 且該 material 的所有 step 都是 0 → 直接納入
        if int(row.get('isAssembleStationShow') or 0) == 1 and all_zero_by_mid.get(mid, False):
            filtered_results.append(row)
            index=index-1
            continue
        print("ffff11.....continue", row['assemble_id'], index)

        ptype = map_pt_from_step_code(int(row['process_step_code']))  # 21/22/23
        mid   = str(row['id'])

        # 該製程/料的使用者名單（list），挑出是否包含 _user_id
        #print(user_ids_by_type, ptype, mid)
        ulist = pick_user_list(user_ids_by_type, ptype, mid)
        print("ulist:",ulist)
        #print("_user_id:",_user_id)
        if _user_id not in ulist:
          index=index-1
          continue  # 不是該 user 的「已開始」紀錄 → 略過
        #print("ffff22.....continue", row['assemble_id'], index)

        # 3) 再套 end_ok 條件（必須 True 才留下）
        if not end_ok_flag(s, material_id=row['id'], process_step_code=int(row['process_step_code'])):
          index=index-1
          continue
        #print("ffff33.....continue", row['assemble_id'], index)

        filtered_results.append(row)
    ###

    #s.close()

    # ① step → pt 對應
    def _map_step_to_pt(step: int) -> int:
        # step=3 -> pt=21, step=2 -> pt=22, step=1 -> pt=23
        return 21 if step == 3 else 22 if step == 2 else 23

    # ② 依 material_id + pt 加總所有 process.process_work_time_qty
    def count_all_by_mid_and_step(mid: int, step: int) -> int:
        pt = _map_step_to_pt(int(step or 0))
        total = (
            s.query(func.coalesce(func.sum(Process.process_work_time_qty), 0))
             .filter(Process.material_id == mid)
             .filter(Process.process_type == pt)
             .scalar()
        ) or 0
        return int(total)

    # 只回傳符合該 user 的 rows
    print("1.materials_and_assembles_by_user:", len(_results))

    ##_results = filtered_results

    """
    for row in _results:
      #print("### _results:", _results)

      # 以每筆資料的 material_id 與該筆的 process_step_code 計算
      mid = int(row['id'])
      step = int(row.get('process_step_code') or 0)
      row['total_completed_qty_num'] = count_all_by_mid_and_step(mid, step)
    """



    """
      check1 = int(row['total_completed_qty_num'])
      check2 = int(row['must_receive_end_qty'])
      print("assemble_id, check1, check2:", row['assemble_id'], check1, check2)
      #if (check1 < check2):
      if (check2 > 0):
        row['input_end_disable'] = False
        print("check1..., False", check1, check2)
      else:
        row['input_end_disable'] = True
        print("check2..., True", check1, check2)
    """
      #print("### _results:", _results)


    s.close()

    temp_len = len(_results)
    print("getMaterialsAndAssemblesByUser, 總數: ", temp_len)
    print("2.materials_and_assembles_by_user:", len(_results))
    print("active_counts_all:", counts_by_type)
    print("active_user_ids_all:", user_ids_by_type)

    #print("_results:", _results)

    if (temp_len == 0):
      return_value = False

    # 先依 id（升冪）排一次
    _results.sort(key=lambda x: x.get('id') or 0)

    # 再依 create_at（降冪）排一次 → 穩定排序會保留同日期下的 id 排序
    _results.sort(key=lambda x: x.get('create_at') or datetime.min, reverse=True)

    return jsonify({
      'status': return_value,
      'materials_and_assembles_by_user': _results,
      'active_counts_all': counts_by_type,
      'active_user_ids_all': user_ids_by_type,
    })


@getTable.route("/getMaterialsAndAssemblesByUserP", methods=['POST'])
def get_materials_and_assembles_by_user_p():
    print("getMaterialsAndAssemblesByUserP....")

    request_data = request.get_json()

    _user_id = request_data['user_id']
    print("_user_id:", _user_id)
    s = Session()

    _results = []
    return_value = True
    code_to_name = {'106':'雷射', '109':'組裝', '110':'檢驗'}    # 組裝區工作代號
    code_to_pt = {'106': 23, '109': 21, '110': 22}              # process table 工序代號

    code_to_assembleStep = read_all_p_part_process_code_p()
    print("code_to_assembleStep:", code_to_assembleStep)
    process_types = sorted(set(code_to_assembleStep.values()))

    #       0         1       2            3              4            5           6            7           8            9           10             11            12
    str2=['未備料', '備料中', '備料完成',   '等待組裝作業', '組裝進行中', '00/00/00', '檢驗進行中', '00/00/00', '雷射進行中', '00/00/00', '等待入庫作業', '入庫進行中',  '入庫完成']

    def safe_str(v, default=''):
      try:
        return '' if v is None else str(v)
      except Exception:
        return default

    _objects = s.query(P_Material).all()
    material_ids_all = [m.id for m in _objects]

    # 1) 篩選「該使用者、且 has_started=True」的未結束 P_Process 名單/計數
    counts_by_type = active_count_map_by_material_multi_P(
        s, material_ids_all,
        process_types=process_types,
        include_paused=False,           # 是否把暫停算在「未結束」內，False:不包括
        #only_user_id=None               # 全員
        only_user_id=_user_id,          # 只算該使用者本人（看你要哪種）
        has_started=True,               # 只找 has_started=True
    )
    print("start....")

    # 篩選「誰」正在該料號/該製程上有未結束(進行中或暫停中)的流程, 並將結果依「製程別(21/22/23) → 料號ID」分組，回傳每一組底下的使用者ID清單。
    user_ids_by_type = active_user_ids_by_material_multi(
        s, material_ids_all,
        process_types=(21, 22, 23),
        include_paused=True,
        #only_user_id=None,              # 全員名單
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
      process_records = material_record._process

      for assemble_record in material_record._assemble:   # loop_a_rec
        # 篩選登入者的製程紀錄
        user_proc_records = [p for p in process_records if (p.user_id == _user_id and not p.end_time or p.end_time !='')]

        if assemble_record.process_step_code==0 and not assemble_record.isAssembleStationShow:
           continue

        ### 相同登入者 ###

        # 依 work_num 判斷對應的 process_type
        work = assemble_record.work_num or ''
        target_pt = None
        if 'B109' in work:
            target_pt = 21
        elif 'B110' in work:
            target_pt = 22
        elif 'B106' in work:
            target_pt = 23

        matched_count = 0
        if target_pt is not None:
            # 這裡一定要是 list，不是數字！
            target_procs = [
                p for p in process_records
                if p.material_id == assemble_record.material_id
                and p.assemble_id == assemble_record.id
                and p.process_type == target_pt

                and p.user_id == _user_id

                and p.begin_time
                and (not p.end_time or p.end_time !='')
            ]

            matched_count = len(target_procs)

        if matched_count == 0 and not assemble_record.isAssembleStationShow:
          continue

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
        print("sssss index:",index)

        # 處理 show2_ok 的情況
        print("temp_show2_ok, temp_assemble_show2_ok:", temp_show2_ok, temp_assemble_show2_ok)
        if temp_show2_ok in [5, 7, 9] or temp_assemble_show2_ok in [5, 7, 9]:
          for temp2_assemble_record in assemble_records:
            if temp2_assemble_record.total_ask_qty_end in [1, 2, 3]:
              completed_qty = str(temp2_assemble_record.completed_qty)                  # 將數值轉換為字串
              date_parts = temp_assemble_process_str.split('/')                         # 分割 00/00/00 為 ['00', '00', '00']
              date_parts[temp2_assemble_record.total_ask_qty_end - 1] = completed_qty   # 替換對應位置
              temp_assemble_process_str = '/'.join(date_parts)                          # 合併回字串
        #

        work_num = safe_str(assemble_record.work_num)     # 可能為 ''（避免 None）
        code = work_num[1:] if len(work_num) >= 2 else work_num
        name = code_to_name.get(code, '')
        pt =code_to_pt.get(code, 0)

        ok, process_total = need_more_process_qty(k1=assemble_record.material_id, a1=assemble_record.id, t1=pt, must_qty=assemble_record.must_receive_end_qty, s=s)

        r = next(
          (p for p in user_proc_records
          if p.material_id == assemble_record.material_id and p.process_type == pt),
          None
        )

        def _norm_end_time(x):
          if x is None:
              return None
          if isinstance(x, str):
              x = x.strip()
              if x == "" or x == "0000-00-00 00:00:00":
                  return None
              return x
          # 若是 datetime 物件就直接回傳
          return x

        user_receive_qty = int((getattr(r, "process_work_time_qty", 0) or 0))

        _end_time = _norm_end_time(getattr(r, "end_time", None))
        user_is_show_last_time = _end_time is not None

        # 若有結束時間才顯示字串化的工時；沒有就給空字串
        user_last_time = getattr(r, "str_elapsedActive_time", "") if user_is_show_last_time else ""

        print("工序format_name:", format_name)
        print("assemble_record.input_end_disable:", assemble_record.input_end_disable)

        _object = {
          'index': index,                                   #agv送料序號
          'id': material_record.id,                         #訂單編號
          'order_num': material_record.order_num,           ## 訂單編號
          'material_num': material_record.material_num,     ## 物料編號
          'req_qty': material_record.material_qty,          ## 組裝區需求數量(訂單數量)
          'ask_qty': assemble_record.ask_qty,               ## 組裝區領取數量

          'assemble_work': format_name,                     #工序
          'assemble_process': '' if (num > 2 and not step_enable) else temp_assemble_process_str,
          'assemble_process_num': num,
          'assemble_id': assemble_record.id,
          'total_ask_qty_end': assemble_record.total_ask_qty_end,
          'process_step_code': assemble_record.process_step_code,

          'total_completed_qty': f"({assemble_record.total_completed_qty})",
          'total_completed_qty_num': process_total,

          #'must_receive_end_qty': assemble_record.ask_qty,                    ## 組裝區應完成數量
          'must_receive_end_qty': assemble_record.must_receive_end_qty,
          'abnormal_qty': assemble_record.abnormal_qty,                       ## 組裝區異常數量

          #'receive_qty': user_receive_qty,                                    ## 組裝區完成數量
          'receive_qty': assemble_record.completed_qty,                       ## 組裝區完成數量

          'delivery_date': material_record.material_delivery_date,            # 交期
          'delivery_qty': material_record.delivery_qty,                       # 現況數量
          'abnormal_qty': assemble_record.isAssembleFirstAlarm_qty if code == '109' else assemble_record.abnormal_qty,

          'total_assemble_qty': material_record.total_assemble_qty,           # 已(組裝）完成總數量

          'comment': cleaned_comment,                                         # 說明
          'isAssembleAlarm' : material_record.isAssembleAlarm,

          'isAssembleFirstAlarm' : assemble_record.isAssembleFirstAlarm,
          'isAssembleFirstAlarm_qty' : assemble_record.isAssembleFirstAlarm_qty,
          'alarm_enable' : assemble_record.alarm_enable,

          'whichStation' : material_record.whichStation,
          'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,   # true:組裝站製程3完成(最後製程)
          'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,   # true:組裝站製程3完成(最後製程)
          'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,   # true:組裝站製程3完成(最後製程)
          'isLackMaterial': material_record.isLackMaterial,
          'shortage_note': material_record.shortage_note,

          'isAssembleStationShow': bool(assemble_record.isAssembleStationShow==1),         # true:完成生產報工(按結束按鍵),
          'currentStartTime': assemble_record.currentStartTime,
          'tooltipVisible': False,
                                                                                                                      #顯示數字輸入欄位alarm
          'abnormal_tooltipVisible': False,
                                                                                                                    #顯示數字輸入欄位alarm
          'input_end_disable': assemble_record.input_end_disable,
          #'input_abnormal_disable': assemble_record.isAssembleFirstAlarm_qty if code == '110' else True,
          'input_abnormal_disable': assemble_record.input_abnormal_disable,
          'alarm_enable': assemble_record.alarm_enable,

          'process_step_enable': step_enable,

          'code': code,

          'isShowLastTime': user_is_show_last_time,
          'last_time': user_last_time,

          'assemble_count': len(material_record._assemble),

          'is_copied_from_id': assemble_record.is_copied_from_id,

          'create_at': assemble_record.create_at,
        }

        processed_records.add((order_num_id, format_name))
        _results.append(_object)
      # end loop_a_rec
    # end loop_m_rec

    print("kkkkk length:", len(_results), index)

    record_sum = (
        s.query(
          P_Assemble.material_id,
          func.coalesce(func.sum(cast(P_Assemble.completed_qty, Integer)), 0).label("sum_completed_qty")
        )
        .filter(P_Assemble.isAssembleStationShow == 1)
        .group_by(P_Assemble.material_id)
        .order_by(P_Assemble.material_id)
        .all()
    )

    all_zero_by_mid = {}
    for r in _results:
        mid  = str(r['id'])
        code = int((r.get('process_step_code') or 0))
        if mid not in all_zero_by_mid:
            all_zero_by_mid[mid] = True
        if code != 0:
            all_zero_by_mid[mid] = False

        for material_id, total in record_sum:
          if r['id']==material_id:
             r['total_completed_qty_num']=total

    filtered_results = []
    for row in _results:
        # 先處理 isAssembleStationShow==1 且該 material 的所有 step 都是 0 → 直接納入
        if int(row.get('isAssembleStationShow') or 0) == 1 and all_zero_by_mid.get(mid, False):
            filtered_results.append(row)
            index=index-1
            continue

        ptype = map_pt_from_step_code(int(row['process_step_code']))  # 21/22/23
        mid   = str(row['id'])

        # 該製程/料的使用者名單（list），挑出是否包含 _user_id
        ulist = pick_user_list(user_ids_by_type, ptype, mid)
        print("ulist:",ulist)
        if _user_id not in ulist:
          index=index-1
          continue  # 不是該 user 的「已開始」紀錄 → 略過

        # 3) 再套 end_ok 條件（必須 True 才留下）
        if not end_ok_flag(s, material_id=row['id'], process_step_code=int(row['process_step_code'])):
          index=index-1
          continue

        filtered_results.append(row)

    # ① step → pt 對應
    def _map_step_to_pt(step: int) -> int:
      return 21 if step == 3 else 22 if step == 2 else 23

    # ② 依 material_id + pt 加總所有 process.process_work_time_qty
    def count_all_by_mid_and_step(mid: int, step: int) -> int:
        pt = _map_step_to_pt(int(step or 0))
        total = (
            s.query(func.coalesce(func.sum(P_Process.process_work_time_qty), 0))
             .filter(P_Process.material_id == mid)
             .filter(P_Process.process_type == pt)
             .scalar()
        ) or 0
        return int(total)

    # 只回傳符合該 user 的 rows
    print("1.materials_and_assembles_by_user:", len(_results))

    s.close()

    temp_len = len(_results)
    print("getMaterialsAndAssemblesByUser, 總數: ", temp_len)
    print("2.materials_and_assembles_by_user:", len(_results))
    print("active_counts_all:", counts_by_type)
    print("active_user_ids_all:", user_ids_by_type)

    if (temp_len == 0):
      return_value = False

    # 先依 id（升冪）排一次
    _results.sort(key=lambda x: x.get('id') or 0)

    # 再依 create_at（降冪）排一次 → 穩定排序會保留同日期下的 id 排序
    _results.sort(key=lambda x: x.get('create_at') or datetime.min, reverse=True)

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


# 前端呼叫用的 API，回傳當前使用者在特定 assemble_id 清單上的計數
@getTable.route("/getCountsByAssembleIdsBegin", methods=['POST'])
def get_counts_by_assemble_ids_begin():
    data = request.json
    user_id = data["user_id"]
    assemble_ids = data.get("assemble_ids", [])  # e.g., [6, 38]
    s = Session()
    try:
        counts = active_count_map_by_assemble_multi(
            s,
            assemble_ids,
            process_types=(21, 22, 23),
            include_paused=False,     # 只算正在跑
            only_user_id=user_id,     # 只看本人
            has_started=True,         # 只看 has_started=True
        )
        return jsonify(success=True, counts=counts)
    finally:
        s.close()