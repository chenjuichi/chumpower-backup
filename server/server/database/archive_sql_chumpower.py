from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String,
    DateTime,
    inspect,
)

from tables import (
    engine,
    Material,
    Bom,
    Assemble,
    Process,
    Product,
)

from p_tables import (
    P_Material,
    P_Bom,
    P_Assemble,
    P_Process,
    P_Product,
)


ARCHIVE_TABLE_MAP = [
    ("material_archive", Material.__table__),
    ("bom_archive", Bom.__table__),
    ("assemble_archive", Assemble.__table__),
    ("process_archive", Process.__table__),
    ("product_archive", Product.__table__),

    ("p_material_archive", P_Material.__table__),
    ("p_bom_archive", P_Bom.__table__),
    ("p_assemble_archive", P_Assemble.__table__),
    ("p_process_archive", P_Process.__table__),
    ("p_product_archive", P_Product.__table__),
]


def clone_table_for_archive(archive_table_name, source_table):
    metadata = MetaData()

    columns = [
        Column("archive_id", Integer, primary_key=True, autoincrement=True),
    ]

    for col in source_table.columns:
        columns.append(
            Column(
                col.name,
                col.type,
                primary_key=False,
                nullable=col.nullable,
                autoincrement=False,
            )
        )

    extra_columns = [
        Column("archive_batch_no", String(50), nullable=True),
        Column("archived_at", DateTime, nullable=True),
        Column("archived_by", String(50), nullable=True),
        Column("restored_at", DateTime, nullable=True),
        Column("restored_by", String(50), nullable=True),
    ]

    existing = {c.name for c in columns}

    for c in extra_columns:
        if c.name not in existing:
            columns.append(c)

    archive_table = Table(
        archive_table_name,
        metadata,
        *columns,
        extend_existing=True,
    )

    metadata.create_all(engine, tables=[archive_table])

    return archive_table


def drop_all_archive_tables():
    metadata = MetaData()

    inspector = inspect(engine)

    # 子表先 drop，主表後 drop
    drop_order = [
        "product_archive",
        "process_archive",
        "assemble_archive",
        "bom_archive",
        "material_archive",

        "p_product_archive",
        "p_process_archive",
        "p_assemble_archive",
        "p_bom_archive",
        "p_material_archive",
    ]

    with engine.begin() as conn:
        for table_name in drop_order:
            if inspector.has_table(table_name):
                t = Table(table_name, metadata, autoload_with=engine)
                t.drop(bind=conn, checkfirst=True)
                print(f"DROP OK: {table_name}")
            else:
                print(f"SKIP DROP: {table_name}")


def create_all_archive_tables():
    inspector = inspect(engine)

    for archive_table_name, source_table in ARCHIVE_TABLE_MAP:
        if inspector.has_table(archive_table_name):
            print(f"SKIP CREATE: {archive_table_name} already exists")
            continue

        clone_table_for_archive(
            archive_table_name=archive_table_name,
            source_table=source_table,
        )

        print(f"CREATE OK: {archive_table_name}")


def rebuild_all_archive_tables():
    drop_all_archive_tables()
    create_all_archive_tables()


if __name__ == "__main__":
    rebuild_all_archive_tables()
    print("Archive tables rebuild finished.")