from datetime import datetime

from database.tables import Session
#from sqlalchemy import text

from flask import Blueprint, jsonify, request

archiveTable = Blueprint('archiveTable', __name__)

from sqlalchemy import (MetaData, Table, select, insert, delete, update, func, inspect, or_,)

from database.tables import (Session, engine, Material, Assemble, Process, Product, Bom,)
from database.p_tables import (P_Material, P_Assemble, P_Process, P_Product, P_Bom,)

# ------------------------------------------------------------
# basic helpers
# ------------------------------------------------------------


def expand_ids_with_copies(s, table, ids):
    ids = normalize_ids(ids)
    all_ids = set(ids)

    changed = True

    while changed:
        changed = False

        child_rows = s.execute(
            select(table.c.id)
            .where(table.c.is_copied_from_id.in_(list(all_ids)))
        ).mappings().all()

        for r in child_rows:
            cid = r.get("id")
            if cid and cid not in all_ids:
                all_ids.add(cid)
                changed = True

    return sorted(all_ids)


def now_dt():
    return datetime.now()


def make_archive_batch_no():
    return datetime.now().strftime("ARCH%Y%m%d%H%M%S")


def normalize_ids(values):
    result = []

    for x in values or []:
        try:
            v = int(x)
            if v > 0:
                result.append(v)
        except Exception:
            pass

    return sorted(set(result))


def table_exists(table_name):
    return inspect(engine).has_table(table_name)


def reflect_table(table_name):
    metadata = MetaData()
    return Table(table_name, metadata, autoload_with=engine)


def get_common_column_names(source_table, target_table, exclude_archive_columns=False):
    source_cols = set(source_table.c.keys())
    target_cols = set(target_table.c.keys())

    cols = list(source_cols & target_cols)

    if exclude_archive_columns:
        archive_cols = {
            "archive_batch_no",
            "archived_at",
            "archived_by",
            "restored_at",
            "restored_by",
        }
        cols = [c for c in cols if c not in archive_cols]

    return cols


def row_to_dict(row):
    return dict(row._mapping)


def copy_rows_to_archive(
    s,
    *,
    source_table,
    archive_table,
    where_clause,
    archive_batch_no,
    archived_by,
):
    archived_at = now_dt()

    cols = get_common_column_names(source_table, archive_table)

    rows = s.execute(
        select(source_table).where(where_clause)
    ).mappings().all()

    if not rows:
        return 0

    insert_rows = []

    for row in rows:
        data = {}

        for c in cols:
            data[c] = row.get(c)

        if "archive_batch_no" in archive_table.c:
            data["archive_batch_no"] = archive_batch_no
        if "archived_at" in archive_table.c:
            data["archived_at"] = archived_at
        if "archived_by" in archive_table.c:
            data["archived_by"] = archived_by
        if "restored_at" in archive_table.c:
            data["restored_at"] = None
        if "restored_by" in archive_table.c:
            data["restored_by"] = None

        insert_rows.append(data)

    s.execute(insert(archive_table), insert_rows)

    return len(insert_rows)


def restore_rows_from_archive(
    s,
    *,
    archive_table,
    target_table,
    archive_batch_no,
):
    cols = get_common_column_names(
        archive_table,
        target_table,
        exclude_archive_columns=True,
    )

    rows = s.execute(
        select(archive_table)
        .where(archive_table.c.archive_batch_no == archive_batch_no)
    ).mappings().all()

    if not rows:
        return 0

    # 防止主鍵 id 重複
    if "id" in target_table.c and "id" in archive_table.c:
        ids = [r.get("id") for r in rows if r.get("id") is not None]

        if ids:
            exists_count = s.execute(
                select(func.count())
                .select_from(target_table)
                .where(target_table.c.id.in_(ids))
            ).scalar() or 0

            if exists_count > 0:
                raise Exception(
                    f"{target_table.name} 已存在相同 id，不能還原，請先確認是否已還原過"
                )

    insert_rows = []

    for row in rows:
        data = {}
        for c in cols:
            data[c] = row.get(c)
        insert_rows.append(data)

    s.execute(insert(target_table), insert_rows)

    return len(insert_rows)


def update_restore_info(
    s,
    *,
    archive_table,
    archive_batch_no,
    restored_by,
):
    values = {}

    if "restored_at" in archive_table.c:
        values["restored_at"] = now_dt()

    if "restored_by" in archive_table.c:
        values["restored_by"] = restored_by

    if not values:
        return

    s.execute(
        update(archive_table)
        .where(archive_table.c.archive_batch_no == archive_batch_no)
        .values(**values)
    )


def get_archive_table(table_name):
    if not table_exists(table_name):
        return None

    return reflect_table(table_name)


# ------------------------------------------------------------
# archive normal assemble line
# ------------------------------------------------------------

"""
def archive_materials(material_ids, archived_by, archive_batch_no=None):
    s = Session()

    try:
        material_ids = normalize_ids(material_ids)

        # 把 A1 的 A2/A3... 複製列一起封存，避免 is_copied_from_id 外鍵擋刪除
        material_ids = expand_ids_with_copies(
            s,
            Material.__table__,
            material_ids,
        )

        if not material_ids:
            return {
                "success": False,
                "error": "material_ids is empty",
            }

        archive_batch_no = archive_batch_no or make_archive_batch_no()

        material_archive = get_archive_table("material_archive")
        assemble_archive = get_archive_table("assemble_archive")
        process_archive = get_archive_table("process_archive")
        product_archive = get_archive_table("product_archive")
        bom_archive = get_archive_table("bom_archive")

        #if not material_archive or not assemble_archive or not process_archive or not product_archive:
        #    return {
        #        "success": False,
        #        "error": "缺少 archive table：material_archive / assemble_archive / process_archive / product_archive",
        #    }
        #
        if (
            material_archive is None
            or assemble_archive is None
            or process_archive is None
            or product_archive is None
            or bom_archive is None
        ):
            return {
                "success": False,
                "error": "缺少 archive table：material_archive / assemble_archive / process_archive / product_archive / bom_archive",
            }

        material_table = Material.__table__
        assemble_table = Assemble.__table__
        process_table = Process.__table__
        product_table = Product.__table__
        bom_table = Bom.__table__

        material_count = copy_rows_to_archive(
            s,
            source_table=material_table,
            archive_table=material_archive,
            where_clause=material_table.c.id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        assemble_count = copy_rows_to_archive(
            s,
            source_table=assemble_table,
            archive_table=assemble_archive,
            where_clause=assemble_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        process_count = copy_rows_to_archive(
            s,
            source_table=process_table,
            archive_table=process_archive,
            where_clause=process_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        product_count = copy_rows_to_archive(
            s,
            source_table=product_table,
            archive_table=product_archive,
            where_clause=product_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        bom_count = copy_rows_to_archive(
            s,
            source_table=bom_table,
            archive_table=bom_archive,
            where_clause=bom_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        # 刪除順序：子表 → 主表
        s.execute(
            delete(product_table)
            .where(product_table.c.material_id.in_(material_ids))
        )

        s.execute(
            delete(process_table)
            .where(process_table.c.material_id.in_(material_ids))
        )

        s.execute(
            delete(assemble_table)
            .where(assemble_table.c.material_id.in_(material_ids))
        )

        s.execute(
            delete(bom_table)
            .where(bom_table.c.material_id.in_(material_ids))
        )

        s.execute(
            delete(material_table)
            .where(material_table.c.id.in_(material_ids))
        )

        s.commit()

        return {
            "success": True,
            "archive_batch_no": archive_batch_no,
            "line": "assemble",
            "material_count": material_count,
            "assemble_count": assemble_count,
            "process_count": process_count,
            "product_count": product_count,
            "bom_count": bom_count,
        }

    except Exception as e:
        s.rollback()
        print("archive_materials ERROR:", repr(e))

        return {
            "success": False,
            "error": str(e),
        }

    finally:
        s.close()
"""


def archive_materials(material_ids, archived_by, archive_batch_no=None):
    s = Session()

    try:
        material_ids = normalize_ids(material_ids)

        if not material_ids:
            return {
                "success": False,
                "error": "material_ids is empty",
            }

        # 把 A1 的 A2/A3... 複製列一起封存
        material_ids = expand_ids_with_copies(
            s,
            Material.__table__,
            material_ids,
        )

        archive_batch_no = archive_batch_no or make_archive_batch_no()

        material_archive = get_archive_table("material_archive")
        assemble_archive = get_archive_table("assemble_archive")
        process_archive = get_archive_table("process_archive")
        product_archive = get_archive_table("product_archive")
        bom_archive = get_archive_table("bom_archive")

        if (
            material_archive is None
            or assemble_archive is None
            or process_archive is None
            or product_archive is None
            or bom_archive is None
        ):
            return {
                "success": False,
                "error": "缺少 archive table：material_archive / assemble_archive / process_archive / product_archive / bom_archive",
            }

        material_table = Material.__table__
        assemble_table = Assemble.__table__
        process_table = Process.__table__
        product_table = Product.__table__
        bom_table = Bom.__table__

        material_count = copy_rows_to_archive(
            s,
            source_table=material_table,
            archive_table=material_archive,
            where_clause=material_table.c.id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        assemble_count = copy_rows_to_archive(
            s,
            source_table=assemble_table,
            archive_table=assemble_archive,
            where_clause=assemble_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        process_count = copy_rows_to_archive(
            s,
            source_table=process_table,
            archive_table=process_archive,
            where_clause=process_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        product_count = copy_rows_to_archive(
            s,
            source_table=product_table,
            archive_table=product_archive,
            where_clause=product_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        bom_count = copy_rows_to_archive(
            s,
            source_table=bom_table,
            archive_table=bom_archive,
            where_clause=bom_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        '''
        # 刪除順序：子表 → 主表
        s.execute(delete(product_table).where(product_table.c.material_id.in_(material_ids)))
        s.execute(delete(process_table).where(process_table.c.material_id.in_(material_ids)))
        s.execute(delete(assemble_table).where(assemble_table.c.material_id.in_(material_ids)))
        s.execute(delete(bom_table).where(bom_table.c.material_id.in_(material_ids)))

        # 先清掉 material 自我外鍵，避免 is_copied_from_id 擋刪除
        s.execute(
            update(material_table)
            .where(material_table.c.id.in_(material_ids))
            .values(is_copied_from_id=None)
        )

        s.execute(delete(material_table).where(material_table.c.id.in_(material_ids)))
        '''
        #
        # ==========================================================
        # 先取得本次要刪除的 assemble id
        # ==========================================================
        assemble_ids = [
            r[0]
            for r in s.execute(
                select(assemble_table.c.id).where(
                    assemble_table.c.material_id.in_(material_ids)
                )
            ).fetchall()
        ]

        # ==========================================================
        # 清掉 assemble 自我外鍵
        # 避免 assemble.is_copied_from_id -> assemble.id 擋刪除
        # ==========================================================
        if assemble_ids:
            s.execute(
                update(assemble_table)
                .where(
                    assemble_table.c.is_copied_from_id.in_(assemble_ids)
                )
                .values(is_copied_from_id=None)
            )

        # ==========================================================
        # 清掉 material 自我外鍵
        # 避免 material.is_copied_from_id -> material.id 擋刪除
        # ==========================================================
        s.execute(
            update(material_table)
            .where(
                material_table.c.is_copied_from_id.in_(material_ids)
            )
            .values(is_copied_from_id=None)
        )

        # ==========================================================
        # 刪除順序：子表 → 主表
        # ==========================================================
        s.execute(delete(product_table).where(product_table.c.material_id.in_(material_ids)))
        s.execute(delete(process_table).where(process_table.c.material_id.in_(material_ids)))
        s.execute(delete(assemble_table).where(assemble_table.c.material_id.in_(material_ids)))
        s.execute(delete(bom_table).where(bom_table.c.material_id.in_(material_ids)))
        s.execute(delete(material_table).where(material_table.c.id.in_(material_ids)))
        #

        s.commit()

        return {
            "success": True,
            "archive_batch_no": archive_batch_no,
            "line": "assemble",
            "material_ids": material_ids,
            "material_count": material_count,
            "assemble_count": assemble_count,
            "process_count": process_count,
            "product_count": product_count,
            "bom_count": bom_count,
        }

    except Exception as e:
        s.rollback()
        print("archive_materials ERROR:", repr(e))

        return {
            "success": False,
            "error": str(e),
        }

    finally:
        s.close()


# ------------------------------------------------------------
# archive process line
# ------------------------------------------------------------

"""
def archive_p_materials(material_ids, archived_by, archive_batch_no=None):
    s = Session()

    try:
        material_ids = normalize_ids(material_ids)

        if not material_ids:
            return {
                "success": False,
                "error": "p_material_ids is empty",
            }

        archive_batch_no = archive_batch_no or make_archive_batch_no()

        p_material_archive = get_archive_table("p_material_archive")
        p_bom_archive = get_archive_table("p_bom_archive")
        p_assemble_archive = get_archive_table("p_assemble_archive")
        p_process_archive = get_archive_table("p_process_archive")
        p_product_archive = get_archive_table("p_product_archive")

        #if not p_material_archive or not p_assemble_archive or not p_process_archive or not p_product_archive:
        #    return {
        #        "success": False,
        #        "error": "缺少 archive table：p_material_archive / p_assemble_archive / p_process_archive / p_product_archive",
        #    }
        #
        if (
            p_material_archive is None
            or p_bom_archive is None
            or p_assemble_archive is None
            or p_process_archive is None
            or p_product_archive is None
        ):
            return {
                "success": False,
                "error": "缺少 archive table：p_material_archive / p_assemble_archive / p_process_archive / p_product_archive",
            }


        p_material_table = P_Material.__table__
        p_bom_table = P_Bom.__table__
        p_assemble_table = P_Assemble.__table__
        p_process_table = P_Process.__table__
        p_product_table = P_Product.__table__

        material_count = copy_rows_to_archive(
            s,
            source_table=p_material_table,
            archive_table=p_material_archive,
            where_clause=p_material_table.c.id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        bom_count = copy_rows_to_archive(
            s,
            source_table=p_bom_table,
            archive_table=p_bom_archive,
            where_clause=p_bom_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        assemble_count = copy_rows_to_archive(
            s,
            source_table=p_assemble_table,
            archive_table=p_assemble_archive,
            where_clause=p_assemble_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        process_count = copy_rows_to_archive(
            s,
            source_table=p_process_table,
            archive_table=p_process_archive,
            where_clause=p_process_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        product_count = copy_rows_to_archive(
            s,
            source_table=p_product_table,
            archive_table=p_product_archive,
            where_clause=p_product_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        s.execute(
            delete(p_product_table)
            .where(p_product_table.c.material_id.in_(material_ids))
        )

        s.execute(
            delete(p_process_table)
            .where(p_process_table.c.material_id.in_(material_ids))
        )

        s.execute(
            delete(p_assemble_table)
            .where(p_assemble_table.c.material_id.in_(material_ids))
        )

        s.execute(
            delete(p_bom_table)
            .where(p_bom_table.c.material_id.in_(material_ids))
        )

        s.execute(
            delete(p_material_table)
            .where(p_material_table.c.id.in_(material_ids))
        )

        s.commit()

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
        s.rollback()
        print("archive_p_materials ERROR:", repr(e))

        return {
            "success": False,
            "error": str(e),
        }

    finally:
        s.close()
"""


def archive_p_materials(material_ids, archived_by, archive_batch_no=None):
    s = Session()

    try:
        material_ids = normalize_ids(material_ids)

        if not material_ids:
            return {
                "success": False,
                "error": "p_material_ids is empty",
            }

        # 把加工線 A1 的 A2/A3... 複製列一起封存
        material_ids = expand_ids_with_copies(
            s,
            P_Material.__table__,
            material_ids,
        )

        archive_batch_no = archive_batch_no or make_archive_batch_no()

        p_material_archive = get_archive_table("p_material_archive")
        p_bom_archive = get_archive_table("p_bom_archive")
        p_assemble_archive = get_archive_table("p_assemble_archive")
        p_process_archive = get_archive_table("p_process_archive")
        p_product_archive = get_archive_table("p_product_archive")

        if (
            p_material_archive is None
            or p_bom_archive is None
            or p_assemble_archive is None
            or p_process_archive is None
            or p_product_archive is None
        ):
            return {
                "success": False,
                "error": "缺少 archive table：p_material_archive / p_bom_archive / p_assemble_archive / p_process_archive / p_product_archive",
            }

        p_material_table = P_Material.__table__
        p_bom_table = P_Bom.__table__
        p_assemble_table = P_Assemble.__table__
        p_process_table = P_Process.__table__
        p_product_table = P_Product.__table__

        material_count = copy_rows_to_archive(
            s,
            source_table=p_material_table,
            archive_table=p_material_archive,
            where_clause=p_material_table.c.id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        bom_count = copy_rows_to_archive(
            s,
            source_table=p_bom_table,
            archive_table=p_bom_archive,
            where_clause=p_bom_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        assemble_count = copy_rows_to_archive(
            s,
            source_table=p_assemble_table,
            archive_table=p_assemble_archive,
            where_clause=p_assemble_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        process_count = copy_rows_to_archive(
            s,
            source_table=p_process_table,
            archive_table=p_process_archive,
            where_clause=p_process_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )

        product_count = copy_rows_to_archive(
            s,
            source_table=p_product_table,
            archive_table=p_product_archive,
            where_clause=p_product_table.c.material_id.in_(material_ids),
            archive_batch_no=archive_batch_no,
            archived_by=archived_by,
        )
        '''
        # 刪除順序：子表 → 主表
        s.execute(delete(p_product_table).where(p_product_table.c.material_id.in_(material_ids)))
        s.execute(delete(p_process_table).where(p_process_table.c.material_id.in_(material_ids)))
        s.execute(delete(p_assemble_table).where(p_assemble_table.c.material_id.in_(material_ids)))
        s.execute(delete(p_bom_table).where(p_bom_table.c.material_id.in_(material_ids)))

        # 先清掉 p_material 自我外鍵，避免 is_copied_from_id 擋刪除
        s.execute(
            update(p_material_table)
            .where(p_material_table.c.id.in_(material_ids))
            .values(is_copied_from_id=None)
        )

        s.execute(delete(p_material_table).where(p_material_table.c.id.in_(material_ids)))
        '''
        #
        # ==========================================================
        # 先取得本次要刪除的 p_assemble id
        # ==========================================================
        p_assemble_ids = [
            r[0]
            for r in s.execute(
                select(p_assemble_table.c.id).where(
                    p_assemble_table.c.material_id.in_(material_ids)
                )
            ).fetchall()
        ]

        # ==========================================================
        # 清掉 p_assemble 自我外鍵
        # 避免 p_assemble.is_copied_from_id -> p_assemble.id 擋刪除
        # ==========================================================
        if p_assemble_ids:
            s.execute(
                update(p_assemble_table)
                .where(
                    p_assemble_table.c.is_copied_from_id.in_(p_assemble_ids)
                )
                .values(is_copied_from_id=None)
            )

        # ==========================================================
        # 清掉其他 p_material 指向本批 p_material 的 FK
        # 避免 p_material.is_copied_from_id -> p_material.id 擋刪除
        # ==========================================================
        s.execute(
            update(p_material_table)
            .where(
                p_material_table.c.is_copied_from_id.in_(material_ids)
            )
            .values(is_copied_from_id=None)
        )

        # ==========================================================
        # 刪除順序：子表 → 主表
        # ==========================================================
        s.execute(delete(p_product_table).where(p_product_table.c.material_id.in_(material_ids)))
        s.execute(delete(p_process_table).where(p_process_table.c.material_id.in_(material_ids)))
        s.execute(delete(p_assemble_table).where(p_assemble_table.c.material_id.in_(material_ids)))
        s.execute(delete(p_bom_table).where(p_bom_table.c.material_id.in_(material_ids)))
        s.execute(delete(p_material_table).where(p_material_table.c.id.in_(material_ids)))
        #

        s.commit()

        return {
            "success": True,
            "archive_batch_no": archive_batch_no,
            "line": "process",
            "material_ids": material_ids,
            "material_count": material_count,
            "bom_count": bom_count,
            "assemble_count": assemble_count,
            "process_count": process_count,
            "product_count": product_count,
        }

    except Exception as e:
        s.rollback()
        print("archive_p_materials ERROR:", repr(e))

        return {
            "success": False,
            "error": str(e),
        }

    finally:
        s.close()


# ------------------------------------------------------------
# API: archive selected warehouse rows
# ------------------------------------------------------------
"""
@archiveTable.route("/archiveWarehouseOrders", methods=["POST"])
def archive_warehouse_orders():
    print("archiveWarehouseOrders...")

    data = request.get_json() or {}

    rows = data.get("rows", [])
    material_ids = data.get("material_ids", [])
    archived_by = data.get("archived_by", "system")

    normal_ids = []
    p_ids = []

    # 新版前端建議傳 rows: [{ id, line }]
    if rows:
        for r in rows:
            line = str(r.get("line") or "").strip()
            mid = r.get("id") or r.get("material_id")

            try:
                mid = int(mid)
            except Exception:
                continue

            if line in ("process", "加工線", "p", "p_material"):
                p_ids.append(mid)
            else:
                normal_ids.append(mid)

    # 相容舊版，只傳 material_ids 時，預設組裝線
    else:
        normal_ids = normalize_ids(material_ids)

    normal_ids = normalize_ids(normal_ids)
    p_ids = normalize_ids(p_ids)

    if not normal_ids and not p_ids:
        return jsonify({
            "success": False,
            "error": "沒有可封存的資料",
        })

    archive_batch_no = make_archive_batch_no()
    results = []

    if normal_ids:
        r1 = archive_materials(
            material_ids=normal_ids,
            archived_by=archived_by,
            archive_batch_no=archive_batch_no,
        )

        results.append(r1)

        if not r1.get("success"):
            return jsonify(r1)

    if p_ids:
        r2 = archive_p_materials(
            material_ids=p_ids,
            archived_by=archived_by,
            archive_batch_no=archive_batch_no,
        )

        results.append(r2)

        if not r2.get("success"):
            return jsonify(r2)

    return jsonify({
        "success": True,
        "archive_batch_no": archive_batch_no,
        "normal_count": len(normal_ids),
        "process_count": len(p_ids),
        "results": results,
    })
"""


@archiveTable.route("/archiveWarehouseOrders", methods=["POST"])
def archive_warehouse_orders():
    print("archiveWarehouseOrders...")

    data = request.get_json() or {}

    rows = data.get("rows", [])
    material_ids = data.get("material_ids", [])
    archived_by = data.get("archived_by", "system")

    normal_ids = []
    p_ids = []

    if rows:
        for r in rows:
            line = str(r.get("line") or r.get("line_key") or "").strip()
            mid = r.get("id") or r.get("material_id")

            try:
                mid = int(mid)
            except Exception:
                continue

            if line in ("process", "加工線", "p", "p_material"):
                p_ids.append(mid)
            else:
                normal_ids.append(mid)
    else:
        normal_ids = normalize_ids(material_ids)

    normal_ids = normalize_ids(normal_ids)
    p_ids = normalize_ids(p_ids)

    if not normal_ids and not p_ids:
        return jsonify({
            "success": False,
            "error": "沒有可封存的資料",
        })

    archive_batch_no = make_archive_batch_no()
    results = []

    if normal_ids:
        r1 = archive_materials(
            material_ids=normal_ids,
            archived_by=archived_by,
            archive_batch_no=archive_batch_no,
        )

        results.append(r1)

        if not r1.get("success"):
            return jsonify(r1)

    if p_ids:
        r2 = archive_p_materials(
            material_ids=p_ids,
            archived_by=archived_by,
            archive_batch_no=archive_batch_no,
        )

        results.append(r2)

        if not r2.get("success"):
            return jsonify(r2)

    return jsonify({
        "success": True,
        "archive_batch_no": archive_batch_no,
        "normal_count": len(normal_ids),
        "process_count": len(p_ids),
        "results": results,
    })


# ------------------------------------------------------------
# API: restore archive batch
# ------------------------------------------------------------

@archiveTable.route("/restoreWarehouseOrders", methods=["POST"])
def restore_warehouse_orders():
    print("restoreWarehouseOrders...")

    data = request.get_json() or {}

    archive_batch_no = data.get("archive_batch_no")
    restored_by = data.get("restored_by", "system")

    if not archive_batch_no:
        return jsonify({
            "success": False,
            "error": "archive_batch_no is required",
        })

    s = Session()

    try:
        tables = [
            ("material_archive", Material.__table__),
            ("assemble_archive", Assemble.__table__),
            ("process_archive", Process.__table__),
            ("product_archive", Product.__table__),

            ("p_material_archive", P_Material.__table__),
            ("p_assemble_archive", P_Assemble.__table__),
            ("p_process_archive", P_Process.__table__),
            ("p_product_archive", P_Product.__table__),
        ]

        restored_counts = {}

        # 還原順序：主表 → 子表
        for archive_table_name, target_table in tables:
            if not table_exists(archive_table_name):
                restored_counts[archive_table_name] = 0
                continue

            archive_table = reflect_table(archive_table_name)

            count = restore_rows_from_archive(
                s,
                archive_table=archive_table,
                target_table=target_table,
                archive_batch_no=archive_batch_no,
            )

            restored_counts[archive_table_name] = count

        for archive_table_name, _target_table in tables:
            if not table_exists(archive_table_name):
                continue

            archive_table = reflect_table(archive_table_name)

            update_restore_info(
                s,
                archive_table=archive_table,
                archive_batch_no=archive_batch_no,
                restored_by=restored_by,
            )

        s.commit()

        return jsonify({
            "success": True,
            "archive_batch_no": archive_batch_no,
            "restored_counts": restored_counts,
        })

    except Exception as e:
        s.rollback()
        print("restoreWarehouseOrders ERROR:", repr(e))

        return jsonify({
            "success": False,
            "error": str(e),
        })

    finally:
        s.close()


# ------------------------------------------------------------
# API: list archive batches
# ------------------------------------------------------------

@archiveTable.route("/listArchiveBatches", methods=["POST"])
def list_archive_batches():
    print("listArchiveBatches...")

    s = Session()

    try:
        archive_tables = [
            ("material_archive", "assemble"),
            ("p_material_archive", "process"),
        ]

        batch_map = {}

        for table_name, line_name in archive_tables:
            if not table_exists(table_name):
                continue

            t = reflect_table(table_name)

            if "archive_batch_no" not in t.c:
                continue

            rows = s.execute(
                select(
                    t.c.archive_batch_no.label("archive_batch_no"),
                    func.min(t.c.archived_at).label("archived_at"),
                    func.max(t.c.archived_by).label("archived_by"),
                    func.max(t.c.restored_at).label("restored_at"),
                    func.max(t.c.restored_by).label("restored_by"),
                    func.count().label("total_count"),
                )
                .group_by(t.c.archive_batch_no)
                .order_by(func.min(t.c.archived_at).desc())
            ).all()

            for r in rows:
                row = row_to_dict(r)
                batch_no = row.get("archive_batch_no")

                if not batch_no:
                    continue

                if batch_no not in batch_map:
                    batch_map[batch_no] = {
                        "archive_batch_no": batch_no,
                        "archived_at": row.get("archived_at"),
                        "archived_by": row.get("archived_by"),
                        "restored_at": row.get("restored_at"),
                        "restored_by": row.get("restored_by"),
                        "normal_count": 0,
                        "process_count": 0,
                        "total_count": 0,
                    }

                if line_name == "assemble":
                    batch_map[batch_no]["normal_count"] += int(row.get("total_count") or 0)
                else:
                    batch_map[batch_no]["process_count"] += int(row.get("total_count") or 0)

                batch_map[batch_no]["total_count"] += int(row.get("total_count") or 0)

                if row.get("archived_at") and (
                    not batch_map[batch_no]["archived_at"]
                    or row.get("archived_at") < batch_map[batch_no]["archived_at"]
                ):
                    batch_map[batch_no]["archived_at"] = row.get("archived_at")

                if row.get("restored_at"):
                    batch_map[batch_no]["restored_at"] = row.get("restored_at")

                if row.get("restored_by"):
                    batch_map[batch_no]["restored_by"] = row.get("restored_by")

        results = list(batch_map.values())

        results.sort(
            key=lambda x: str(x.get("archived_at") or ""),
            reverse=True,
        )

        for r in results:
            r["archived_at"] = str(r["archived_at"]) if r.get("archived_at") else None
            r["restored_at"] = str(r["restored_at"]) if r.get("restored_at") else None

        return jsonify({
            "success": True,
            "data": results,
        })

    except Exception as e:
        print("listArchiveBatches ERROR:", repr(e))

        return jsonify({
            "success": False,
            "error": str(e),
            "data": [],
        })

    finally:
        s.close()


# ------------------------------------------------------------
# API: 查詢入庫封存歷史明細
# ------------------------------------------------------------

@archiveTable.route("/listWarehouseArchiveHistory", methods=["POST"])
def list_warehouse_archive_history():
    print("listWarehouseArchiveHistory...")

    data = request.get_json() or {}

    source = data.get("source", "not_restored")  # not_restored / restored / all
    keyword = (data.get("keyword") or "").strip()
    archive_batch_no = (data.get("archive_batch_no") or "").strip()

    s = Session()

    try:
        results = []

        bind = s.get_bind()
        metadata = MetaData()

        def has_table(table_name):
            return inspect(bind).has_table(table_name)

        def load_table(table_name):
            return Table(table_name, metadata, autoload_with=bind)

        def safe_get(row, key, default=None):
            try:
                return row.get(key, default)
            except Exception:
                return default

        def dt_to_str(v):
            if not v:
                return None
            try:
                return v.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return str(v)

        def latest_stockin_qty(process_archive_table, material_id, archive_batch_no):
            if process_archive_table is None:
                return 0

            cols = process_archive_table.c

            if not all(hasattr(cols, x) for x in ["material_id", "archive_batch_no", "process_type"]):
                return 0

            q = (
                select(func.coalesce(func.sum(cols.process_work_time_qty), 0))
                .where(cols.material_id == material_id)
                .where(cols.archive_batch_no == archive_batch_no)
                .where(cols.process_type == 31)
            )

            if hasattr(cols, "has_started"):
                q = q.where(cols.has_started == True)

            if hasattr(cols, "end_time"):
                q = q.where(cols.end_time.isnot(None))
                q = q.where(cols.end_time != "")

            return int(s.execute(q).scalar() or 0)

        def query_archive_line(
            *,
            line_key,
            line_name,
            material_archive_name,
            assemble_archive_name,
            process_archive_name,
            product_archive_name,
        ):
            if not has_table(material_archive_name):
                return

            mat_t = load_table(material_archive_name)
            asm_t = load_table(assemble_archive_name) if has_table(assemble_archive_name) else None
            proc_t = load_table(process_archive_name) if has_table(process_archive_name) else None
            prd_t = load_table(product_archive_name) if has_table(product_archive_name) else None

            cols = mat_t.c

            q = select(mat_t)

            if archive_batch_no and hasattr(cols, "archive_batch_no"):
                q = q.where(cols.archive_batch_no == archive_batch_no)

            if source == "not_restored" and hasattr(cols, "restored_at"):
                q = q.where(cols.restored_at.is_(None))
            elif source == "restored" and hasattr(cols, "restored_at"):
                q = q.where(cols.restored_at.isnot(None))

            if keyword:
                like_value = f"%{keyword}%"

                conds = []

                if hasattr(cols, "order_num"):
                    conds.append(cols.order_num.like(like_value))
                if hasattr(cols, "material_num"):
                    conds.append(cols.material_num.like(like_value))
                if hasattr(cols, "material_comment"):
                    conds.append(cols.material_comment.like(like_value))
                if hasattr(cols, "archive_batch_no"):
                    conds.append(cols.archive_batch_no.like(like_value))

                if conds:
                    q = q.where(or_(*conds))

            if hasattr(cols, "archived_at"):
                q = q.order_by(cols.archived_at.desc(), cols.id.desc())
            else:
                q = q.order_by(cols.id.desc())

            rows = s.execute(q).mappings().all()

            for r in rows:
                material_id = safe_get(r, "id", 0)
                batch_no = safe_get(r, "archive_batch_no", "")

                stockin_qty = latest_stockin_qty(proc_t, material_id, batch_no)

                results.append({
                    "line": line_key,
                    "line_name": line_name,

                    "id": material_id,
                    "material_id": material_id,
                    "archive_batch_no": batch_no,

                    "order_num": safe_get(r, "order_num", ""),
                    "material_num": safe_get(r, "material_num", ""),
                    "comment": safe_get(r, "material_comment", ""),

                    "req_qty": int(safe_get(r, "material_qty", 0) or 0),
                    "delivery_qty": int(safe_get(r, "delivery_qty", 0) or 0),
                    "total_delivery_qty": int(safe_get(r, "total_delivery_qty", 0) or 0),

                    "total_allOk_qty": stockin_qty,

                    "material_date": dt_to_str(safe_get(r, "material_date", None)),
                    "delivery_date": dt_to_str(safe_get(r, "material_delivery_date", None)),

                    "archived_at": dt_to_str(safe_get(r, "archived_at", None)),
                    "archived_by": safe_get(r, "archived_by", ""),

                    "restored_at": dt_to_str(safe_get(r, "restored_at", None)),
                    "restored_by": safe_get(r, "restored_by", ""),

                    "can_restore": False if safe_get(r, "restored_at", None) else True,
                })

        query_archive_line(
            line_key="assemble",
            line_name="組裝線",
            material_archive_name="material_archive",
            assemble_archive_name="assemble_archive",
            process_archive_name="process_archive",
            product_archive_name="product_archive",
        )

        query_archive_line(
            line_key="process",
            line_name="加工線",
            material_archive_name="p_material_archive",
            assemble_archive_name="p_assemble_archive",
            process_archive_name="p_process_archive",
            product_archive_name="p_product_archive",
        )

        results.sort(
            key=lambda x: (
                x.get("archived_at") or "",
                x.get("archive_batch_no") or "",
                int(x.get("id") or 0),
            ),
            reverse=True
        )

        for i, row in enumerate(results, start=1):
            row["index"] = i

        return jsonify({
            "success": True,
            "status": len(results) > 0,
            "data": results,
        })

    except Exception as e:
        print("listWarehouseArchiveHistory ERROR:", repr(e))

        return jsonify({
            "success": False,
            "status": False,
            "error": str(e),
            "data": [],
        })

    finally:
        s.close()


# ------------------------------------------------------------
# API: 還原已選入庫封存資料
# ------------------------------------------------------------

@archiveTable.route("/restoreWarehouseArchiveRows", methods=["POST"])
def restore_warehouse_archive_rows():
    print("restoreWarehouseArchiveRows...")

    data = request.get_json() or {}

    rows = data.get("rows", [])
    restored_by = data.get("restored_by", "system")

    if not rows:
        return jsonify({
            "success": False,
            "error": "rows is empty",
        })

    s = Session()

    try:
        bind = s.get_bind()
        metadata = MetaData()

        def has_table(table_name):
            return inspect(bind).has_table(table_name)

        def load_table(table_name):
            return Table(table_name, metadata, autoload_with=bind)

        def normalize_selected_rows(rows):
            normal = {}
            process = {}

            for r in rows:
                line = str(r.get("line") or "").strip()
                batch_no = str(r.get("archive_batch_no") or "").strip()

                try:
                    mid = int(r.get("id") or r.get("material_id") or 0)
                except Exception:
                    mid = 0

                if not batch_no or mid <= 0:
                    continue

                if line in ("process", "加工線", "p", "p_material"):
                    process.setdefault(batch_no, set()).add(mid)
                else:
                    normal.setdefault(batch_no, set()).add(mid)

            return normal, process

        def common_columns(source_table, target_table):
            archive_columns = {
                "archive_batch_no",
                "archived_at",
                "archived_by",
                "restored_at",
                "restored_by",
            }

            source_cols = set(source_table.c.keys())
            target_cols = set(target_table.c.keys())

            return [
                c for c in target_table.c.keys()
                if c in source_cols and c not in archive_columns
            ]

        def insert_from_archive_rows(
            *,
            archive_table,
            target_table,
            archive_batch_no,
            material_ids,
            is_material_table=False,
        ):
            cols = common_columns(archive_table, target_table)

            if not cols:
                return 0

            q = select(archive_table).where(
                archive_table.c.archive_batch_no == archive_batch_no
            )

            if is_material_table:
                q = q.where(archive_table.c.id.in_(material_ids))
            else:
                q = q.where(archive_table.c.material_id.in_(material_ids))

            if "restored_at" in archive_table.c:
                q = q.where(archive_table.c.restored_at.is_(None))

            archive_rows = s.execute(q).mappings().all()

            if not archive_rows:
                return 0

            insert_rows = []

            for row in archive_rows:
                insert_rows.append({
                    c: row.get(c)
                    for c in cols
                })

            # 主鍵防呆
            if "id" in target_table.c:
                ids = [
                    row.get("id")
                    for row in insert_rows
                    if row.get("id") is not None
                ]

                if ids:
                    exists_count = s.execute(
                        select(func.count())
                        .select_from(target_table)
                        .where(target_table.c.id.in_(ids))
                    ).scalar() or 0

                    if exists_count > 0:
                        raise Exception(
                            f"{target_table.name} 已存在相同 id，可能已還原過，請重新查詢"
                        )

            s.execute(insert(target_table), insert_rows)

            return len(insert_rows)

        def mark_restored(
            *,
            archive_table,
            archive_batch_no,
            material_ids,
            is_material_table=False,
        ):
            if "restored_at" not in archive_table.c:
                return

            q = (
                update(archive_table)
                .where(archive_table.c.archive_batch_no == archive_batch_no)
            )

            if is_material_table:
                q = q.where(archive_table.c.id.in_(material_ids))
            else:
                q = q.where(archive_table.c.material_id.in_(material_ids))

            values = {
                "restored_at": datetime.now(),
            }

            if "restored_by" in archive_table.c:
                values["restored_by"] = restored_by

            s.execute(q.values(**values))

        def restore_line(
            *,
            selected_map,
            material_archive_name,
            assemble_archive_name,
            process_archive_name,
            product_archive_name,
            MaterialCls,
            AssembleCls,
            ProcessCls,
            ProductCls,
        ):
            total_counts = {
                "material": 0,
                "assemble": 0,
                "process": 0,
                "product": 0,
            }

            if not selected_map:
                return total_counts

            required_tables = [
                material_archive_name,
                assemble_archive_name,
                process_archive_name,
                product_archive_name,
            ]

            for tn in required_tables:
                if not has_table(tn):
                    raise Exception(f"缺少封存資料表：{tn}")

            material_archive = load_table(material_archive_name)
            assemble_archive = load_table(assemble_archive_name)
            process_archive = load_table(process_archive_name)
            product_archive = load_table(product_archive_name)

            for batch_no, mids_set in selected_map.items():
                mids = sorted(list(mids_set))

                # 還原順序：主表 → 子表
                total_counts["material"] += insert_from_archive_rows(
                    archive_table=material_archive,
                    target_table=MaterialCls.__table__,
                    archive_batch_no=batch_no,
                    material_ids=mids,
                    is_material_table=True,
                )

                total_counts["assemble"] += insert_from_archive_rows(
                    archive_table=assemble_archive,
                    target_table=AssembleCls.__table__,
                    archive_batch_no=batch_no,
                    material_ids=mids,
                    is_material_table=False,
                )

                total_counts["process"] += insert_from_archive_rows(
                    archive_table=process_archive,
                    target_table=ProcessCls.__table__,
                    archive_batch_no=batch_no,
                    material_ids=mids,
                    is_material_table=False,
                )

                total_counts["product"] += insert_from_archive_rows(
                    archive_table=product_archive,
                    target_table=ProductCls.__table__,
                    archive_batch_no=batch_no,
                    material_ids=mids,
                    is_material_table=False,
                )

                # 標記已還原
                mark_restored(
                    archive_table=material_archive,
                    archive_batch_no=batch_no,
                    material_ids=mids,
                    is_material_table=True,
                )

                mark_restored(
                    archive_table=assemble_archive,
                    archive_batch_no=batch_no,
                    material_ids=mids,
                    is_material_table=False,
                )

                mark_restored(
                    archive_table=process_archive,
                    archive_batch_no=batch_no,
                    material_ids=mids,
                    is_material_table=False,
                )

                mark_restored(
                    archive_table=product_archive,
                    archive_batch_no=batch_no,
                    material_ids=mids,
                    is_material_table=False,
                )

            return total_counts

        normal_map, process_map = normalize_selected_rows(rows)

        normal_counts = restore_line(
            selected_map=normal_map,
            material_archive_name="material_archive",
            assemble_archive_name="assemble_archive",
            process_archive_name="process_archive",
            product_archive_name="product_archive",
            MaterialCls=Material,
            AssembleCls=Assemble,
            ProcessCls=Process,
            ProductCls=Product,
        )

        process_counts = restore_line(
            selected_map=process_map,
            material_archive_name="p_material_archive",
            assemble_archive_name="p_assemble_archive",
            process_archive_name="p_process_archive",
            product_archive_name="p_product_archive",
            MaterialCls=P_Material,
            AssembleCls=P_Assemble,
            ProcessCls=P_Process,
            ProductCls=P_Product,
        )

        s.commit()

        return jsonify({
            "success": True,
            "normal_counts": normal_counts,
            "process_counts": process_counts,
        })

    except Exception as e:
        s.rollback()
        print("restoreWarehouseArchiveRows ERROR:", repr(e))

        return jsonify({
            "success": False,
            "error": str(e),
        })

    finally:
        s.close()


@archiveTable.route("/archiveAllStockinAssembleMaterials", methods=["POST"])
def archive_all_stockin_assemble_materials():
    print("archiveAllStockinAssembleMaterials...")

    data = request.get_json() or {}
    archived_by = data.get("archived_by", "system")

    s = Session()

    try:
        material_ids = [
            r[0]
            for r in (
                s.query(Material.id)
                .filter(Material.move_by_process_type == 2)
                .filter(Material.show2_ok == "12")
                .all()
            )
        ]

        if not material_ids:
            return jsonify({
                "success": False,
                "error": "沒有可封存的組裝線已入庫資料",
                "count": 0,
            })

        archive_batch_no = make_archive_batch_no()

        result = archive_materials(
            material_ids=material_ids,
            archived_by=archived_by,
            archive_batch_no=archive_batch_no,
        )

        if not result.get("success"):
            return jsonify(result)

        return jsonify({
            "success": True,
            "archive_batch_no": archive_batch_no,
            "count": len(material_ids),
            "result": result,
        })

    except Exception as e:
        s.rollback()
        print("archiveAllStockinAssembleMaterials ERROR:", repr(e))
        return jsonify({
            "success": False,
            "error": str(e),
        })

    finally:
        s.close()