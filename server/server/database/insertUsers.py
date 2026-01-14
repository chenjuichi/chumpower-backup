from tables import User, Setting, Session

import pymysql
from sqlalchemy import exc

from werkzeug.security import generate_password_hash


# --------------------------


s = Session()

# create setting table data
obj_list = []
settings = [                                                                                  #  1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7
  {'items_per_page': -1,  'message': '#f9f9f9#f9f9f9', 'lastRoutingName': 'Main', 'routingPriv': '1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1'},
  {'items_per_page': 10, 'message': 'hello user2', 'lastRoutingName': '',     'routingPriv':    '1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0'},
  {                      'message': 'hello user3', 'lastRoutingName': '',     'routingPriv':    '0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0'},
  {                      'message': 'hello user4', 'lastRoutingName': '',     'routingPriv':    '0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0'},
  {                      'message': 'hello user5', 'lastRoutingName': '',     'routingPriv':    '0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0'},
  {                      'message': 'hello user6', 'lastRoutingName': '',     'routingPriv':    '0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0'},
  {                      'message': 'hello user7', 'lastRoutingName': '',     'routingPriv':    '0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0'},
  {                      'message': 'hello user8', 'lastRoutingName': '',     'routingPriv':    '0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0'},
  {                      'message': 'hello user9', 'lastRoutingName': '',     'routingPriv':    '0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0'},
  {                      'message': 'hello user10', 'lastRoutingName': '',     'routingPriv':   '0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0'},
  {'items_per_page': 5,  'message': '#f9f9f9#f9f9f9', 'lastRoutingName': 'Main', 'routingPriv': '1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1'},

  {'items_per_page': 5,  'message': '#f9f9f9#f9f9f9', 'lastRoutingName': 'Main', 'routingPriv': '1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1'},
  {'items_per_page': 5,  'message': '#f9f9f9#f9f9f9', 'lastRoutingName': 'Main', 'routingPriv': '1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1'},
  {'items_per_page': 5,  'message': '#f9f9f9#f9f9f9', 'lastRoutingName': 'Main', 'routingPriv': '1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1'},
  {'items_per_page': 5,  'message': '#f9f9f9#f9f9f9', 'lastRoutingName': 'Main', 'routingPriv': '1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1'},
  {'items_per_page': 5,  'message': '#f9f9f9#f9f9f9', 'lastRoutingName': 'Main', 'routingPriv': '1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1'},

  #{'items_per_page': 5,  'message': '#f9f9f9#f9f9f9', 'pdf__manager': 1, 'lastRoutingName': 'Main', 'routingPriv': '1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1'},
  #{'items_per_page': 5,  'message': '#f9f9f9#f9f9f9', 'pdf__manager': 2, 'lastRoutingName': 'Main', 'routingPriv': '1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1'},
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


# insert 10 users
#s = Session()
user_count = 0

# user 1
emp_id = "00008241"
emp_name = "陳瑞琪"
password = "a12345"
dep_name = "11112260-配件生管課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                #password=generate_password_hash(password, method='sha256'))
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 2
emp_id = "01012002"
emp_name = "林淑雲"
password = "a12345"
dep_name = "11112260-配件生管課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                #password=generate_password_hash(password, method='sha256'))
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 3
emp_id = "01018054"
emp_name = "白旭珊"
password = "a12345"
dep_name = "11112260-配件生管課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                #password=generate_password_hash(password, method='sha256'))
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 4
emp_id = "01004005"
emp_name = "陳世玟"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                #password=generate_password_hash(password, method='sha256'))
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 5
emp_id = "01023027"
emp_name = "洪芷瞳"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                #password=generate_password_hash(password, method='sha256'))
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 6
emp_id = "01024010"
emp_name = "吳靜茹"
dep_name = "11112251-配件倉儲課"
password = "a12345"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 7
emp_id = "01007001"
emp_name = "陰文龍"
password = "a12345"
dep_name = "11112251-配件倉儲課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 8
emp_id = "01023034"
emp_name = "劉時瑋"
password = "a12345"
dep_name = "11112220-配件加工課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 9
emp_id = "01010001"
emp_name = "廖萬潔"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 10
emp_id = "01018070"
emp_name = "張家瑞"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 11
emp_id = "01002002"
emp_name = "莊依瑾"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 12
emp_id = "01010016"
emp_name = "林信廷"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 13
emp_id = "01011010"
emp_name = "丁柏夫"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 14
emp_id = "01024013"
emp_name = "林湘絨"
password = "a12345"
dep_name = "11112260-配件生管課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                #password=generate_password_hash(password, method='sha256'))
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 15
emp_id = "01010017"
emp_name = "郭中一"
password = "a12345"
dep_name = "11112251-配件倉儲課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 16
emp_id = "01011018"
emp_name = "謝桂芳"
password = "a12345"
dep_name = "11112251-配件倉儲課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 17
emp_id = "01023030"
emp_name = "白旻展"
password = "a12345"
dep_name = "11112251-配件倉儲課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 18
emp_id = "01011002"
emp_name = "陳惠美"
password = "a12345"
dep_name = "11112251-配件倉儲課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 19
emp_id = "01017009"
emp_name = "蘇拉朋"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 20
emp_id = "01004003"
emp_name = "廖淑惠"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 21
emp_id = "01007003"
emp_name = "林美伶"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 22
emp_id = "01008003"
emp_name = "柯宜佩"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 23
emp_id = "01010015"
emp_name = "林桂春"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 24
emp_id = "01011001"
emp_name = "張文菁"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 25
emp_id = "01011019"
emp_name = "吳能惠"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 26
emp_id = "01025009"
emp_name = "趙尉佑"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 27
emp_id = "01016022"
emp_name = "廖柏維"
password = "a12345"
dep_name = "11112220-配件加工課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 28
emp_id = "01025011"
emp_name = "曹之理"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 29
emp_id = "01014013"
emp_name = "陳俊宏"
password = "a12345"
dep_name = "11112220-配件加工課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 30
emp_id = "01017026"
emp_name = "黃昱翔"
password = "a12345"
dep_name = "11112220-配件加工課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 31
emp_id = "01018021"
emp_name = "塔瓦猜"
password = "a12345"
dep_name = "11112220-配件加工課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 32
emp_id = "01020005"
emp_name = "阿迪順"
password = "a12345"
dep_name = "11112220-配件加工課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 33
emp_id = "01024002"
emp_name = "塔拉提"
password = "a12345"
dep_name = "11112220-配件加工課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 34
emp_id = "01992001"
emp_name = "吳昆成"
password = "a12345"
dep_name = "11112220-配件加工課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1

# user 35
emp_id = "01025014"
emp_name = "林恆億"
password = "a12345"
dep_name = "11112230-配件組立課"
new_user = User(emp_id=emp_id, emp_name=emp_name, dep_name=dep_name, perm_id=2, setting_id=1,
                password=generate_password_hash(password, method='scrypt'))
s.add(new_user)
user_count += 1


try:
  s.commit()
  #print("User data committed successfully")
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

print('insert ' + str(user_count) + ' users is ok...')

