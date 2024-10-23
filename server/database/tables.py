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
  #_process =  relationship('Process', backref="user")                 # 一對多(一), 備料
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


class Material(BASE):
    __tablename__ = 'material'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_num = Column(String(20), nullable=False)                  #訂單編號
    material_num = Column(String(20), nullable=False)               #成品料號
    material_comment = Column(String(70), nullable=False)           #料號說明
    material_qty = Column(Integer, nullable=False)                  #(成品)需求數量
    material_date = Column(String(12), nullable=False)              #建置日期
    material_delivery_date = Column(String(12), nullable=False)     #交期
    isTakeOk = Column(Boolean, default=False)                       # true:檢料完成
    isShow = Column(Boolean, default=False)                         # true: 檢料完成且已callAGV, disable show it
    isAssembleStation1TakeOk = Column(Boolean, default=False)       # true:組裝站製程1完成
    isAssembleStation2TakeOk = Column(Boolean, default=False)       # true:組裝站製程2完成
    isAssembleStation3TakeOk = Column(Boolean, default=False)       # true:組裝站製程3完成
    station1_Qty = Column(Integer)
    station2_Qty = Column(Integer)
    station3_Qty = Column(Integer)
    whichStation = Column(Integer, default=1)                       # 目標途程, 目前途程為1:檢料, 2: 組裝, 3:成品
    show1_ok = Column(String(20), server_default='1')
    show2_ok = Column(String(20), server_default='0')
    show3_ok = Column(String(20), server_default='0')
    isAllOk = Column(Boolean, default=False)                        # true:已成品入庫
    #status_comment = Column(Integer, default=0)                    # 0: 空白, 1:等待agv搬運, 2:已送至組裝區, 3:已送至成品區, 4:agv送料進行中
    _bom =  relationship('Bom', backref="material")                 # 一對多(一),
    _assemble =  relationship('Assemble', backref="material")       # 一對多(一),
    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
    #  return "id={}, order_num={}, material_num={}, material_comment={}, material_qty={}, material_date={}, material_delivery_date={}, whichStation={}, is_assem1_ok={}, is_assem2_ok={}, is_assem3_ok={}, bom_agv_status={}".format(
    #  self.id, self.order_num, self.material_num, self.material_comment, self.material_qty, self.material_date, self.material_delivery_date, self.whichStation, self.is_assem1_ok, self.is_assem2_ok, self.is_assem3_ok, self.bom_agv_status)
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    # 定義class的dict內容
    def get_dict(self):
      '''
      return {
        'id': self.id,
        'order_num': self.order_num,
        'material_num': self.material_num,
        'material_comment': self.material_comment,
        'material_qty': self.material_qty,
        'material_date': self.material_date,
        'material_delivery_date': self.material_delivery_date,
        'whichStation': self.whichStation,
        'bom_agv_status': self.bom_agv_status
      }
      '''
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


# ------------------------------------------------------------------


class Bom(BASE):
    __tablename__ = 'bom'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('material.id'))      #單號
    seq_num = Column(String(20), nullable=False)                  #序號
    material_num = Column(String(20), nullable=False)             #料號
    material_comment = Column(String(70), nullable=False)         #料號說明
    req_qty = Column(Integer)                   #需求數量
    pick_qty = Column(Integer, default=0)       #領料數量
    non_qty = Column(Integer, default=0)        #未結數量
    lack_qty = Column(Integer, default=0)       #缺料數量
    receive = Column(Boolean, default=True)
    lack = Column(Boolean, default=False)
    isPickOK = Column(Boolean, default=False)               # true:檢料完成
    start_date = Column(String(12), nullable=False)         #開始日期
    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
      return "id={}, material_id={}, seq_num={}, material_num={}, material_comment={}, req_qty={}, pick_qty={}, non_qty={}, lack_qty={}, receive={}, lack={}, isPickOK={}, start_date={}".format(
      self.id, self.material_id, self.seq_num, self.material_num, self.material_comment, self.req_qty, self.pick_qty, self.non_qty, self.lack_qty, self.receive, self.lack, self.isPickOK, self.start_date)

    # 定義class的dict內容
    def get_dict(self):
      return {
        'id': self.id,
        'material_id': self.material_id,
        'seq_num': self.seq_num,
        'material_num': self.material_num,
        'material_comment': self.material_comment,
        'req_qty': self.req_qty,
        'pick_qty': self.pick_qty,
        'non_qty': self.non_qty,
        'lack_qty': self.lack_qty,
        'receive': self.receive,
        'lack': self.lack,
        'isPickOK': self.isPickOK,
        'start_date': self.start_date,
      }


# ------------------------------------------------------------------


class Assemble(BASE):
    __tablename__ = 'assemble'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('material.id'))      #訂單號碼
    material_num = Column(String(20), nullable=False)             #料號
    material_comment = Column(String(70), nullable=False)         #料號說明
    seq_num = Column(String(20), nullable=False)                  #序號
    work_num = Column(String(20))                                 #工作中心
    process_step_code = Column(Integer, default=0)                #工作中芯的順序, 3:最先作動, 0:作動完畢
    ask_qty = Column(Integer, default=0)                          #領取數量
    total_ask_qty = Column(Integer, default=0)                    #已領取總數量
    user_id = Column(String(8))                                   #員工編號(領料)
    good_qty = Column(Integer, default=0)                         #確認良品數量
    total_good_qty = Column(Integer, default=0)                   #已交付確認良品總數
    non_good_qty = Column(Integer, default=0)                     #廢品數量

    meinh_qty = Column(Integer, default=0)                        #作業數量

    #receive_qty = Column(Integer)                #領取數量
    #already_received_qty = Column(Integer)       #已經領取數量
    completed_qty = Column(Integer)                               #完成數量

    reason = Column(String(50))                                   #差異原因
    #emp_num = Column(String(8))                                   #員工編號 8碼
    confirm_comment = Column(String(70))                          #確認內文
    is_assemble_ok = Column(Boolean, default=False)               # true: 目前途程為組裝, false: 不是

    currentStartTime = Column(String(30))                         #領料生產報工開始時間
    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
      '''
      return "id={}, material_id={}, material_num={}, material_comment={}, seq_num={}, work_num={}, meinh_qty={}, good_qty={}, non_good_qty={}, reason={}, emp_num={}, confirm_comment={}, is_assemble_ok={}".format(
      self.id, self.material_id, self.material_num, self.material_comment, self.seq_num, self.work_num, self.meinh_qty, self.good_qty, self.non_good_qty, self.reason, self.emp_num, self.confirm_comment, self.is_assemble_ok)
      '''
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    # 定義class的dict內容
    def get_dict(self):
      '''
      return {
        'id': self.id,
        'material_id': self.material_id,
        'material_num': self.material_num,
        'material_comment': self.material_comment,
        'seq_num': self.seq_num,
        'work_num': self.work_num,
        'meinh_qty': self.meinh_qty,
        'good_qty': self.good_qty,
        'non_good_qty': self.non_good_qty,
        'reason': self.reason,
        'emp_num':self.emp_num,
        'confirm_comment': self.confirm_comment,
        'is_assemble_ok': self.is_assemble_ok,
      }
      '''
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


# ------------------------------------------------------------------


class Process(BASE):
    __tablename__ = 'process'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_num = Column(String(20), nullable=False)                #訂單編號
    work_num =  Column(String(20))                                #工作中心
    user_id = Column(String(8), nullable=False)                   #員工編號
    begin_time = Column(String(30))                               #開始時間
    end_time = Column(String(30))                                 #結束時間
    period_time =  Column(String(30))
    process_type = Column(Integer, default=1)                     #1:備料區,
                                                                  #2:組裝區(含21, 22, 23)
                                                                  #3:成品區(含31, 32, 33)
                                                                  #4:加工區(含41, 42, 43)
                                                                  #99:agv
    #process_status = Column(Integer, default=0)                   # material bom_agv_status
    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
      '''
      return "id={}, order_num={}, user_id={}, begin_time={}, end_time={}, period_time={}, process_type={}, process_status={}".format(
      self.id, self.order_num, self.user_id, self.begin_time, self.end_time, self.period_time, self.process_type, self.process_status)
      '''
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    # 定義class的dict內容
    def get_dict(self):
      '''
      return {
        'id': self.id,
        'order_num': self.order_num,
        'user_id': self.user_id,
        'begin_time': self.begin_time,
        'end_time': self.end_time,
        'period_time': self.period_time,
        'process_type': self.process_type,
        #'process_status': self.process_status
      }
      '''
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}



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