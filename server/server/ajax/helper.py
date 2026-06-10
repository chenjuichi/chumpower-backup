import datetime
from datetime import datetime as dt

from sqlalchemy import func

from database.tables import Material, Assemble, Process, Session
from database.tables import default_process_steps


# ------------------------------------------------------------------


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
        .filter(Assemble.reason != "B109_RELEASE_BATCH")
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


