from sqlalchemy import text
from tables import engine


def safe_add_column(conn, table_name, column_sql, column_name):

    check_sql = text(f"""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = :table_name
        AND COLUMN_NAME = :column_name
    """)

    result = conn.execute(check_sql, {
        "table_name": table_name,
        "column_name": column_name,
    }).scalar()

    if result == 0:

        alter_sql = text(f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_sql}
        """)

        conn.execute(alter_sql)

        print(f"ADD COLUMN OK: {table_name}.{column_name}")

    else:

        print(f"SKIP COLUMN: {table_name}.{column_name}")


ARCHIVE_SQLS = [

    # =========================================================
    # 組裝線
    # =========================================================

    """
    CREATE TABLE IF NOT EXISTS material_archive LIKE material
    """,

    """
    ALTER TABLE material_archive
    ADD COLUMN archive_batch_no VARCHAR(50),
    ADD COLUMN archived_at DATETIME,
    ADD COLUMN archived_by VARCHAR(20),
    ADD COLUMN restored_at DATETIME NULL,
    ADD COLUMN restore_batch_no VARCHAR(50) NULL
    """,

    """
    CREATE TABLE IF NOT EXISTS bom_archive LIKE bom
    """,

    """
    ALTER TABLE bom_archive
    ADD COLUMN archive_batch_no VARCHAR(50),
    ADD COLUMN archived_at DATETIME,
    ADD COLUMN archived_by VARCHAR(20),
    ADD COLUMN restored_at DATETIME NULL,
    ADD COLUMN restore_batch_no VARCHAR(50) NULL
    """,

    """
    CREATE TABLE IF NOT EXISTS assemble_archive LIKE assemble
    """,

    """
    ALTER TABLE assemble_archive
    ADD COLUMN archive_batch_no VARCHAR(50),
    ADD COLUMN archived_at DATETIME,
    ADD COLUMN archived_by VARCHAR(20),
    ADD COLUMN restored_at DATETIME NULL,
    ADD COLUMN restore_batch_no VARCHAR(50) NULL
    """,

    """
    CREATE TABLE IF NOT EXISTS process_archive LIKE process
    """,

    """
    ALTER TABLE process_archive
    ADD COLUMN archive_batch_no VARCHAR(50),
    ADD COLUMN archived_at DATETIME,
    ADD COLUMN archived_by VARCHAR(20),
    ADD COLUMN restored_at DATETIME NULL,
    ADD COLUMN restore_batch_no VARCHAR(50) NULL
    """,

    """
    CREATE TABLE IF NOT EXISTS product_archive LIKE product
    """,

    """
    ALTER TABLE product_archive
    ADD COLUMN archive_batch_no VARCHAR(50),
    ADD COLUMN archived_at DATETIME,
    ADD COLUMN archived_by VARCHAR(20),
    ADD COLUMN restored_at DATETIME NULL,
    ADD COLUMN restore_batch_no VARCHAR(50) NULL
    """,

    # =========================================================
    # 加工線
    # =========================================================

    """
    CREATE TABLE IF NOT EXISTS p_material_archive LIKE p_material
    """,

    """
    ALTER TABLE p_material_archive
    ADD COLUMN archive_batch_no VARCHAR(50),
    ADD COLUMN archived_at DATETIME,
    ADD COLUMN archived_by VARCHAR(20),
    ADD COLUMN restored_at DATETIME NULL,
    ADD COLUMN restore_batch_no VARCHAR(50) NULL
    """,

    """
    CREATE TABLE IF NOT EXISTS p_bom_archive LIKE p_bom
    """,

    """
    ALTER TABLE p_bom_archive
    ADD COLUMN archive_batch_no VARCHAR(50),
    ADD COLUMN archived_at DATETIME,
    ADD COLUMN archived_by VARCHAR(20),
    ADD COLUMN restored_at DATETIME NULL,
    ADD COLUMN restore_batch_no VARCHAR(50) NULL
    """,

    """
    CREATE TABLE IF NOT EXISTS p_assemble_archive LIKE p_assemble
    """,

    """
    ALTER TABLE p_assemble_archive
    ADD COLUMN archive_batch_no VARCHAR(50),
    ADD COLUMN archived_at DATETIME,
    ADD COLUMN archived_by VARCHAR(20),
    ADD COLUMN restored_at DATETIME NULL,
    ADD COLUMN restore_batch_no VARCHAR(50) NULL
    """,

    """
    CREATE TABLE IF NOT EXISTS p_process_archive LIKE p_process
    """,

    """
    ALTER TABLE p_process_archive
    ADD COLUMN archive_batch_no VARCHAR(50),
    ADD COLUMN archived_at DATETIME,
    ADD COLUMN archived_by VARCHAR(20),
    ADD COLUMN restored_at DATETIME NULL,
    ADD COLUMN restore_batch_no VARCHAR(50) NULL
    """,

    """
    CREATE TABLE IF NOT EXISTS p_product_archive LIKE p_product
    """,

    """
    ALTER TABLE p_product_archive
    ADD COLUMN archive_batch_no VARCHAR(50),
    ADD COLUMN archived_at DATETIME,
    ADD COLUMN archived_by VARCHAR(20),
    ADD COLUMN restored_at DATETIME NULL,
    ADD COLUMN restore_batch_no VARCHAR(50) NULL
    """,

]


def create_archive_tables():

    with engine.begin() as conn:

        table_sqls = [

            ("material_archive", "material"),
            ("bom_archive", "bom"),
            ("assemble_archive", "assemble"),
            ("process_archive", "process"),
            ("product_archive", "product"),

            ("p_material_archive", "p_material"),
            ("p_bom_archive", "p_bom"),
            ("p_assemble_archive", "p_assemble"),
            ("p_process_archive", "p_process"),
            ("p_product_archive", "p_product"),
        ]

        for archive_table, source_table in table_sqls:

            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {archive_table}
                LIKE {source_table}
            """))

            print(f"CREATE OK: {archive_table}")

            safe_add_column(
                conn,
                archive_table,
                "archive_batch_no VARCHAR(50)",
                "archive_batch_no"
            )

            safe_add_column(
                conn,
                archive_table,
                "archived_at DATETIME",
                "archived_at"
            )

            safe_add_column(
                conn,
                archive_table,
                "archived_by VARCHAR(20)",
                "archived_by"
            )

            safe_add_column(
                conn,
                archive_table,
                "restored_at DATETIME NULL",
                "restored_at"
            )

            safe_add_column(
                conn,
                archive_table,
                "restore_batch_no VARCHAR(50) NULL",
                "restore_batch_no"
            )


if __name__ == "__main__":

    create_archive_tables()
    print("Archive tables created successfully...")