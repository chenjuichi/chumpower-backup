# log_util.py
import logging
import os
from datetime import datetime

def setup_logger(name='app'):
  log_dir = "logs"
  if not os.path.exists(log_dir):
    os.makedirs(log_dir)

  log_file = os.path.join(log_dir, datetime.now().strftime(f"{name}_%Y-%m-%d.log"))

  logger = logging.getLogger(name)
  logger.setLevel(logging.DEBUG)

  formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s')

  # 檔案處理器
  fh = logging.FileHandler(log_file, encoding='utf-8')
  fh.setFormatter(formatter)
  logger.addHandler(fh)

  # 可選：終端顯示
  # sh = logging.StreamHandler()
  # sh.setFormatter(formatter)
  # logger.addHandler(sh)

  return logger
