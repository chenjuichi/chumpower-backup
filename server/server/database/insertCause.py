from tables import AbnormalCause, Session

import pymysql
from sqlalchemy import exc


# --------------------------


s = Session()

new_cause = AbnormalCause(number='109001', message='尺寸異常')
s.add(new_cause)
new_cause = AbnormalCause(number='109002', message='精度異常')
s.add(new_cause)
new_cause = AbnormalCause(number='109003', message='表面粗度度異常')
s.add(new_cause)
new_cause = AbnormalCause(number='109004', message='表面損傷')
s.add(new_cause)
new_cause = AbnormalCause(number='109005', message='零件生鏽')
s.add(new_cause)

try:
  s.commit()
  print("AbnormalCause data committed successfully")
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

print("insert 5 AbnormalCause data is ok...")