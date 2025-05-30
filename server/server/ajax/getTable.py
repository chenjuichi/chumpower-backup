import re

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash
from database.tables import User, Material, Bom, Agv, Permission, Process, AbnormalCause, Setting, Session
from sqlalchemy import and_, or_, not_, func

from flask_cors import CORS

from operator import itemgetter

from datetime import datetime

getTable = Blueprint('getTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


# list user, department, permission and setting table all data
@getTable.route('/login', methods=['POST'])
def login():
    print("login....")

    request_data = request.get_json()
    userID = (request_data['empID'] or '')
    password = (request_data['password'] or '')

    s = Session()

    _user_object = {}
    user = s.query(User).filter_by(emp_id=userID).first()
    if user and user.isRemoved:
        print("login user: ", user)

        if user.isOnline:
          print("step1...")
          s.close()
          return jsonify({
            'status': False,          # false: 資料錯誤
            'message': '使用者已上線!'
          })

        if not check_password_hash(user.password, password):
          print("step2...")
          s.close()
          return jsonify({
            'status': False,          # false: 資料錯誤
            'message': '密碼錯誤!'
          })

        perm_item = s.query(Permission).filter_by(id=user.perm_id).first()
        setting_item = s.query(Setting).filter_by(id=user.setting_id).first()

        s.query(User).filter(User.emp_id == userID).update({'isOnline': True})   # true: user已經上線
        s.commit()

        _user_object = {
          'empID': user.emp_id,
          'name': user.emp_name,
          'dep': user.dep_name,
          'perm_name': perm_item.auth_name,
          'perm': perm_item.auth_code,
          'password': password,
          'isOnline': user.isOnline,
          'setting_items_per_page': setting_item.items_per_page,
          'setting_isSee': setting_item.isSee,
          'setting_message': setting_item.message,
          'setting_routingPriv': setting_item.routingPriv,
          'setting_lastRoutingName': setting_item.lastRoutingName,
        }
    else:
      print("step3...")
      s.close()
      return jsonify({
        'status': False,                        # false: 資料錯誤
        'message': '錯誤! 找不到工號' + userID
      })

    print("step4...")
    s.close()

    return jsonify({
      'status': True,
      'user': _user_object,
    })

'''
# get material by order_num
@getTable.route("/getMaterial", methods=['POST'])
def get_material():
  print("getMaterial....")

  request_data = request.get_json()
  _order_num = request_data['order_num']
  print("_order_num:", _order_num)
  return_value = False
  s = Session()

  # 查詢 Material，根據 order_num 取得對應的 Material 資料
  material = s.query(Material).filter(Material.order_num == _order_num).first()
  if material and material.isTakeOk:
    return_value = True

  return jsonify({
    'status': return_value
  })
'''

# list all bom
@getTable.route("/getBoms", methods=['POST'])
def get_boms():
  print("getBoms....")

  request_data = request.get_json()
  #_order_num = request_data['order_num']
  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  #print("_order_num:", _order_num)
  return_value = True
  s = Session()


  # 檢查傳入的參數，選擇查詢條件
  material_record = None
  if _order_num is not None:  # 如果傳入了 order_num
    #print("step for order_num")
    material_record = s.query(Material).filter_by(order_num=_order_num).first()
  elif _id is not None:       # 如果傳入了 id
    #print("step for id")
    material_record = s.query(Material).filter_by(id=_id).first()

  #if material_record is None:
  #  return_value = False
  #else:
  boms = material_record._bom


  # 查詢 Material，根據 order_num 取得對應的 Material 資料
  #material = s.query(Material).filter(Material.order_num == _order_num).first()
  #print("material:", material)
  #boms = material._bom  # 透過關聯屬性取得所有 bom
  #print("boms:", boms)

  # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
  results = [
    {
      'id': bom.id,
      'order_num': material_record.order_num,
      'seq_num': bom.seq_num,           # 項目編號
      'material_num': bom.material_num,     # 物料編號
      'mtl_comment': bom.material_comment,  # 物料說明
      'qty': bom.req_qty,                   # 數量
      'date': material_record.material_date,       # 日期
      'date_alarm': '',
      'receive': bom.receive,               #領取
      'lack': bom.lack,                     #缺料
      'isPickOK': bom.isPickOK
    }
    for bom in boms if not bom.isPickOK
  ]

  s.close()

  temp_len = len(results)
  print("getBoms, 總數: ", temp_len)
  #print("getBoms: ", results)
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'boms': results
  })

'''
# list all bom
@getTable.route("/getAbnormalCauses", methods=['POST'])
def get_abnormal_causes():
  print("getAbnormalCauses....")

  request_data = request.get_json()
  #_order_num = request_data['order_num']
  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  #print("_order_num:", _order_num)
  return_value = True
  s = Session()


  # 檢查傳入的參數，選擇查詢條件
  material_record = None
  if _order_num is not None:  # 如果傳入了 order_num
    #print("step for order_num")
    material_record = s.query(Material).filter_by(order_num=_order_num).first()
  elif _id is not None:       # 如果傳入了 id
    #print("step for id")
    material_record = s.query(Material).filter_by(id=_id).first()
  # 下面代處理:
  boms = material_record._bom


  # 查詢 Material，根據 order_num 取得對應的 Material 資料
  #material = s.query(Material).filter(Material.order_num == _order_num).first()
  #print("material:", material)
  #boms = material._bom  # 透過關聯屬性取得所有 bom
  #print("boms:", boms)

  # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
  results = [
    {
      'id': bom.id,
      'order_num': material_record.order_num,
      'seq_num': bom.seq_num,           # 項目編號
      'material_num': bom.material_num,     # 物料編號
      'mtl_comment': bom.material_comment,  # 物料說明
      'qty': bom.req_qty,                   # 數量
      'date': material_record.material_date,       # 日期
      'date_alarm': '',
      'receive': bom.receive,               #領取
      'lack': bom.lack,                     #缺料
      'isPickOK': bom.isPickOK
    }
    for bom in boms if not bom.isPickOK
  ]

  s.close()

  temp_len = len(results)
  print("getBoms, 總數: ", temp_len)
  #print("getBoms: ", results)
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'boms': results
  })
'''

'''
# list detail information by order_num
@getTable.route("/getInformationDetails", methods=['POST'])
def get_information_details():
  print("getInformationDetails....")

  request_data = request.get_json()
  _order_num = request_data['order_num']
  print("order_num:", _order_num)

  code_to_name = {
    '106': '雷射',
    '109': '組裝',
    '110': '檢驗'
  }
  return_value = True
  s = Session()

  # 查詢 Material，根據 order_num 取得對應的 Material 資料
  material = s.query(Material).filter(Material.order_num == _order_num).first()
  #print("material:", material)
  information_details = material._assemble  # 透過關聯屬性取得所有 bom
  #print("information_details:", information_details)

  work_name = code_to_name.get(information_details.work_num, 'Unknown')  # 使用字典的 get() 方法來獲取名稱
  # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
  results = [
    {
      'id': information_details.id,
      'order_num': information_details.order_num,
      'work_name': work_name,                               # 工作中心名稱
      'material_num': information_details.material_num,     # 物料編號
      'mtl_comment': information_details.material_comment,  # 物料說明
      'receive_qty': information_details.ask_qty,           # 領取數量
      'delivery_date': material.material_delivery_date,     # 交期
      #'actual_spent_time':  spent,
      'isPickOK': bom.isPickOK
    }
    for bom in boms if bom.good_qty !=0
  ]

  s.close()

  temp_len = len(results)
  print("getInformationDetails, 總數: ", temp_len)
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'information_details': results
  })
'''

# get all processes data by order number
@getTable.route("/getProcessesByOrderNum", methods=['POST'])
def get_processes_by_order_num():
    print("getProcessesByOrderNum....")

    request_data = request.get_json()
    _order_num = request_data['order_num']
    print("order_num:", _order_num)

    code_to_name = {
      1 : '備料',
      19: '等待AGV(備料區)',
      2: 'AGV運行(備料區->組裝區)',
      22: '雷射',  #第2個動作b106
      21: '組裝',  #第1個動作b110
      23: '檢驗',   #第3個動作b109
      29: '等待AGV(組裝區)',
      3: 'AGV運行(組裝區->成品區)',
      31: '成品入庫',
    }
    _results = []

    s = Session()

    material = s.query(Material).filter(Material.order_num == _order_num).first()
    work_qty = material.total_delivery_qty
    #processes = s.query(Process).filter(Process.order_num == _order_num).all()
    seq_num =0
    for record in material._process:

        # 轉換為 datetime 物件
        start_time = datetime.strptime(record.begin_time, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(record.end_time, "%Y-%m-%d %H:%M:%S")

        # 計算時間差
        time_diff = end_time - start_time

        # 轉換為分鐘數（小數點去掉）
        period_time = int(time_diff.total_seconds() // 60)

        work_time = period_time / work_qty
        work_time = round(period_time / work_qty, 1)  # 取小數點後 1 位


        # 轉換為字串格式
        time_diff_str = str(time_diff)
        period_time_str = str(period_time)
        work_time_str = str(work_time)  if (record.process_type == 21 or record.process_type == 22 or record.process_type == 23) else ''
        single_std_time_str = ''
        if record.process_type == 21:
          single_std_time_str = str(material.sd_time_B110)
        if record.process_type == 22:
          single_std_time_str = str(material.sd_time_B106)
        if record.process_type == 23:
          single_std_time_str = str(material.sd_time_B109)

        if record.process_type == 31:
          single_std_time_str = str(material.sd_time_B110)

        print("period_time:",period_time_str)

        status = code_to_name.get(record.process_type, '空白')
        print("name:", record.user_id)
        name = record.user_id.lstrip("0")
        if record.process_type == 1:
          user = s.query(User).filter_by(emp_id=record.user_id).first()
          status = status + '(' + name + user.emp_name + ')'
        print("status:", status)
        seq_num = seq_num + 1
        _object = {
            'seq_num': seq_num,
            'id': material.id,
            'order_num': material.order_num,
            'total_delivery_qty': material.total_delivery_qty,
            'sd_time_B109': material.sd_time_B109,
            'sd_time_B106': material.sd_time_B106,
            'sd_time_B110': material.sd_time_B110,
            'user_id': name,
            'begin_time': record.begin_time,
            'end_time': record.end_time if record.process_type != 31 else '',
            'period_time': period_time_str if record.process_type != 31 else '',
            'work_time': work_time_str if record.process_type != 31 else '',
            'single_std_time': single_std_time_str if record.process_type != 31 else '',
            'process_type': status,
            'create_at': record.create_at
        }
        _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("getProcessesByOrderNum, 總數: ", temp_len)

    # 根據 create_at 屬性的值進行排序
    _results = sorted(_results, key=lambda x: x['create_at'])

    return jsonify({

      'processes': _results
    })


# # get all all Warehouse For Assemble
@getTable.route("/getAbnormalCausesByHistory", methods=['POST'])
def get_abnormal_causes_by_history():
    print("getAbnormalCausesByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True

    materials = [u.__dict__ for u in s.query(Material).all()]

    # 過濾 isAssembleAlarm 為 True 的資料
    filtered_materials = [record for record in materials if record['isAssembleAlarm']]
    for record in filtered_materials:
      #包含歷史檔：_history_flag=true
      #不包含歷史檔:_history_flag=false and record['isAssembleAlarmRpt']=false
      if not (_history_flag==True or (record['isAssembleAlarmRpt']==False and _history_flag==False)):
        continue


# # get all all Warehouse For Assemble
@getTable.route("/getWarehouseForAssembleByHistory", methods=['POST'])
def get_Warehouse_For_assemble_by_history():
    print("getWarehouseForAssembleByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True

    materials = [u.__dict__ for u in s.query(Material).all()]
    #processed_order_nums = set()

    # 過濾掉 isAssembleStationShow 為 True 的資料
    filtered_materials = [record for record in materials if record['isAssembleStationShow']]
    for record in filtered_materials:
      #包含歷史檔：_history_flag=true
      #不包含歷史檔:_history_flag=false and record['isAllOk']=false
      if not (_history_flag==True or (record['isAllOk']==False and _history_flag==False)):
        continue
      cleaned_comment = record['material_comment'].strip()  # 刪除 material_comment 字串前後的空白

      _object = {
        'id': record['id'],
        'order_num': record['order_num'],                   #訂單編號
        'material_num': record['material_num'],             #物料編號
        'req_qty': record['material_qty'],                  #訂單數量
        'date': record['material_delivery_date'],           #交期
        'delivery_qty': record['assemble_qty'],             #組裝完成數量(到庫數量)
        'allOk_qty': record['allOk_qty'],                   #確認完成數量
        'total_allOk_qty': record['total_allOk_qty'],
        'input_disable': record['input_disable'],
        'delivery_date':record['material_delivery_date'],   #交期
        'shortage_note': record['shortage_note'],           #缺料註記 '元件缺料'
        'comment': cleaned_comment,                         #說明
        'isTakeOk' : record['isAllOk'],                     #true:成品已入庫
        'isShow' : record['isAssembleStationShow'],         #false:歷史檔案
        'isLackMaterial' : record['isLackMaterial'],
        'isBatchFeeding' :  record['isBatchFeeding'],
        'whichStation' : record['whichStation'],
        'show1_ok' : record['show1_ok'],
        'show2_ok' : record['show2_ok'],
        'show3_ok' : record['show3_ok'],
      }

      _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("getWarehouseForAssembleByHistory, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 isTakeOk 屬性的值進行排序
    _results = sorted(_results, key=lambda x: not x['isTakeOk'])

    return jsonify({
      'status': return_value,
      'warehouse_for_assemble': _results
    })

'''
@getTable.route("/getInformationsForAssembleErrorByHistory", methods=['POST'])
def get_informations_for_assemble_error_by_history():
    print("getInformationsForAssembleErrorByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True
    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                3              4             5           6             7            8             9           10                 11           12            13          14                15            16          17
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)    16(agv_start)
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業',  'agv Start']

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for material_record in _objects:    # for loop a
      #包含歷史檔：_history_flag=true
      #不包含歷史檔:_history_flag=false and record['isAssembleAlarmRpt']=false
      if not (_history_flag==True or (material_record.isAssembleAlarm==False and material_record.isAssembleAlarmRpt==False and _history_flag==False)):
        continue

      skip_material = False   # 標誌變數，預設為 False
      assemble_ok = False
      assemble_users = []               # 用於存儲處理後的 user_id
      assemble_work_nums = []           # 用於存儲處理後的 user_id
      for assemble_record in material_record._assemble:   # for loop b
        if assemble_record.alarm_enable:   #False:異常
          continue

        assemble_ok = True

        user_id = assemble_record.user_id.lstrip('0')       # 去除前導的 0
        writer_id = assemble_record.writer_id.lstrip('0')   # 去除前導的 0

        #if user_id not in assemble_user_ids: # 於 user_ids 中, 檢查 user_id
        assemble_users.append(user_id)
        assemble_work_nums.append(assemble_record.work_num)
      #end for loop b

      temp_alarm_message=assemble_record.alarm_message.strip()
      temp_alarm_enable=assemble_record.alarm_enable

      user = ', '.join(assemble_users)        # 將列表轉換為以逗號分隔的字符串
      work =  ', '.join(assemble_work_nums)

      abnormal_cause_ids = [str(abnormal.id) for abnormal in material_record._abnormal_cause]       # 轉換為字串列表
      abnormal_cause_id_str = ",".join(abnormal_cause_ids) if len(abnormal_cause_ids) > 0 else ''   # 用逗號合併

      # 取得 material_record 關聯的 AbnormalCause
      abnormal_cause_strs = [
          f"{abnormal.message}({abnormal.number})" for abnormal in material_record._abnormal_cause
      ]
      abnormal_cause_message_str = ",".join(abnormal_cause_strs)  if len(abnormal_cause_strs) > 0 else '' #用逗號連接所有字串

      print("abnormal_cause_id_str:", len(abnormal_cause_ids), abnormal_cause_id_str)
      print("abnormal_cause_message_str:",len(abnormal_cause_strs), abnormal_cause_message_str)

      print("user:", user)
      print("work:", work)
      print("material order num:", material_record.order_num)
      cleaned_comment = material_record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

      temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
      temp_show2_ok = int(material_record.show2_ok)
      if (temp_show2_ok == 1):
        temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note

      _object = {
        'id': material_record.id,                                # 訂單編號的 table id
        'order_num': material_record.order_num,                  # 訂單編號
        'material_num': material_record.material_num,            # 物料編號
        'isTakeOk': material_record.isTakeOk,
        'whichStation': material_record.whichStation,
        'req_qty': material_record.material_qty,                 # 需求數量
        'delivery_date': material_record.material_delivery_date, # 交期
        'delivery_qty': material_record.delivery_qty,            # 現況數量
        'comment': cleaned_comment,                              # 說明
        'show1_ok': str1[int(material_record.show1_ok) - 1],     # 現況進度
        'show2_ok': temp_temp_show2_ok_str,
        'show3_ok': str3[int(material_record.show3_ok)],         # 現況備註
        'user': user,
        'work': work,
        #**abnormal_cause                                         # 將 cause_id, cause_number, cause_message 展開加入字典
        #'cause_number': '',
        'cause_id': abnormal_cause_id_str,
        'cause_message': abnormal_cause_message_str,
        #'assemble_id': assemble_record.id,
      }

      _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listInformationsForAssembleError, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 'order_num' 排序
    _results = sorted(_results, key=lambda x: x['order_num'])

    return jsonify({
      'status': return_value,
      'informations_for_assemble_error': _results
    })
'''

# 取得訂單「組裝異常」相關的歷史資訊清單
@getTable.route("/getInformationsForAssembleErrorByHistory", methods=['POST'])
def get_informations_for_assemble_error_by_history():
    print("getInformationsForAssembleErrorByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)   # 是否包含歷史資料
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True

    code_to_name = {
      '106': '雷射',  #第2個動作
      '109': '組裝',  #第1個動作
      '110': '檢驗'   #第3個動作
    }

    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                3              4             5           6             7            8             9           10                 11           12            13          14                15            16          17
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)    16(agv_start)
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業',  'agv Start']

    _alarm_objects = s.query(AbnormalCause).all()  # 取得所有 AbnormalCause 物件

    _alarm_objects_list = [
      {"id": item.id, "message": f"{item.message}({item.number})"}
      for item in _alarm_objects
    ]
    print("_alarm_objects_list: ", _alarm_objects_list)

    _alarm_objects_dict = {
      str(item.id): f"{item.message}({item.number})"
      for item in _alarm_objects
    }
    print("_alarm_objects_dict: ", _alarm_objects_dict)

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    index = 0

    for material_record in _objects:    # for loop a
      #包含歷史檔：_history_flag=true
      #不包含歷史檔:_history_flag=false and record['isAssembleAlarmRpt']=false
      if not (_history_flag==True or (material_record.isAssembleAlarm==False and material_record.isAssembleAlarmRpt==False and _history_flag==False)):
        continue

      skip_material = False             # 標誌變數，預設為 False
      assemble_ok = False
      assemble_users = []               # 用於存儲處理後的 user_id
      assemble_work_nums = []           # 用於存儲處理後的 user_id

      temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
      temp_show2_ok = int(material_record.show2_ok)

      for assemble_record in material_record._assemble:   # for loop b
        if assemble_record.alarm_enable:   #False:異常
          continue

        assemble_ok = True

        #user_id = assemble_record.user_id.lstrip('0')       # 去除前導的 0
        user = s.query(User).filter_by(emp_id=assemble_record.user_id).first()
        #writer_id = assemble_record.writer_id.lstrip('0') if assemble_record.writer_id else ''
        if assemble_record.writer_id:
          writer = s.query(User).filter_by(emp_id=assemble_record.writer_id).first()
          writerName = writer.emp_name
        else:
          writerName = ''

        #從 assemble_record 中取得 alarm_message 欄位，這個欄位是以逗號與空白分隔的字串（例如 "異常1, 異常2, 異常3"）。
        temp_alarm_message = assemble_record.alarm_message
        print("temp_alarm_message:", temp_alarm_message)

        # 解析字串(非 None 或空字串, 且以', '作為分隔符號)轉成 ID list，例如 ['1', '3', '4'], "" 或 None → []
        alarm_id_list = temp_alarm_message.split(', ')  if temp_alarm_message else []
        print("alarm_id_list:", alarm_id_list)

        # 對應出異常訊息文字，並過濾掉找不到的 id
        temp_alarm_message_list = [
          _alarm_objects_dict.get(alarm_id) for alarm_id in alarm_id_list
          if _alarm_objects_dict.get(alarm_id)
        ]
        print("temp_alarm_message_list:", temp_alarm_message_list)

        #說明: 進一步過濾 temp_alarm_message_list 中的元素，只保留非空字串（msg 為 True）。
        #      這是為了避免有空的異常訊息（例如 "異常1, , 異常3"）也被加入。
        filtered_list = [msg for msg in temp_alarm_message_list if msg]
        print("filtered_list:", filtered_list)

        temp_alarm_enable = assemble_record.alarm_enable

        #abnormal_cause_ids = [str(abnormal.id) for abnormal in material_record._abnormal_cause]       # 轉換為字串列表
        #abnormal_cause_id_str = ",".join(abnormal_cause_ids) if len(abnormal_cause_ids) > 0 else ''   # 用逗號合併

        # 取得 material_record 關聯的 AbnormalCause
        #abnormal_cause_strs = [
        #    f"{abnormal.message}({abnormal.number})" for abnormal in material_record._abnormal_cause
        #]
        #abnormal_cause_message_str = ",".join(abnormal_cause_strs)  if len(abnormal_cause_strs) > 0 else '' #用逗號連接所有字串

        cleaned_comment = material_record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

        code = assemble_record.work_num[1:]                           # 取得字串中的代碼 (去掉字串中的第一個字元)
        work = code_to_name.get(code, '')                             # 查找對應的中文名稱
        '''
        temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
        temp_show2_ok = int(material_record.show2_ok)

        if (temp_show2_ok == 1):
          temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note
        '''

        # 處理 show2_ok 的情況
        if temp_show2_ok == 5 or temp_show2_ok == 7 or temp_show2_ok == 9:
          for _record in material_record._assemble:
            # 如果 `total_ask_qty_end` 為 1, 2 或 3，替換 `00/00/00` 的相應部分
            if _record.total_ask_qty_end in [1, 2, 3]:
              completed_qty = str(_record.completed_qty)  # 將數值轉換為字串
              date_parts = temp_temp_show2_ok_str.split('/')  # 分割 `00/00/00` 為 ['00', '00', '00']
              date_parts[_record.total_ask_qty_end - 1] = completed_qty  # 替換對應位置
              temp_temp_show2_ok_str = '/'.join(date_parts)  # 合併回字串

        if (temp_show2_ok == 1):
          temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note

        #temp_temp_show2_ok_str = re.sub(r'\b00\b', 'na', temp_temp_show2_ok_str)
        temp_temp_show2_ok_str = re.sub(r'\b00\b', '', temp_temp_show2_ok_str)

        index += 1

        _object = {
          'index': index,
          'id': material_record.id,                                # 訂單編號的 table id
          'assemble_id': assemble_record.id,
          'order_num': material_record.order_num,                  # 訂單編號
          'material_num': material_record.material_num,            # 物料編號
          'isTakeOk': material_record.isTakeOk,
          'whichStation': material_record.whichStation,
          'req_qty': material_record.material_qty,                  # 需求數量
          'delivery_date': material_record.material_delivery_date,  # 交期
          'delivery_qty': material_record.delivery_qty,             # 現況數量
          'comment': cleaned_comment,                               # 說明
          'show1_ok': str1[int(material_record.show1_ok) - 1],      # 現況進度
          'show2_ok' : temp_temp_show2_ok_str,                      #現況進度(途程)
          'show3_ok': str3[int(material_record.show3_ok)],          # 現況備註
          'cause_user': writerName,   #填寫人員
          'user': user.emp_name,      #檢點人員
          #'user': user_id,
          'work': work,
          #**abnormal_cause                                         # 將 cause_id, cause_number, cause_message 展開加入字典
          #'cause_number': '',
          #'cause_id': abnormal_cause_id_str,
          #'cause_message': abnormal_cause_message_str,
          'cause_message':filtered_list,
          #'assemble_id': assemble_record.id,
        }

        _results.append(_object)
        #end loop b
    #end loop a
    s.close()

    temp_len = len(_results)
    print("getInformationsForAssembleErrorByHistory, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 'order_num' 排序
    _results = sorted(_results, key=lambda x: x['order_num'])

    return jsonify({
      'status': return_value,
      'informations_for_assemble_error': _results,
      'alarm_objects_list': _alarm_objects_list,
    })


# 取得訂單「組裝異常」相關的歷史資訊清單
@getTable.route("/getSchedulesForAssembleError", methods=['POST'])
def get_schedule_for_assemble_error():
    print("getScheduleForAssembleError....")

    data = request.json
    _history_flag = data.get('history_flag', False)   # 是否包含歷史資料
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True

    code_to_name = {
      '106': '雷射',  #第2個動作
      '109': '組裝',  #第1個動作
      '110': '檢驗'   #第3個動作
    }

    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                3              4             5           6             7            8             9           10                 11           12            13          14                15            16          17
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)    16(agv_start)
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業',  'agv Start']

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for material_record in _objects:    # for loop a
      #包含歷史檔：_history_flag=true
      #不包含歷史檔:_history_flag=false and record['isAssembleAlarmRpt']=false
      if not (_history_flag==True or (material_record.isAssembleAlarm==False and material_record.isAssembleAlarmRpt==False and _history_flag==False)):
        continue

      temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
      temp_show2_ok = int(material_record.show2_ok)

      for assemble_record in material_record._assemble:   # for loop b
        if assemble_record.alarm_enable:   #False:異常
          continue

        code = assemble_record.work_num[1:]                           # 取得字串中的代碼 (去掉字串中的第一個字元)
        work = code_to_name.get(code, '')                             # 查找對應的中文名稱

        # 處理 show2_ok 的情況
        if temp_show2_ok == 5 or temp_show2_ok == 7 or temp_show2_ok == 9:
          for _record in material_record._assemble:
            # 如果 `total_ask_qty_end` 為 1, 2 或 3，替換 `00/00/00` 的相應部分
            if _record.total_ask_qty_end in [1, 2, 3]:
              completed_qty = str(_record.completed_qty)  # 將數值轉換為字串
              date_parts = temp_temp_show2_ok_str.split('/')  # 分割 `00/00/00` 為 ['00', '00', '00']
              date_parts[_record.total_ask_qty_end - 1] = completed_qty  # 替換對應位置
              temp_temp_show2_ok_str = '/'.join(date_parts)  # 合併回字串

        if (temp_show2_ok == 1):
          temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note

        #temp_temp_show2_ok_str = re.sub(r'\b00\b', 'na', temp_temp_show2_ok_str)
        temp_temp_show2_ok_str = re.sub(r'\b00\b', '', temp_temp_show2_ok_str)

        _object = {
          'id': material_record.id,                                # 訂單編號的 table id
          'assemble_id': assemble_record.id,
          'order_num': material_record.order_num,                  # 訂單編號
          'material_num': material_record.material_num,            # 物料編號
          'isTakeOk': material_record.isTakeOk,
          'whichStation': material_record.whichStation,
          'show1_ok': str1[int(material_record.show1_ok) - 1],      # 現況進度
          'show2_ok' : temp_temp_show2_ok_str,                      #現況進度(途程)
          'show3_ok': str3[int(material_record.show3_ok)],          # 現況備註
          'work': work,
        }

        _results.append(_object)
        #end loop b
    #end loop a
    s.close()

    temp_len = len(_results)
    print("getScheduleForAssembleError, 總數: ", temp_len)
    if (temp_len == 0):
      return_value = False

    # 根據 'order_num' 排序
    _results = sorted(_results, key=lambda x: x['order_num'])

    return jsonify({
      'status': return_value,
      'schedules_for_assemble_error': _results,
    })

'''
# get all assemble error information by history
@getTable.route("/getInformationsForAssembleErrorByHistory", methods=['POST'])
def get_2_informations_for_assemble_error_by_history():
    print("2 getInformationsForAssembleErrorByHistory....")

    data = request.json
    _history_flag = data.get('history_flag', False)
    print("history_flag:", _history_flag)

    s = Session()

    _results = []
    return_value = True
    str1=['備料站', '組裝站', '成品站']
    #       0        1         2                3              4             5           6             7            8             9           10                 11           12            13          14                15            16          17
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']
    #      0        1         2(agv_begin)      3(agv_end)     4(開始鍵)     5(結束鍵)     6(開始鍵)     7(結束鍵)    8(開始鍵)     9(結束鍵)    10(agv_begin)     11(agv_end)    12(開始鍵)    13(結束鍵)   14(agv_begin)    15(agv_end)    16(agv_start)
    str3=['',      '等待agv', 'agv移至組裝區中', '等待組裝作業', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫作業', '入庫進行中', '入庫完成',  'agv移至備料區中', '等待備料作業',  'agv Start']

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for material_record in _objects:
      #print("material id:", material_record.id)
      skip_material = False  # 標誌變數，預設為 False
      user_ids = []  # 用於存儲處理後的 user_id
      #print("step a...", material_record.id)
      assemble_ok = False
      for assemble_record in material_record._assemble:
        if assemble_record.material_id != material_record.id:
          skip_material = True
        if assemble_record.alarm_enable == False:
          continue

        assemble_ok = True
        #print("assemble id:", assemble_record.id)
        user_id = assemble_record.user_id.lstrip('0')  # 去除前導的 0
        #user_ids.append(user_id)  # 將處理後的值加入列表
        # 檢查 user_id 是否已存在於 user_ids 中
        if user_id not in user_ids:
          user_ids.append(user_id)  # 如果不存在，則插入列表

      if skip_material or not assemble_ok:
          continue                # 跳過當前 material_record，進入下一個 _objects 的迴圈

      #print("material id:", material_record.id)

      temp_alarm_message=assemble_record.alarm_message.strip()
      temp_alarm_enable=assemble_record.alarm_enable
      if not _history_flag and temp_alarm_enable and temp_alarm_message:
        continue
      print("temp_alarm_message:",temp_alarm_message)

      user = ', '.join(user_ids)  # 將列表轉換為以逗號分隔的字符串
      print("user:", user)
      print("material order num:", material_record.order_num)
      cleaned_comment = material_record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

      temp_temp_show2_ok_str = str2[int(material_record.show2_ok)]
      temp_show2_ok = int(material_record.show2_ok)
      if (temp_show2_ok == 1):
        temp_temp_show2_ok_str = temp_temp_show2_ok_str + material_record.shortage_note

      ## 取得所有相關聯的 AbnormalCause 資料
      #abnormal_cause = (
      #  {
      #    "cause_id": material_record._abnormal_cause[0].id,
      #    "cause_number": material_record._abnormal_cause[0].number,
      #    "cause_message": material_record._abnormal_cause[0].message,
      #  }
      #  if material_record._abnormal_cause and len(material_record._abnormal_cause) > 0
      #  else {
      #    "cause_id": '',
      #    "cause_number": '',
      #    "cause_message": '',
      #  }
      #)


      temp_list = [x.strip("'") for x in temp_alarm_message.split(",")] if temp_alarm_message else []
      _object = {
        'id': material_record.id,                                # 訂單編號的 table id
        'order_num': material_record.order_num,                  # 訂單編號
        'material_num': material_record.material_num,            # 物料編號
        'isTakeOk': material_record.isTakeOk,
        'whichStation': material_record.whichStation,
        'req_qty': material_record.material_qty,                 # 需求數量
        'delivery_date': material_record.material_delivery_date, # 交期
        'delivery_qty': material_record.delivery_qty,            # 現況數量
        'comment': cleaned_comment,                              # 說明
        'show1_ok': str1[int(material_record.show1_ok) - 1],     # 現況進度
        'show2_ok': temp_temp_show2_ok_str,
        'show3_ok': str3[int(material_record.show3_ok)],         # 現況備註
        'user': user,
        #**abnormal_cause                                         # 將 cause_id, cause_number, cause_message 展開加入字典
        #'cause_number': '',
        'cause_message': temp_list,
        'assemble_id': assemble_record.id,
      }

      _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listInformationsForAssembleError, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    # 根據 'order_num' 排序
    _results = sorted(_results, key=lambda x: x['order_num'])

    return jsonify({
      'status': return_value,
      'informations_for_assemble_error': _results
    })
'''

# list all materials and assemble data by current user
@getTable.route("/getMaterialsAndAssemblesByUser", methods=['POST'])
def get_materials_and_assembles_by_user():
    print("getMaterialsAndAssemblesByUser....")

    request_data = request.get_json()
    print("request_data:", request_data)
    _user_id = request_data['user_id']
    print("user_id:", _user_id)
    #_history = request_data['history']

    s = Session()

    _results = []
    return_value = True
    code_to_name = {'106':'雷射', '109':'組裝', '110':'檢驗'}
    code_to_assembleStep = {
      '109': 3,   #第1, 1,      個製程
      '106': 2,   #第2     1,   個製程
      '110': 1    #第3, 2, 2, 1 個製程
    }

    #       0         1        2                 3              4           5            6            7            8             9           10                  11            12
    str2=['未備料', '備料中',  '備料完成',       '等待組裝作業', '組裝進行中', '00/00/00',  '雷射進行中', '00/00/00',  '檢驗進行中',  '00/00/00', '等待入庫作業',     '入庫進行中',  '入庫完成']

    # 使用 with_for_update() 來加鎖
    _objects = s.query(Material).with_for_update().all()

    ## 初始化一個 set 來追蹤已處理的 (order_num, format_name)
    # 初始化一個 set 來追蹤已處理的 (order_num_id, format_name)
    processed_records = set()

    ## 初始化一個暫存字典來存放每個 order_num 下的最大 process_step_code
    # 初始化一個暫存字典來存放每個 order_num_id 下的最大 process_step_code
    max_step_code_per_order = {}

    # 搜尋所有紀錄，找出每個訂單下最大的 process_step_code
    for material_record in _objects:
      for assemble_record in material_record._assemble:

        # 檢查員工編號是否符合, 且生產報工的已領取總數是否為0
        if assemble_record.user_id != _user_id or assemble_record.total_ask_qty == 0:
          continue  # 如果不符合，跳過這筆紀錄

        #code = assemble_record.work_num[1:]                  # 取得字串中的代碼 (去掉字串中的第一個字元)
        #step_code = code_to_assembleStep.get(code, 0)        # 取得對應的 step code
        step_code = assemble_record.process_step_code         # 直接使用資料中的 step_code

        #order_num = material_record.order_num               # 訂單編號
        order_num_id = material_record.id                   # 該筆訂單編號的table id

        ## 設定或更新該 order_num_id 下的最大 step code
        #if order_num_id not in max_step_code_per_order:
        #    max_step_code_per_order[order_num_id] = step_code
        #else:
        #    max_step_code_per_order[order_num_id] = max(max_step_code_per_order[order_num_id], step_code)

        #    print(f"Processing material id={order_num_id}, assemble work_num={assemble_record.work_num}, step_code={step_code}")

        # 設定或更新該 order_num_id 下的最大 step code
        if order_num_id not in max_step_code_per_order:
            max_step_code_per_order[order_num_id] = step_code
            print(f"Set initial max step_code for id={order_num_id}: {step_code}")
        else:
            current_max = max_step_code_per_order[order_num_id]
            max_step_code_per_order[order_num_id] = max(current_max, step_code)
            print(f"Updated max step_code for id={order_num_id}: {current_max} -> {max_step_code_per_order[order_num_id]}")

    print("Final max_step_code_per_order:", max_step_code_per_order)

    #流程追蹤與狀態管理：
    #根據工序代碼（如 '106', '109', '110'）判斷當前流程階段，並匹配對應的名稱和步驟。
    #追蹤每個訂單的最大進度階段，確保顯示的資料反映正確的流程狀態。

    # 在此期間，_objects 中的資料會被鎖定，其他進程或交易無法修改這些資料, 但自己可以執行你需要的操作，如更新或處理資料
    #_objects = s.query(Material).all()
    index = 0
    for material_record in _objects:
      assemble_records = material_record._assemble
      for assemble_record in material_record._assemble:

        # 檢查員工編號是否符合及生產報工的已領取總數不為0
        if assemble_record.user_id != _user_id or assemble_record.total_ask_qty == 0 or material_record.isAssembleStationShow:
          continue  # 如果不符合，跳過這筆紀錄

        code = assemble_record.work_num[1:]                 # 取得字串中的代碼 (去掉字串中的第一個字元)
        name = code_to_name.get(code, '')                   # 查找對應的中文名稱
        format_name = f"{assemble_record.work_num}({name})"
        order_num_id = material_record.id                   # 該筆訂單編號的table id
        # 如果 (order_num_id, format_name) 組合已經存在，則跳過
        if (order_num_id, format_name) in processed_records:
          continue

        # 比較該筆記錄的 step_code 是否為該訂單下最大的
        #max_step_code = max_step_code_per_order.get(order_num, 0)
        max_step_code = max_step_code_per_order.get(order_num_id, 0)
        step_code = assemble_record.process_step_code
        step_enable = (step_code == max_step_code and material_record.whichStation==2)                # 如果是最大值，則啟用
        #print("max_step_code_per_order:",max_step_code_per_order)
        #print("step_code , max_step_code:", step_code , max_step_code)
        num = int(material_record.show2_ok)
        print("bug num:", num)
        cleaned_comment = material_record.material_comment.strip()          # 刪除 material_comment 字串前後的空白

        temp_assemble_process_str = str2[num]

        temp_assemble_process_str = str2[num]
        temp_show2_ok = int(material_record.show2_ok)

        #if (num == 1):
        if temp_show2_ok == 1:
          temp_assemble_process_str = temp_assemble_process_str + material_record.shortage_note

        index += 1

        #
        # 處理 show2_ok 的情況

        if temp_show2_ok in [5, 7, 9]:
          for temp2_assemble_record in assemble_records:
            if temp2_assemble_record.total_ask_qty_end in [1, 2, 3]:
              completed_qty = str(temp2_assemble_record.completed_qty)                  # 將數值轉換為字串
              date_parts = temp_assemble_process_str.split('/')                         # 分割 00/00/00 為 ['00', '00', '00']
              date_parts[temp2_assemble_record.total_ask_qty_end - 1] = completed_qty   # 替換對應位置
              temp_assemble_process_str = '/'.join(date_parts)                          # 合併回字串
        #

        _object = {
          'index': index,                             #agv送料序號
          'id': material_record.id,                   #訂單編號
          'order_num': material_record.order_num,                   #訂單編號
          'assemble_work': format_name,                             #工序
          'material_num': material_record.material_num,             #物料編號
          #'assemble_process': '' if (num > 2 and not step_enable) else str2[num],       #途程目前狀況 isTakeOk & step_enable
          'assemble_process': '' if (num > 2 and not step_enable) else temp_assemble_process_str,
          'assemble_process_num': num,
          'assemble_id': assemble_record.id,
          'req_qty': material_record.material_qty,                                         #需求數量(作業數量)
          'total_ask_qty': assemble_record.total_ask_qty,
          'total_ask_qty_end': assemble_record.total_ask_qty_end,
          'process_step_code': assemble_record.process_step_code,

          'total_receive_qty_num': assemble_record.total_ask_qty,                       #領取總數量
          'total_receive_qty': f"({assemble_record.total_completed_qty})",              # 已完成總數量
          'total_receive_qty_num': assemble_record.total_completed_qty,
          'receive_qty': assemble_record.completed_qty,                                 #完成數量
          'delivery_date': material_record.material_delivery_date,                      #交期
          'delivery_qty': material_record.delivery_qty,                                 #現況數量
          'assemble_qty': material_record.assemble_qty,                                 #(組裝）完成數量
          'total_assemble_qty': material_record.total_assemble_qty,                     #已(組裝）完成總數量

          'comment': cleaned_comment,                                                   #說明
          'isAssembleAlarm' : material_record.isAssembleAlarm,
          'alarm_enable' : assemble_record.alarm_enable,
          'whichStation' : material_record.whichStation,
          'isTakeOk': material_record.isAssembleStation3TakeOk,                         # true:組裝站製程3完成(最後製程)
          'isLackMaterial': material_record.isLackMaterial,
          'isShow': assemble_record.isAssembleStationShow,
          'currentStartTime': assemble_record.currentStartTime,
          'tooltipVisible': False,                                                      #顯示數字輸入欄位alarm
          'input_disable': assemble_record.input_end_disable,
          'process_step_enable': step_enable,
        }

        processed_records.add((order_num_id, format_name))
        _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("getMaterialsAndAssemblesByUser, 總數: ", temp_len)
    if (temp_len == 0):
      return_value = False

    return jsonify({
        'status': return_value,
        'materials_and_assembles_by_user': _results
    })


# get agv status by id
@getTable.route("/getAGV", methods=['POST'])
def get_agv():
  print("getAGV....")

  request_data = request.get_json()
  #_id = request_data['id']
  _id = request_data.get('agv_id')
  #print("request_data", request_data, _id)
  s = Session()

  myAgv = s.query(Agv).filter(Agv.id == _id).first()
  #print("myAgv", myAgv, myAgv.station)
  _object = {
    #'id': myAgv.id,
    'status': myAgv.status,
    'station': myAgv.station
  }

  s.close()

  return jsonify({
    'agv_data': _object
  })
