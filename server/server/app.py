import os
import socket
import json
import ctypes
from dotenv import dotenv_values

from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask, session, jsonify, request
from flask_cors import CORS

from ajax.listTable import listTable
from ajax.getTable import getTable
from ajax.createTable import createTable
from ajax.updateTable import updateTable
from ajax.deleteTable import deleteTable
from ajax.excelTable import excelTable
from ajax.browseDirectory import browseDirectory

#from travel.kuka_car import kuka_car


# --------------------------


app = Flask(__name__)  # 初始化Flask物件

hostName = socket.gethostname()
local_ip = socket.gethostbyname(hostName)                           # get local ip address
print('\n' + 'Lan ip: ' + '\033[46m' + local_ip + '\033[0m')
print('Build:  ' + '\033[42m' + '2024-07-08' + '\033[0m' + '\n')
host_ip = local_ip

# prevent the screen saver or sleep.
ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)
#Flask 在處理 JSON 資料時，針對中文、日文、韓文等非 ASCII 字符, 避免將非 ASCII 字符轉換為 Unicode escape 序列
app.config['JSON_AS_ASCII'] = False

app.register_blueprint(listTable)
app.register_blueprint(getTable)
app.register_blueprint(createTable)
app.register_blueprint(updateTable)
app.register_blueprint(deleteTable)
app.register_blueprint(excelTable)
app.register_blueprint(browseDirectory)

#app.register_blueprint(kuka_car)

CORS(app, resources={r'/*': {'origins': '*'}})

# --------------------------
#當 with 區塊結束時，文件會自動關閉
with open('database/data.json', 'r', encoding='utf-8') as f:      # 開啟系統設定檔案
  data = json.load(f)

app.config['envDir'] = data[0]['envDir']
env_vars = dotenv_values(app.config['envDir'])
app.config['baseDir'] = env_vars["baseDir"]
_base_dir = env_vars["baseDir"]
print("Excel檔案在目錄:", _base_dir)

app.config['excel_product_sheet'] = env_vars["excel_product_sheet"]   #excel檔案內的工作表名稱
_excel_product_sheet = app.config['excel_product_sheet']
app.config['excel_bom_sheet'] = env_vars["excel_bom_sheet"]   #excel檔案內的工作表名稱
_excel_bom_sheet = app.config['excel_bom_sheet']
app.config['excel_work_time_sheet'] = env_vars["excel_work_time_sheet"]   #excel檔案內的工作表名稱
_excel_work_time_sheet = app.config['excel_work_time_sheet']
print("Excel 工作表名稱 為:", _excel_product_sheet, _excel_bom_sheet, _excel_work_time_sheet)

app.config['startRow'] = env_vars["startRow"]       #excel工作表的起始列
_startRow = app.config['startRow']
#print("Excel sheet 資料起始列 為:", _startRow)

#print("Excel檔案在目錄:", _base_dir)
app.config['file_ok'] = False                         # 初始化file_ok
#app.config['socket_server_ip'] = '192.168.32.241'
app.config['socket_server_ip'] = local_ip
f.close()

# --------------------------

scheduler = BackgroundScheduler()       # 初始化调度器

@app.route("/")
def helloWorld():
  print("hello Chumpower")
  return "Hello..."

@app.route('/hello', methods=['GET'])
def hello():
  print("fetch hello....")
  output = {"name": "",
            "local_ip": local_ip,
  }
  return jsonify(output)

# --------------------------

def my_job1():
    print("hello, Scheduled job1 is running...")
    with app.app_context():
        do_read_all_excel_files()

def my_job2():
    print("hello, Scheduled job2 is running...")
    with app.app_context():
        do_read_all_excel_files()

schedule_1=[]
schedule_2=[]
# 注册第一個作業每天執行時間
schedule_1_str= env_vars["schedule_1_24HHMM"]
if schedule_1_str:
    schedule_1 = schedule_1_str.split(",")
    if len(schedule_1) >= 2:
        print("schedule_1預計於" +  schedule_1[0] + ' :' + schedule_1[1] + " 啟動")
        scheduler.add_job(my_job1, 'cron', hour=int(schedule_1[0]), minute=int(schedule_1[1]))
# 注册第二個作業每天執行時間
schedule_2_str= env_vars["schedule_2_24HHMM"]
if schedule_2_str:
    schedule_2 = schedule_2_str.split(",")
    if len(schedule_2) >= 2:
        print("schedule_2預計於" + schedule_2[0] + ' :' + schedule_2[1] + " 啟動")
        scheduler.add_job(my_job2, 'cron', hour=int(schedule_2[0]), minute=int(schedule_2[1]))

# --------------------------

if __name__ == '__main__':
  #scheduler.start()                            # 啟動scheduler
  #print("Scheduled version...")
  #方法1
  app.run(host=host_ip, port=7010, debug=True)  # 啟動app
  #方法2
  '''
  from werkzeug.serving import make_server
  def run_server():
      http_server = make_server(host_ip, 7010, app)
      http_server.serve_forever()
  print("後端應用程式已經啟動...")
  run_server()
  '''