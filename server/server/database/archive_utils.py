from sqlalchemy import Column


def clone_column(column):
    return Column(
        column.type,
        primary_key=column.primary_key,
        nullable=column.nullable,
        default=column.default,
        server_default=column.server_default,
        index=column.index,
        unique=column.unique,
    )


def create_archive_model(base, source_model, archive_table_name, extra_columns=None):

    attrs = {
        '__tablename__': archive_table_name,
    }

    # 複製正式表欄位
    for column in source_model.__table__.columns:
        attrs[column.name] = clone_column(column)

    # 加 archive 額外欄位
    if extra_columns:
        attrs.update(extra_columns)

    # 建立 class
    archive_model = type(
        f"{source_model.__name__}Archive",
        (base,),
        attrs
    )

    return archive_model