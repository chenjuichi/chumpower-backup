import os

os.environ['SQLALCHEMY_WARN_20'] = '0'    # 設置環境變數來顯示所有與SQLAlchemy 2.0相關的警告
os.environ['SQLALCHEMY_SILENCE_UBER_WARNING'] = '0'   # 設置環境變數來靜音指定的警告

from datetime import datetime

from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean, func, ForeignKey, create_engine
from sqlalchemy import text
#from sqlalchemy.orm import relationship, backref, sessionmaker
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker, declarative_base  #for 2.0版

BASE = declarative_base()   # 宣告一個映射, 建立一個基礎類別


# ------------------------------------------------------------------


class User(BASE):
  __tablename__ = 'user'

  id = Column(Integer, primary_key=True, autoincrement=True)
  emp_id = Column(String(8), nullable=False)              #員工編號 8碼
  emp_name = Column(String(10), nullable=False)           #員工姓名
  dep_name = Column(String(20), nullable=False)           #部門名稱
  password = Column(String(255))                          #預設值 a12345
  perm_id = Column(Integer, ForeignKey('permission.id'))  # 一對多(多)
  setting_id = Column(Integer, ForeignKey('setting.id'))  # 一對多(多)
  isRemoved = Column(Boolean, default=True)               # false:已經刪除資料
  isOnline = Column(Boolean, default=False)               # false:user不在線上(logout)
  #_production = relationship('Production', backref="user")              # 一對多(一), 生管
  #_material =  relationship('Material', backref="user")                 # 一對多(一), 備料
  #_assembler =  relationship('Assembler', backref="user")               # 一對多(一), 裝配
  #_finished_goods =  relationship('Finished_Goods', backref="user")     # 一對多(一), 成品
  create_at = Column(DateTime, server_default=func.now())

  # 定義變數輸出的內容
  def __repr__(self):
    return "id={}, emp_id={}, emp_name={}, dep_name={}, password={}, perm_id={}, setting_id={}, isRemoved={}, isOnline={}".format(
    self.id, self.emp_id, self.emp_name, self.dep_name, self.password, self.perm_id, self.setting_id, self.isRemoved, self.isOnline)

  # 定義class的dict內容
  def get_dict(self):
    return {
      'id': self.id,
      'emp_id': self.emp_id,
      'emp_name': self.emp_name,
      'dep_name': self.dep_name,
      'password': self.password,
      'perm_id': self.perm_id,
      'setting_id': self.setting_id,
      'isRemoved': self.isRemoved,
      'isOnline': self.isOnline,
    }


# ------------------------------------------------------------------


class Permission(BASE):  # 一對多, "一":permission, "多":user
    __tablename__ = 'permission'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 0:none, 1:system, 2:admin, 3: staff, 4:member
    auth_code = Column(Integer, default=0)
    auth_name = Column(String(10), default='none')
    # 一對多(一)
    # 設定cascade後,可刪除級關連
    # 不設定cascade, 則perm_id為空的, 但沒刪除級關連
    _user = relationship('User', backref='permission')  #一對多(一)
    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
      return "id={}, auth_code={}".format(self.id, self.auth_code)

    # 定義class的dict內容
    def get_dict(self):
      return {
        'id': self.id,
        'auth_code': self.auth_code,
      }


# ------------------------------------------------------------------


class Setting(BASE):  # 一對多, "一":permission, "多":user
    __tablename__ = 'setting'

    id = Column(Integer, primary_key=True, autoincrement=True)
    items_per_page = Column(Integer, default=10)            # 每頁顯示行數, default=10
    isSee = Column(String(1), default=text("0"))            # 0:user沒有看公告資料
    message = Column(String(30))                            # 訊息
    routingPriv = Column(String(70), default=text("0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0"))
    lastRoutingName = Column(String(70), default=text(""))  # user最後瀏覽的網頁routing name, max 3 個, 以,分隔
    _user = relationship('User', backref='setting')         # 一對多(一 )
    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
      return "id={}, items_per_page={}, isSee={}, message={}, lastRoutingName={}".format(
      self.id, self.items_per_page, self.isSee, self.message, self.lastRoutingName)

    # 定義class的dict內容
    def get_dict(self):
      return {
        'id': self.id,
        'items_per_page': self.items_per_page,
        'isSee': self.isSee,
        'message': self.message,
        'lastRoutingName': self.lastRoutingName,
      }


# ------------------------------------------------------------------


# 建立連線
engine = create_engine("mysql+pymysql://root:77974590@localhost:3306/chumpower?charset=utf8mb4", echo=False)
if __name__ == "__main__":
  # 建立表格
  BASE.metadata.create_all(engine)
  print("Tables created successfully...")

  # 修改字符集設定
  # 中文字需要 4-bytes 來作為 UTF-8 encoding.
  # MySQL databases and tables are created using a UTF-8 with 3-bytes encoding.
  # 儲存中文字, 改為使用 utf8mb4 字符集設定

  with engine.connect() as connection:   # for 2.0版
      connection.execute(text("ALTER DATABASE chumpower CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;"))
      connection.execute(text("ALTER TABLE user CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
      connection.execute(text("ALTER TABLE permission CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
      connection.execute(text("ALTER TABLE setting CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
      connection.execute(text("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"))

# 將己連結的資料庫engine綁定到這個session
Session = sessionmaker(bind=engine)