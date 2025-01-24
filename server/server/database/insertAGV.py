from tables import Agv, Session

import pymysql
from sqlalchemy import exc


# --------------------------


s = Session()

agv_station = 1
new_agv = Agv(station=agv_station)
s.add(new_agv)

try:
  s.commit()
  print("Agv data committed successfully")
except pymysql.err.IntegrityError as e:
  print(f"IntegrityError: {e}")
  s.rollback()
except exc.IntegrityError as e:
  print(f"SQLAlchemy IntegrityError: {e}")
  s.rollback()
except Exception as e:
  print(f"Exception: {e}")
  s.rollback()

# --------------------------

s.close()

print("insert 1 agv data is ok...")

