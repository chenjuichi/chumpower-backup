
try:
    from .tables import BASE

    from .p_tables import (
        P_Material,
        P_Bom,
        P_Assemble,
        P_Process,
        P_Product
    )

    from .archive_utils import create_archive_model
    from .archive_tables import archive_extra_columns

except ImportError:
    from tables import BASE

    from p_tables import (
        P_Material,
        P_Bom,
        P_Assemble,
        P_Process,
        P_Product
    )

    from .archive_utils import create_archive_model
    from .archive_tables import get_archive_extra_columns


P_MaterialArchive = create_archive_model(
    BASE,
    P_Material,
    'p_material_archive',
    get_archive_extra_columns(),
)

P_BomArchive = create_archive_model(
    BASE,
    P_Bom,
    'p_bom_archive',
    get_archive_extra_columns(),
)

P_AssembleArchive = create_archive_model(
    BASE,
    P_Assemble,
    'p_assemble_archive',
    get_archive_extra_columns(),
)

P_ProcessArchive = create_archive_model(
    BASE,
    P_Process,
    'p_process_archive',
    get_archive_extra_columns(),
)

P_ProductArchive = create_archive_model(
    BASE,
    P_Product,
    'p_product_archive',
    get_archive_extra_columns(),
)