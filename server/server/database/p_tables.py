# p_tables.py  —— 放加工線的 P_* tables

from datetime import datetime
from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship


# 共用 tables.py 裡的 BASE
# tables.py 與 p_tables.py 在同一層
try:
    # ✅ package 模式 (例如: from database import p_tables)
    from .tables import BASE
except ImportError:
    # ✅ script 模式 (例如: python database\dropManyTables.py → from tables import BASE)
    from tables import BASE


# ------------------------------------------------------------------
# 加工線

p_association_material_abnormal = Table(
    'p_association_material_abnormal', BASE.metadata,
    Column('material_id', Integer, ForeignKey('p_material.id')),
    Column('abnormal_cause_id', Integer, ForeignKey('p_abnormal_cause.id'))
)


class P_Material(BASE):
    __tablename__ = 'p_material'

    id = Column(Integer, primary_key=True, autoincrement=True)

    abnormal_cause_id = Column(Integer, ForeignKey('p_abnormal_cause.id'))

    order_num = Column(String(20), nullable=False)
    material_num = Column(String(20), nullable=False)
    material_comment = Column(String(70), nullable=False)
    material_qty = Column(Integer, nullable=False)
    delivery_qty = Column(Integer, default=0)
    total_delivery_qty = Column(Integer, default=0)
    input_disable = Column(Boolean, default=False)

    material_date = Column(String(12), nullable=False)
    material_delivery_date = Column(String(12), nullable=False)

    isBom = Column(Boolean, default=False)              # True:在領料中, 不要顯示詳情(bom表), False:要顯示詳情

    isTakeOk = Column(Boolean, default=False)
    isShow = Column(Boolean, default=False)
    isAssembleAlarm = Column(Boolean, default=True)

    isAssembleAlarmRpt = Column(Boolean, default=False)
    isAssembleStation1TakeOk = Column(Boolean, default=False)
    isAssembleStation2TakeOk = Column(Boolean, default=False)
    isAssembleStation3TakeOk = Column(Boolean, default=False)
    isAssembleStationShow = Column(Boolean, default=False)
    assemble_qty = Column(Integer, default=0)
    total_assemble_qty = Column(Integer, default=0)

    whichStation = Column(Integer, default=1)
    show1_ok = Column(String(20), server_default='1')
    show2_ok = Column(String(20), server_default='0')
    show3_ok = Column(String(20), server_default='0')
    shortage_note = Column(String(20), server_default='')
    isAllOk = Column(Boolean, default=False)
    allOk_qty = Column(Integer, default=0)

    Incoming0_Abnormal = Column(String(30), default='')
    Incoming2_Abnormal = Column(String(30), default='')

    must_allOk_qty = Column(Integer, default=0)

    total_allOk_qty = Column(Integer, default=0)
    isLackMaterial = Column(Integer, default=99)
    isBatchFeeding = Column(Integer, default=99)
    # 加工線
    sd_time_B100 = Column(String(30))
    sd_time_B102 = Column(String(30))
    sd_time_B103 = Column(String(30))
    sd_time_B107 = Column(String(30))
    sd_time_B108 = Column(String(30))

    move_by_automatic_or_manual = Column(Boolean, default=False)
    move_by_process_type = Column(Integer, default=4)               # 2:工單給組裝線, 4:工單給加工線

    isOpen = Column(Boolean, default=False)                         #True: dialog open, False: dialog close
    isOpenEmpId = Column(String(8), default="")       # 工單已經開始備料的員工
    hasStarted = Column(Boolean, default=False)       # True:工單已經開始備料進行中, False:尚未備料或備料已完成
    startStatus = Column(Boolean, default=False)      # toggle status, True:開始

    _bom = relationship('P_Bom', backref="p_material")
    _assemble = relationship('P_Assemble', backref="p_material")
    _abnormal_cause = relationship(
        "P_AbnormalCause",
        secondary=p_association_material_abnormal,
        back_populates="_material"
    )
    _product = relationship('P_Product', backref="p_material")
    _process = relationship('P_Process', backref="p_material")

    material_stockin_date = Column(String(12))
    update_time = Column(String(30))
    create_at = Column(DateTime, server_default=func.now())

    is_copied_from_id = Column(Integer, ForeignKey('p_material.id'), nullable=True)
    copied_from = relationship("P_Material", remote_side=[id], backref="copied_to")

    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}

    def to_dict(self):
      return {
        'id': self.id,
        'order_num': self.order_num,
        'material_num': self.material_num,
        'req_qty': self.material_qty,
        'delivery_qty': self.delivery_qty,
        'total_delivery_qty': self.total_delivery_qty,
        'input_disable': self.input_disable,
        'date': self.material_date,
        'delivery_date': self.material_delivery_date,
        'shortage_note': self.shortage_note,
        'comment': self.material_comment,
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


class P_AbnormalCause(BASE):
    __tablename__ = 'p_abnormal_cause'

    id = Column(Integer, primary_key=True, autoincrement=True)
    number = Column(String(6), nullable=False)
    message = Column(String(30), nullable=False)
    _material = relationship(
        "P_Material",
        secondary=p_association_material_abnormal,
        back_populates="_abnormal_cause",
    )
    create_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


class P_Bom(BASE):
    __tablename__ = 'p_bom'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('p_material.id'))
    seq_num = Column(String(20), nullable=False)
    material_num = Column(String(20), nullable=False)
    material_comment = Column(String(70), nullable=False)
    req_qty = Column(Integer)
    pick_qty = Column(Integer, default=0)
    non_qty = Column(Integer, default=0)
    lack_qty = Column(Integer, default=0)
    receive = Column(Boolean)
    lack = Column(Boolean, default=False)
    isPickOK = Column(Boolean, default=False)
    lack_bom_qty = Column(Integer, default=0)
    start_date = Column(String(12), nullable=False)
    create_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


class P_Assemble(BASE):
    __tablename__ = 'p_assemble'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('p_material.id'))
    material_num = Column(String(20), nullable=False)
    material_comment = Column(String(70), nullable=False)
    seq_num = Column(String(20), nullable=False)
    work_num = Column(String(20))
    process_step_code = Column(Integer, default=0)

    Incoming1_Abnormal = Column(String(30), default='')
    must_receive_qty = Column(Integer, default=0)

    ask_qty = Column(Integer, default=0)
    total_ask_qty = Column(Integer, default=0)
    total_ask_qty_end = Column(Integer, default=0)

    must_receive_end_qty = Column(Integer, default=0)
    abnormal_qty = Column(Integer, default=0)

    user_id = Column(String(8))
    writer_id = Column(String(8))
    write_date = Column(String(18))
    good_qty = Column(Integer, default=0)
    total_good_qty = Column(Integer, default=0)
    non_good_qty = Column(Integer, default=0)

    meinh_qty = Column(Integer, default=0)

    completed_qty = Column(Integer, default=0)
    total_completed_qty = Column(Integer, default=0)
    allOk_qty = Column(Integer, default=0)                        # 入庫數量

    reason = Column(String(50), default='')
    confirm_comment = Column(String(70), default='')
    is_assemble_ok = Column(Boolean, default=False)

    currentStartTime = Column(String(30))
    currentEndTime = Column(String(30))

    input_disable = Column(Boolean, default=False)
    input_end_disable = Column(Boolean, default=False)
    input_allOk_disable = Column(Boolean, default=False)
    input_abnormal_disable = Column(Boolean, default=False)

    isAssembleStationShow = Column(Boolean, default=False)
    isWarehouseStationShow = Column(Boolean, default=False)

    isStockIn = Column(Boolean, default=False)          # 是否入庫, True: 必須入庫(作業短文以Z開頭)
    isSimultaneously = Column(Boolean, default=False)   # True: 各個加工製程同步(平行製程), False: 各個加工製程是有順序性
    isShowBomGif = Column(Boolean, default=False)       # True: 不顯示Bom動態gif圖示

    alarm_enable = Column(Boolean, default=True)
    alarm_message = Column(String(250), default='', nullable=False)

    isAssembleFirstAlarm = Column(Boolean, default=True)
    isAssembleFirstAlarm_message = Column(String(100), default='')
    isAssembleFirstAlarm_qty = Column(Integer, default=0)

    whichStation = Column(Integer, default=1)
    show1_ok = Column(String(20), server_default='1')
    show2_ok = Column(String(20), server_default='0')
    show3_ok = Column(String(20), server_default='0')

    update_time = Column(String(30))
    create_at = Column(DateTime, server_default=func.now())
    is_copied_from_id = Column(Integer, ForeignKey('p_assemble.id'), nullable=True)
    copied_from = relationship("P_Assemble", remote_side=[id], backref="copied_to")

    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


class P_Product(BASE):
    __tablename__ = 'p_product'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('p_material.id'))
    process_id = Column(Integer)                                  #process table id
    line_difference = Column(Integer, default=1)             # 0:組裝線, 1:加工線

    delivery_qty = Column(Integer, default=0)
    assemble_qty = Column(Integer, default=0)
    allOk_qty = Column(Integer, default=0)

    good_qty = Column(Integer, default=0)
    non_good_qty = Column(Integer, default=0)
    reason = Column(String(50))
    confirm_comment = Column(String(70))

    create_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


class P_Process(BASE):
    __tablename__ = 'p_process'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('p_material.id'))
    assemble_id = Column(Integer, default=0)                          #assemble table id, 0:備料
    has_started = Column(Boolean, nullable=False, default=False)      # 標記「這筆工單是否已經按過開始」, true:已經按過開始鍵
    user_id = Column(String(20), nullable=False)
    user_delegate_id = Column(String(20), default='')                             #代理人員工編號

    begin_time = Column(String(30))
    end_time = Column(String(30))
    period_time = Column(String(30))
    pause_time = Column(Integer, default=0)               # 總共暫停時間
    pause_started_at = Column(DateTime, nullable=True)    # 正在暫停的起點
    elapsedActive_time = Column(Integer, default=0)       # 總計時時間
    str_elapsedActive_time = Column(String(30))           # 總計時時間(hh:mm:ss)

    is_pause = Column(Boolean, default=True)
    process_type = Column(Integer, default=1)
    process_work_time_qty = Column(Integer, default=0)            # 報工數量(成品, 到庫數量)
    must_allOk_qty = Column(Integer, default=0)                   # 成品, 應入庫數量
    allOk_qty = Column(Integer, default=0)                        # 成品, 入庫數量
    isAllOk = Column(Boolean, default=False)                      # true: 已入庫
    normal_work_time = Column(Integer, default=1)                 # 最後1筆工序(1:yes, 0:no), 正常工序(1:正常工時, 0:異常整修工時)
    abnormal_cause_message = Column(String(30), default='')       # 異常原因訊息
    create_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}


class P_Part(BASE):
    __tablename__ = 'p_part'

    id = Column(Integer, primary_key=True, autoincrement=True)
    process_step_code= Column(Integer)
    part_code  = Column(String(10))   # 製程代號 (B100-01)
    part_comment = Column(String(30)) # 製程說明(作業描述)
    work_code  = Column(String(10))   # 工作中心
    work_name  = Column(String(30))   # 工作中心名稱
    cost_code  = Column(String(10))   # 成本中心
    cost_name  = Column(String(30))   # 成本中心名稱
    create_at = Column(DateTime, server_default=func.now())   #

    def __repr__(self):
      fields = ', '.join([f"{name}={getattr(self, name)}" for name in self.__mapper__.columns.keys()])
      return f"<LargeTable({fields})>"

    def get_dict(self):
      return {name: getattr(self, name) for name in self.__mapper__.columns.keys()}

