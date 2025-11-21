import os
import stat
import datetime

def delete_exec_files():
  print("delete_exec_files()....")

  print("刪除.xlsx檔案作業開始...")

  today = datetime.datetime.now()

  log_dir = "C:\\vue\\chumpower\\logs"
  os.makedirs(log_dir, exist_ok=True)
  log_path = os.path.join(log_dir, "remove_excel_log.txt")

  def write_log(message):
    with open(log_path, "a", encoding="utf-8") as f:
      timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      f.write(f"[{timestamp}] {message}\n")

  # ✅ 檢查是否為星期日（Sunday 對應 weekday() == 6）
  if today.weekday() != 6:
    msg = "今天不是星期日，跳過刪除 Excel 檔案。"
    #print(msg)
    write_log(msg)
    return

  target_folder = "C:\\vue\\chumpower\\excel_out"
  deleted_count = 0

  if not os.path.exists(target_folder):
    msg = f"目錄不存在: {target_folder}"
    #print(msg)
    write_log(msg)
    return

  # ✅ 基準時間為 7 天前
  #cutoff_time = today - datetime.timedelta(days=7)

  for filename in os.listdir(target_folder):  # for loop
    if filename.lower().endswith(".xlsx"):    # if loop_1
      file_path = os.path.join(target_folder, filename)
      if os.path.exists(file_path):           # if loop_2
        try:
          #file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

          #if file_mtime < cutoff_time:
          os.chmod(file_path, stat.S_IWRITE)   # 解除唯讀屬性（必要時）
          os.remove(file_path)
          msg = f"✅ 已刪除: {file_path}"
          #print(msg)
          write_log(msg)
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
      else: # else loop_2
        print(f"⚠️ 檔案不存在（可能已被刪除）: {file_path}")
      # end if loop_2
    # end if loop_1
  # end for loop
  msg = f"✅ Excel 檔案刪除完畢，共刪除 {deleted_count} 個檔案。"
  print(msg)
  write_log(msg)

delete_exec_files()



