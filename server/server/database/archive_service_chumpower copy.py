from datetime import datetime

from sqlalchemy import text

from database.tables import Session


def archive_materials(material_ids, archived_by="system"):

    s = Session()

    try:

        archive_batch_no = datetime.now().strftime("ARCH%Y%m%d%H%M%S")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ids = ",".join([str(int(x)) for x in material_ids])

        # =====================================================
        # material
        # =====================================================

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

        # =====================================================
        # bom
        # =====================================================

        s.execute(text(f"""
            INSERT INTO bom_archive
            SELECT b.*, :archive_batch_no, :archived_at, :archived_by, NULL, NULL
            FROM bom b
            WHERE b.material_id IN ({ids})
        """), {
            "archive_batch_no": archive_batch_no,
            "archived_at": now,
            "archived_by": archived_by,
        })

        # =====================================================
        # assemble
        # =====================================================

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

        # =====================================================
        # process
        # =====================================================

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

        # =====================================================
        # product
        # =====================================================

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

        # =====================================================
        # delete active tables
        # =====================================================

        s.execute(text(f"""
            DELETE FROM product
            WHERE material_id IN ({ids})
        """))

        s.execute(text(f"""
            DELETE FROM process
            WHERE material_id IN ({ids})
        """))

        s.execute(text(f"""
            DELETE FROM assemble
            WHERE material_id IN ({ids})
        """))

        s.execute(text(f"""
            DELETE FROM bom
            WHERE material_id IN ({ids})
        """))

        s.execute(text(f"""
            DELETE FROM material
            WHERE id IN ({ids})
        """))

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


def restore_archive_batch(archive_batch_no):

    s = Session()

    try:

        # =====================================================
        # material
        # =====================================================

        s.execute(text("""
            INSERT INTO material
            SELECT
                id,
                abnormal_cause_id,
                order_num,
                material_num,
                material_comment,
                material_qty,
                delivery_qty,
                total_delivery_qty,
                input_disable,
                material_date,
                material_delivery_date,
                isTakeOk,
                isShow,
                isAssembleAlarm,
                isAssembleAlarmRpt,
                isAssembleStation1TakeOk,
                isAssembleStation2TakeOk,
                isAssembleStation3TakeOk,
                isAssembleStationShow,
                station1_Qty,
                station2_Qty,
                station3_Qty,
                assemble_qty,
                total_assemble_qty,
                whichStation,
                show1_ok,
                show2_ok,
                show3_ok,
                shortage_note,
                isAllOk,
                allOk_qty,
                Incoming0_Abnormal,
                Incoming2_Abnormal,
                must_allOk_qty,
                total_allOk_qty,
                isLackMaterial,
                isBatchFeeding,
                merge_enabled,
                sd_time_B109,
                sd_time_B106,
                sd_time_B110,
                move_by_automatic_or_manual,
                move_by_automatic_or_manual_2,
                move_by_process_type,
                isOpen,
                isOpenEmpId,
                hasStarted,
                startStatus,
                material_stockin_date,
                process_steps,
                process_step_enable,
                create_at,
                update_time,
                is_copied_from_id
            FROM material_archive
            WHERE archive_batch_no = :archive_batch_no
        """), {
            "archive_batch_no": archive_batch_no,
        })

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