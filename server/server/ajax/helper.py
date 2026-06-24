import datetime
from datetime import datetime as dt

from sqlalchemy import func, or_

from database.tables import Material, Assemble, Process, Session
from database.tables import default_process_steps

from zoneinfo import ZoneInfo


TPE = ZoneInfo("Asia/Taipei")


# ------------------------------------------------------------------


def fmt_hhmmss(seconds: int):
    seconds = max(0, int(seconds or 0))
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_dt_maybe_aw2(value):
    """
    把 value(可能是 str/datetime/None) 轉成 Asia/Taipei 的 aware datetime。
    若無法解析回傳 None。
    """
    if value in (None, "", "None"):
        return None

    parsed_dt = None

    # 已是 datetime
    if isinstance(value, dt):
        parsed_dt = value
    else:
        s = str(value).strip()

        # 常見格式先試
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                parsed_dt = dt.strptime(s, fmt)
                break
            except ValueError:
                pass

        # 仍然不行再用 dateutil
        if parsed_dt is None:
            try:
                from dateutil import parser as dateparser
                parsed_dt = dateparser.parse(s)
            except Exception:
                return None

    # 補上/轉成 TPE 時區
    if parsed_dt.tzinfo is None:
        return parsed_dt.replace(tzinfo=TPE)
    else:
        return parsed_dt.astimezone(TPE)


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


def parse_dt_maybe(v):
    '''
    把 v 轉成 datetime；支援 'YYYY-MM-DD HH:MM:SS[.ffffff]'、'YYYY-MM-DDTHH:MM:SS[.ffffff]'、結尾 'Z'。失敗回 None。
    '''
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


def safe_str(v, default=''):
  try:
      return '' if v is None else str(v)
  except Exception:
      return default


def _checked_ids(process_steps, group_name):
    return [
        int(x.get("id"))
        for x in (process_steps or {}).get(group_name, [])
        if x.get("checked") and not x.get("deleted", False) and x.get("id") is not None
    ]


def release_b109_batch_to_b110(session, material_id):
    """
    B109 組裝批次釋放到 B110 檢驗。

    規則：
    1. 只看 process_steps['assemble'] 目前 checked 的組裝工序。
    2. 每個 schedule_id 取最大可釋放數量，避免剩餘補工序 0 擋住 min。
    3. release_qty = 各組裝工序可釋放數量的最小值。
    4. release_qty > 0 時，依 process_steps['check'] 建立 B110 批次檢驗列。
    5. 原始 B110 只當 template，不顯示在 Begin。
    6. B109 total_ask_qty_end 作為「已釋放到 B110 的數量」。
    """

    def safe_str(v):
        try:
            return "" if v is None else str(v).strip()
        except Exception:
            return ""

    material = session.query(Material).filter(Material.id == material_id).first()
    if not material:
        return {
            "released": False,
            "release_qty": 0,
            "created_ids": [],
            "message": "material not found"
        }

    process_steps = material.process_steps or default_process_steps()

    assemble_ids = _checked_ids(process_steps, "assemble")
    check_ids = _checked_ids(process_steps, "check")

    if not assemble_ids:
        return {
            "released": False,
            "release_qty": 0,
            "created_ids": [],
            "message": "no assemble steps"
        }

    if not check_ids:
        return {
            "released": False,
            "release_qty": 0,
            "created_ids": [],
            "message": "no check steps"
        }

    # ------------------------------------------------------------
    # 1) 只抓有完成 Process 的 B109 rows
    # ------------------------------------------------------------
    b109_rows = (
        session.query(Assemble)
        .join(Process, Process.assemble_id == Assemble.id)
        .filter(Assemble.material_id == material_id)
        .filter(Assemble.work_num == "B109")
        .filter(Assemble.schedule_id.isnot(None))
        .filter(Assemble.schedule_id > 0)
        .filter(Process.material_id == material_id)
        .filter(Process.process_type == 21)
        .filter(Process.has_started.is_(True))
        .filter(Process.end_time.isnot(None))
        .filter(Process.end_time != "")
        .group_by(Assemble.id)
        .order_by(Assemble.schedule_id.asc(), Assemble.id.asc())
        .all()
    )

    print(
        "b109_rows:",
        [(r.id, r.schedule_id, r.must_receive_qty, r.total_ask_qty_end, r.reason) for r in b109_rows]
    )

    if not b109_rows:
        return {
            "released": False,
            "release_qty": 0,
            "created_ids": [],
            "message": "no B109 rows"
        }

    #
    # ✅ 只要還有任何 B109 未完成，就不能釋放 B110
    # 包含 a1[組裝]-異常
    remaining_b109_not_done = (
        session.query(Assemble)
        .filter(Assemble.material_id == material_id)
        .filter(Assemble.work_num == "B109")
        .filter(Assemble.process_step_code > 0)
        .filter(Assemble.schedule_id.isnot(None))
        .filter(Assemble.schedule_id > 0)
        .filter(or_(Assemble.reason.is_(None), Assemble.reason != "B109_RELEASED"))
        .all()
    )

    if remaining_b109_not_done:
        return {
            "released": False,
            "release_qty": 0,
            "created_ids": [],
            "remaining_b109_ids": [r.id for r in remaining_b109_not_done],
            "message": "B109 still active, do not release B110"
        }
    #

    #
    # ------------------------------------------------------------
    # 異常返工：B109[異常] 完成後，只釋放它自己的 B110[異常]
    # 不要走一般 B109_RELEASE_BATCH 建立新 B110
    # ------------------------------------------------------------
    abnormal_b109_ids = [
        int(r.id)
        for r in b109_rows
        if safe_str(getattr(r, "reason", "")) == "異常返工"
    ]

    if abnormal_b109_ids:
        abnormal_b110_rows = (
            session.query(Assemble)
            .filter(Assemble.material_id == material_id)
            .filter(Assemble.work_num == "B110")
            .filter(Assemble.is_copied_from_id.in_(abnormal_b109_ids))
            .filter(Assemble.reason == "異常返工")
            .filter(Assemble.process_step_code > 0)
            .all()
        )

        if abnormal_b110_rows:
            created_ids = []

            for row in abnormal_b110_rows:
                row.isAssembleStationShow = True
                row.isWarehouseStationShow = False
                row.input_disable = False
                row.input_end_disable = False
                row.input_allOk_disable = False
                row.input_abnormal_disable = False
                row.show1_ok = 1
                row.show2_ok = 5
                row.show3_ok = 5
                row.reason = "異常返工"
                created_ids.append(row.id)

            for row in b109_rows:
                if int(row.id) in abnormal_b109_ids:
                    row.process_step_code = 0
                    row.isAssembleStationShow = False
                    row.input_disable = True
                    row.input_end_disable = True
                    row.input_abnormal_disable = True

            material.isAssembleStation3TakeOk = False

            return {
                "released": True,
                "release_qty": sum(int(r.must_receive_qty or 0) for r in abnormal_b110_rows),
                "created_ids": created_ids,
                "updated_b109_ids": abnormal_b109_ids,
                "message": "released abnormal B109 to abnormal B110"
            }
    #

    # ------------------------------------------------------------
    # 2) 計算每個 schedule_id 可釋放數量
    # ------------------------------------------------------------
    available_by_schedule = {}

    for row in b109_rows:
        sid = int(row.schedule_id or 0)

        if sid not in assemble_ids:
            continue

        done_qty = (
            session.query(func.coalesce(func.sum(Process.process_work_time_qty), 0))
            .filter(Process.material_id == material_id)
            .filter(Process.assemble_id == row.id)
            .filter(Process.process_type == 21)
            .filter(Process.has_started.is_(True))
            .filter(Process.end_time.isnot(None))
            .filter(Process.end_time != "")
            .scalar()
        ) or 0

        done_qty = int(done_qty or 0)

        released_qty = int(getattr(row, "total_ask_qty_end", 0) or 0)

        # ⭐ 原始排程的 total_ask_qty_end 可能是 1，不代表已釋放
        if safe_str(getattr(row, "reason", "")) != "B109_RELEASED":
            released_qty = 0

        available_qty = max(0, done_qty - released_qty)

        available_by_schedule[sid] = max(
            int(available_by_schedule.get(sid, 0) or 0),
            available_qty
        )

    if any(int(available_by_schedule.get(sid, 0) or 0) <= 0 for sid in assemble_ids):
        return {
            "released": False,
            "release_qty": 0,
            "created_ids": [],
            "available_by_schedule": available_by_schedule,
            "message": "no releasable B109 batch"
        }

    release_qty = min(int(available_by_schedule[sid] or 0) for sid in assemble_ids)

    if release_qty <= 0:
        return {
            "released": False,
            "release_qty": 0,
            "created_ids": [],
            "available_by_schedule": available_by_schedule,
            "message": "release_qty <= 0"
        }

    # ------------------------------------------------------------
    # 3) 關掉原始 B110 template rows
    #    原始 B110 不應顯示在 Begin，只保留當 template
    # ------------------------------------------------------------
    original_b110_rows = (
        session.query(Assemble)
        .filter(Assemble.material_id == material_id)
        .filter(Assemble.work_num == "B110")
        #.filter(Assemble.reason != "B109_RELEASE_BATCH")
        .filter(or_(
            Assemble.reason.is_(None),
            Assemble.reason == "",
            ~Assemble.reason.in_(["B109_RELEASE_BATCH", "異常返工"])
        ))
        .all()
    )

    for row in original_b110_rows:
        row.process_step_code = 0
        row.isAssembleStationShow = False
        row.input_disable = True
        row.input_end_disable = True
        row.input_abnormal_disable = True

    # ------------------------------------------------------------
    # 4) 找 B110 template
    # ------------------------------------------------------------
    b110_template = (
        session.query(Assemble)
        .filter(Assemble.material_id == material_id)
        .filter(Assemble.work_num == "B110")
        .order_by(Assemble.id.asc())
        .first()
    )

    if not b110_template:
        b110_template = b109_rows[0]

    now_str_value = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------
    # 5) 建立 B110 批次檢驗 rows
    # ------------------------------------------------------------
    created_ids = []
    base_new_row = None

    for sid in check_ids:
        new_row = Assemble(
            material_id=material.id,
            material_num=material.material_num,
            material_comment=material.material_comment,

            seq_num=getattr(b110_template, "seq_num", 20) or 20,
            work_num="B110",
            process_step_code=2,

            Incoming1_Abnormal=getattr(b110_template, "Incoming1_Abnormal", "") or "",

            must_receive_qty=release_qty,
            ask_qty=release_qty,
            total_ask_qty=release_qty,
            total_ask_qty_end=0,
            must_receive_end_qty=release_qty,

            abnormal_qty=0,
            user_id="",
            writer_id=None,
            write_date=None,

            good_qty=0,
            total_good_qty=0,
            non_good_qty=0,
            meinh_qty=0,
            completed_qty=0,
            total_completed_qty=0,
            allOk_qty=0,

            reason="B109_RELEASE_BATCH",
            confirm_comment="",
            is_assemble_ok=0,

            currentStartTime=None,
            currentEndTime=None,

            input_disable=False,
            input_end_disable=False,
            input_allOk_disable=False,
            input_abnormal_disable=False,

            isAssembleStationShow=True,
            isWarehouseStationShow=False,

            alarm_enable=True,
            alarm_message="",

            isAssembleFirstAlarm=True,
            isAssembleFirstAlarm_message="",
            isAssembleFirstAlarm_qty=0,

            whichStation=getattr(material, "whichStation", 2) or 2,

            show1_ok=1,
            show2_ok=5,
            show3_ok=5,

            update_time=now_str_value,
            create_at=now_str_value,

            schedule_id=sid,
            is_copied_from_id=base_new_row.id if base_new_row else None,
        )

        session.add(new_row)
        session.flush()

        if base_new_row is None:
            base_new_row = new_row

        created_ids.append(new_row.id)

    # ------------------------------------------------------------
    # 6) 回寫 B109 已釋放數量，並關閉已完成/已釋放的 B109
    # ------------------------------------------------------------
    updated_b109_ids = []

    for row in b109_rows:
        sid = int(row.schedule_id or 0)

        if sid not in assemble_ids:
            continue

        done_qty = (
            session.query(func.coalesce(func.sum(Process.process_work_time_qty), 0))
            .filter(Process.material_id == material_id)
            .filter(Process.assemble_id == row.id)
            .filter(Process.process_type == 21)
            .filter(Process.has_started.is_(True))
            .filter(Process.end_time.isnot(None))
            .filter(Process.end_time != "")
            .scalar()
        ) or 0

        done_qty = int(done_qty or 0)

        released_qty = int(getattr(row, "total_ask_qty_end", 0) or 0)

        if safe_str(getattr(row, "reason", "")) != "B109_RELEASED":
            released_qty = 0

        available_qty = max(0, done_qty - released_qty)

        if available_qty < release_qty:
            continue

        row.total_ask_qty_end = released_qty + release_qty
        row.reason = "B109_RELEASED"

        updated_b109_ids.append(row.id)

        if done_qty <= int(row.total_ask_qty_end or 0):
            row.process_step_code = 0
            row.isAssembleStationShow = False
            row.input_disable = True
            row.input_end_disable = True
            row.input_abnormal_disable = True

            # ⭐ 同 schedule_id 的剩餘補工序 row 一起關掉
            sibling_rows = (
                session.query(Assemble)
                .filter(Assemble.material_id == material_id)
                .filter(Assemble.work_num == "B109")
                .filter(Assemble.schedule_id == row.schedule_id)
                .filter(Assemble.id != row.id)
                .filter(Assemble.process_step_code > 0)
                .all()
            )

            for sib in sibling_rows:
                sib.process_step_code = 0
                sib.isAssembleStationShow = False
                sib.input_disable = True
                sib.input_end_disable = True
                sib.input_abnormal_disable = True
                sib.reason = "B109_RELEASED"

    material.isAssembleStation3TakeOk = False

    return {
        "released": True,
        "release_qty": release_qty,
        "created_ids": created_ids,
        "updated_b109_ids": updated_b109_ids,
        "available_by_schedule": available_by_schedule,
        "message": f"released B109 batch qty={release_qty} to B110"
    }



def sync_assemble_schedule_rows(session, material_id, process_steps, qty=None):
    material = session.query(Material).filter(Material.id == material_id).first()
    if not material:
        print("material not found:", material_id)
        return

    process_steps = process_steps or default_process_steps()

    all_rows = (
        session.query(Assemble)
        .filter(Assemble.material_id == material_id)
        .all()
    )

    def get_base_by_work_num(work_num):
        for row in all_rows:
            if row.is_copied_from_id is None and (row.work_num or '').strip() == work_num:
                return row
        return None

    def get_any_template_base():
        for row in all_rows:
            if row.is_copied_from_id is None:
                return row
        return all_rows[0] if all_rows else None

    def build_base_row_from_template(template, work_num, process_step_code):
        new_base = Assemble(
            material_id=material.id,
            material_num=material.material_num,
            material_comment=material.material_comment,
            seq_num=getattr(template, 'seq_num', 10) if template else 10,
            work_num=work_num,
            process_step_code=process_step_code,
            Incoming1_Abnormal=getattr(template, 'Incoming1_Abnormal', '') if template else '',
            must_receive_qty=getattr(template, 'must_receive_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            ask_qty=getattr(template, 'ask_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            total_ask_qty=getattr(template, 'total_ask_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            total_ask_qty_end=getattr(template, 'total_ask_qty_end', 0) if template else 0,
            must_receive_end_qty=getattr(template, 'must_receive_end_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            abnormal_qty=getattr(template, 'abnormal_qty', 0) if template else 0,
            user_id=getattr(template, 'user_id', material.isOpenEmpId) if template else material.isOpenEmpId,
            writer_id=getattr(template, 'writer_id', None) if template else None,
            write_date=getattr(template, 'write_date', None) if template else None,
            good_qty=getattr(template, 'good_qty', 0) if template else 0,
            total_good_qty=getattr(template, 'total_good_qty', 0) if template else 0,
            non_good_qty=getattr(template, 'non_good_qty', 0) if template else 0,
            meinh_qty=getattr(template, 'meinh_qty', 0) if template else 0,
            completed_qty=getattr(template, 'completed_qty', 0) if template else 0,
            total_completed_qty=getattr(template, 'total_completed_qty', 0) if template else 0,
            allOk_qty=getattr(template, 'allOk_qty', 0) if template else 0,
            reason='',
            confirm_comment=getattr(template, 'confirm_comment', '') if template else '',
            is_assemble_ok=getattr(template, 'is_assemble_ok', 0) if template else 0,
            currentStartTime=None,
            currentEndTime=None,
            input_disable=True,
            input_end_disable=True,
            input_allOk_disable=True,
            input_abnormal_disable=True,
            isAssembleStationShow=False,
            isWarehouseStationShow=False,
            alarm_enable=getattr(template, 'alarm_enable', 1) if template else 1,
            alarm_message=getattr(template, 'alarm_message', '') if template else '',
            isAssembleFirstAlarm=getattr(template, 'isAssembleFirstAlarm', 1) if template else 1,
            isAssembleFirstAlarm_message=getattr(template, 'isAssembleFirstAlarm_message', '') if template else '',
            isAssembleFirstAlarm_qty=getattr(template, 'isAssembleFirstAlarm_qty', 0) if template else 0,
            whichStation=getattr(template, 'whichStation', material.whichStation) if template else material.whichStation,
            show1_ok=0,
            show2_ok=0,
            show3_ok=0,
            schedule_id=None,
            is_copied_from_id=None
        )
        session.add(new_base)
        session.flush()
        return new_base

    def close_schedule_row(row):
        row.schedule_id = None
        row.process_step_code = 0
        row.isAssembleStationShow = False
        row.isWarehouseStationShow = False
        row.input_disable = True
        row.input_end_disable = True
        row.input_allOk_disable = True
        row.input_abnormal_disable = True
        row.show1_ok = 0
        row.show2_ok = 0
        row.show3_ok = 0
        row.must_receive_qty = 0
        row.ask_qty = 0
        row.total_ask_qty = 0
        row.must_receive_end_qty = 0
        row.total_ask_qty_end = 0
        row.currentStartTime = None
        row.currentEndTime = None

    def apply_schedule_row(row, sid, process_step_code, base_qty, work_num, base):
        row.schedule_id = sid
        row.process_step_code = process_step_code
        row.work_num = work_num
        row.material_num = base.material_num
        row.material_comment = base.material_comment
        row.seq_num = base.seq_num

        row.input_disable = False
        row.input_end_disable = False
        row.input_allOk_disable = False
        row.input_abnormal_disable = False

        row.isAssembleStationShow = True
        row.isWarehouseStationShow = False

        row.show1_ok = 1
        if work_num == "B110":
            row.show2_ok = 5
            row.show3_ok = 5
        else:
            row.show2_ok = 3
            row.show3_ok = 3

        row.must_receive_qty = base_qty
        row.ask_qty = base_qty
        row.total_ask_qty = base_qty
        row.must_receive_end_qty = base_qty

        if qty is not None and qty != '':
            row.abnormal_qty = int(base_qty or 0)
            row.reason = '異常返工'
        else:
            if row.reason == '異常返工':
                row.reason = ''

    def ensure_base_row(work_num, process_step_code, target_steps):
        if work_num == 'B109':
            process_type = 21
        elif work_num == 'B110':
            process_type = 22
        else:
            process_type = None

        completed_schedule_ids = set()

        if process_type:
            completed_schedule_ids = {
                int(r[0])
                for r in (
                    session.query(Assemble.schedule_id)
                    .join(Process, Process.assemble_id == Assemble.id)
                    .filter(Assemble.material_id == material_id)
                    .filter(Assemble.work_num == work_num)
                    .filter(Assemble.schedule_id.isnot(None))
                    .filter(Process.process_type == process_type)
                    .filter(Process.has_started.is_(True))
                    .filter(Process.end_time.isnot(None))
                    .filter(Process.end_time != '')
                    .all()
                )
                if r[0] is not None
            }

        checked_ids = [
            int(x.get('id'))
            for x in (target_steps or [])
            if (
                x.get('checked')
                and not x.get('deleted', False)
                and x.get('id') is not None
                and int(x.get('id')) not in completed_schedule_ids
            )
        ]

        print("sync schedule:", material_id, work_num, checked_ids)

        base = get_base_by_work_num(work_num)

        if not base and checked_ids:
            template = get_any_template_base()
            base = build_base_row_from_template(template, work_num, process_step_code)
            all_rows.append(base)

        if not base:
            return

        base_qty = (
            qty
            or material.total_delivery_qty
            or material.delivery_qty
            or material.material_qty
            or 0
        )
        base_qty = int(base_qty or 0)

        schedule_rows = (
            session.query(Assemble)
            .filter(Assemble.material_id == material_id)
            .filter(Assemble.work_num == work_num)
            .filter(or_(Assemble.reason.is_(None), Assemble.reason != '異常返工'))
            .order_by(Assemble.id)
            .all()
        )

        usable_rows = [base] + [r for r in schedule_rows if r.id != base.id]

        for idx, sid in enumerate(checked_ids):
            if idx < len(usable_rows):
                row = usable_rows[idx]
            else:
                row = Assemble(
                    material_id=base.material_id,
                    material_num=base.material_num,
                    material_comment=base.material_comment,
                    seq_num=base.seq_num,
                    work_num=base.work_num,
                    process_step_code=base.process_step_code,
                    Incoming1_Abnormal=base.Incoming1_Abnormal,
                    must_receive_qty=base.must_receive_qty,
                    ask_qty=base.ask_qty,
                    total_ask_qty=base.total_ask_qty,
                    total_ask_qty_end=base.total_ask_qty_end,
                    must_receive_end_qty=base.must_receive_end_qty,
                    abnormal_qty=base.abnormal_qty,
                    user_id=base.user_id,
                    writer_id=base.writer_id,
                    write_date=base.write_date,
                    good_qty=base.good_qty,
                    total_good_qty=base.total_good_qty,
                    non_good_qty=base.non_good_qty,
                    meinh_qty=base.meinh_qty,
                    completed_qty=base.completed_qty,
                    total_completed_qty=base.total_completed_qty,
                    allOk_qty=base.allOk_qty,
                    reason='',
                    confirm_comment=base.confirm_comment,
                    is_assemble_ok=base.is_assemble_ok,
                    currentStartTime=None,
                    currentEndTime=None,
                    input_disable=False,
                    input_end_disable=False,
                    input_allOk_disable=False,
                    input_abnormal_disable=False,
                    isAssembleStationShow=True,
                    isWarehouseStationShow=False,
                    alarm_enable=base.alarm_enable,
                    alarm_message=base.alarm_message,
                    isAssembleFirstAlarm=base.isAssembleFirstAlarm,
                    isAssembleFirstAlarm_message=base.isAssembleFirstAlarm_message,
                    isAssembleFirstAlarm_qty=base.isAssembleFirstAlarm_qty,
                    whichStation=base.whichStation,
                    show1_ok=1,
                    show2_ok=5 if work_num == "B110" else 3,
                    show3_ok=5 if work_num == "B110" else 3,
                    schedule_id=sid,
                    is_copied_from_id=base.id
                )
                session.add(row)
                session.flush()
                usable_rows.append(row)

            apply_schedule_row(row, sid, process_step_code, base_qty, work_num, base)

        for row in usable_rows[len(checked_ids):]:
            close_schedule_row(row)

    ensure_base_row(
        work_num='B109',
        process_step_code=3,
        target_steps=process_steps.get('assemble', [])
    )

    ensure_base_row(
        work_num='B110',
        process_step_code=2,
        target_steps=process_steps.get('check', [])
    )

