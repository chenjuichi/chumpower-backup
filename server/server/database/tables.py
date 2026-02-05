import os
#os.environ['SQLALCHEMY_WARN_20'] = '0'    # 設置環境變數來顯示所有與SQLAlchemy 2.0相關的警告
#os.environ['SQLALCHEMY_SILENCE_UBER_WARNING'] = '0'   # 設置環境變數來靜音指定的警告

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*SQLALCHEMY_SILENCE_UBER_WARNING.*")

from datetime import datetime, UTC

from datetime import datetime as dt

from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean, func, ForeignKey, create_engine
from sqlalchemy import text
from sqlalchemy.orm import relationship, backref, scoped_session, sessionmaker, declarative_base  #for 2.0版

#import p_tables             # 讓 P_* 類別被載入並註冊到 BASE.metadata

BASE = declarative_base()   # 宣告一個映射, 建立一個基礎類別


# ------------------------------------------------------------------
# 確保 P_* tables 也會註冊到同一個 BASE.metadata
try:
    # package 模式 (例如 from database import tables)
    from . import p_tables
except ImportError:
    # 直接在 database 資料夾裡用 python tables.py 執行
    import p_tables


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
  is_user_delegate = Column(Boolean, default=False)       # false: 目前不須代理人
  isRemoved = Column(Boolean, default=True)               # true: 資料還存在, false:資料已刪除
  isOnline = Column(Boolean, default=False)               # false: user不在線上(logout)
  last_login_ip = Column(String(100), nullable=True)      # 紀錄登入IP
  last_login_time = Column(DateTime, nullable=True)       # 紀錄登入時間
  updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC))
  create_at = Column(DateTime, server_default=func.now())

  # 定義變數輸出的內容
  def __repr__(self):
    return "id={}, emp_id={}, emp_name={}, dep_name={}, password={}, perm_id={}, setting_id={}, is_user_delegate={}, isRemoved={}, isOnline={}".format(
    self.id, self.emp_id, self.emp_name, self.dep_name, self.password, self.perm_id, self.setting_id, self.is_user_delegate, self.isRemoved, self.isOnline)

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
      'is_user_delegate': self.is_user_delegate,
      'isRemoved': self.isRemoved,
      'isOnline': self.isOnline,
    }


# ------------------------------------------------------------------


class UserDelegate(BASE):
    __tablename__ = 'user_delegate'

    id = Column(Integer, primary_key=True, autoincrement=True)
    #user_id = Column(Integer, ForeignKey('user.id'), nullable=False)  # 被代理的員工(user.id)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    delegate_emp_id = Column(String(8), nullable=False)               # 代理人員工編號(8 碼，和 User.emp_id 一致)
    start_date = Column(DateTime, nullable=False)                     # 代理開始日期
    end_date = Column(DateTime, nullable=True)                        # 代理結束日期, NULL: 表示「持續到另行終止」
    reason = Column(String(100), nullable=True)                       # 代理事由

    #user = relationship("User", backref="delegates")
    user = relationship(
        "User",
        backref=backref("delegates", cascade="all, delete-orphan")
    )

    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    # 定義class的dict內容
    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


# ------------------------------------------------------------------


class Permission(BASE):  # 一對多, "一":permission, "多":user
    __tablename__ = 'permission'

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth_code = Column(Integer, default=0)    # 0:none, 1:system, 2:admin, 3: staff, 4:member
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
    #pdf__manager = Column(Integer, default=0)               # 1:配件生管主管, 2:配件組立加工主管
    merg_manage = Column(Boolean, default=True)             # False: 備料工單在組裝線不合併
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
# 組裝線


association_material_abnormal = Table('association_material_abnormal', BASE.metadata,
  Column('material_id', Integer, ForeignKey('material.id')),
  Column('abnormal_cause_id', Integer, ForeignKey('abnormal_cause.id'))
)


# ------------------------------------------------------------------


class ProcessedFile(BASE):
    __tablename__ = 'processed_file'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), unique=True, nullable=False)  # 不含 copy_x 的原始檔名
    processed_time = Column(DateTime, default=datetime.now(UTC))
    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    # 定義class的dict內容
    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


# ------------------------------------------------------------------


class Material(BASE):
    __tablename__ = 'material'

    id = Column(Integer, primary_key=True, autoincrement=True)

    abnormal_cause_id = Column(Integer, ForeignKey('abnormal_cause.id'))      #異常原因 id, 一對多(多),

    order_num = Column(String(20), nullable=False)                  #訂單編號(1)
    material_num = Column(String(20), nullable=False)               #成品料號(2)
    material_comment = Column(String(70), nullable=False)           #料號說明(3)
    material_qty = Column(Integer, nullable=False)                  #(成品)需求數量(4),訂單數量
    delivery_qty = Column(Integer, default=0)                       #送料數量(現況數量), 備料數量
    total_delivery_qty = Column(Integer, default=0)                 #已送料總數量, 應備數量
    input_disable = Column(Boolean, default=False)                  #送料數量達上限(需求數量), 或尚未備料, 則禁止再輸入

    material_date = Column(String(12), nullable=False)              #建置日期(5)
    material_delivery_date = Column(String(12), nullable=False)     #交期(6)
    isTakeOk = Column(Boolean, default=False)                       # true:檢料區檢料完成,指定訂單可以派車
    isShow = Column(Boolean, default=False)                         # true:檢料完成且已call AGV, 就disable詳情按鍵
    isAssembleAlarm = Column(Boolean, default=True)                 # false:組裝異常,

    isAssembleAlarmRpt = Column(Boolean, default=False)             # false:未填報異常原因,
    isAssembleStation1TakeOk = Column(Boolean, default=False)       # true:組裝站製程1完成,
    isAssembleStation2TakeOk = Column(Boolean, default=False)       # true:組裝站製程2完成, 即完成生產報工中, 按結束鍵
    isAssembleStation3TakeOk = Column(Boolean, default=False)       # true:
    isAssembleStationShow = Column(Boolean, default=False)          # true:完成生產報工(press結束按鍵), 且是最後1個製成, 且已經call AGV, disable
    station1_Qty = Column(Integer)
    station2_Qty = Column(Integer)
    station3_Qty = Column(Integer)
    assemble_qty = Column(Integer, default=0)                       #(組裝）完成數量
    total_assemble_qty = Column(Integer, default=0)                 #已(組裝）完成總數量

    whichStation = Column(Integer, default=1)                       # 目標途程, 目前途程為1:檢料, 2: 組裝, 3:成品
    show1_ok = Column(String(20), server_default='1')
    show2_ok = Column(String(20), server_default='0')
    show3_ok = Column(String(20), server_default='0')
    shortage_note = Column(String(20), server_default='')           # 缺料註釋說明
    isAllOk = Column(Boolean, default=False)                        # true:成品已入庫
    allOk_qty = Column(Integer, default=0)                          # (成品）確認完成數量

    Incoming0_Abnormal = Column(String(30), default='')              #備料區檢料異常, 正常:''
    Incoming2_Abnormal = Column(String(30), default='')              #成品區來料異常, 正常:''

    must_allOk_qty = Column(Integer, default=0)                     # (成品）應入庫數量, 2025-06-24 add

    total_allOk_qty = Column(Integer, default=0)                    # (成品）完成總數量
    isLackMaterial = Column(Integer, default=99)                    # 0:缺料且檢料完成(還沒拆單),  1:拆單1, 2:拆單2, ... 99: 備料正常, 沒缺料
    isBatchFeeding =  Column(Integer, default=99)                   # 0:分批送料(必須拆單),       1:拆單1, 2:拆單2, ... 99: 正常送料, 單次送料

    #merge_enabled = Column(Boolean, nullable=False, default=True)   # 2026-2-2新增, true:預設值, 併單
    merge_enabled = Column(Boolean, nullable=False, server_default=text("1"))

    # 組裝線
    sd_time_B109 = Column(String(30))
    sd_time_B106 = Column(String(30))
    sd_time_B110 = Column(String(30))

    move_by_automatic_or_manual = Column(Boolean, default=True)     # 備料區->組裝區, true:agv自動搬運, false:人工送料
    move_by_automatic_or_manual_2 = Column(Boolean, default=True)   # 組裝區->成品區, true:agv自動搬運, false:人工送料
    move_by_process_type = Column(Integer, default = 2)             # 2:工單給組裝線, 4:工單給加工線

    isOpen = Column(Boolean, default=False)                         #True: dialog open, False: dialog close
    isOpenEmpId = Column(String(8), default="")       # 工單已經開始備料的員工
    hasStarted = Column(Boolean, default=False)       # True:工單已經開始備料進行中, False:尚未備料或備料已完成
    startStatus = Column(Boolean, default=False)      # toggle status, True:開始

    _bom =  relationship('Bom', backref="material")                 # 一對多(一),
    _assemble =  relationship('Assemble', backref="material")       # 一對多(一),
    _abnormal_cause = relationship("AbnormalCause", secondary=association_material_abnormal, back_populates="_material")
    _product =  relationship('Product', backref="material")         # 一對多(一),
    _process =  relationship('Process', backref="material")         # 一對多(一),
    material_stockin_date = Column(String(12))                      # 入庫日期
    create_at = Column(DateTime, server_default=func.now())
    update_time = Column(String(30))

    # 新增欄位：追蹤來源
    is_copied_from_id = Column(Integer, ForeignKey('material.id'), nullable=True)
    # 建立 self-reference 關聯關係, optional relationship for back-reference
    # backref="copied_to", 可從原始資料中查到所有從它複製出去的資料清單。
    copied_from = relationship("Material", remote_side=[id], backref="copied_to")

    # 定義變數輸出的內容
    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    # 定義class的dict內容
    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}

    def to_dict(self):
      return {
        'id': self.id,
        'order_num': self.order_num,
        'material_num': self.material_num,

        'req_qty': self.material_qty,                   #需求數量(訂單數量)
        'delivery_qty': self.delivery_qty,              #備料數量
        'total_delivery_qty': self.total_delivery_qty,  #應備數量
        'input_disable': self.input_disable,
        'date': self.material_date,                     #(建立日期)
        'delivery_date': self.material_delivery_date,   #交期
        'shortage_note': self.shortage_note,            #缺料註記 '元件缺料'
        'comment': self.material_comment,               #說明
        'isTakeOk' : self.isTakeOk,
        'isLackMaterial' : self.isLackMaterial,
        'isBatchFeeding' :  self.isBatchFeeding,
        'isShow' : self.isShow,
        'whichStation' : self.whichStation,
        'show1_ok' : self.show1_ok,
        'show2_ok' : self.show2_ok,
        'show3_ok' : self.show3_ok,
        'Incoming0_Abnormal': self.Incoming0_Abnormal == '',
        'is_copied': bool(self.is_copied_from_id and self.is_copied_from_id > 0),
      }


# ------------------------------------------------------------------


class AbnormalCause(BASE):
    __tablename__ = 'abnormal_cause'

    id = Column(Integer, primary_key=True, autoincrement=True)
    number = Column(String(6), nullable=False)                          #異常原因訊息編號
    message = Column(String(30), nullable=False)                        #異常原因訊息
    _material = relationship("Material", secondary=association_material_abnormal, back_populates="_abnormal_cause")
    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    # 定義class的dict內容
    def get_dict(self):
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
    lack_qty = Column(Integer, default=0)       #數量
    #receive = Column(Boolean)     # False: 不領料 checkbox
    #receive = Column(Boolean, nullable=False, default=False)  # 2026-1-30修改
    receive = Column(Boolean, nullable=False, default=False, server_default=text("0"))  # 2026-2-4修改
    lack = Column(Boolean, default=False)
    isPickOK = Column(Boolean, default=False)               # true:檢料完成
    lack_bom_qty = Column(Integer, default=0)
    start_date = Column(String(12), nullable=False)         #開始日期
    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    # 定義class的dict內容
    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


# ------------------------------------------------------------------


class Assemble(BASE):
    __tablename__ = 'assemble'

    id = Column(Integer, primary_key=True, autoincrement=True)    #
    material_id = Column(Integer, ForeignKey('material.id'))      #material table id
    material_num = Column(String(20), nullable=False)             #料號
    material_comment = Column(String(70), nullable=False)         #料號說明
    seq_num = Column(String(20), nullable=False)                  #序號
    work_num = Column(String(20))                                 #工作中心
    process_step_code = Column(Integer, default=0)                #工作中心的工作順序編號, 3:最先作動, 0:作動完畢

    Incoming1_Abnormal = Column(String(30), default='')           #組裝區來料異常, 正常:''
    must_receive_qty = Column(Integer, default=0)                 #應領取數量, 2025-06-16 add, 改順序

    ask_qty = Column(Integer, default=0)                          #組裝區領取數量
    total_ask_qty = Column(Integer, default=0)                    #領取(完成)數量總數
    total_ask_qty_end = Column(Integer, default=0)                #已結束(完成)總數量顯示順序

    must_receive_end_qty = Column(Integer, default=0)             #應完成總數量
    abnormal_qty = Column(Integer, default=0)                     #異常數量

    user_id = Column(String(8))                                   #工序作業員工工號(領料)
    writer_id = Column(String(8))                                 #工序異常資料填寫員工編號
    write_date = Column(String(18))                               #工序異常資料填寫日期 2025-05-12 add
    good_qty = Column(Integer, default=0)                         #確認良品數量
    total_good_qty = Column(Integer, default=0)                   #已交付確認良品總數
    non_good_qty = Column(Integer, default=0)                     #廢品數量

    meinh_qty = Column(Integer, default=0)                        #作業數量

    #receive_qty = Column(Integer)                #領取數量
    #already_received_qty = Column(Integer)       #已經領取數量
    #Incomin2_Abnormal = Column(String(20), default='')           #成品區來料異常, 正常:''
    completed_qty = Column(Integer, default=0)                    #完成數量
    total_completed_qty = Column(Integer, default=0)              #已完成總數量
    allOk_qty = Column(Integer, default=0)                        # 入庫數量

    reason = Column(String(50), default='')                       #差異原因
    confirm_comment = Column(String(70), default='')              #確認內文
    is_assemble_ok = Column(Boolean, default=False)               # true: 目前途程為組裝, false: 不是

    currentStartTime = Column(String(30))                         #領料生產報工開始時間
    currentEndTime = Column(String(30))                           #完工生產報工結束時間

    input_disable = Column(Boolean, default=False)                #領取數量欄位, 禁止再輸入
    input_end_disable = Column(Boolean, default=False)            #完成數量欄位, 禁止再輸入
    input_allOk_disable = Column(Boolean, default=False)          #入庫數量欄位, 禁止再輸入
    input_abnormal_disable = Column(Boolean, default=False)       #異常數量欄位, 禁止再輸入, 2025-06-17 add, 改順序

    isAssembleStationShow = Column(Boolean, default=False)        # true:完成生產報工(最後途程的結束鍵按下), 且是最後1個製成, 且已經call AGV, disable,
    isWarehouseStationShow = Column(Boolean, default=False)       # true:已經進入 倉儲

    alarm_enable = Column(Boolean, default=True)                  # false: 在途程中按了異常鍵->異常, true: 在途程中取消了異常鍵(或沒有按異常鍵)->沒有異常
    alarm_message = Column(String(250), default='', nullable=False)

    isAssembleFirstAlarm = Column(Boolean, default=True)          # false:組裝途程第1工序按了異常鍵->異常,
    isAssembleFirstAlarm_message = Column(String(100), default='')
    isAssembleFirstAlarm_qty = Column(Integer, default=0)

    whichStation = Column(Integer, default=1)                     # 目標途程, 目前途程為1:檢料, 2: 組裝, 3:成品
    show1_ok = Column(String(20), server_default='1')
    show2_ok = Column(String(20), server_default='0')
    show3_ok = Column(String(20), server_default='0')

    update_time = Column(String(30))
    create_at = Column(DateTime, server_default=func.now())
    # 新增欄位：追蹤來源
    is_copied_from_id = Column(Integer, ForeignKey('assemble.id'), nullable=True)
    # 建立 self-reference 關聯關係, optional relationship for back-reference
    # backref="copied_to", 可從原始資料中查到所有從它複製出去的資料清單。
    copied_from = relationship("Assemble", remote_side=[id], backref="copied_to")

    # 定義變數輸出的內容
    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    # 定義class的dict內容
    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


# ------------------------------------------------------------------


class Product(BASE):
    __tablename__ = 'product'

    id = Column(Integer, primary_key=True, autoincrement=True)    #
    material_id = Column(Integer, ForeignKey('material.id'))      #material table id
    process_id = Column(Integer)                                  #process table id
    line_difference = Column(Integer, default=0)             # 0:組裝線, 1:加工線

    delivery_qty = Column(Integer, default=0)                     #備料完成數量
    assemble_qty = Column(Integer, default=0)                     #組裝完成數量
    allOk_qty = Column(Integer, default=0)                        #成品入庫數量

    good_qty = Column(Integer, default=0)                         #成品良品數量
    non_good_qty = Column(Integer, default=0)                     #成品廢品數量
    reason = Column(String(50))                                   #差異原因
    confirm_comment = Column(String(70))                          #確認內文

    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    # 定義class的dict內容
    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


# ------------------------------------------------------------------


class Process(BASE):
    __tablename__ = 'process'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('material.id'))          #material table id
    assemble_id = Column(Integer, default=0)                          #assemble table id, 0:備料
    #has_started = Column(Boolean, nullable=False, default=False)      # 標記「這筆工單是否已經按過開始」, true:已經按過開始鍵
    has_started = Column(Boolean, nullable=False, default=False, server_default=text("0"))  # 2026-2-4 修改
    user_id = Column(String(20), nullable=False)                      #員工編號
    user_delegate_id = Column(String(20), default='')                             #代理人員工編號
    begin_time = Column(String(30))                                   #開始時間
    end_time = Column(String(30))                                     #結束時間
    period_time =  Column(String(30))
    pause_time = Column(Integer, default=0)               # 總共暫停時間
    pause_started_at = Column(DateTime, nullable=True)    # 正在暫停的起點
    elapsedActive_time = Column(Integer, default=0)       # 總計時時間
    str_elapsedActive_time = Column(String(30))           # 總計時時間(hh:mm:ss)

    is_pause = Column(Boolean, default=True)

    process_type = Column(Integer, default=1)
    #bit7, bit6, bit5 bit4 bit3 bit2, bit1, bit0

                                                                  # 1:備料區(組裝線),
                                                                  # 2:組裝區(含20, 21, 22, 23)
                                                                   # 20:AGV運行到組裝區
                                                                  # 21:在第1途程, 組裝
                                                                  # 22:在第2途程, 檢驗
                                                                  # 23:在第3途程, 雷射
                                                                  # (含20, 21, 22, 23)
                                                                  # 3:成品區(含31, 32, 33)
                                                                  # 4:加工區(含41, 42, 43, ...)
                                                                  #
                                                                  # 99:agv, 98:forklift
                                                                  # 88: 暫停

                                                                  # 19: '等待AGV(備料區)',
                                                                  # 2: 'AGV運行(備料區->組裝區)',
                                                                  # 29: '等待AGV(組裝區)',
                                                                  # 3: 'AGV運行(組裝區->成品區)',
                                                                  # 31: '成品入庫',

                                                                  # 5: '堆高機運行(備料區->組裝區)',
                                                                  # 6: '堆高機運行(組裝區->成品區)',

    process_work_time_qty = Column(Integer, default=0)            # 報工數量(成品, 到庫數量)
    must_allOk_qty = Column(Integer, default=0)                   # 成品, 應入庫數量
    allOk_qty = Column(Integer, default=0)                        # 成品, 入庫數量
    isAllOk = Column(Boolean, default=False)                      # true: 已入庫

    normal_work_time = Column(Integer, default=1)                 # 最後1筆工序(1:yes, 0:no), 正常工序(1:正常工時, 0:異常整修工時)
                                                                  #bit0: 正常工序(1:正常工時, 0:異常整修工時)
                                                                  #bit1: 最後1筆工序(1:yes, 0:no)
                                                                  #bit2: 已入庫(1:yes, 0:no)

                                                                  #bit3 bit2, bit1, bit0
                                                                  #0      0     0     1  =1 (default), 正常工時
                                                                  #0      0     1     1  =3, 正常工時, 且是最後工序
                                                                  #0      0     0     0  =0, 異常工時
                                                                  #0      0     1     0  =2, 異常工時, 且是最後工序
                                                                  #0      1     x     x  >=4
    abnormal_cause_message = Column(String(30), default='')                   # 異常原因訊息
    create_at = Column(DateTime, server_default=func.now())

    # 定義變數輸出的內容
    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    # 定義class的dict內容
    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


# ------------------------------------------------------------------


class Agv(BASE):
  __tablename__ = 'agv'

  id = Column(Integer, primary_key=True, autoincrement=True)
  status = Column(Integer, default=0)                             # 0: ready, 1:準備中, 2:行走中, 99:error alarm
  station =  Column(Integer, default=1)                           # 1:備料區, 2:組裝區, 3:成品區, 4:加工區
  create_at = Column(DateTime, server_default=func.now())

  def __repr__(self):
    fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
    return f"<LargeTable({fields})>"

  def get_dict(self):
    return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


# ------------------------------------------------------------------


# 建立連線（設定 charset=utf8mb4）
DB_URL = "mysql+pymysql://root:77974590@localhost:3306/chumpower?charset=utf8mb4"
engine = create_engine(
  DB_URL,
  echo=False,
  pool_size=20,           # ↑ 原本默認5太小
  max_overflow=40,        # 允許額外暫增連線
  pool_timeout=30,        # 等待連線最久秒數
  pool_recycle=1800,      # 30分鐘回收 (避免 MySQL 8 wait_timeout)
  pool_pre_ping=True,     # 斷線自動偵測/重連
  isolation_level="READ COMMITTED",  # 合理隔離等級
  future=True,
)

SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Session = scoped_session(SessionFactory)  #建立與資料庫連線的 Session 類別, 每個 thread/context 有自己的 session
#
## 建立與資料庫連線的 Session 類別
#Session = sessionmaker(bind=engine)
#

## 建立連線
#engine = create_engine("mysql+pymysql://root:77974590@localhost:3306/chumpower?charset=utf8mb4", echo=False)
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

## 將己連結的資料庫engine綁定到這個session
#Session = sessionmaker(bind=engine)