from datetime import datetime

from database.tables import Session
from sqlalchemy import text

from flask import Blueprint, jsonify, request

archiveTable = Blueprint('archiveTable', __name__)


# ------------------------------------------------------------------


def archive_materials(material_ids, archived_by):
    s = Session()

    try:
        archive_batch_no = datetime.now().strftime("ARCH%Y%m%d%H%M%S")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ids = ",".join([str(int(x)) for x in material_ids])

        s.execute(text(f"""
            INSERT INTO material_archive
            SELECT m.*, :archive_batch_no, :archived_at, :archived_by, NULL, NULL
            FROM material m
            WHERE m.id IN ({ids})
        """), {
            "archive_batch_no": archive_batch_no,
            "archived_at": now,
            "archived_by": archived_by,
        })

        s.execute(text(f"""
            INSERT INTO assemble_archive
            SELECT a.*, :archive_batch_no, :archived_at, :archived_by, NULL, NULL
            FROM assemble a
            WHERE a.material_id IN ({ids})
        """), {
            "archive_batch_no": archive_batch_no,
            "archived_at": now,
            "archived_by": archived_by,
        })

        s.execute(text(f"""
            INSERT INTO process_archive
            SELECT p.*, :archive_batch_no, :archived_at, :archived_by, NULL, NULL
            FROM process p
            WHERE p.material_id IN ({ids})
        """), {
            "archive_batch_no": archive_batch_no,
            "archived_at": now,
            "archived_by": archived_by,
        })

        s.execute(text(f"""
            INSERT INTO product_archive
            SELECT p.*, :archive_batch_no, :archived_at, :archived_by, NULL, NULL
            FROM product p
            WHERE p.material_id IN ({ids})
        """), {
            "archive_batch_no": archive_batch_no,
            "archived_at": now,
            "archived_by": archived_by,
        })

        s.execute(text(f"DELETE FROM product WHERE material_id IN ({ids})"))
        s.execute(text(f"DELETE FROM process WHERE material_id IN ({ids})"))
        s.execute(text(f"DELETE FROM assemble WHERE material_id IN ({ids})"))
        s.execute(text(f"DELETE FROM material WHERE id IN ({ids})"))

        s.commit()

        return {
            "success": True,
            "archive_batch_no": archive_batch_no,
        }

    except Exception as e:
        s.rollback()
        return {
            "success": False,
            "error": str(e),
        }

    finally:
        s.close()


@archiveTable.route('/archiveWarehouseOrders', methods=['POST'])
def archive_warehouse_orders():
    print("archiveWarehouseOrders...")

    data = request.get_json() or {}

    material_ids = data.get("material_ids", [])
    archived_by = data.get("archived_by", "system")

    if not material_ids:
        return jsonify({
            "success": False,
            "error": "material_ids is empty"
        })

    result = archive_materials(
        material_ids=material_ids,
        archived_by=archived_by
    )

    return jsonify(result)


# ------------------------------------------------------------------


@archiveTable.route('/restoreWarehouseOrders', methods=['POST'])
def restore_warehouse_orders():
    print("restoreWarehouseOrders...")

    data = request.get_json() or {}

    archive_batch_no = data.get("archive_batch_no")

    if not archive_batch_no:
        return jsonify({
            "success": False,
            "error": "archive_batch_no is required"
        })

    s = Session()

    try:

        # ------------------------------------------------------
        # material
        # ------------------------------------------------------

        s.execute(text("""
            INSERT INTO material
            SELECT
                m.id,
                m.abnormal_cause_id,
                m.order_num,
                m.material_num,
                m.material_comment,
                m.material_qty,
                m.delivery_qty,
                m.total_delivery_qty,
                m.input_disable,
                m.material_date,
                m.material_delivery_date,
                m.isBom,
                m.isTakeOk,
                m.isShow,
                m.isAssembleAlarm,
                m.isAssembleAlarmRpt,
                m.isAssembleStation1TakeOk,
                m.isAssembleStation2TakeOk,
                m.isAssembleStation3TakeOk,
                m.isAssembleStationShow,
                m.assemble_qty,
                m.total_assemble_qty,
                m.whichStation,
                m.show1_ok,
                m.show2_ok,
                m.show3_ok,
                m.move_by_process_type,
                m.move_by_automatic_or_manual,
                m.shortage_note,
                m.merge_enabled,
                m.process_steps,
                m.process_step_enable,
                m.create_at
            FROM material_archive m
            WHERE m.archive_batch_no = :archive_batch_no
        """), {
            "archive_batch_no": archive_batch_no
        })

        # ------------------------------------------------------
        # assemble
        # ------------------------------------------------------

        s.execute(text("""
            INSERT INTO assemble
            SELECT
                a.id,
                a.material_id,
                a.material_num,
                a.material_comment,
                a.seq_num,
                a.work_num,
                a.process_step_code,
                a.Incoming1_Abnormal,
                a.must_receive_qty,
                a.ask_qty,
                a.total_ask_qty,
                a.total_ask_qty_end,
                a.must_receive_end_qty,
                a.abnormal_qty,
                a.user_id,
                a.writer_id,
                a.write_date,
                a.good_qty,
                a.total_good_qty,
                a.non_good_qty,
                a.meinh_qty,
                a.completed_qty,
                a.total_completed_qty,
                a.allOk_qty,
                a.reason,
                a.confirm_comment,
                a.is_assemble_ok,
                a.currentStartTime,
                a.currentEndTime,
                a.input_disable,
                a.input_end_disable,
                a.input_allOk_disable,
                a.input_abnormal_disable,
                a.isAssembleStationShow,
                a.isWarehouseStationShow,
                a.alarm_enable,
                a.alarm_message,
                a.isAssembleFirstAlarm,
                a.isAssembleFirstAlarm_message,
                a.isAssembleFirstAlarm_qty,
                a.whichStation,
                a.show1_ok,
                a.show2_ok,
                a.show3_ok,
                a.update_time,
                a.create_at,
                a.is_copied_from_id,
                a.schedule_id
            FROM assemble_archive a
            WHERE a.archive_batch_no = :archive_batch_no
        """), {
            "archive_batch_no": archive_batch_no
        })

        # ------------------------------------------------------
        # process
        # ------------------------------------------------------

        s.execute(text("""
            INSERT INTO process
            SELECT
                p.id,
                p.material_id,
                p.assemble_id,
                p.has_started,
                p.user_id,
                p.user_delegate_id,
                p.begin_time,
                p.end_time,
                p.period_time,
                p.pause_time,
                p.pause_started_at,
                p.elapsedActive_time,
                p.str_elapsedActive_time,
                p.is_pause,
                p.process_type,
                p.process_work_time_qty,
                p.must_allOk_qty,
                p.allOk_qty,
                p.isAllOk,
                p.normal_work_time,
                p.abnormal_cause_message,
                p.create_at
            FROM process_archive p
            WHERE p.archive_batch_no = :archive_batch_no
        """), {
            "archive_batch_no": archive_batch_no
        })

        # ------------------------------------------------------
        # product
        # ------------------------------------------------------

        s.execute(text("""
            INSERT INTO product
            SELECT
                p.id,
                p.material_id,
                p.product_qty,
                p.allOk_qty,
                p.create_at
            FROM product_archive p
            WHERE p.archive_batch_no = :archive_batch_no
        """), {
            "archive_batch_no": archive_batch_no
        })

        # ------------------------------------------------------
        # 更新 restore 時間
        # ------------------------------------------------------

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        s.execute(text("""
            UPDATE material_archive
            SET restored_at = :restored_at
            WHERE archive_batch_no = :archive_batch_no
        """), {
            "restored_at": now,
            "archive_batch_no": archive_batch_no
        })

        s.commit()

        return jsonify({
            "success": True,
            "archive_batch_no": archive_batch_no
        })

    except Exception as e:
        s.rollback()

        return jsonify({
            "success": False,
            "error": str(e)
        })

    finally:
        s.close()


# ------------------------------------------------------------------


@archiveTable.route('/listArchiveBatches', methods=['POST'])
def list_archive_batches():
    print("listArchiveBatches...")

    s = Session()

    try:

        rows = s.execute(text("""
            SELECT
                archive_batch_no,
                archived_at,
                archived_by,
                restored_at,
                COUNT(*) AS total_count
            FROM material_archive
            GROUP BY archive_batch_no
            ORDER BY archived_at DESC
        """)).fetchall()

        results = []

        for r in rows:
            results.append({
                "archive_batch_no": r.archive_batch_no,
                "archived_at": str(r.archived_at),
                "archived_by": r.archived_by,
                "restored_at": str(r.restored_at) if r.restored_at else None,
                "total_count": int(r.total_count or 0),
            })

        return jsonify({
            "success": True,
            "data": results
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })

    finally:
        s.close()