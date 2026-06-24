from tables import Session
from sqlalchemy import text

s = Session()

def truncate_table(table_name):
    try:
        print("Truncating table", table_name)
        s.execute(text(f"TRUNCATE TABLE {table_name}"))
    except Exception as e:
        print(f"Table {table_name} truncate failed:", e)

# 關閉 foreign key
s.execute(text('SET FOREIGN_KEY_CHECKS = 0'))

truncate_table('processed_file')
# 組裝線正式表
truncate_table('bom')
truncate_table('assemble')
truncate_table('product')
truncate_table('process')

truncate_table('association_material_abnormal')
truncate_table('material')
truncate_table('abnormal_cause')

# 加工線正式表
truncate_table('p_bom')
truncate_table('p_assemble')
truncate_table('p_product')
truncate_table('p_process')

truncate_table('p_association_material_abnormal')
truncate_table('p_material')
truncate_table('p_abnormal_cause')

truncate_table('p_part')

# 組裝線 archive 表
truncate_table('bom_archive')
truncate_table('assemble_archive')
truncate_table('product_archive')
truncate_table('process_archive')
truncate_table('material_archive')

# 加工線 archive 表
truncate_table('p_bom_archive')
truncate_table('p_assemble_archive')
truncate_table('p_product_archive')
truncate_table('p_process_archive')
truncate_table('p_material_archive')

truncate_table('agv')
truncate_table('user_delegate')
truncate_table('user')
truncate_table('permission')
truncate_table('setting')

# 開啟 foreign key
s.execute(text('SET FOREIGN_KEY_CHECKS = 1'))

s.commit()
s.close()

print("Truncate table process completed...")