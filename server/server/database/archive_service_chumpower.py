from datetime import datetime

from sqlalchemy import MetaData, Table, select, insert, delete, update, func, inspect

from database.tables import (
    Session,
    Material,
    Bom,
    Assemble,
    Process,
    Product,
)

from database.p_tables import (
    P_Material,
    P_Bom,
    P_Assemble,
    P_Process,
    P_Product,
)


def make_archive_batch_no():
    return datetime.now().strftime("ARCH%Y%m%d%H%M%S")


def normalize_ids(values):
    ids = []

    for x in values or []:
        try:
            v = int(x)
            if v > 0:
                ids.append(v)
        except Exception:
            pass

    return sorted(set(ids))


def load_table(session, table_name):
    metadata = MetaData()
    return Table(table_name, metadata, autoload_with=session.get_bind())


def table_exists(session, table_name):
    return inspect(session.get_bind()).has_table(table_name)


def common_columns(source_table, archive_table):
    archive_cols = {
        "archive_id",
        "archive_batch_no",
        "archived_at",
        "archived_by",
        "restored_at",
        "restored_by",
    }

    return [
        c for c in source_table.c.keys()
        if c in archive_table.c.keys()
        and c not in archive_cols
    ]


def archive_table_rows(
    session,
    *,
    source_table,
    archive_table_name,
    where_clause,
    archive_batch_no,
    archived_by,
):
    archive_table = load_table(session, archive_table_name)

    cols = common_columns(source_table, archive_table)

    rows = session.execute(
        select(source_table).where(where_clause)
    ).mappings().all()

    if not rows:
        return 0

    now = datetime.now()
    insert_rows = []

    for r in rows:
        data = {c: r.get(c) for c in cols}
        data["archive_batch_no"] = archive_batch_no
        data["archived_at"] = now
        data["archived_by"] = archived_by
        data["restored_at"] = None
        data["restored_by"] = None
        insert_rows.append(data)

    session.execute(insert(archive_table), insert_rows)

    return len(insert_rows)


def restore_table_rows(
    session,
    *,
    archive_table_name,
    target_table,
    archive_batch_no,
    material_ids,
    is_material_table=False,
):
    archive_table = load_table(session, archive_table_name)

    archive_cols = {
        "archive_id",
        "archive_batch_no",
        "archived_at",
        "archived_by",
        "restored_at",
        "restored_by",
    }

    cols = [
        c for c in target_table.c.keys()
        if c in archive_table.c.keys()
        and c not in archive_cols
    ]

    if not cols:
        return 0

    q = select(archive_table).where(
        archive_table.c.archive_batch_no == archive_batch_no
    )

    if "restored_at" in archive_table.c:
        q = q.where(archive_table.c.restored_at.is_(None))

    if is_material_table:
        q = q.where(archive_table.c.id.in_(material_ids))
    else:
        q = q.where(archive_table.c.material_id.in_(material_ids))

    rows = session.execute(q).mappings().all()

    if not rows:
        return 0

    insert_rows = []

    for r in rows:
        insert_rows.append({c: r.get(c) for c in cols})

    # 防止正式表已有相同 id
    if "id" in target_table.c:
        ids = [r.get("id") for r in insert_rows if r.get("id") is not None]

        if ids:
            exists_count = session.execute(
                select(func.count())
                .select_from(target_table)
                .where(target_table.c.id.in_(ids))
            ).scalar() or 0

            if exists_count > 0:
                raise Exception(f"{target_table.name} 已存在相同 id，不能重複還原")

    session.execute(insert(target_table), insert_rows)

    return len(insert_rows)


def mark_archive_restored(
    session,
    *,
    archive_table_name,
    archive_batch_no,
    material_ids,
    restored_by,
    is_material_table=False,
):
    archive_table = load_table(session, archive_table_name)

    q = update(archive_table).where(
        archive_table.c.archive_batch_no == archive_batch_no
    )

    if is_material_table:
        q = q.where(archive_table.c.id.in_(material_ids))
    else:
        q = q.where(archive_table.c.material_id.in_(material_ids))

    values = {
        "restored_at": datetime.now(),
        "restored_by": restored_by,
    }

    session.execute(q.values(**values))


def archive_materials(material_ids, archived_by="system", archive_batch_no=None):
    session = Session()

    try:
        material_ids = normalize_ids(material_ids)

        if not material_ids:
            return {
                "success": False,
                "error": "material_ids is empty",
            }

        required_tables = [
            "material_archive",
            "bom_archive",
            "assemble_archive",
            "process_archive",
            "product_archive",
        ]

        for table_name in required_tables:
            if not table_exists(session, table_name):
                return {
                    "success": False,
                    "error": f"缺少 archive table: {table_name}",
                }

        archive_batch_no = archive_batch_no or make_archive_batch_no()

        material_count = archive_table_rows(
            session,
            source_table=Material.__table__,
            archive_table_name="material_archive",
            where_clause=Material.__table__.c.id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        bom_count = archive_table_rows(
            session,
            source_table=Bom.__table__,
            archive_table_name="bom_archive",
            where_clause=Bom.__table__.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        assemble_count = archive_table_rows(
            session,
            source_table=Assemble.__table__,
            archive_table_name="assemble_archive",
            where_clause=Assemble.__table__.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        process_count = archive_table_rows(
            session,
            source_table=Process.__table__,
            archive_table_name="process_archive",
            where_clause=Process.__table__.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        product_count = archive_table_rows(
            session,
            source_table=Product.__table__,
            archive_table_name="product_archive",
            where_clause=Product.__table__.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        # 刪除順序：子表 → 父表
        session.execute(delete(Product.__table__).where(Product.__table__.c.material_id.in_(material_ids)))
        session.execute(delete(Process.__table__).where(Process.__table__.c.material_id.in_(material_ids)))
        session.execute(delete(Assemble.__table__).where(Assemble.__table__.c.material_id.in_(material_ids)))
        session.execute(delete(Bom.__table__).where(Bom.__table__.c.material_id.in_(material_ids)))
        session.execute(delete(Material.__table__).where(Material.__table__.c.id.in_(material_ids)))

        session.commit()

        return {
            "success": True,
            "archive_batch_no": archive_batch_no,
            "line": "assemble",
            "material_count": material_count,
            "bom_count": bom_count,
            "assemble_count": assemble_count,
            "process_count": process_count,
            "product_count": product_count,
        }

    except Exception as e:
        session.rollback()
        return {
            "success": False,
            "error": str(e),
        }

    finally:
        session.close()


def archive_p_materials(material_ids, archived_by="system", archive_batch_no=None):
    session = Session()

    try:
        material_ids = normalize_ids(material_ids)

        if not material_ids:
            return {
                "success": False,
                "error": "p_material_ids is empty",
            }

        required_tables = [
            "p_material_archive",
            "p_bom_archive",
            "p_assemble_archive",
            "p_process_archive",
            "p_product_archive",
        ]

        for table_name in required_tables:
            if not table_exists(session, table_name):
                return {
                    "success": False,
                    "error": f"缺少 archive table: {table_name}",
                }

        archive_batch_no = archive_batch_no or make_archive_batch_no()

        material_count = archive_table_rows(
            session,
            source_table=P_Material.__table__,
            archive_table_name="p_material_archive",
            where_clause=P_Material.__table__.c.id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        bom_count = archive_table_rows(
            session,
            source_table=P_Bom.__table__,
            archive_table_name="p_bom_archive",
            where_clause=P_Bom.__table__.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        assemble_count = archive_table_rows(
            session,
            source_table=P_Assemble.__table__,
            archive_table_name="p_assemble_archive",
            where_clause=P_Assemble.__table__.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        process_count = archive_table_rows(
            session,
            source_table=P_Process.__table__,
            archive_table_name="p_process_archive",
            where_clause=P_Process.__table__.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        product_count = archive_table_rows(
            session,
            source_table=P_Product.__table__,
            archive_table_name="p_product_archive",
            where_clause=P_Product.__table__.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        p_bom_before = session.execute(
            select(func.count())
            .select_from(P_Bom.__table__)
            .where(P_Bom.__table__.c.material_id.in_(material_ids))
        ).scalar() or 0

        print("archive_p_materials(), delete 前 p_bom 筆數:", p_bom_before, "material_ids:", material_ids)

        session.execute(delete(P_Product.__table__).where(P_Product.__table__.c.material_id.in_(material_ids)))
        session.execute(delete(P_Process.__table__).where(P_Process.__table__.c.material_id.in_(material_ids)))
        session.execute(delete(P_Assemble.__table__).where(P_Assemble.__table__.c.material_id.in_(material_ids)))
        session.execute(delete(P_Bom.__table__).where(P_Bom.__table__.c.material_id.in_(material_ids)))

        p_bom_after = session.execute(
            select(func.count())
            .select_from(P_Bom.__table__)
            .where(P_Bom.__table__.c.material_id.in_(material_ids))
        ).scalar() or 0

        print("archive_p_materials(), delete 後 p_bom 筆數:", p_bom_after)

        session.execute(delete(P_Material.__table__).where(P_Material.__table__.c.id.in_(material_ids)))

        session.commit()

        return {
            "success": True,
            "archive_batch_no": archive_batch_no,
            "line": "process",
            "material_count": material_count,
            "bom_count": bom_count,
            "assemble_count": assemble_count,
            "process_count": process_count,
            "product_count": product_count,
        }

    except Exception as e:
        session.rollback()
        return {
            "success": False,
            "error": str(e),
        }

    finally:
        session.close()


def restore_archive_rows(rows, restored_by="system"):
    session = Session()

    try:
        normal_map = {}
        process_map = {}

        for r in rows or []:
            line = str(r.get("line") or "").strip()
            batch_no = str(r.get("archive_batch_no") or "").strip()

            try:
                mid = int(r.get("id") or r.get("material_id") or 0)
            except Exception:
                mid = 0

            if not batch_no or mid <= 0:
                continue

            if line in ("process", "加工線", "p", "p_material"):
                process_map.setdefault(batch_no, set()).add(mid)
            else:
                normal_map.setdefault(batch_no, set()).add(mid)

        counts = {
            "normal": {},
            "process": {},
        }

        for batch_no, ids_set in normal_map.items():
            ids = sorted(list(ids_set))

            counts["normal"]["material"] = restore_table_rows(
                session,
                archive_table_name="material_archive",
                target_table=Material.__table__,
                archive_batch_no=batch_no,
                material_ids=ids,
                is_material_table=True,
            )

            counts["normal"]["bom"] = restore_table_rows(
                session,
                archive_table_name="bom_archive",
                target_table=Bom.__table__,
                archive_batch_no=batch_no,
                material_ids=ids,
                is_material_table=False,
            )

            counts["normal"]["assemble"] = restore_table_rows(
                session,
                archive_table_name="assemble_archive",
                target_table=Assemble.__table__,
                archive_batch_no=batch_no,
                material_ids=ids,
                is_material_table=False,
            )

            counts["normal"]["process"] = restore_table_rows(
                session,
                archive_table_name="process_archive",
                target_table=Process.__table__,
                archive_batch_no=batch_no,
                material_ids=ids,
                is_material_table=False,
            )

            counts["normal"]["product"] = restore_table_rows(
                session,
                archive_table_name="product_archive",
                target_table=Product.__table__,
                archive_batch_no=batch_no,
                material_ids=ids,
                is_material_table=False,
            )

            mark_archive_restored(session, archive_table_name="material_archive", archive_batch_no=batch_no, material_ids=ids, restored_by=restored_by, is_material_table=True)
            mark_archive_restored(session, archive_table_name="bom_archive", archive_batch_no=batch_no, material_ids=ids, restored_by=restored_by)
            mark_archive_restored(session, archive_table_name="assemble_archive", archive_batch_no=batch_no, material_ids=ids, restored_by=restored_by)
            mark_archive_restored(session, archive_table_name="process_archive", archive_batch_no=batch_no, material_ids=ids, restored_by=restored_by)
            mark_archive_restored(session, archive_table_name="product_archive", archive_batch_no=batch_no, material_ids=ids, restored_by=restored_by)

        for batch_no, ids_set in process_map.items():
            ids = sorted(list(ids_set))

            counts["process"]["material"] = restore_table_rows(
                session,
                archive_table_name="p_material_archive",
                target_table=P_Material.__table__,
                archive_batch_no=batch_no,
                material_ids=ids,
                is_material_table=True,
            )

            counts["process"]["bom"] = restore_table_rows(
                session,
                archive_table_name="p_bom_archive",
                target_table=P_Bom.__table__,
                archive_batch_no=batch_no,
                material_ids=ids,
                is_material_table=False,
            )

            counts["process"]["assemble"] = restore_table_rows(
                session,
                archive_table_name="p_assemble_archive",
                target_table=P_Assemble.__table__,
                archive_batch_no=batch_no,
                material_ids=ids,
                is_material_table=False,
            )

            counts["process"]["process"] = restore_table_rows(
                session,
                archive_table_name="p_process_archive",
                target_table=P_Process.__table__,
                archive_batch_no=batch_no,
                material_ids=ids,
                is_material_table=False,
            )

            counts["process"]["product"] = restore_table_rows(
                session,
                archive_table_name="p_product_archive",
                target_table=P_Product.__table__,
                archive_batch_no=batch_no,
                material_ids=ids,
                is_material_table=False,
            )

            mark_archive_restored(session, archive_table_name="p_material_archive", archive_batch_no=batch_no, material_ids=ids, restored_by=restored_by, is_material_table=True)
            mark_archive_restored(session, archive_table_name="p_bom_archive", archive_batch_no=batch_no, material_ids=ids, restored_by=restored_by)
            mark_archive_restored(session, archive_table_name="p_assemble_archive", archive_batch_no=batch_no, material_ids=ids, restored_by=restored_by)
            mark_archive_restored(session, archive_table_name="p_process_archive", archive_batch_no=batch_no, material_ids=ids, restored_by=restored_by)
            mark_archive_restored(session, archive_table_name="p_product_archive", archive_batch_no=batch_no, material_ids=ids, restored_by=restored_by)

        session.commit()

        return {
            "success": True,
            "counts": counts,
        }

    except Exception as e:
        session.rollback()
        return {
            "success": False,
            "error": str(e),
        }

    finally:
        session.close()