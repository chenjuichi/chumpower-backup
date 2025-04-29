# wakeup.py
import ctypes
import time

# 定義參數
ES_CONTINUOUS       = 0x80000000
ES_DISPLAY_REQUIRED = 0x00000002
ES_SYSTEM_REQUIRED  = 0x00000001

# 呼叫 Windows API
def prevent_sleep():
    while True:
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        time.sleep(60)  # 每 60 秒送一次保持喚醒訊號

if __name__ == "__main__":
    prevent_sleep()

