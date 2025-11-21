import os
import stat
import datetime

def delete_pdf_files():
  print("delete_pdf_files()....")

  print("刪除.pdf檔案作業開始...")

  log_dir = os.path.join("C:\\vue\\chumpower\\logs")
  os.makedirs(log_dir, exist_ok=True)  # 如果 logs 資料夾不存在則建立
  log_file_path = os.path.join(log_dir, "remoe_pdf_log.txt")

  pdf_dirs = [
      "C:\\vue\\chumpower\\pdf_file\\領退料單",
      "C:\\vue\\chumpower\\pdf_file\\物料清單"
  ]

  deleted_files = 0
  now = datetime.datetime.now()

  with open(log_file_path, "a", encoding="utf-8") as log_file:
    log_file.write(f"\n=== 執行時間: {now.strftime('%Y-%m-%d %H:%M:%S')} ===\n")

    for pdf_dir in pdf_dirs:      # for loop_1
      if not os.path.exists(pdf_dir):
        msg = f"目錄不存在：{pdf_dir}"
        #print(msg)
        log_file.write(msg + "\n")
        continue

      for filename in os.listdir(pdf_dir):    # for loop_2
        if filename.lower().endswith('.pdf'):
          file_path = os.path.join(pdf_dir, filename)
          if os.path.exists(file_path):
            try:
              file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

              os.chmod(file_path, stat.S_IWRITE)   # 解除唯讀屬性（必要時）
              os.remove(file_path)
              deleted_files += 1
              msg = f"✅ 已刪除: {file_path}（時間：{file_mtime}）"

              #print(msg)
              log_file.write(msg + "\n")

            except Exception as e:
              err_msg = f"❌ 無法刪除 {file_path}: {e}"
              print(err_msg)
              log_file.write(err_msg + "\n")
          else:
            print(f"⚠️ 檔案不存在（可能已被刪除）: {file_path}")
      # end for loop_2
    # end for loop_1
    summary_msg = f"\nPDF檔案刪除完畢，共刪除 {deleted_files} 個檔案。\n"
    print(summary_msg)
    log_file.write(summary_msg)

delete_pdf_files()



