from sqlalchemy import MetaData, Table, select, func, inspect, or_

from database.tables import Session


def load_table(session, table_name):
    metadata = MetaData()
    return Table(table_name, metadata, autoload_with=session.get_bind())


def table_exists(session, table_name):
    return inspect(session.get_bind()).has_table(table_name)


def dt_to_str(v):
    if not v:
        return None

    try:
        return v.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(v)


def get_warehouse_archive_history(source="not_restored", keyword="", archive_batch_no=""):
    session = Session()

    try:
        results = []
        keyword = (keyword or "").strip()
        archive_batch_no = (archive_batch_no or "").strip()

        def append_line(
            *,
            line,
            line_name,
            material_archive_table_name,
            process_archive_table_name,
        ):
            if not table_exists(session, material_archive_table_name):
                return

            mat_t = load_table(session, material_archive_table_name)
            proc_t = load_table(session, process_archive_table_name) if table_exists(session, process_archive_table_name) else None

            q = select(mat_t)

            if source == "not_restored" and "restored_at" in mat_t.c:
                q = q.where(mat_t.c.restored_at.is_(None))
            elif source == "restored" and "restored_at" in mat_t.c:
                q = q.where(mat_t.c.restored_at.isnot(None))

            if archive_batch_no and "archive_batch_no" in mat_t.c:
                q = q.where(mat_t.c.archive_batch_no == archive_batch_no)

            if keyword:
                like_value = f"%{keyword}%"
                conds = []

                for col_name in ["order_num", "material_num", "material_comment", "archive_batch_no"]:
                    if col_name in mat_t.c:
                        conds.append(mat_t.c[col_name].like(like_value))

                if conds:
                    q = q.where(or_(*conds))

            if "archived_at" in mat_t.c:
                q = q.order_by(mat_t.c.archived_at.desc(), mat_t.c.id.desc())
            else:
                q = q.order_by(mat_t.c.id.desc())

            rows = session.execute(q).mappings().all()

            for r in rows:
                material_id = r.get("id")
                batch_no = r.get("archive_batch_no")

                total_allOk_qty = 0

                if proc_t is not None and "process_type" in proc_t.c:
                    total_allOk_qty = session.execute(
                        select(func.coalesce(func.sum(proc_t.c.process_work_time_qty), 0))
                        .where(proc_t.c.material_id == material_id)
                        .where(proc_t.c.archive_batch_no == batch_no)
                        .where(proc_t.c.process_type == 31)
                    ).scalar() or 0

                results.append({
                    "line": line,
                    "line_name": line_name,
                    "id": material_id,
                    "material_id": material_id,
                    "archive_batch_no": batch_no,

                    "order_num": r.get("order_num", ""),
                    "material_num": r.get("material_num", ""),
                    "comment": r.get("material_comment", ""),

                    "req_qty": int(r.get("material_qty", 0) or 0),
                    "delivery_qty": int(r.get("delivery_qty", 0) or 0),
                    "total_delivery_qty": int(r.get("total_delivery_qty", 0) or 0),
                    "total_allOk_qty": int(total_allOk_qty or 0),

                    "delivery_date": dt_to_str(r.get("material_delivery_date")),
                    "material_date": dt_to_str(r.get("material_date")),

                    "archived_at": dt_to_str(r.get("archived_at")),
                    "archived_by": r.get("archived_by", ""),

                    "restored_at": dt_to_str(r.get("restored_at")),
                    "restored_by": r.get("restored_by", ""),

                    "can_restore": False if r.get("restored_at") else True,
                })

        append_line(
            line="assemble",
            line_name="組裝線",
            material_archive_table_name="material_archive",
            process_archive_table_name="process_archive",
        )

        append_line(
            line="process",
            line_name="加工線",
            material_archive_table_name="p_material_archive",
            process_archive_table_name="p_process_archive",
        )

        results.sort(
            key=lambda x: (
                x.get("archived_at") or "",
                x.get("archive_batch_no") or "",
                int(x.get("id") or 0),
            ),
            reverse=True,
        )

        for i, row in enumerate(results, start=1):
            row["index"] = i

        return {
            "success": True,
            "status": len(results) > 0,
            "items": results,
        }

    except Exception as e:
        return {
            "success": False,
            "status": False,
            "error": str(e),
            "items": [],
        }

    finally:
        session.close()