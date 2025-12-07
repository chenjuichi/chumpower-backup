# print_p_tables_sql.py
from sqlalchemy.schema import CreateTable
from tables import engine
#from p_tables import P_Material, P_AbnormalCause, P_Bom, P_Assemble, P_Product, P_Process
#from p_tables import P_Part

from p_tables import (
  p_association_material_abnormal,
  P_Material,
  P_AbnormalCause,
  P_Bom,
  P_Assemble,
  P_Product,
  P_Process,
  P_Part
)

# 把要建立的 table 都列出來
tables = [
    P_Material.__table__,
    P_AbnormalCause.__table__,
    P_Bom.__table__,
    P_Assemble.__table__,
    P_Product.__table__,
    P_Process.__table__,
    P_Part.__table__,

    p_association_material_abnormal,
]

print("SET FOREIGN_KEY_CHECKS = 0;\n")

for t in tables:
    sql = str(CreateTable(t).compile(engine))
    print(sql + ";\n")

print("SET FOREIGN_KEY_CHECKS = 1;\n")