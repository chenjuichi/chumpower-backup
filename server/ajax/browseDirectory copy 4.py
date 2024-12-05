import time
import datetime
import pytz

from flask import Blueprint, jsonify, request, send_file, after_this_request
import os
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import RectangleObject
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image
from io import BytesIO
import tempfile
import threading
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

browseDirectory = Blueprint('browseDirectory', __name__)

# ------------------------------------------------------------------
'''
def delete_crdownload_files():
    """
    自動獲取當前用戶的下載目錄，並刪除其中所有 .crdownload 檔案
    """
    try:
        # 使用 pathlib 獲取當前用戶的下載目錄
        download_dir = str(Path.home() / "Downloads")

        # 檢查目錄是否存在
        if not os.path.exists(download_dir):
            print(f"指定目錄不存在: {download_dir}")
            return

        # 遍歷目錄中的檔案
        for file_name in os.listdir(download_dir):
            # 檢查檔案是否以 .crdownload 結尾
            if file_name.endswith(".crdownload"):
                file_path = os.path.join(download_dir, file_name)
                try:
                    os.remove(file_path)
                    print(f"已刪除檔案: {file_path}")
                except Exception as e:
                    print(f"無法刪除檔案 {file_path}: {e}")
    except Exception as e:
        print(f"無法訪問目錄 {download_dir}: {e}")
'''

def delete_crdownload_files():
    """
    自動獲取當前用戶的下載目錄，並刪除其中所有 .crdownload 檔案
    """
    try:
        # 獲取當前用戶的下載目錄
        download_dir = str(Path.home() / "Downloads")

        # 檢查目錄是否存在
        if not os.path.exists(download_dir):
            print(f"指定目錄不存在: {download_dir}")
            return

        # 遍歷下載目錄中的檔案
        for file_name in os.listdir(download_dir):
            # 檢查是否為 .crdownload 文件
            if file_name.endswith(".crdownload"):
                file_path = os.path.join(download_dir, file_name)
                try:
                    # 刪除 .crdownload 文件
                    os.remove(file_path)
                    print(f"已刪除檔案: {file_path}")
                except Exception as e:
                    print(f"無法刪除檔案 {file_path}: {e}")
    except Exception as e:
        print(f"無法訪問目錄 {download_dir}: {e}")

# ------------------------------------------------------------------

# 瀏覽目錄 API
@browseDirectory.route('/listDirectory', methods=['POST'])
def list_directory():
  print("listDirectory....")

  data = request.json
  # 設定預設路徑
  default_path = r'C:\vue\chumpower\pdf_file'   # 使用 raw 字串避免反斜線轉義
  path = data.get('path', default_path)         # 使用預設路徑

  # 將路徑正規化（支援 UNC 路徑）
  path = os.path.normpath(path)
  # 檢查目錄是否存在，且確保是可讀目錄
  if not os.path.exists(path):
    return jsonify({'error': f'Path does not exist: {path}'}), 400
  if not os.path.isdir(path):
    return jsonify({'error': f'Path is not a directory: {path}'}), 400

  items = []
  for entry in os.scandir(path):
    items.append({
      'name': entry.name,
      'is_dir': entry.is_dir()
    })

  temp_len = len(items)
  print("listDirectory, 總數: ", temp_len)
  if (temp_len == 0):
    return jsonify({'error': f'No file!'}), 400

  return jsonify(items)

# 讀取 PDF API
@browseDirectory.route('/readFile', methods=['POST'])
def read_file():
  print("readFile....")

  data = request.json
  filepath = data.get('filepath')
  print("readFile, step0...", filepath)

  # 定義基礎目錄
  base_directory = r'C:\vue\chumpower\pdf_file'
  # 如果 filepath 為相對路徑，拼接基礎目錄
  if not os.path.isabs(filepath):  # 如果不是絕對路徑
    filepath = os.path.join(base_directory, filepath)

  if not filepath or not filepath.endswith('.pdf') or not os.path.exists(filepath):
    return jsonify({'error': 'Invalid file'}), 400
  print("readFile, step1...")
  reader = PdfReader(filepath)
  content = ''.join(page.extract_text() for page in reader.pages)
  return jsonify({'content': content})

# 儲存 PDF API
@browseDirectory.route('/saveFile', methods=['POST'])
def save_file():
    print("saveFile....")

    # 初始化變數
    writer_path = None

    data = request.json
    filepath = data.get('filepath')
    barcode_text = data.get('barcode_text', '')

    insert_position = data.get('position', {'x': 50, 'y': 750})  # 預設插入位置
    # 偏移量：右移 100px，向下移動 300px
    insert_position['x'] += 70  # 向右移動
    insert_position['y'] -= 130  # 向下移動

    base_directory = r'C:\vue\chumpower\pdf_file'
    temp_directory = r'C:\vue\chumpower\temp'

    # 驗證文件路徑
    if not filepath or not filepath.endswith('.pdf') or not os.path.exists(filepath):
        return jsonify({'error': 'Invalid file'}), 400

    # 定義 writer_path
    writer_path = os.path.join(base_directory, f"NEW_{os.path.basename(filepath)}")
    print(f"Writer path: {writer_path}")
    print("File exists:", os.path.exists(writer_path))

    try:
        # 創建條碼圖片保存目錄
        os.makedirs(temp_directory, exist_ok=True)
        barcode_path = os.path.join(temp_directory, 'barcode.png')

        # 生成條碼圖片
        print(f"Generating barcode for: {barcode_text}")
        output = BytesIO()
        barcode = Code128(barcode_text, writer=ImageWriter())
        barcode.write(output)

        # 檢查條碼生成是否成功
        if output.getbuffer().nbytes == 0:
            raise ValueError("Barcode generation failed.")

        with open(barcode_path, 'wb') as f:
            f.write(output.getvalue())
        print(f"Barcode saved at: {barcode_path}")

        # 生成新 PDF
        reader = PdfReader(filepath)
        writer = PdfWriter()

        # 遍歷每一頁，添加條碼到指定位置
        for page_number, page in enumerate(reader.pages):
          packet = BytesIO()

          # 使用 ReportLab 繪製條碼
          c = canvas.Canvas(packet, pagesize=letter)
          c.drawImage(barcode_path, insert_position['x'], insert_position['y'], width=100, height=40)
          c.save()

          # 將新內容合併到原始頁面
          packet.seek(0)
          overlay = PdfReader(packet)
          page.merge_page(overlay.pages[0])
          writer.add_page(page)

        #for page in reader.pages:
        #    writer.add_page(page)

        with open(writer_path, 'wb') as f:
            writer.write(f)
        print(f"New PDF saved at: {writer_path}")

        # 清理條碼文件
        if os.path.exists(barcode_path):
            os.remove(barcode_path)

    except Exception as e:
        print(f"Error saving file: {e}")
        return jsonify({'error': f'Failed to save file: {e}'}), 500

    # 清理 .crdownload 文件
    @after_this_request
    def cleanup_crdownload_files(response):
        def delete_temp_files():
            time.sleep(5)  # 等待下載完成
            try:
                delete_crdownload_files()  # 調用刪除 .crdownload 文件的函數
            except Exception as e:
                print(f"Error deleting .crdownload files: {e}")
        threading.Thread(target=delete_temp_files).start()
        return response

    # 發送生成的新 PDF 文件
    return send_file(
        writer_path,
        as_attachment=True,
        download_name=f"NEW_{os.path.basename(filepath)}",
        mimetype="application/pdf",
        conditional=False  # 確保完整文件被發送
    )


