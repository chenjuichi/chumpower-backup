from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func


try:
    from .tables import BASE
    from .tables import Material, Bom, Assemble, Process, Product
    from .p_tables import P_Material, P_Bom, P_Assemble, P_Process, P_Product
    from .archive_utils import create_archive_model

except ImportError:
    from tables import BASE
    from tables import Material, Bom, Assemble, Process, Product
    from p_tables import P_Material, P_Bom, P_Assemble, P_Process, P_Product
    from archive_utils import create_archive_model


def get_archive_extra_columns():
    return {
        'archive_batch_no': Column(String(50), index=True),
        'archived_at': Column(DateTime, server_default=func.now()),
        'archived_by': Column(String(50)),
        'restored_at': Column(DateTime, nullable=True),
        'restored_by': Column(String(50), nullable=True),
    }


# ============================================================
# 組裝線 archive tables
# ============================================================

MaterialArchive = create_archive_model(
    BASE,
    Material,
    'material_archive',
    get_archive_extra_columns(),
)

BomArchive = create_archive_model(
    BASE,
    Bom,
    'bom_archive',
    get_archive_extra_columns(),
)

AssembleArchive = create_archive_model(
    BASE,
    Assemble,
    'assemble_archive',
    get_archive_extra_columns(),
)

ProcessArchive = create_archive_model(
    BASE,
    Process,
    'process_archive',
    get_archive_extra_columns(),
)

ProductArchive = create_archive_model(
    BASE,
    Product,
    'product_archive',
    get_archive_extra_columns(),
)


# ============================================================
# 加工線 archive tables
# ============================================================

PMaterialArchive = create_archive_model(
    BASE,
    P_Material,
    'p_material_archive',
    get_archive_extra_columns(),
)

PBomArchive = create_archive_model(
    BASE,
    P_Bom,
    'p_bom_archive',
    get_archive_extra_columns(),
)

PAssembleArchive = create_archive_model(
    BASE,
    P_Assemble,
    'p_assemble_archive',
    get_archive_extra_columns(),
)

PProcessArchive = create_archive_model(
    BASE,
    P_Process,
    'p_process_archive',
    get_archive_extra_columns(),
)

PProductArchive = create_archive_model(
    BASE,
    P_Product,
    'p_product_archive',
    get_archive_extra_columns(),
)