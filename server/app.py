import os
import socket
import json
import ctypes
from dotenv import dotenv_values

from flask import Flask, session, jsonify, request
from flask_cors import CORS

from apscheduler.schedulers.background import BackgroundScheduler

# --------------------------

app = Flask(__name__)  # 初始化Flask物件

hostName = socket.gethostname()
local_ip = socket.gethostbyname(hostName)   # get local ip address
print('\n' + 'Lan ip: ' + '\033[46m' + local_ip + '\033[0m')
print('Build:  ' + '\033[42m' + '2024-05-07' + '\033[0m' + '\n')
host_ip = local_ip

ctypes.windll.kernel32.SetThreadExecutionState(0x80000002)  # prevent the screen saver or sleep.
#Flask 在處理 JSON 資料時，針對中文、日文、韓文等非 ASCII 字符, 避免將非 ASCII 字符轉換為 Unicode escape 序列
app.config['JSON_AS_ASCII'] = False

CORS(app, resources={r'/*': {'origins': '*'}})

# --------------------------
'''
with open('database/data.json', 'r', encoding='utf-8') as f:
  data = json.load(f)

app.config['customer_row'] = data[0]['customer_row']
app.config['spindle_cat_row'] = data[0]['spindle_cat_row']
app.config['id_row'] = data[0]['id_row']
app.config['id_column'] = data[0]['id_column']
app.config['emp_id_row'] = data[0]['emp_id_row']
app.config['date_row'] = data[0]['date_row']
app.config['date_column'] = data[0]['date_column']
app.config['runin_row'] = data[0]['runin_row']
app.config['envDir'] = data[0]['envDir']

env_path = app.config['envDir']

env_vars = dotenv_values(env_path)
app.config['baseDir'] = env_vars["baseDir"]
_base_dir = env_vars["baseDir"]
print("read excel files, dir: ", _base_dir)
###

# 初始化file_ok
app.config['file_ok'] = False
print("file_ok", app.config['file_ok'])

f.close()
'''
# --------------------------

# 初始化调度器
scheduler = BackgroundScheduler()

@app.route("/")
def helloWorld():
  print("Hello chumpower")
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
    #with app.app_context():
    #    do_read_all_excel_files()

def my_job2():
    print("hello, Scheduled job2 is running...")
    #with app.app_context():
    #    do_read_all_excel_files()
'''
env_vars = dotenv_values(env_path)
schedule_1=[]
schedule_2=[]
schedule_1_str= env_vars["schedule_1_24HHMM"]
if schedule_1_str:
    schedule_1 = schedule_1_str.split(",")
    if len(schedule_1) >= 2:
        print("schedule_1: ", schedule_1[0], schedule_1[1])
        scheduler.add_job(my_job1, 'cron', hour=int(schedule_1[0]), minute=int(schedule_1[1]))

schedule_2_str= env_vars["schedule_2_24HHMM"]
if schedule_2_str:
    schedule_2 = schedule_2_str.split(",")
    if len(schedule_2) >= 2:
        print("schedule_2: ", schedule_2[0], schedule_2[1])
        scheduler.add_job(my_job2, 'cron', hour=int(schedule_2[0]), minute=int(schedule_2[1]))


# 注册第一個作業，每天的 9:00 执行
#scheduler.add_job(my_job1, 'cron', hour=9, minute=0)
# 注册第二個作業，每天的 14:00 执行
#scheduler.add_job(my_job2, 'cron', hour=14, minute=0)
#scheduler.add_job(my_job1, 'cron', hour=int(schedule_1[0]), minute=int(schedule_1[1]))
#scheduler.add_job(my_job2, 'cron', hour=int(schedule_2[0]), minute=int(schedule_2[1]))
'''
# --------------------------

if __name__ == '__main__':
  #scheduler.start()
  #print("Scheduled version...")
  app.run(host=host_ip, port=2680, debug=True)
