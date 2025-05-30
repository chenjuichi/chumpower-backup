import os
import datetime
import pathlib
import csv
import time
import shutil
import psutil
import glob
import math

import pymysql
from sqlalchemy import exc

import re

import pandas as pd
import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from database.tables import User, Session, Material, Bom, Assemble, Product
from flask import Blueprint, jsonify, request, current_app

#from werkzeug.utils import secure_filename

excelTable = Blueprint('excelTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


# 生成唯一檔案名稱的函式
def get_unique_filename(target_dir, filename, chip):
    base, ext = os.path.splitext(filename)  # 分離檔案名稱與副檔名
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(target_dir, unique_filename)):  # 檢查檔案是否已存在
        unique_filename = f"{base}_{chip}_{counter}{ext}"  # 為檔名新增後綴
        counter += 1
    return unique_filename


#to convert date format
'''
def convert_date(date_str):
  try:
      return datetime.datetime.strptime(date_str, "%Y/%m/%d").date()
  except ValueError:
      return None
'''
def convert_date(date_value):
    try:
        return pd.to_datetime(date_value).date()  # 使用 pandas 轉換為日期
    except (ValueError, TypeError):
        return None


def close_open_file(filepath):
    # 遍歷所有進程
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # 檢查該進程打開的所有文件
            for item in proc.open_files():
                if item.path == filepath:
                    # 如果文件被打開，嘗試關閉
                    print(f"關閉進程 {proc.pid} 打開的文件: {filepath}")
                    proc.terminate()  # 終止進程
                    proc.wait()  # 等待進程終止
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False


def pad_zeros(str):
    #length = len(str)
    #if length <= 1:
    return str.zfill(4)
    #else:
    #    return str.zfill(length + 3)


@excelTable.route("/fetchGlobalVar", methods=['GET'])
def fetch_global_var():
  print("fetchGlobalVar....")

  global global_var
  return jsonify({'value': global_var})


@excelTable.route("/countExcelFiles", methods=['GET'])
def count_excel_files():
    print("countExcelFiles....")

    _base_dir = current_app.config['baseDir']

    # 構建路徑模式，匹配以 "Report_" 開頭的 .xlsx 檔案
    #path_pattern = f"{_base_dir}/Report_*.xlsx"
    path_pattern = f"{_base_dir}/*.xlsx"
    # 使用 glob 找到所有符合條件的檔案
    files = glob.glob(path_pattern)
    # 計算檔案數量
    count = len(files)
    print("count:", count)
    # 如果沒有找到檔案，返回0
    #return count if count > 0 else 0
    return jsonify({
      'count': count
    })

'''
@excelTable.route("/readAllExcelFiles", methods=['GET'])
def read_all_excel_files():
  print("readAllExcelFiles....")

  global global_var

  return_value = False
  return_message1 = '錯誤, 沒有工單檔案!'
  return_message2 = ''
  return_message = ''
  file_count_total = 0  #檔案總數目
  file_count_ok = 0     #檔案內總筆數

  code_to_assembleStep = {'109': 3, '106': 2, '110': 1}

  _base_dir = current_app.config['baseDir']
  _target_dir = _base_dir.replace("_in", "_out")
  print("read excel files, 目錄: ", _base_dir)
  print("move excel files to, 目錄: ", _target_dir)

  # 讀取指定目錄下的所有指定檔案名稱
  files = [f for f in os.listdir(_base_dir) if os.path.isfile(os.path.join(_base_dir, f)) and f.startswith('Report_') and f.endswith('.xlsx')]
  if (files):   #有工單檔案, if condition_a
    sheet_names_to_check = [
      current_app.config['excel_product_sheet'],
      current_app.config['excel_bom_sheet'],
      current_app.config['excel_work_time_sheet']
    ]
    _startRow = int(current_app.config['startRow'])

    s = Session()

    for _file_name in files:  #檔案讀取, for loop_1
      file_count_total +=1
      _path = _base_dir + '\\' + _file_name
      global_var = _path + ' 檔案讀取中...'

      with open(_path, 'rb') as file:   # with loop_1_a
        workbook = openpyxl.load_workbook(filename=file, read_only=True)
        return_value = True
        return_message1 = ''
        missing_sheets = [sheet for sheet in sheet_names_to_check if sheet not in workbook.sheetnames]

        if missing_sheets:
          return_value = False
          return_message1 = '錯誤, 工單檔案內沒有相關工作表!'
          print(return_message1)
          break

        print(sheet_names_to_check[0] + ' sheet exists, data reading...')

        material_df = pd.read_excel(_path, sheet_name=0)  # First sheet for Material
        bom_df = pd.read_excel(_path, sheet_name=1)       # Second sheet for Bom
        assemble_df = pd.read_excel(_path, sheet_name=2)  # 3rd sheet for Assemble

        # Insert Material data, for loop_1_a_1
        for index, row in material_df.iloc[0:].iterrows():
          tempQty=row['數量']
          material = Material(
            order_num=row['單號'],
            material_num=row['料號'],
            material_comment=row['說明'],
            material_qty=tempQty,
            material_date=convert_date(row['立單日']),
            material_delivery_date=convert_date(row['交期']),
            total_delivery_qty=tempQty,
          )
          s.add(material)
          s.flush()

          product = Product(
              material_id=material.id,
          )
          s.add(product)

          s.commit()

          material_order = str(row.iloc[1]).strip()                 #確保 row.iloc[1] 為 str 型別

          bom_df['訂單'] = bom_df['訂單'].fillna(0).astype(int)      #檢查是否存在 NaN 值
          bom_df['訂單'] = bom_df['訂單'].fillna('').astype(str)     #保持字串型態
          bom_entries = bom_df[bom_df.iloc[:, 0] == material_order] # 查詢對應的 BOM 項目
          print(f"bom_entries 中的資料筆數: {len(bom_entries)}")

          # Insert corresponding BOM entries, for loop_1_a_1_a
          for bom_index, bom_row in bom_entries.iterrows():

            bom = Bom(
                material_id=material.id,                  # Use the ID of the inserted material
                seq_num=bom_row['預留項目'],
                material_num=bom_row['物料'],
                material_comment=bom_row['物料說明'],
                req_qty=bom_row['需求數量'],
                start_date=convert_date(row['交期'])
            )
            s.add(bom)
          #end for loop_1_a_1_a
          s.commit()

          assemble_entries = assemble_df[assemble_df.iloc[:, 0].astype(str).str.strip() == material_order.strip()]  #清除空格
          print(f"assemble_entries 中的資料筆數: {len(assemble_entries)}")

          # Insert corresponding Assemble entries, for loop_1_a_1_b
          for assemble_index, assemble_row in assemble_entries.iterrows():
            # 處理 NaN 值，將 NaN 替換為 None（SQLAlchemy 可以接受 None）
            reason = assemble_row['差異原因'] if not pd.isna(assemble_row['差異原因']) else None
            emp_num = assemble_row['員工號碼'] if not pd.isna(assemble_row['員工號碼']) else None
            confirm_comment = assemble_row['確認內文'] if not pd.isna(assemble_row['確認內文']) else None

            GMEIN = assemble_row['確認良品率 (GMEIN)']
            if GMEIN == 0:
              continue

            workNum = assemble_row['工作中心']
            code = workNum[1:]             # 取得字串中的代碼 (去掉字串中的第一個字元)
            step_code = code_to_assembleStep.get(code, 0)   #

            assemble = Assemble(
              material_id=material.id,                    # Use the ID of the inserted material
              material_num=assemble_row['物料'],
              material_comment=assemble_row['物料說明'],
              seq_num=assemble_row['作業'],
              work_num = workNum,
              process_step_code = step_code,
              meinh_qty=assemble_row['作業數量 (MEINH)'],
              good_qty = assemble_row['確認良品率 (GMEIN)'],           #確認良品數量
              non_good_qty = assemble_row['確認廢品 (MEINH)'],        #廢品數量

              reason = reason,
              user_id = emp_num,
              confirm_comment = confirm_comment,
            )
            s.add(assemble)
          #end for loop_1_a_1_b
          s.commit()
        #end for loop_1_a_1
      #end with loop_1_a

      try:
        unique_filename = get_unique_filename(_target_dir, _file_name, "copy")  # 生成唯一檔案名稱
        unique_target_path = os.path.join(_target_dir, unique_filename)         # 獲取完整目標路徑
        print("unique_target_path:",unique_target_path)
        shutil.move(_path, unique_target_path)                                  # 移動檔案到目標路徑
        print(f"檔案 {_path} 已成功移動到 {unique_target_path}")
      except PermissionError as e:
        print(f"無法移動文件 {_path}，因為它仍然被佔用: {e}")
      except Exception as e:
        print(f"移動檔案時發生錯誤: {e}")

    #end for loop_1
    s.close()
  #end if condition_a

  return jsonify({
    'status': return_value,
    'message': return_message1,
  })
'''


@excelTable.route("/readAllExcelFiles", methods=['GET'])
def read_all_excel_files():
  print("readAllExcelFiles....")

  global global_var

  return_value = False
  return_message1 = '錯誤, 沒有工單檔案!'
  return_message2 = ''
  return_message = ''
  file_count_total = 0  #檔案總數目
  file_count_ok = 0     #檔案內總筆數

  code_to_assembleStep = {'109': 3, '106': 2, '110': 1}

  _base_dir = current_app.config['baseDir']
  _target_dir = _base_dir.replace("_in", "_out")
  print("read excel files, 目錄: ", _base_dir)
  print("move excel files to, 目錄: ", _target_dir)

  # 讀取指定目錄下的所有指定檔案名稱
  #files = [f for f in os.listdir(_base_dir) if os.path.isfile(os.path.join(_base_dir, f)) and f.startswith('Report_') and f.endswith('.xlsx')]
  files = [f for f in os.listdir(_base_dir) if os.path.isfile(os.path.join(_base_dir, f)) and f.endswith('.xlsx')]
  if (files):   #有工單檔案, if condition_a
    sheet_names_to_check = [
      current_app.config['excel_product_sheet'],
      current_app.config['excel_bom_sheet'],
      current_app.config['excel_work_time_sheet']
    ]
    _startRow = int(current_app.config['startRow'])

    s = Session()

    for _file_name in files:  #檔案讀取, for loop_1
      file_count_total +=1
      _path = _base_dir + '\\' + _file_name
      global_var = _path + ' 檔案讀取中...'

      with open(_path, 'rb') as file:   # with loop_1_a
        workbook = openpyxl.load_workbook(filename=file, read_only=True)
        return_value = True
        return_message1 = ''
        missing_sheets = [sheet for sheet in sheet_names_to_check if sheet not in workbook.sheetnames]

        if missing_sheets:
          return_value = False
          return_message1 = '錯誤, 工單檔案內沒有相關工作表!'
          print(return_message1)
          break

        print(sheet_names_to_check[0] + ' sheet exists, data reading...')

        material_df = pd.read_excel(_path, sheet_name=0)  # First sheet for Material
        bom_df = pd.read_excel(_path, sheet_name=1)       # Second sheet for Bom
        assemble_df = pd.read_excel(_path, sheet_name=2)  # 3rd sheet for Assemble

        # Insert Material data, for loop_1_a_1
        for index, row in material_df.iloc[0:].iterrows():
          ### 新增 Material table 資料
          tempQty=row['數量']
          temp_sd_time_B109 =  0 if math.isnan(row['B109組裝工時(分)']) else row['B109組裝工時(分)']
          temp_sd_time_B106 =  0 if math.isnan(row['B106雷刻工時(分)']) else row['B106雷刻工時(分)']
          temp_sd_time_B110 =  0 if math.isnan(row['B110檢驗工時(分)']) else row['B110檢驗工時(分)']

          material = Material(
            order_num=row['單號'],
            material_num=row['料號'],
            material_comment=row['說明'],
            material_qty=tempQty,
            material_date=convert_date(row['立單日']),
            material_delivery_date=convert_date(row['交期']),
            total_delivery_qty=tempQty,
            sd_time_B109 = "{:.2f}".format(temp_sd_time_B109),
            sd_time_B106 = "{:.2f}".format(temp_sd_time_B106),
            sd_time_B110 = "{:.2f}".format(temp_sd_time_B110),
          )
          s.add(material)

          s.flush()
          ###

          ### 新增 Product table 資料
          product = Product(
            material_id=material.id,
          )
          s.add(product)

          s.commit()
          ###

          ### 新增 Bom table 資料
          material_order = str(row.iloc[1]).strip()                 #確保 row.iloc[1] 為 str 型別

          bom_df['訂單'] = bom_df['訂單'].fillna(0).astype(int)      #檢查是否存在 NaN 值
          bom_df['訂單'] = bom_df['訂單'].fillna('').astype(str)     #保持字串型態
          bom_entries = bom_df[bom_df.iloc[:, 0] == material_order] # 查詢對應的 BOM 項目
          print(f"bom_entries 中的資料筆數: {len(bom_entries)}")

          # Insert corresponding BOM entries, for loop_1_a_1_a
          for bom_index, bom_row in bom_entries.iterrows():

            bom = Bom(
                material_id=material.id,                  # Use the ID of the inserted material
                seq_num=bom_row['預留項目'],
                material_num=bom_row['物料'],
                material_comment=bom_row['物料說明'],
                req_qty=bom_row['需求數量'],
                start_date=convert_date(row['交期'])
            )
            s.add(bom)
          #end for loop_1_a_1_a
          s.commit()
          ###

          ### 新增 Assemble table 資料
          assemble_entries = assemble_df[assemble_df.iloc[:, 0].astype(str).str.strip() == material_order.strip()]  #清除空格
          print(f"assemble_entries 中的資料筆數: {len(assemble_entries)}")

          order_nums = set()  # 用於追踪已處理過的 order_num

          # Insert corresponding Assemble entries, for loop_1_a_1_b
          for assemble_index, assemble_row in assemble_entries.iterrows():
            # 處理 NaN 值，將 NaN 替換為 None（SQLAlchemy 可以接受 None）
            #reason = assemble_row['差異原因'] if not pd.isna(assemble_row['差異原因']) else None
            #
            #emp_num = assemble_row['員工號碼'] if not pd.isna(assemble_row['員工號碼']) else None
            #
            emp_num = assemble_row.get('員工號碼')
            emp_num = emp_num if not pd.isna(emp_num) else None
            #confirm_comment = assemble_row['確認內文'] if not pd.isna(assemble_row['確認內文']) else None

            #GMEIN = assemble_row['確認良品率 (GMEIN)']
            #if GMEIN == 0:
            #  continue

            workNum = assemble_row['工作中心']
            if workNum in order_nums:
              continue
            order_nums.add(workNum)

            code = workNum[1:]             # 取得字串中的代碼 (去掉字串中的第一個字元)
            step_code = code_to_assembleStep.get(code, 0)   #

            assemble = Assemble(
              material_id=material.id,                    # Use the ID of the inserted material
              material_num=assemble_row['物料'],
              material_comment=assemble_row['物料說明'],
              seq_num=assemble_row['作業'],
              work_num = workNum,
              process_step_code = step_code,

              #user_id = emp_num,
              user_id = '',
            )
            s.add(assemble)
          #end for loop_1_a_1_b
          s.commit()
          ###
        #end for loop_1_a_1
      #end with loop_1_a

      try:
        unique_filename = get_unique_filename(_target_dir, _file_name, "copy")  # 生成唯一檔案名稱
        unique_target_path = os.path.join(_target_dir, unique_filename)         # 獲取完整目標路徑
        print("unique_target_path:",unique_target_path)
        shutil.move(_path, unique_target_path)                                  # 移動檔案到目標路徑
        print(f"檔案 {_path} 已成功移動到 {unique_target_path}")
      except PermissionError as e:
        print(f"無法移動文件 {_path}，因為它仍然被佔用: {e}")
      except Exception as e:
        print(f"移動檔案時發生錯誤: {e}")

    #end for loop_1
    s.close()
  #end if condition_a

  return jsonify({
    'status': return_value,
    'message': return_message1,
  })


@excelTable.route("/modifyExcelFiles", methods=['POST'])
def modify_excel_files():

  data = request.json
  material_id = data.get("material_id")
  _id = data.get("id")
  _material_id = int(material_id)
  print("_id, _material_id:",_id, _material_id, type(_id), type(_material_id))

  global global_var

  return_value = False
  return_message1 = '錯誤, excel檔案內沒有該筆工單!'
  return_message = ''
  modifyBom = []  # 用於儲存 BOM 資料的清單

  _base_dir = current_app.config['baseDir']
  _modify_dir = _base_dir.replace("_in", "_modify")
  _target_dir = _base_dir.replace("_in", "_out")
  print("read modify excel files, 目錄: ", _modify_dir)
  print("move excel files to, 目錄: ", _target_dir)
  # 讀取指定目錄下的所有指定檔案名稱
  #files = [f for f in os.listdir(_modify_dir) if os.path.isfile(os.path.join(_modify_dir, f)) and f.startswith('Report_') and f.endswith('.xlsx')]
  files = [f for f in os.listdir(_modify_dir) if os.path.isfile(os.path.join(_modify_dir, f)) and f.endswith('.xlsx')]
  if (files):   #有工單檔案
    sheet_names_to_check = [
      current_app.config['excel_product_sheet'],
      current_app.config['excel_bom_sheet'],
    ]
    _startRow = int(current_app.config['startRow'])

    s = Session()

    #find_material = s.query(Material).filter_by(order_num = _material_id).first()
    find_material = s.query(Material).filter_by(id = _id).first() #找出一筆工單資料

    # 取得現有的 BOM 資料
    existing_bom = s.query(Bom).filter_by(material_id = find_material.id).all()
    existing_materials = {bom.material_num for bom in existing_bom}

    for _file_name in files:  #檔案讀取
      _path = _modify_dir + '\\' + _file_name
      global_var = _path + ' 檔案讀取中...'

      with open(_path, 'rb') as file:
        workbook = openpyxl.load_workbook(filename=file, read_only=True)
        return_value = True
        return_message1 = ''
        missing_sheets = [sheet for sheet in sheet_names_to_check if sheet not in workbook.sheetnames]

        if missing_sheets:
          return_value = False
          return_message1 = '錯誤, 工單檔案內沒有相關工作表!'
          print(return_message1)
          break

        print(sheet_names_to_check[0] + ' sheet exists, data reading...')

        bom_df = pd.read_excel(_path, sheet_name=1)               # Second sheet for Bom

        bom_df['訂單'] = bom_df['訂單'].fillna(0).astype(int)     # 檢查是否存在 NaN 值
        bom_df['訂單'] = bom_df['訂單'].fillna('').astype(str)    # 保持字串型態
        bom_entries = bom_df[bom_df['訂單'] == material_id]       # 查詢對應的 BOM 項目
        print(f"bom_entries 中的資料筆數: {len(bom_entries)}")

        # Insert corresponding BOM entries
        bom_data= []
        for bom_index, bom_row in bom_entries.iterrows():
          bom_data.append({
            'material_id': find_material.id,
            'seq_num': bom_row['預留項目'],
            'material_num': bom_row['物料'],
            'material_comment': bom_row['物料說明'],
            'req_qty': bom_row['需求數量'],
          })


        # 將現有的 BOM 資料加入 modifyBom
        id = 0
        for existing in existing_bom:
          id +=1
          modifyBom.append({
            "id": id,
            "material_id": existing.material_id,
            "seq_num": existing.seq_num,
            "material_num": existing.material_num,
            "mtl_comment": existing.material_comment,
            "qty": existing.req_qty,
            "start_date": existing.start_date,
            "date_alarm": '',
          })

        # 新增的 material_num
        for bom_entry in bom_data:
          material_num = bom_entry.get("material_num")
          if material_num not in existing_materials:
            '''
            new_bom = Bom(
              material_id = find_material.id,
              material_num = material_num,
              seq_num = bom_entry.get("seq_num"),
              material_comment = bom_entry.get("material_comment"),
              req_qty = bom_entry.get("req_qty"),
              start_date = find_material.material_delivery_date
            )
            s.add(new_bom)
            '''
            #existing_bom.append(new_bom)
            id +=1
            modifyBom.append({
              "id": id,
              "material_id": find_material.id,
              "seq_num": id,
              "material_num": material_num,
              "mtl_comment": bom_entry.get("material_comment"),
              "qty": bom_entry.get("req_qty"),
              "start_date": find_material.material_delivery_date,
              "date_alarm": '',
            })
      '''
      # 在程式的移動檔案邏輯中使用
      try:
        print("file_name:", _file_name)
        unique_filename = get_unique_filename(_target_dir, _file_name, "mdf")  # 生成唯一檔案名稱
        unique_target_path = os.path.join(_target_dir, unique_filename)  # 獲取完整目標路徑

        shutil.move(_path, unique_target_path)  # 移動檔案到目標路徑
        print(f"檔案 {_path} 已成功移動到 {unique_target_path}")
      except PermissionError as e:
        print(f"無法移動文件 {_path}，因為它仍然被佔用: {e}")
      except Exception as e:
        print(f"移動檔案時發生錯誤: {e}")
      '''
    #end for loop

    # 提交到資料庫
    #s.commit()
    #s.close()
  # end if

  return jsonify({
    'status': return_value,
    'message': return_message1,
    'modifyBom': modifyBom,
    'modifyFileName': _file_name,
  })


@excelTable.route("/deleteAssemblesWithNegativeGoodQty", methods=['GET'])
def delete_assembles_with_negative_good_qty():
  print("deleteAssemblesWithNegativeGoodQty...")

  s = Session()

  # 查詢所有 Assemble 資料
  _objects = s.query(Assemble).all()

  # 用來追蹤前一筆資料
  previous_assemble = None

  # 迭代每一筆 Assemble 資料
  for current_assemble in _objects:
    if current_assemble.good_qty < 0:
      # 如果發現 ask_qty 小於 0，則刪除當前及前一筆 Assemble 紀錄
      if previous_assemble:
        print(f"Deleting previous assemble: {previous_assemble.id}, good_qty={previous_assemble.good_qty}")
        s.delete(previous_assemble)  # 刪除前一筆 Assemble 紀錄
      print(f"Deleting current assemble: {current_assemble.id}, ask_qty={current_assemble.good_qty}")
      s.delete(current_assemble)  # 刪除當前 Assemble 紀錄

      # 處理與 Material 的關聯（如有必要）
      # 根據業務邏輯決定是否刪除 Material，或更新 Material 的某些狀態
      material = s.query(Material).filter(Material.id == current_assemble.material_id).first()
      if material:
        # 更新 Material 的欄位，例如 isTakeOk 或其他狀態
        # material.isTakeOk = False  # 更新某些狀態
        # 如果需要刪除 Material，也可以使用：
        # s.delete(material)
        print(f"Updating or deleting related material: {material.id}, material_num={material.material_num}")

    # 更新 previous_assemble 為當前 Assemble
    previous_assemble = current_assemble

  # 提交刪除
  s.commit()
  s.close()

  return jsonify({
    'status': True,
    #'message': return_message1,
  })


@excelTable.route("/exportToExcelForError", methods=['POST'])
def export_to_excel_for_error():
    print("exportToExcelForError....")

    request_data = request.get_json()

    _blocks = request_data['blocks']
    _count = request_data['count']
    _name = request_data['name']
    #temp = len(_blocks)

    print("_blocks:", _blocks)

    date = datetime.datetime.now()
    today = date.strftime('%Y-%m-%d-%H%M')
    file_name = '組裝異常記錄查詢_'+today + '.xlsx'
    current_file = 'C:\\vue\\chumpower\\excel_export\\'+ file_name

    print("filename:", current_file)
    file_check = os.path.exists(current_file)  # true:excel file exist

    return_value = True  # true: export into excel成功

    if file_check:
      try:
        os.remove(current_file)  # 刪除舊檔案
      except PermissionError:
        print(f"無法刪除 {current_file}，請確認是否已關閉該檔案")
        return_value = False
        return jsonify({"success": False, "message": "請關閉 Excel 檔案後重試"})
    #if file_check:
    #  wb = openpyxl.load_workbook(current_file)  # 開啟現有的 Excel 活頁簿物件
    #else:
    #  wb = Workbook()     # 建立空白的 Excel 活頁簿物件
    wb = Workbook()     # 建立空白的 Excel 活頁簿物件
    # ws = wb.active
    ws = wb.worksheets[0]   # 取得第一個工作表

    ws.title = '組裝異常記錄查詢-' + _name                # 修改工作表 1 的名稱為 oxxo
    ws.sheet_properties.tabColor = '7da797'  # 修改工作表 1 頁籤顏色為紅色

    for obj in _blocks:
      temp_array = []

      # 在寫入 Excel 時做轉換
      raw_str = obj['cause_message_str']  # e.g., "混料(M01001),散爪(M01002),掉爪(M01003)"
      messages = [re.sub(r'\(.*?\)', '', m).strip() for m in raw_str.split(',')]  # 移除括號和裡面內容
      cleaned_str = ','.join(messages)  # "混料,散爪,掉爪"

      temp_array.append(obj['order_num'])
      temp_array.append(obj['comment'])
      temp_array.append(obj['delivery_date'])
      temp_array.append(obj['req_qty'])
      temp_array.append(obj['delivery_qty'])
      temp_array.append(obj['user'])
      #temp_array.append(obj['cause_message_str'])
      temp_array.append(cleaned_str)
      temp_array.append(obj['cause_user'])
      temp_array.append(obj['cause_date'])

      ws.append(temp_array)

    for col in ws.columns:
      column = col[0].column_letter  # Get the column name
      temp_cell = column + '1'
      ws[temp_cell].font = Font(
          name='微軟正黑體', color='ff0000', bold=True)  # 設定儲存格的文字樣式
      ws[temp_cell].alignment = Alignment(horizontal='center')
      ws.column_dimensions[column].bestFit = True

    #wb.save(current_file)
    #預防 Excel 檔案被鎖定
    temp_file = current_file.replace(".xlsx", "_temp.xlsx")
    wb.save(temp_file)
    os.replace(temp_file, current_file)  # 用新檔案取代舊檔案

    #myDrive = pathlib.Path.home().drive
    #mypath = 'e:\\CMUHCH\\print.csv'
    #mypath = myDrive + '\\CMUHCH\\print.csv'
    #myDir = 'e:\\CMUHCH\\'
    #myDir = myDrive + "\\CMUHCH\\" + current_file0
    #myDir = "e:\\CMUHCH\\" + current_file0
    #print("myDir", myDir)

    print("file_name:", file_name)

    return jsonify({
      'status': return_value,
      'message': current_file,
      'file_name': file_name,
      # 'outputs': myDir,
    })


@excelTable.route("/exportToExcelForAssembleInformation", methods=['POST'])
def export_to_excel_for_assemble_information():
  print("exportToExcelForAssembleInformation....")

  request_data = request.get_json()
  _blocks = request_data['blocks']
  _name = request_data['name']
  print("_blocks:", _blocks)

  date = datetime.datetime.now()
  today = date.strftime('%Y-%m-%d-%H%M')
  file_name = '組裝區在製品生產資訊查詢_'+today + '.xlsx'
  current_file = 'C:\\vue\\chumpower\\excel_export\\'+ file_name

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

  file_check = os.path.exists(current_file)  # true:excel file exist

  return_value = True  # true: export into excel成功

  if file_check:
    try:
      os.remove(current_file)  # 刪除舊檔案
    except PermissionError:
      print(f"無法刪除 {current_file}，請確認是否已關閉該檔案")
      return_value = False
      return jsonify({"success": False, "message": "請關閉 Excel 檔案後重試"})

  wb = Workbook()                                 # 建立空白的 Excel 活頁簿物件
  ws = wb.worksheets[0]                           # 取得第一個工作表
  ws.title = '組裝區在製品生產資訊查詢-' + _name    # 修改工作表 1 的名稱為 oxxo
  ws.sheet_properties.tabColor = '7da797'         # 修改工作表 1 頁籤顏色為紅色

  # 表頭
  header = ['訂單編號', '說明', '交期', '訂單數量', '現況數量', '工序', '開始時間', '結束時間']
  ws.append(header)

  s = Session()

  for obj in _blocks:
    # 先寫入 Material 主資料列
    base_row = [
      obj.get('order_num', ''),
      obj.get('comment', ''),
      obj.get('delivery_date', ''),
      obj.get('req_qty', ''),
      obj.get('delivery_qty', ''),
      '', '', ''  # 空的 process 欄位
    ]
    ws.append(base_row)

    # 尋找對應的 process（根據 order_num -> 查 material -> 查其 _process）
    material = s.query(Material).filter(Material.order_num == obj['order_num']).first()
    work_qty = material.total_delivery_qty

    if material and material._process:
      for process in material._process:

        # 轉換為 datetime 物件
        start_time = datetime.datetime.strptime(process.begin_time, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.datetime.strptime(process.end_time, "%Y-%m-%d %H:%M:%S") if process.process_type != 31 else ''

        # 計算時間差
        time_diff = end_time - start_time

        # 轉換為分鐘數（小數點去掉）
        period_time = int(time_diff.total_seconds() // 60)

        work_time = period_time / work_qty
        work_time = round(period_time / work_qty, 1)  # 取小數點後 1 位

        # 轉換為字串格式
        time_diff_str = str(time_diff)
        period_time_str = str(period_time)
        work_time_str = str(work_time)  if (process.process_type == 21 or process.process_type == 22 or process.process_type == 23) else ''
        single_std_time_str = ''
        if process.process_type == 21:
          single_std_time_str = str(material.sd_time_B110)
        if process.process_type == 22:
          single_std_time_str = str(material.sd_time_B106)
        if process.process_type == 23:
          single_std_time_str = str(material.sd_time_B109)

        if process.process_type == 31:
          single_std_time_str = str(material.sd_time_B110)

        #print("period_time:",period_time_str)

        status = code_to_name.get(process.process_type, '空白')
        #print("name:", process.user_id)
        name = process.user_id.lstrip("0")
        if process.process_type == 1:
          user = s.query(User).filter_by(emp_id=process.user_id).first()
          status = status + '(' + name + user.emp_name + ')'
        #print("status:", status)

        ws.append([
          '', '', '', '', '',  # 空白欄位對齊 Material 欄
          status,
          process.begin_time,
          process.end_time
        ])

    # end if

  s.close()

  # 美化表頭
  for col in ws.columns:
    column = col[0].column_letter  # Get the column name
    #temp_cell = column + '1'
    temp_cell = f"{column}1"
    ws[temp_cell].font = Font(name='微軟正黑體', color='ff0000', bold=True)  # 設定儲存格的文字樣式
    ws[temp_cell].alignment = Alignment(horizontal='center')
    ws.column_dimensions[column].bestFit = True

  # 儲存檔案
  temp_file = current_file.replace(".xlsx", "_temp.xlsx")
  wb.save(temp_file)
  os.replace(temp_file, current_file)  # 用新檔案取代舊檔案

  print("file_name:", file_name)

  return jsonify({
    'status': return_value,
    'message': current_file,
    'file_name': file_name,
  })


# 上傳.xlsx工單檔案的 API
@excelTable.route('/uploadExcelFile', methods=['POST'])
def upload_excel_file():
  print("uploadExcelFile....")

  _base_dir = current_app.config['baseDir']

  if not os.path.exists(_base_dir):
    os.makedirs(_base_dir)

  file = request.files.get('file')

  if not file:
    return jsonify({'message': '沒有選擇檔案'}), 400

  # 確保是 Excel 檔案
  if not file.filename.endswith(('.xlsx', '.xls')):
    return jsonify({'message': '只允許上傳 Excel 檔案'}), 400

  if file.filename == '':
    return jsonify({'message': '沒有選擇檔案'}), 400

  file_path = os.path.join(_base_dir, file.filename)
  # 檢查檔案是否已存在
  if os.path.exists(file_path):
    #return jsonify({'message': f'檔案 "{file.filename}" 已存在'}), 400
    unique_filename = get_unique_filename(_base_dir, file.filename, "copy")
    file_path = os.path.join(_base_dir, unique_filename)

  file.save(file_path)

  try:
    with open(file_path, 'rb') as f:
        print(f"檔案成功儲存並可讀取: {file_path}")
        return jsonify({
          'message': '上傳成功',
          'filename': file.filename,
          'status': True,
        })
  except Exception as e:
      print(f"檔案儲存後讀取失敗: {str(e)}")
      return jsonify({'message': f'檔案儲存後讀取失敗: {str(e)}'}), 500
  #return jsonify({'message': '上傳成功', 'filename': file.filename}), 200


@excelTable.route('/uploadPdfFiles', methods=['POST'])
def upload_pdf_files():
  print("uploadPdfFiles....")

  _base_dir = current_app.config['pdfBaseDir']

  upload_type = request.form.get('uploadType')
  # 根據 uploadType 動態調整儲存目錄
  if upload_type == 'pdf1':
      _base_dir = _base_dir.replace('物料清單', '領退料單')
  if not os.path.exists(_base_dir):
    os.makedirs(_base_dir)
  print("實際儲存路徑:", _base_dir)

  files = request.files.getlist('files')  # multiple files
  #print("files:",files)

  if not files or len(files) == 0:
    return jsonify({'message': '沒有選擇檔案'}), 400

  saved_files = []
  for file in files:
    print("file.filename:",file.filename)

    if not file.filename.endswith('.pdf'):
      return jsonify({'message': f'檔案 {file.filename} 不是 PDF'}), 400

    #filename = secure_filename(file.filename)
    filename = file.filename
    filename = os.path.basename(filename)
    file_path = os.path.join(_base_dir, filename)
    #print("filename:",filename)
    #print("file_path:",file_path)

    if os.path.exists(file_path):
      filename = get_unique_filename(_base_dir, filename, "copy")
      file_path = os.path.join(_base_dir, filename)

    file.save(file_path)
    saved_files.append(filename)

  return jsonify({
    'message': f'{len(saved_files)} 個 PDF 檔案上傳成功',
    'files': saved_files,
    'status': True
  })