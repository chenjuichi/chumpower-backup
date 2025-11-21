import time
import threading
from flask import Blueprint, jsonify, request

kuka_car = Blueprint('kuka_car', __name__)

# 全局的任務儲存
tasks = {}
task_lock = threading.Lock()

class KukaTask(threading.Thread):
    def __init__(self, task_id, name, api_url, begin=0, end=10):
        threading.Thread.__init__(self)
        self.task_id = task_id
        self.name = name
        self.api_url = api_url
        self.begin = begin
        self.end = end
        self.counter = begin
        self.running = False
        self.paused = True
        self.work = "AGV運行中..."
        self.pause_cond = threading.Condition(threading.Lock())

    def run(self):
        while self.running:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()
                if self.counter < self.end:
                    self.counter += 1
                    time.sleep(20)  # 每20秒計數一次
                    self.call_api()  # 執行 API 呼叫
                else:
                    self.stop()
                    self.work = "AGV運行停止..."
                    break

    def call_api(self):
        try:
            response = requests.get(self.api_url)
            if response.status_code == 200:
                print(f"Task {self.task_id}: API 呼叫成功，返回數據：{response.json()}")
            else:
                print(f"Task {self.task_id}: API 呼叫失敗，狀態碼：{response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Task {self.task_id}: API 呼叫錯誤: {e}")

    def start_task(self):
        if not self.running:
            self.running = True
            self.start()

    def pause(self):
        self.paused = True

    def resume(self):
        with self.pause_cond:
            self.paused = False
            self.pause_cond.notify()

    def reset(self):
        self.counter = self.begin
        self.work = "AGV運行中..."

    def stop(self):
        self.running = False
        self.resume()  # 在暫停狀態下，要確保停止

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'name': self.name,
            'counter': self.counter,
            'work': self.work
        }

@kuka_car.route('/kuka/create', methods=['GET'])
def create_task():
    with task_lock:
        if len(tasks) >= 3:
            return jsonify({'status': False, 'message': '最多允許3個任務'}), 400

        task_id = len(tasks) + 1
        task_name = f'hello task {task_id}'
        task = KukaTask(task_id, task_name)
        tasks[task_id] = task

    return jsonify({'status': True, 'task_id': task_id, 'task_name': task_name})

@kuka_car.route('/kuka/startAll', methods=['GET'])
def start_all_tasks():
    with task_lock:
        for task in tasks.values():
            task.reset()
            task.start_task()
            task.resume()

    return jsonify({'status': True, 'tasks': [task.to_dict() for task in tasks.values()]})

@kuka_car.route('/kuka/start', methods=['POST'])
def start_task():
    request_data = request.get_json()
    task_id = request_data.get('task_id')
    begin = request_data.get('begin', 0)
    end = request_data.get('end', 10)

    with task_lock:
        task = tasks.get(task_id)
        if not task:
            return jsonify({'status': False, 'message': '任務未找到'}), 404

        task.begin = begin
        task.end = end
        task.reset()
        task.start_task()
        task.resume()

    return jsonify({'status': True, 'task': task.to_dict()})



@kuka_car.route('/kuka/viewAll', methods=['GET'])
def view_all_tasks():
    with task_lock:
        all_tasks = [{'task_id': task_id, 'task_name': task.name, 'counter': task.counter} for task_id, task in tasks.items()]
    return jsonify({'status': True, 'tasks': all_tasks})


@kuka_car.route('/kuka/view', methods=['POST'])
def view_task():
    request_data = request.get_json()
    task_id = request_data.get('task_id')

    with task_lock:
        task = tasks.get(task_id)
        if not task:
            return jsonify({'status': False, 'message': 'Task not found'}), 404

    return jsonify({'status': True, 'task_id': task_id, 'task_name': task.name, 'counter': task.counter})


@kuka_car.route('/kuka/count', methods=['GET'])
def count_tasks():
    with task_lock:
        task_count = len(tasks)
    return jsonify({'status': True, 'count': task_count})


@kuka_car.route('/kuka/stop', methods=['POST'])
def stop_task():
    request_data = request.get_json()
    task_id = request_data.get('task_id')

    with task_lock:
        task = tasks.get(task_id)
        if not task:
            return jsonify({'status': False, 'message': 'Task not found'}), 404
        task.pause()

    return jsonify({'status': True})


@kuka_car.route('/kuka/stopAll', methods=['GET'])
def stop_all_tasks():
    with task_lock:
        for task in tasks.values():
            task.pause()

    return jsonify({'status': True})


@kuka_car.route('/kuka/play', methods=['POST'])
def play_task():
    request_data = request.get_json()
    task_id = request_data.get('task_id')

    with task_lock:
        task = tasks.get(task_id)
        if not task:
            return jsonify({'status': False, 'message': 'Task not found'}), 404
        task.resume()

    return jsonify({'status': True})


@kuka_car.route('/kuka/playAll', methods=['GET'])
def play_all_tasks():
    with task_lock:
        for task in tasks.values():
            task.resume()

    return jsonify({'status': True})


@kuka_car.route('/kuka/reset', methods=['POST'])
def reset_task():
    request_data = request.get_json()
    task_id = request_data.get('task_id')

    with task_lock:
        task = tasks.get(task_id)
        if not task:
            return jsonify({'status': False, 'message': 'Task not found'}), 404
        task.reset()

    return jsonify({'status': True})


@kuka_car.route('/kuka/resetAll', methods=['GET'])
def reset_all_tasks():
    with task_lock:
        for task in tasks.values():
            task.reset()

    return jsonify({'status': True})


@kuka_car.route('/kuka/remove', methods=['POST'])
def remove_task():
    request_data = request.get_json()
    task_id = request_data.get('task_id')

    with task_lock:
        task = tasks.pop(task_id, None)
        if not task:
            return jsonify({'status': False, 'message': 'Task not found'}), 404
        task.stop()

    return jsonify({'status': True})


@kuka_car.route('/kuka/removeAll', methods=['GET'])
def remove_all_tasks():
    with task_lock:
        for task_id in list(tasks.keys()):
            task = tasks.pop(task_id)
            task.stop()

    return jsonify({'status': True})
