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

truncate_table('p_bom')
truncate_table('p_assemble')
truncate_table('p_product')
truncate_table('p_process')

truncate_table('p_association_material_abnormal')
truncate_table('p_material')
truncate_table('p_abnormal_cause')

s.execute(text('SET FOREIGN_KEY_CHECKS = 1'))

s.close()

print("truncate table is ok...")
