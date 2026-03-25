import re
import random
from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import check_password_hash
from server.database.x_tables import User, Material, Assemble, Bom, Agv, Permission, Process, AbnormalCause, Setting, Session
from database.p_tables import P_Material, P_Assemble, P_Process, P_Part,P_AbnormalCause
from sqlalchemy import and_, or_, not_, func

from sqlalchemy.orm.exc import MultipleResultsFound

from sqlalchemy import func, cast, Integer

from collections import defaultdict

from datetime import datetime, timezone, timedelta
from datetime import datetime as dt

from zoneinfo import ZoneInfo

getTable = Blueprint('getTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


def get_val(row, key, default=None):
    """同時支援 dict 與 ORM 物件取值。"""
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


TPE = ZoneInfo("Asia/Taipei")
FMT = "%Y-%m-%d %H:%M:%S"


def now_tpe_aware():
    return datetime.now(TPE).replace(microsecond=0)


def now_tpe_str():
    return now_tpe_aware().strftime(FMT)


def seconds_to_hms_str(seconds: int) -> str:
    """將秒數轉換成 hh:mm:ss"""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:02}"


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

    if material_id is None or process_type is None or not user_id:
      return jsonify({
          "return_value": False,
          "message": "missing params: material_id/process_type/user_id"
      }), 400

    s = Session()

    material_record = s.query(Material).filter_by(id=material_id).first()

    """
    # ✅ 1) 同工單(同製程) 只允許一筆「未結束」的 active process
    #    ⚠️ 不要用 user_id 當條件，否則不同人會各自開一筆 → 造成同步/回寫混亂
    q = (
        s.query(Process)
          .filter(Process.material_id == int(material_id))
          .filter(Process.process_type == int(process_type))
          .filter(Process.end_time.is_(None))
    )
    # assemble_id 可能是 0 / None / 有值：有值就一起鎖定這張工單
    if assemble_id is not None:
        q = q.filter(Process.assemble_id == int(assemble_id))

    log = q.order_by(Process.id.desc()).first()
    """


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

        user_id = log.user_id,  # 這裡回傳「真正持有該 active 流程的人」
      )

    # 2) 沒有未結束流程 → 幫當前 user 新建
    new_log = Process(
      material_id=material_id,
      assemble_id=assemble_id,
      #user_id=user_id,
      process_type=process_type,
      begin_time=None,               # 由「開始」時再補
      end_time=None,
      elapsedActive_time=0,
      is_pause=True,                 # 進入即顯示「開始」
      has_started=False,
      pause_time=0,
      pause_started_at=None,

      user_id=str(user_id),
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


@getTable.route("/dialog2CloseProcessBegin", methods=["POST"])
def close_process_begin():
    print("dialog2CloseProcessBegin API....")

    data = request.get_json() or {}
    process_id   = data.get("process_id")
    elapsed_time = data.get("elapsed_time")
    receive_qty  = data.get("receive_qty", 0)
    alarm_enable = data.get("alarm_enable")
    alarm_message = data.get("alarm_message")
    isAssembleFirstAlarm = data.get("isAssembleFirstAlarm")
    assemble_id  = data.get("assemble_id")

    print("process_id:", process_id, "receive_qty:", receive_qty,
          "alarm_enable:", alarm_enable, "assemble_id:", assemble_id)

    if not process_id:
        return jsonify(success=False, message="missing process_id"), 400

    # rq
    try:
        rq = int(receive_qty or 0)
    except Exception:
        rq = 0

    TPE = ZoneInfo("Asia/Taipei")
    now_aw = datetime.now(TPE).replace(microsecond=0)

    s = Session()
    try:
        with s.begin():
            # ✅ 1) 鎖住 Process 這筆，避免兩個人同時 close
            log = (
                s.query(Process)
                 .filter(Process.id == int(process_id))
                 .with_for_update()
                 .first()
            )
            if not log:
                return jsonify(success=False, message="process not found"), 404

            # ✅ 2) 只要 end_time 有值就視為已關閉（避免重複加總/重複寫）
            if log.end_time is not None:
                return jsonify(
                    success=True,
                    message="already closed",
                    elapsed_time=int(log.elapsedActive_time or 0),
                    pause_time=int(log.pause_time or 0),
                    end_time=log.end_time,
                ), 200

            # ✅ 3) 若暫停中，先把最後一段暫停秒數補進 pause_time
            if getattr(log, "is_pause", False) and getattr(log, "pause_started_at", None):
                try:
                    ps = log.pause_started_at
                    if isinstance(ps, str):
                        ps = datetime.fromisoformat(ps)
                    if ps.tzinfo is None:
                        ps = ps.replace(tzinfo=TPE)

                    delta = int((now_aw - ps).total_seconds())
                    log.pause_time = (log.pause_time or 0) + max(delta, 0)
                except Exception as e:
                    print("close_process: pause_time accumulate failed:", e)
                finally:
                    log.pause_started_at = None

            # ✅ 4) 校正有效秒數（單向遞增）
            if elapsed_time is not None:
                try:
                    last_secs = int(elapsed_time)
                except Exception:
                    last_secs = int(log.elapsedActive_time or 0)
                cur_secs = int(log.elapsedActive_time or 0)
                log.elapsedActive_time = max(cur_secs, last_secs)

            # 文字欄位
            try:
                log.str_elapsedActive_time = seconds_to_hms_str(int(log.elapsedActive_time or 0))
            except Exception:
                pass

            # ✅ 5) 關閉：end_time、qty
            log.end_time = now_aw.strftime("%Y-%m-%d %H:%M:%S")

            # 建議：結束不是暫停
            log.is_pause = False
            log.pause_started_at = None

            log.process_work_time_qty = rq
            log.must_allOk_qty = rq

            # abnormal / normal
            if alarm_enable:
                log.normal_work_time = 1
                log.abnormal_cause_message = ""
            elif (not alarm_enable) and isAssembleFirstAlarm:
                log.normal_work_time = 1
                log.abnormal_cause_message = ""
            else:
                log.normal_work_time = 0
                log.abnormal_cause_message = alarm_message or ""

            # ✅ 6) 更新 Assemble 的已完成總數（total_ask_qty_end）
            #    只做「加總」，絕對不要在這裡動 must_receive_end_qty（避免 8 -> 10）
            is_completed = False
            total_completed = None
            must_qty = None

            if assemble_id is not None and rq > 0:
                asm = (
                    s.query(Assemble)
                     .filter(Assemble.id == int(assemble_id))
                     .with_for_update()
                     .first()
                )
                if asm:
                    # ✅ 用 must_receive_end_qty 判斷是否完成（你異常調整後是 8 就以 8 為準）
                    must_qty = int(asm.must_receive_end_qty or 0)

                    cur_total = int(asm.total_ask_qty_end or 0)
                    new_total = cur_total + rq
                    asm.total_ask_qty_end = new_total

                    total_completed = new_total
                    is_completed = (must_qty > 0 and new_total >= must_qty)

        # with s.begin() 自動 commit
        return jsonify(
            success=True,
            end_time=log.end_time,
            elapsed_time=int(log.elapsedActive_time or 0),
            pause_time=int(log.pause_time or 0),
            is_completed=is_completed,
            total_completed=total_completed,
            must_qty=must_qty
        )

    except Exception as e:
        s.rollback()
        print("dialog2CloseProcessBegin error:", e)
        return jsonify(success=False, message=str(e)), 500
    finally:
        s.close()


# -----dialog2~MP for 前端 MaterialListForProcess.vue -------------------------------------------------------------


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