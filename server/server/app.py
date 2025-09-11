import os
import socket
import json
import ctypes
from dotenv import dotenv_values

from apscheduler.schedulers.background import BackgroundScheduler

#from flask import Flask, session, jsonify, request
from flask import Flask, jsonify
from flask_cors import CORS

from ajax.listTable import listTable
from ajax.getTable import getTable
from ajax.createTable import createTable
from ajax.updateTable import updateTable
from ajax.deleteTable import deleteTable
#from ajax.excelModifyTable import excelModifyTable
from ajax.excelTable import excelTable
from ajax.browseDirectory import browseDirectory
from ajax.hardware import hardware

from ajax.scheduleDoTable import do_read_user_table, delete_log_files, delete_pdf_files, delete_exec_files

from apscheduler.schedulers.background import BackgroundScheduler

from database.tables import Session


from log_util import setup_logger
logger = setup_logger('main')       # 將 app 取名為 main


# --------------------------


app = Flask(__name__)  # 初始化Flask物件

hostName = socket.gethostname()
local_ip = socket.gethostbyname(hostName)                           # get local ip address
print('\n' + 'Lan ip: ' + '\033[46m' + local_ip + '\033[0m')
logger.info(f'Lan ip: {local_ip}')
print('Build:  ' + '\033[42m' + '2025-09-11' + '\033[0m' + '\n')
host_ip = local_ip

# 保持持續有效 + 防止螢幕關閉 + 防止系統睡眠
#ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)
# 呼叫 wakeup.exe，保持常亮
#subprocess.Popen([r"C:\chumpower\server\dist\wakeup.exe"])

#Flask 在處理 JSON 資料時，針對中文、日文、韓文等非 ASCII 字符, 避免將非 ASCII 字符轉換為 Unicode escape 序列
app.config['JSON_AS_ASCII'] = False

app.register_blueprint(listTable)
app.register_blueprint(getTable)
app.register_blueprint(createTable)
app.register_blueprint(updateTable)
app.register_blueprint(deleteTable)
app.register_blueprint(excelTable)
#app.register_blueprint(excelModifyTable)
app.register_blueprint(browseDirectory)
app.register_blueprint(hardware)

CORS(app, resources={r'/*': {'origins': '*'}})
#CORS(app, resources={r'/*': {'origins': '*'}}, supports_credentials=True)

# --------------------------
#當 with 區塊結束時，文件會自動關閉
with open('database/data.json', 'r', encoding='utf-8') as f:      # 開啟系統設定檔案
  data = json.load(f)

app.config['envDir'] = data[0]['envDir']
env_vars = dotenv_values(app.config['envDir'])
app.config['baseDir'] = env_vars["baseDir"]
app.config['pdfBaseDir'] = env_vars["pdfBaseDir"]

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
  output = {
    "name": "",
    "local_ip": local_ip,
  }
  return jsonify(output)

#
@app.teardown_appcontext
def remove_session(exc):
    # 不論成功/失敗，每次請求結束都清掉這個 thread 的 session
    Session.remove()
#

# --------------------------

def my_job1():
    print("Scheduled job1 正在執行...")
    with app.app_context():
        do_read_user_table()
        #delete_pdf_files()

def my_job2():
    print("Scheduled job2 正在執行...")
    with app.app_context():
        do_read_user_table()
        #delete_pdf_files()

def my_job3():
    print("Scheduled job3 正在執行...")
    with app.app_context():
        delete_log_files()
        #delete_pdf_files()
        #delete_exec_files()

schedule_1=[]
schedule_2=[]
schedule_3=[]
# 注册第一個排程任務
schedule_1_str= env_vars["schedule_1_24HHMM"]
if schedule_1_str:
    schedule_1 = schedule_1_str.split(",")
    if len(schedule_1) >= 2:
        print("schedule_1預計於" +  schedule_1[0] + ':' + schedule_1[1].strip() + " 啟動")
        scheduler.add_job(my_job1, 'cron', hour=int(schedule_1[0]), minute=int(schedule_1[1]))
# 注册第二個排程任務
schedule_2_str= env_vars["schedule_2_24HHMM"]
if schedule_2_str:
    schedule_2 = schedule_2_str.split(",")
    if len(schedule_2) >= 2:
        print("schedule_2預計於" + schedule_2[0] + ':' + schedule_2[1].strip() + " 啟動")
        scheduler.add_job(my_job2, 'cron', hour=int(schedule_2[0]), minute=int(schedule_2[1]))
# 註冊第三個排程任務
schedule_3_str = env_vars["schedule_3_24HHMM"]
schedule_3 = []
if schedule_3_str:
    schedule_3 = schedule_3_str.split(",")
    if len(schedule_3) >= 2:
        print("schedule_3預計於 " + schedule_3[0] + ':' + schedule_3[1].strip() + " 啟動")
        scheduler.add_job(my_job3, 'cron', hour=int(schedule_3[0]), minute=int(schedule_3[1]))


# --------------------------


if __name__ == '__main__':
  scheduler.start()                            # 啟動scheduler
  #print("Scheduled version...")
  #方法1
  #app.run(host=host_ip, port=7010, debug=True)  # 啟動app
  #方法2
  #app.run(host='0.0.0.0', port=7010, debug=True)  # 啟動app
  #方法3
  app.run(host='0.0.0.0', port=7010, debug=False, use_reloader=False)  # 啟動app, 避免觸發reloader，連線就被中斷

  #方法4
  '''
  from werkzeug.serving import make_server
  def run_server():
      http_server = make_server(host_ip, 7010, app)
      http_server.serve_forever()
  print("後端應用程式已經啟動...")
  run_server()
  '''