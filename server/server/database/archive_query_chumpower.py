from sqlalchemy import text

from database.tables import Session


def get_warehouse_history(source="active"):

    s = Session()

    try:

        if source == "active":

            sql = """
                SELECT
                    m.id,
                    m.order_num,
                    m.material_num,
                    m.material_comment AS comment,
                    m.material_delivery_date AS delivery_date,
                    m.total_allOk_qty,
                    m.material_stockin_date,
                    '正式表' AS source_table,
                    '' AS archive_batch_no
                FROM material m
                WHERE m.total_allOk_qty > 0
                ORDER BY m.id DESC
            """

        elif source == "archive":

            sql = """
                SELECT
                    m.id,
                    m.order_num,
                    m.material_num,
                    m.material_comment AS comment,
                    m.material_delivery_date AS delivery_date,
                    m.total_allOk_qty,
                    m.material_stockin_date,
                    '封存表' AS source_table,
                    m.archive_batch_no
                FROM material_archive m
                ORDER BY m.id DESC
            """

        else:

            sql = """
                SELECT
                    m.id,
                    m.order_num,
                    m.material_num,
                    m.material_comment AS comment,
                    m.material_delivery_date AS delivery_date,
                    m.total_allOk_qty,
                    m.material_stockin_date,
                    '正式表' AS source_table,
                    '' AS archive_batch_no
                FROM material m
                WHERE m.total_allOk_qty > 0

                UNION ALL

                SELECT
                    m.id,
                    m.order_num,
                    m.material_num,
                    m.material_comment AS comment,
                    m.material_delivery_date AS delivery_date,
                    m.total_allOk_qty,
                    m.material_stockin_date,
                    '封存表' AS source_table,
                    m.archive_batch_no
                FROM material_archive m

                ORDER BY id DESC
            """

        result = s.execute(text(sql))

        rows = []

        for row in result.mappings():

            rows.append(dict(row))

        return {
            "success": True,
            "items": rows,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }

    finally:

        s.close()
