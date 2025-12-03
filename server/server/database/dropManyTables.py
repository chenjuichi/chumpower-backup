from tables import Session, engine
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy import text, MetaData

s = Session()

def drop_table(table_name):
    #base = declarative_base()
    metadata = MetaData()
    metadata.reflect(bind=engine, only=[table_name])
    table = metadata.tables.get(table_name)
    if table is not None:
        print("Dropping table", table_name)
        #base.metadata.drop_all(engine, [table], checkfirst=True)
        table.drop(bind=engine, checkfirst=True)
    else:
        print(f"Table {table_name} does not exist. Skipping...")

# 設定 FOREIGN_KEY_CHECKS = 0
s.execute(text('SET FOREIGN_KEY_CHECKS = 0'))

# 執行多個資料表的 DROP
drop_table('processed_file')

drop_table('bom')
drop_table('assemble')
drop_table('product')
drop_table('process')

drop_table('association_material_abnormal')
drop_table('material')
drop_table('abnormal_cause')

drop_table('p_bom')
drop_table('p_assemble')
drop_table('p_product')
drop_table('p_process')

drop_table('p_association_material_abnormal')
drop_table('p_material')
drop_table('p_abnormal_cause')

drop_table('agv')
drop_table('user_delegate')  #代理人table
drop_table('user')        # 員工table
drop_table('permission')  # 權限table
drop_table('setting')     # 部門table

# 設定 FOREIGN_KEY_CHECKS = 1
s.execute(text('SET FOREIGN_KEY_CHECKS = 1'))

s.close()

print("Drop table process completed...")