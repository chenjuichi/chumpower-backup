from tables import Session, engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import text, MetaData

s = Session()
def drop_table(table_name):
    base = declarative_base()
    metadata = MetaData()
    metadata.reflect(bind=engine)
    table = metadata.tables.get(table_name)
    if table is not None:
        print("Dropping table", table_name)
        base.metadata.drop_all(engine, [table], checkfirst=True)

# 設定 FOREIGN_KEY_CHECKS = 0
s.execute(text('SET FOREIGN_KEY_CHECKS = 0'))

# 執行多個資料表的 DROP
drop_table('bom')
drop_table('assemble')
drop_table('material')
drop_table('process')
drop_table('agv')
drop_table('user')        # 員工table
drop_table('permission')  # 權限table
drop_table('setting')     # 部門table

# 設定 FOREIGN_KEY_CHECKS = 1
s.execute(text('SET FOREIGN_KEY_CHECKS = 1'))

s.close()

print("Drop table is ok...")