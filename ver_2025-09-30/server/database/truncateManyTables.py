from tables import Session, engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import text, MetaData

s = Session()
def truncate_table(table_name):
  #base = declarative_base()
  metadata = MetaData()
  metadata.reflect(bind=engine)
  table = metadata.tables.get(table_name)
  if table is not None:
      print(f"Truncating {table_name} table")
      del_name = text(f'TRUNCATE TABLE chumpower.{table_name}')      ;
      s.execute(del_name)

s.execute(text('SET FOREIGN_KEY_CHECKS = 0'))

truncate_table('bom')
truncate_table('assemble')
truncate_table('material')

truncate_table('process')

truncate_table('user')        # 員工table
truncate_table('permission')  # 權限table
truncate_table('setting')     # 部門table

s.execute(text('SET FOREIGN_KEY_CHECKS = 1'))

s.close()

print("truncate table is ok...")
