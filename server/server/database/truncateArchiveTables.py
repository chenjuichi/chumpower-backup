from tables import Session
from sqlalchemy import text

s = Session()


def truncate_table(table_name):
    try:
        print("Truncating archive table:", table_name)
        s.execute(text(f"TRUNCATE TABLE {table_name}"))
    except Exception as e:
        print(f"Table {table_name} truncate failed:", e)


try:
    # 關閉 foreign key
    s.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

    # 組裝線 archive
    truncate_table("bom_archive")
    truncate_table("assemble_archive")
    truncate_table("product_archive")
    truncate_table("process_archive")
    truncate_table("material_archive")

    # 加工線 archive
    truncate_table("p_bom_archive")
    truncate_table("p_assemble_archive")
    truncate_table("p_product_archive")
    truncate_table("p_process_archive")
    truncate_table("p_material_archive")

    # 若之後有建立封存批次表，也一起清
    truncate_table("archive_batch")

    # 開啟 foreign key
    s.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    s.commit()

except Exception as e:
    s.rollback()
    print("Truncate archive tables failed:", e)

finally:
    s.close()

print("Truncate archive table process completed...")