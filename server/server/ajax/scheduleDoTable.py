import os
import stat
import datetime

from database.tables import User, Session
from flask import Blueprint, jsonify, request, current_app

from apscheduler.schedulers.background import BackgroundScheduler

from dotenv import dotenv_values

scheduleDoTable = Blueprint('scheduleDoTable', __name__)

# ------------------------------------------------------------------

def try_delete_pdf(file_path):
  try:
    # 解除唯讀屬性（必要時）
    os.chmod(file_path, stat.S_IWRITE)
    os.remove(file_path)
    print(f"已刪除: {file_path}")
    return True
  except Exception as e:
    print(f"無法刪除 {file_path}: {e}")
    return False


def do_read_user_table():
  print("do_read_user_table()....")

  s = Session()

  try:
    users_online = s.query(User).filter(User.isOnline == True).all()
    for user in users_online:
      user.isOnline = False
    s.commit()
    print(f"共 {len(users_online)} 位使用者已下線 (isOnline 設為 False)。")
  except Exception as e:
    print("更新失敗：", e)
    s.rollback()
  finally:
    s.close()

  print("end do_read_user_table()....")


def delete_pdf_files():
  print("delete_pdf_files()....")

  print("刪除.pdf檔案作業開始...")

  log_dir = os.path.join("C:\\vue\\chumpower\\logs")
  os.makedirs(log_dir, exist_ok=True)  # 如果 logs 資料夾不存在則建立
  log_file_path = os.path.join(log_dir, "delete_pdf_log.txt")

  pdf_dirs = [
      "C:\\vue\\chumpower\\pdf_file\\領退料單",
      "C:\\vue\\chumpower\\pdf_file\\物料清單"
  ]
  # 使用 current_app 取得設定
  #base_dir = current_app.config['pdfBaseDir']  # 物料清單
  #pdf_dirs = [
  #    base_dir,
  #    os.path.join(os.path.dirname(base_dir), "領退料單")
  #]

  #pdf_dirs = [
  #    os.path.join(current_app.config['pdfBaseDir'].replace("物料清單", "領退料單")),
  #    current_app.config['pdfBaseDir']
  #]

  deleted_files = 0
  now = datetime.datetime.now()
  cutoff_time = now - datetime.timedelta(hours=36)  # ✅ 36 小時前的時間點

  with open(log_file_path, "a", encoding="utf-8") as log_file:
  #with open(log_file_path, "a", encoding="utf-8-sig") as log_file:
    log_file.write(f"\n=== 執行時間: {now.strftime('%Y-%m-%d %H:%M:%S')} ===\n")

    for pdf_dir in pdf_dirs:      # for loop_1
      if not os.path.exists(pdf_dir):
        msg = f"目錄不存在：{pdf_dir}"
        print(msg)
        log_file.write(msg + "\n")
        continue

      for filename in os.listdir(pdf_dir):    # for loop_2
        if filename.lower().endswith('.pdf'):
          file_path = os.path.join(pdf_dir, filename)
          if os.path.exists(file_path):
            try:
              file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

              #if file_mtime < cutoff_time:
              os.chmod(file_path, stat.S_IWRITE)   # 解除唯讀屬性（必要時）
              os.remove(file_path)
              deleted_files += 1
              msg = f"✅ 已刪除: {file_path}（時間：{file_mtime}）"
                #print(f"已刪除: {file_path}")
              #else:
              #  msg = f"⏩ 略過: {file_path}（時間：{file_mtime} < 36 小時）"

              print(msg)
              log_file.write(msg + "\n")

            except Exception as e:
              err_msg = f"❌ 無法刪除 {file_path}: {e}"
              print(err_msg)
              log_file.write(err_msg + "\n")
              #print(f"無法刪除 {file_path}: {e}")
          else:
            print(f"⚠️ 檔案不存在（可能已被刪除）: {file_path}")
      # end for loop_2
    # end for loop_1
    summary_msg = f"\nPDF檔案刪除完畢，共刪除 {deleted_files} 個檔案。\n"
    print(summary_msg)
    log_file.write(summary_msg)
    #print(f"PDF檔案刪除完畢，共刪除 {deleted_files} 個檔案。")


def delete_exec_files():
  print("delete_exec_files()....")

  print("刪除.xlsx檔案作業開始...")

  today = datetime.datetime.now()

  log_dir = "C:\\vue\\chumpower\\logs"
  os.makedirs(log_dir, exist_ok=True)
  log_path = os.path.join(log_dir, "delete_excel_log.txt")

  def write_log(message):
    with open(log_path, "a", encoding="utf-8") as f:
      timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      f.write(f"[{timestamp}] {message}\n")

  #write_log("🔄 開始執行 delete_exec_files()")

  # ✅ 檢查是否為星期日（Sunday 對應 weekday() == 6）
  if today.weekday() != 6:
    msg = "今天不是星期日，跳過刪除 Excel 檔案。"
    print(msg)
    write_log(msg)
    #print("今天不是星期日，跳過刪除 Excel 檔案。")
    return

  target_folder = "C:\\vue\\chumpower\\excel_out"
  deleted_count = 0

  if not os.path.exists(target_folder):
    msg = f"目錄不存在: {target_folder}"
    print(msg)
    write_log(msg)
    #print(f"目錄不存在: {target_folder}")
    return

  # ✅ 基準時間為 7 天前
  cutoff_time = today - datetime.timedelta(days=7)

  for filename in os.listdir(target_folder):  # for loop
    if filename.lower().endswith(".xlsx"):    # if loop_1
      file_path = os.path.join(target_folder, filename)
      if os.path.exists(file_path):           # if loop_2
        try:
          file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

          #if file_mtime < cutoff_time:
          os.chmod(file_path, stat.S_IWRITE)   # 解除唯讀屬性（必要時）
          os.remove(file_path)
          msg = f"✅ 已刪除: {file_path}"
          print(msg)
          write_log(msg)
          #print(f"已刪除: {file_path}")
          deleted_count += 1
          #else:
          #  msg = f"⏩ 略過: {file_path}（最後修改時間：{file_mtime} < 7 天）"
          #  print(msg)
          #  write_log(msg)
            #print(f"略過: {file_path}（最後修改時間：{file_mtime} < 7 天）")
        except Exception as e:
          msg = f"❌ 無法刪除 {file_path}: {e}"
          print(msg)
          write_log(msg)
          #print(f"無法刪除 {file_path}: {e}")
      else: # else loop_2
        print(f"⚠️ 檔案不存在（可能已被刪除）: {file_path}")
      # end if loop_2
    # end if loop_1
  # end for loop
  msg = f"✅ Excel 檔案刪除完畢，共刪除 {deleted_count} 個檔案。"
  print(msg)
  write_log(msg)
  #print(f"Excel 檔案刪除完畢，共刪除 {deleted_count} 個檔案。")


def delete_log_files():
  print("delete_log_files()....")

  print("刪除 .log 檔案作業開始...")

  today = datetime.datetime.now()

  #log_folder = "C:\\chumpower\\server\\logs"
  log_folder = "C:\\vue\\chumpower\\server\\logs"
  record_log_folder = "C:\\vue\\chumpower\\logs"
  os.makedirs(record_log_folder, exist_ok=True)

  log_record_path = os.path.join(record_log_folder, "delete_log_log.txt")

  # ✅ 日誌寫入函式
  def write_log(message):
    with open(log_record_path, "a", encoding="utf-8") as f:
      timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      f.write(f"[{timestamp}] {message}\n")

  write_log("🔄 開始執行 delete_log_files()")

  if not os.path.exists(log_folder):
    msg = f"❗ 目錄不存在: {log_folder}"
    print(msg)
    write_log(msg)
    return

  cutoff_time = today - datetime.timedelta(days=3)
  deleted_count = 0

  for filename in os.listdir(log_folder):
    if filename.lower().endswith(".log"):
      file_path = os.path.join(log_folder, filename)

      # ✅ 先確認檔案是否存在
      if not os.path.exists(file_path):
        msg = f"⚠️ 找不到檔案: {file_path}，可能已被刪除或不存在。"
        print(msg)
        write_log(msg)
        continue

      try:
        file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

        if file_mtime < cutoff_time:
          os.chmod(file_path, stat.S_IWRITE)  # 移除唯讀
          os.remove(file_path)
          msg = f"✅ 已刪除: {file_path}"
          print(msg)
          write_log(msg)
          deleted_count += 1
        else:
          msg = f"⏩ 略過: {file_path}（最後修改時間：{file_mtime} < 3 天）"
          print(msg)
          write_log(msg)
      except PermissionError as pe:
        msg = f"❌ 權限不足，無法刪除 {file_path}: {pe}"
        print(msg)
        write_log(msg)

      except Exception as e:
        msg = f"❌ 無法刪除 {file_path}: {e}"
        print(msg)
        write_log(msg)

  msg = f"🗑️ log 檔案刪除完畢，共刪除 {deleted_count} 個檔案。"
  print(msg)
  write_log(msg)

