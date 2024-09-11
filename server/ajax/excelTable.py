import os
import datetime
import pathlib
import csv
import time
import shutil
import psutil

import pymysql
from sqlalchemy import exc

import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from database.tables import User, Session, Material
from flask import Blueprint, jsonify, request, current_app

excelTable = Blueprint('excelTable', __name__)

# ------------------------------------------------------------------


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

  _base_dir = current_app.config['baseDir']
  _target_dir = _base_dir.replace("_in", "_out")
  print("read excel files, 目錄: ", _base_dir)
  print("move excel files to, 目錄: ", _target_dir)
  # 讀取指定目錄下的所有指定檔案名稱
  files = [f for f in os.listdir(_base_dir) if os.path.isfile(os.path.join(_base_dir, f)) and f.startswith('Report_') and f.endswith('.xlsx')]
  if (files):   #有工單檔案
    _excelSheet = current_app.config['excelSheet']
    _orderRow = int(current_app.config['orderRow'])

    s = Session()

    for _file_name in files:  #檔案讀取
      file_count_total +=1
      _path = _base_dir + '\\' + _file_name
      global_var = _path + ' 檔案讀取中...'

      try:
        with open(_path, 'rb') as file:
          workbook = openpyxl.load_workbook(filename=file, read_only=True)
          return_value = True
          return_message1 = ''
          if _excelSheet not in workbook.sheetnames:    #sheet name不存在
            return_value = False
            return_message1 = '錯誤, excel檔案內沒有 ' + _excelSheet +  ' sheet!'
            print(return_message1)
            continue

          print(_excelSheet + ' sheet exists...')
          sheet = workbook[_excelSheet]             #取得工作表
          print("read data from excel file...")

          _results = []
          for i in range(_orderRow, sheet.max_row+1):
            if sheet.cell(row=i, column=1).value is None:   #資料讀取完畢
              break

            _order_num = str(sheet.cell(row = i, column = 1).value).strip()
            _material_num = str(sheet.cell(row = i, column = 3).value).strip()
            _material_comment = str(sheet.cell(row = i, column = 4).value).strip()
            _material_req_qty = sheet.cell(row = i, column = 5).value
            _material_pick_qty = sheet.cell(row = i, column = 6).value

            newItem = s.query(Material).filter_by(order_num = _order_num, material_num=_material_num).first()
            return_value = True
            return_message2 =''
            if newItem:           #工單內容重複
              return_value = False
              return_message2 = '錯誤! 在' + _path + '檔案內, 系統已經有' + _order_num +'訂單及' + _material_num + '物料編號 相同資料...'
              print(return_message2)
              continue

            _obj = Material(
              order_num = _order_num,
              material_num = _material_num,
              material_comment = _material_comment,
              material_req_qty = _material_req_qty,
              material_pick_qty = _material_pick_qty,
              isPickOK = True,
            )

            _results.append(_obj)

            #file_count_ok += 1        #continue for loop

          s.bulk_save_objects(_results)
          s.commit()

      except pymysql.err.IntegrityError as e:
          s.rollback()
          print(f"IntegrityError: {e}")
      except exc.IntegrityError as e:
          s.rollback()
          print(f"SQLAlchemy IntegrityError: {e}")
      except Exception as e:
          s.rollback()
          print(f"Exception: {e}")

      # 移動檔案到目標目錄
      try:
          shutil.move(_path, _target_dir)
      except PermissionError as e:
          print(f"無法移動文件 {_path}，因為它仍然被佔用: {e}")

        #end for loop

    s.close()

  return jsonify({
    'status': return_value,
    'message': return_message1,
  })

