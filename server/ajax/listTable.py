import math
import random
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.sql import func
from database.tables import User, Material, Bom, Permission, Setting, Session

from flask_cors import CORS

from operator import itemgetter

from dotenv import dotenv_values

import pymysql
from sqlalchemy import exc

listTable = Blueprint('listTable', __name__)

# ------------------------------------------------------------------

@listTable.route("/listFileOK", methods=['GET'])
def list_file_ok():
  print("listFileOK....")

  _file_ok = current_app.config['file_ok']
  print("file_ok flag value is: ", _file_ok)

  if _file_ok:
    current_app.config['file_ok'] = False
    #file_ok = False

  return jsonify({
    'outputs': _file_ok
  })


# list socket server ip
@listTable.route("/listSocketServerIP", methods=['GET'])
def list_Socket_Server_ip():
  print("listSocketServerIP....")

  _socket_server_ip = current_app.config['socket_server_ip']
  print("socket_server_ip is: ", _socket_server_ip)

  return jsonify({
    'socket_server_ip': _socket_server_ip
  })


# list all departments
@listTable.route("/listDepartments", methods=['GET'])
def list_departments():
  print("listDepartments....")

  env_vars = dotenv_values(current_app.config['envDir'])

  #部門資料
  departments_str= env_vars["chumpower_departments"]
  departments = departments_str.split(",")

  return jsonify({
    'departments': departments,
  })

# list all Marquees
@listTable.route("/listMarquees", methods=['GET'])
def list_marquees():
  print("listMarquees....")

  env_vars = dotenv_values(current_app.config['envDir'])
  #marquees資料
  marquees = [env_vars["Marquee_0"], env_vars["Marquee_1"], env_vars["Marquee_2"], env_vars["Marquee_3"]]

  return jsonify({
    'marquees': marquees,
  })


# list all users
@listTable.route("/listUsers", methods=['GET'])
def list_users():
    print("listUsers....")

    s = Session()
    _user_results = []
    return_value = True
    _objects = s.query(User).all()
    users = [u.__dict__ for u in _objects]
    for user in users:
      #print("user:", user)
      if (user['isRemoved']):
        perm_item = s.query(Permission).filter_by(id = user['perm_id']).first()
        setting_item = s.query(Setting).filter_by(id = user['setting_id']).first()

        _user_object = {
          'emp_id': user['emp_id'],
          'emp_name': user['emp_name'],
          'dep_name': user['dep_name'],
          'emp_perm': perm_item.auth_code,    #4, 3, 2, 1
          'emp_lastRoutingName': setting_item.lastRoutingName,
          'routingPriv': setting_item.routingPriv,
        }
        _user_results.append(_user_object)
    s.close()

    temp_len = len(_user_results)
    print("listUsers, 員工總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    return jsonify({
        'status': return_value,
        'users': _user_results    #員工資料
    })
'''
# list all bom
@listTable.route("/listBoms", methods=['GET'])
def list_boms():
    print("listBoms....")

    request_data = request.get_json()
    _order_num = request_data['order_num']
    print("_order_num:", _order_num)
    return_value = True
    s = Session()

    # 查詢 Material，根據 order_num 取得對應的 Material 資料
    material = s.query(Material).filter(Material.order_num == _order_num).first()
    print("material:", material)
    boms = material._bom  # 透過關聯屬性取得所有 bom
    print("boms:", bom)

    # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
    result = [
      {
        'seq_num': bom.seq_num,           # 項目編號
        'material_num': bom.material_num,     # 物料編號
        'mtl_comment': bom.material_comment,  # 物料說明
        'qty': bom.req_qty,                   # 數量
        'date': material.material_date,       # 日期
        'date_alarm': '',
        'receive': True,                      #領取
        'lack': False                         #缺料
      }
      for bom in boms if not bom.isPickOK
    ]

    s.close()

    temp_len = len(results)
    print("listBoms, 總數: ", temp_len)
    if (temp_len == 0):
      return_value = False

    return jsonify({
      'status': return_value,
      'boms': results
    })
'''
# list all materials
@listTable.route("/listMaterials", methods=['GET'])
def list_materials():
    print("listMaterials....")

    s = Session()

    _results = []
    return_value = True

    _objects = s.query(Material).all()
    materials = [u.__dict__ for u in _objects]
    for record in materials:
      #print("material record:", record)
      #if not record['isTakeOk']:   # 檢查 isTakeOk 是否為 False
      if not record['isShow']:   # 檢查 isShow 是否為 False
        cleaned_comment = record['material_comment'].strip()  # 刪除 material_comment 字串前後的空白
        _object = {
          'order_num': record['order_num'],           #訂單編號
          'material_num': record['material_num'],     #物料編號
          #'material_status': 0,                       #0:未備料, 1:備料中, 2:備料完成
          'req_qty': record['material_qty'],          #需求數量
          'date': record['material_date'],            #(建立日期)
          'delivery_date':record['material_delivery_date'],   #交期
          'shortage_note': '',                        #缺料註記 '元件缺料'
          'comment': cleaned_comment,                 #說明
          'isTakeOk' : record['isTakeOk'],
          'isShow' : record['isShow'],
          'whichStation' : record['whichStation'],
          'show1_ok' : record['show1_ok'],
          'show2_ok' : record['show2_ok'],
          'show3_ok' : record['show3_ok'],
        }

        _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listMaterials, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    return jsonify({
        'status': return_value,
        'materials': _results
    })


# list all materials and assemble data
@listTable.route("/listMaterialsAndAssembles", methods=['GET'])
def list_materials_and_assembles():
    print("listMaterialsAndAssembles....")

    s = Session()

    _results = []
    return_value = True
    code_to_name = {
      '106': '雷射',
      '109': '組裝',
      '110': '檢驗'
    }
    code_to_assembleStep = {
      '109': 3,
      '106': 2,
      '110': 1
    }

    #       0         1        2          3        4            5           6            7           8            9
    str2=['未備料', '備料中', '備料完成', '未組裝', '組裝作業中', 'aa/00/00', '雷射作業中', 'aa/bb/00', '檢驗作業中', 'aa/bb/cc',]


    # 使用 with_for_update() 來加鎖
    _objects = s.query(Material).with_for_update().all()

    # 初始化一個暫存字典來存放每個 order_num 下的最大 process_step_code
    max_step_code_per_order = {}

    # 搜尋所有紀錄，找出每個訂單下最大的 process_step_code
    for material_record in _objects:
      for assemble_record in material_record._assemble:
        code = assemble_record.work_num[1:]                # 取得字串中的代碼 (去掉字串中的第一個字元)
        step_code = code_to_assembleStep.get(code, 0)      # 取得對應的 step code

        order_num = material_record.order_num              # 訂單編號

        # 設定或更新該 order_num 下的最大 step code
        if order_num not in max_step_code_per_order:
            max_step_code_per_order[order_num] = step_code
        else:
            max_step_code_per_order[order_num] = max(max_step_code_per_order[order_num], step_code)

    # 在此期間，_objects 中的資料會被鎖定，其他進程或交易無法修改這些資料, 但自己可以執行你需要的操作，如更新或處理資料
    #_objects = s.query(Material).all()
    for material_record in _objects:
      for assemble_record in material_record._assemble:
        cleaned_comment = material_record.material_comment.strip()          # 刪除 material_comment 字串前後的空白

        code = assemble_record.work_num[1:]             # 取得字串中的代碼 (去掉字串中的第一個字元)
        name = code_to_name.get(code, '')               # 查找對應的中文名稱
        #step_code = code_to_assembleStep.get(code, 0)   #
        step_code = assemble_record.process_step_code
        order_num = material_record.order_num                       # 訂單編號

        # 比較該筆記錄的 step_code 是否為該訂單下最大的
        max_step_code = max_step_code_per_order.get(order_num, 0)
        step_enable = (step_code == max_step_code)  # 如果是最大值，則啟用
        format_name = f"{assemble_record.work_num}({name})"
        num = int(material_record.show2_ok)

        _object = {
          'order_num': material_record.order_num,                   #訂單編號
          'assemble_work': format_name,                             #工序
          'material_num': material_record.material_num,             #物料編號
          #'assemble_process': str2[num],                            #途程目前狀況 material_record.isTakeOk & step_enable
          'assemble_process': '' if (num > 2 and not step_enable) else str2[num],                            #途程目前狀況 isTakeOk & step_enable
          'assemble_process_num': num,
          'assemble_id': assemble_record.id,
          'req_qty': assemble_record.meinh_qty,                                 #需求數量(作業數量)
          'total_receive_qty': '(' + str(assemble_record.total_ask_qty) + ')',  #領取總數量
          'total_receive_qty_num': assemble_record.total_ask_qty,               #領取總數量
          'receive_qty': assemble_record.ask_qty,                               #領取數輛
          'delivery_date': material_record.material_delivery_date,  #交期
          'comment': cleaned_comment,                               #說明
          'isTakeOk' : material_record.isTakeOk,
          'whichStation' : material_record.whichStation,
          'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,       # true:組裝站製程1完成
          'isAssembleStation2TakeOk': material_record.isAssembleStation1TakeOk,       # true:組裝站製程2完成
          'isAssembleStation3TakeOk': material_record.isAssembleStation1TakeOk,       # true:組裝站製程3完成
          'currentStartTime': assemble_record.currentStartTime,
          'tooltipVisible': False,
          'input_disable': False,
          #'process_step_code': step_code,
          'process_step_enable': step_enable,
        }
        #print(_object)
        _results.append(_object)

    s.close()

    temp_len = len(_results)
    print("listMaterialsAndAssembles, 總數: ", temp_len)
    if (temp_len == 0):
      return_value = False

    return jsonify({
        'status': return_value,
        'materials_and_assembles': _results
    })


# list all materials for information list
@listTable.route("/listInformations", methods=['GET'])
def list_informations():
    print("listInformation....")

    s = Session()

    _results = []
    return_value = True
    str1=['備料站', '組裝站', '成品站']
    #       0        1         2         3         4             5          6             7           8             9         10        11           12           13          14          15            16          17
    str2=['未備料', '備料中', '備料完成', '未組裝', '組裝作業中', 'aa/00/00', '雷射作業中', 'aa/bb/00', '檢驗作業中', 'aa/bb/cc', '未入庫', '檢料作業中', 'aa/00/00', '雷刻作業中', 'aa/bb/00', '包裝作業中', 'aa/bb/cc', '完成入庫']
    #      0    1          2(agv_begin)     3(agv_end)   4(開始鍵)     5(結束鍵)     6(開始鍵)    7(結束鍵)     8(開始鍵)    9(結束鍵)     10(agv_begin)     11(agv_end)  12(開始鍵)    13(結束鍵)   14(開始鍵)    15(結束鍵)   16(開始鍵)    17(結束鍵)    18(agv_begin)    19(agv_end)  20(agv_alarm)
    str3=['', '等待agv', 'agv移至組裝區中', '等待組裝中', '組裝進行中', '組裝已結束', '雷射進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至成品區中', '等待入庫中', '檢料進行中', '檢料已結束', '雷刻進行中', '雷射已結束', '檢驗進行中', '檢驗已結束', 'agv移至備料區中', '等待備料中', 'agv待處理中...']

    _objects = s.query(Material).all()  # 取得所有 Material 物件

    for record in _objects:
      #assemble_records = record._assemble   # 存取與該 Material 物件關聯的所有 Assemble 物件
      #print("record:", record)
      cleaned_comment = record.material_comment.strip()  # 刪除 material_comment 字串前後的空白
      _object = {
        'order_num': record.order_num,                 #訂單編號
        'material_num': record.material_num,           #物料編號
        'isTakeOk': record.isTakeOk,
        'whichStation': record.whichStation,
        'req_qty': record.material_qty,                #需求數量
        'delivery_date':record.material_delivery_date, #交期
        'comment': cleaned_comment,                    #說明
        'show1_ok' : str1[int(record.show1_ok) - 1],                  #現況進度
        'show2_ok' : str2[int(record.show2_ok)],
        'show3_ok' : str3[int(record.show3_ok)],                  #現況備註
      }

      _results.append(_object)

    s.close()

    temp_len = len(_results)
    #print("listInformations, 資料: ", _results)
    print("listInformations, 總數: ", temp_len)
    if (temp_len == 0):
        return_value = False

    return jsonify({
        'status': return_value,
        'informations': _results
    })

