from tables import User, Setting, Session

import pymysql
from sqlalchemy import exc

from werkzeug.security import generate_password_hash


# --------------------------


s = Session()

# create setting table data
obj_list = []
settings = [
  {'items_per_page': 5,  'message': 'hello1', 'lastRoutingName': 'Main', 'routingPriv': '1,1,1,1,0,0,1,1'},
  {'items_per_page': 10, 'message': 'hello2', 'lastRoutingName': '',     'routingPriv': '1,1,1,1,0,0,1,1'},
  {                      'message': 'hello3', 'lastRoutingName': '',     'routingPriv': '1,1,1,1,0,0,1,1'},
  {                      'message': 'hello4', 'lastRoutingName': '',     'routingPriv': '1,1,1,1,0,0,1,1'},
]

for record in settings:
    user_setting = Setting(**record)
    obj_list.append(user_setting)

s.add_all(obj_list)

try:
  s.commit()
  print("Set data committed successfully")
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


# insert 4 users
#s = Session()
# user 1
emp_id = "8241"
emp_name = "陳瑞琪"
password = "a12345"
dep_name = "部門2"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                #password=generate_password_hash(password, method='sha256'))
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)

# user 2
emp_id = "10507"
emp_name = "李宛玲"
dep_name = "部門1"
password = "a12345"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=2,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)

# user 3
emp_id = "10323"
emp_name = "林政仰"
password = "a12345"
dep_name = "部門3"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=3,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)

# user 4
emp_id = "11228"
emp_name = "紀錦川"
password = "a12345"
dep_name = "部門4"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=3,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)

try:
  s.commit()
  print("User data committed successfully")
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

print("insert 4 user data is ok...")

