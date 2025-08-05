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

import aspose.pdf as ap
from PIL import Image, ImageOps, ImageDraw, ImageFont, ExifTags
import fitz

from io import BytesIO
import tempfile
import threading
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

import urllib.parse

import shutil

from datetime import date

browseDirectory = Blueprint('browseDirectory', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


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


def delete_pdf_files():
  """
  自動獲取當前用戶的下載目錄，並刪除其中所有 .pdf 檔案
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
          if file_name.endswith(".pdf"):
              file_path = os.path.join(download_dir, file_name)
              try:
                  # 刪除 .crdownload 文件
                  os.remove(file_path)
                  print(f"已刪除檔案: {file_path}")
              except Exception as e:
                  print(f"無法刪除檔案 {file_path}: {e}")
  except Exception as e:
      print(f"無法訪問目錄 {download_dir}: {e}")


def delete_pdf_files_on_directory():
  print("delete_pdf_files_on_directory()....")

  """
  自動獲取當前指定目錄，並刪除其中所有 .pdf 檔案
  """
  try:
      # 獲取當前用戶的下載目錄
      #download_dir = str(Path.home() / "Downloads")
      pdf_dir = str(Path(r'C:\vue\chumpower\pdf_file'))

      # 檢查目錄是否存在
      if not os.path.exists(pdf_dir):
          print(f"指定目錄不存在: {pdf_dir}")
          return

      # 遍歷下載目錄中的檔案
      for file_name in os.listdir(pdf_dir):
          # 檢查是否為 .crdownload 文件
          if file_name.endswith(".pdf"):
              file_path = os.path.join(pdf_dir, file_name)
              try:
                  # 刪除 .crdownload 文件
                  os.remove(file_path)
                  print(f"已刪除檔案: {file_path}")
              except Exception as e:
                  print(f"無法刪除檔案 {file_path}: {e}")
  except Exception as e:
      print(f"無法訪問目錄 {pdf_dir}: {e}")


def delete_xlsx_files_on_directory():
  print("delete_xlsx_files_on_directory()....")

  """
  自動獲取當前指定目錄，並刪除其中所有 .xlsx 檔案
  """
  try:
    # 獲取當前用戶的下載目錄
    #xlsx_dir = str(Path(r'C:\vue\chumpower\excel_export'))
    xlsx_dir = r'C:\vue\chumpower\excel_export'

    # 檢查目錄是否存在
    if not os.path.exists(xlsx_dir):
      print(f"指定目錄不存在: {xlsx_dir}")
      return

    # 遍歷下載目錄中的檔案
    for file_name in os.listdir(xlsx_dir):
      # 檢查是否為 .crdownload 文件
      if file_name.endswith(".xlsx"):
        file_path = os.path.join(xlsx_dir, file_name)
        try:
          # 刪除 .crdownload 文件
          os.remove(file_path)
          print(f"已刪除檔案: {file_path}")
        except Exception as e:
          print(f"無法刪除檔案 {file_path}: {e}")
  except Exception as e:
    print(f"無法訪問目錄 {xlsx_dir}: {e}")


def process_and_resize_image(input_path, output_path, scale_factor, text_data):
  with Image.open(input_path) as img:
    # 看看圖檔資料內容
    img_exif = img.getexif()
    print("image type:", type(img_exif))
    if img_exif is not None:
      for key, val in img_exif.items():
        if key in ExifTags.TAGS:
          print(f'{ExifTags.TAGS[key]}:{val}')

    img = ImageOps.exif_transpose(img)  # 確保圖片方向正確（避免旋轉問題）
    img = img.convert("RGBA")           # 設定圖片模式為 RGBA（支持透明度）

    data = img.getdata()

    # 將白色背景設為透明
    new_data = []
    for item in data:
      # 將接近白色的像素（包括純白）設為透明
      if item[:3] == (255, 255, 255):  # 完全白色背景的 RGB 值
        new_data.append((255, 255, 255, 0))  # 設置為透明
      else:
        new_data.append(item)

      #new_data = [(255, 255, 255, 0) if item[:3] == (255, 255, 255) else item for item in data]
      #img.putdata(new_data)

    img.putdata(new_data)
    print("img width:", img.width)
    print("img heigth:", img.height)

    # 計算縮放後的尺寸
    new_width = int(img.width * scale_factor)
    new_height = int(img.height * scale_factor)

    # 使用 LANCZOS 進行圖片縮放
    resized_image = img.resize((new_width, new_height),Image.LANCZOS)
    print("resized_image", resized_image.size)

    # 在圖片上加入文字
    draw = ImageDraw.Draw(resized_image)
    font_path = "C:/Windows/Fonts/kaiu.ttf"  # Windows 的標楷體路徑
    print("image, step10..., text_data", text_data)
    # 定義文字與位置
    first_name = text_data.get("first_name", "")
    stamp_date = text_data.get("stamp_date", "")
    last_name = text_data.get("last_name", "")
    print("image, step101...")

    # 插入第一段文字
    font_size = 24
    font = ImageFont.truetype(font_path, font_size)
    print("image, step101-1...", first_name)
    draw.text((28, 4), first_name, fill="blue", font=font)
    print("image, step102...")

    # 第二段文字
    font_size = 15
    font = ImageFont.truetype(font_path, font_size)
    draw.text((4, 30), stamp_date, fill="blue", font=font)
    print("image, step103...")

    # 插入第三段文字
    font_size = 24
    font = ImageFont.truetype(font_path, font_size)
    draw.text((16, 46), last_name, fill="blue", font=font)
    print("image, step1...")
    # 保存結果
    resized_image.save(output_path, "PNG")
    print(f"Processed and resized image saved at: {output_path}")

def insert_png_into_pdf(pdf_path, processed_png_path, output_pdf_path, insert_position):
  """使用 Aspose.PDF 將縮放後的 PNG 插入到 PDF"""
  # 載入 PDF 文檔
  pdf_document = ap.Document(pdf_path)

  # 對每一頁插入圖片
  for page_num in range(len(pdf_document.pages)):
      page = pdf_document.pages[page_num + 1]  # Aspose 的頁碼從 1 開始

      # 加載圖片並插入到指定位置
      #image_stream = ap.io.FileStream(processed_png_path, ap.io.FileMode.READ)
      #image_stamp = ap.ImageStamp(image_stream)
      with open(processed_png_path, "rb") as image_stream:
        image_stamp = ap.ImageStamp(image_stream)

        # 設定圖片的尺寸與位置
        image_stamp.x_indent = insert_position['x']
        image_stamp.y_indent = insert_position['y']
        image_stamp.height = insert_position['height']
        image_stamp.width = insert_position['width']
        image_stamp.background = False  # 保留圖片的透明度

        # 將圖片添加到當前頁面
        page.add_stamp(image_stamp)

  # 保存生成的 PDF
  pdf_document.save(output_pdf_path)
  print(f"New PDF saved at: {output_pdf_path}")


def add_white_mask_to_pdf(input_pdf_path, output_pdf_path):
    # 打開 PDF 文件
    document = fitz.open(input_pdf_path)

    # 遍歷每一頁
    for page_num in range(len(document)):
        page = document.load_page(page_num)

        # 獲取頁面的長度和寬度
        width = page.rect.width
        height = page.rect.height
        print("height, width:", height, width)

        # 設定遮罩的區域（在頁面底部）(長邊為x, 短邊為y)
        x1, y1 = height-20, 0
        x2, y2 = height, width - 30


        # 在頁面上添加藍色矩形遮罩
        #page.draw_rect([x1, y1, x2, y2], color=(0, 0, 1), fill=(0, 0, 1))  # (0, 0, 1) 是藍色
        page.draw_rect([x1, y1, x2, y2], color=(1, 1, 1), fill=(1, 1, 1))  # (1, 1, 1) 是白色

    # 保存新的 PDF
    document.save(output_pdf_path)
    print(f"已儲存包含藍色遮罩的新 PDF，路徑：{output_pdf_path}")


# 生成唯一檔案名稱的函式
def get_unique_filename(target_dir, filename, chip):
    base, ext = os.path.splitext(filename)  # 分離檔案名稱與副檔名
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(target_dir, unique_filename)):  # 檢查檔案是否已存在
        unique_filename = f"{base}_{chip}_{counter}{ext}"  # 為檔名新增後綴
        counter += 1
    return unique_filename

'''
# 清理 temp 資料夾
def clear_temp_folder(temp_path, days=1):
    """
    自動清理 'temp_path' 資料夾下，超過 'days' 天的檔案
    """
    now = time.time()
    cutoff = now - (days * 86400)  # 1天 = 86400秒

    if not os.path.exists(temp_path):
        print(f"資料夾不存在: {temp_path}")
        return

    deleted_files = 0
    for filename in os.listdir(temp_path):
        file_path = os.path.join(temp_path, filename)
        if os.path.isfile(file_path):
            file_stat = os.stat(file_path)
            if file_stat.st_mtime < cutoff:
                try:
                    os.remove(file_path)
                    print(f"刪除過期檔案: {file_path}")
                    deleted_files += 1
                except Exception as e:
                    print(f"刪除檔案失敗 {file_path}: {e}")

    if deleted_files == 0:
        print("沒有找到過期檔案可以刪除")
    else:
        print(f"共刪除 {deleted_files} 個過期檔案")
'''

def get_folder_size(folder):
    """
    取得整個資料夾大小（單位：Bytes）
    """
    try:
      total_size = 0
      for dirpath, dirnames, filenames in os.walk(folder):
          for f in filenames:
              fp = os.path.join(dirpath, f)
              if os.path.isfile(fp):
                  total_size += os.path.getsize(fp)
      return total_size
    except Exception as e:
        print(f"[錯誤] 無法取得資料夾大小：{e}")
        return 0

def clear_temp_folder(temp_path, days=1, allowed_extensions=None, max_folder_size_mb=None):
    """
    自動清理 'temp_path' 資料夾
    - 超過 'days' 天刪除
    - 只刪特定副檔名
    - 可設定最大資料夾大小（單位：MB）
    """
    now = time.time()
    total_size = 0
    cutoff = now - (days * 86400)  # 1天 = 86400秒

    if not os.path.exists(temp_path):
        print(f"資料夾不存在: {temp_path}")
        return

    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.png']

    log_file_path = os.path.join(temp_path, "clear_log.txt")
    deleted_files = 0

    print("\n=== 清理前目錄列出 ===")
    for filename in os.listdir(temp_path):
        print(filename)
    print("=== 開始清理 ===\n")

    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(f"\n=== 清理時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")

        # 先刪除超過 days 的檔案
        for filename in os.listdir(temp_path):
            file_path = os.path.join(temp_path, filename)
            if file_path == log_file_path:
              continue  # 不刪除自己
            if os.path.isfile(file_path):
                ext = os.path.splitext(filename)[1].lower()
                file_stat = os.stat(file_path)

                if ext in allowed_extensions and file_stat.st_mtime < cutoff:
                    try:
                        os.remove(file_path)
                        log_file.write(f"刪除過期檔案: {filename}\n")
                        print(f"刪除過期檔案: {filename}")
                        deleted_files += 1
                    except Exception as e:
                        log_file.write(f"刪除失敗: {filename}，錯誤: {str(e)}\n")
                        print(f"刪除失敗: {filename}，錯誤: {str(e)}")

        # 再檢查整體資料夾大小
        if max_folder_size_mb is not None:
            folder_size_mb = get_folder_size(temp_path) / (1024 * 1024)
            print(f"目前目錄大小: {folder_size_mb:.2f} MB")

            if folder_size_mb > max_folder_size_mb:
                print(f"資料夾超過 {max_folder_size_mb}MB，強制刪除最舊的檔案...")
                files = []
                for filename in os.listdir(temp_path):
                    file_path = os.path.join(temp_path, filename)
                    if os.path.isfile(file_path):
                        file_stat = os.stat(file_path)
                        files.append((file_path, file_stat.st_mtime))

                # 依最舊的檔案優先刪除
                files.sort(key=lambda x: x[1])

                for file_path, _ in files:
                    if file_path == log_file_path:
                      continue  # 不刪除自己

                    try:
                        os.remove(file_path)
                        deleted_files += 1
                        log_file.write(f"超容量刪除: {os.path.basename(file_path)}\n")
                        print(f"超容量刪除: {os.path.basename(file_path)}")

                        folder_size_mb = get_folder_size(temp_path) / (1024 * 1024)
                        if folder_size_mb <= max_folder_size_mb:
                            break
                    except Exception as e:
                        log_file.write(f"刪除失敗: {file_path}，錯誤: {str(e)}\n")
                        print(f"刪除失敗: {file_path}，錯誤: {str(e)}")

        if deleted_files == 0:
            log_file.write("此次無檔案刪除\n")
            print("此次無檔案刪除")

    print("\n=== 清理結束 ===\n")


# ------------------------------------------------------------------


# 瀏覽server端的目錄 API
@browseDirectory.route('/listDirectory', methods=['POST'])
def list_directory():
  print("listDirectory....")

  data = request.json

  default_path = r'C:\vue\chumpower\pdf_file'   # 設定預設路徑, 使用 raw 字串避免反斜線轉義
  path = data.get('path', default_path)         # 使用預設路徑

  path = os.path.normpath(path)                 # 將路徑正規化（支援 UNC 路徑）

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
  #if (temp_len == 0):
  #  return jsonify({'error': f'No file!'}), 400

  return jsonify(items)


# 讀取 PDF API
@browseDirectory.route('/readFile', methods=['POST'])
def read_file():
  print("readFile....")

  data = request.json
  filepath = data.get('filepath')

  base_directory = r'C:\vue\chumpower\pdf_file'   # 定義基礎目錄
  # 如果 filepath 為相對路徑，拼接基礎目錄
  if not os.path.isabs(filepath):                 # 如果不是絕對路徑
    filepath = os.path.join(base_directory, filepath)

  if not filepath or not filepath.endswith('.pdf') or not os.path.exists(filepath):
    return jsonify({'error': 'Invalid file'}), 400

  reader = PdfReader(filepath)
  content = ''.join(page.extract_text() for page in reader.pages)
  return jsonify({'content': content})

'''
# 儲存 PDF API
@browseDirectory.route('/saveFile', methods=['POST'])
def save_file():
  print("saveFile....")

  writer_path = None

  data = request.json
  filepath = data.get('filepath')
  barcode_text = data.get('barcode_text', '')

  insert_position = data.get('position', {'x': 50, 'y': 750})   # 預設插入位置
  pdfType = data.get('pdfType', 1)                              # 預設插入位置
  # 偏移量：右移 100px，向下移動 300px
  if (pdfType==1):
    insert_position['x'] += 70    # 向右移動
    insert_position['y'] -= 130   # 向下移動
  else:
    insert_position['x'] += 100   # 向右移動
    insert_position['y'] += 10    # 向下移動

  base_directory = r'C:\vue\chumpower\pdf_file'
  temp_directory = r'C:\vue\chumpower\temp'

  # 驗證文件路徑
  if not filepath or not filepath.endswith('.pdf') or not os.path.exists(filepath):
    return jsonify({'error': 'Invalid file'}), 400

  # 定義 writer_path
  writer_path = os.path.join(base_directory, f"NEW_{os.path.basename(filepath)}")
  print(f"Writer path: {writer_path}\n")
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

    # 對每一頁，添加條碼到指定位置
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

  # 清理 .crdownload 及 .pdf 文件
  @after_this_request
  def cleanup_crdownload_files(response):
    def delete_temp_files():
        time.sleep(5)  # 等待下載完成
        try:
          #print("delete...")
          delete_crdownload_files()     # 刪除 .crdownload 文件
          #delete_pdf_files()           # 刪除 .pdf 文件
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
'''
@browseDirectory.route('/saveFile', methods=['POST'])
def save_file():
  print("saveFile....")

  data = request.json
  filepath = data.get('filepath')
  barcode_text = data.get('barcode_text', '')
  pdfType = data.get('pdfType', 1)

  insert_position = {'x': 50, 'y': 750}
  if pdfType == 1:
    insert_position['x'] += 70
    insert_position['y'] -= 130
  else:
    insert_position['x'] += 100
    insert_position['y'] += 10

  base_directory = r'C:\vue\chumpower\pdf_file'
  temp_directory = r'C:\vue\chumpower\temp'
  new_filename = f"NEW_{os.path.basename(filepath)}"
  writer_path = os.path.join(base_directory, new_filename)

  try:
    os.makedirs(temp_directory, exist_ok=True)
    barcode_path = os.path.join(temp_directory, 'barcode.png')

    # 產生條碼圖片
    output = BytesIO()
    barcode = Code128(barcode_text, writer=ImageWriter())
    barcode.write(output)

    if output.getbuffer().nbytes == 0:
      raise ValueError("Barcode generation failed.")

    with open(barcode_path, 'wb') as f:
      f.write(output.getvalue())

    # 插入條碼至 PDF
    reader = PdfReader(filepath)
    writer = PdfWriter()

    for page in reader.pages:
      packet = BytesIO()
      c = canvas.Canvas(packet, pagesize=letter)
      c.drawImage(barcode_path, insert_position['x'], insert_position['y'], width=100, height=40)
      c.save()

      packet.seek(0)
      overlay = PdfReader(packet)
      page.merge_page(overlay.pages[0])
      writer.add_page(page)

    with open(writer_path, 'wb') as f:
      writer.write(f)

    if os.path.exists(barcode_path):
      os.remove(barcode_path)
    '''
    # 異步刪除 .crdownload
    @after_this_request
    def cleanup(response):
      def _delete():
        time.sleep(5)
        delete_crdownload_files()
      threading.Thread(target=_delete).start()
      return response
    '''
    return jsonify({
      'message': 'Barcode inserted successfully',
      'filename': new_filename,
      'filepath': writer_path
    })

  except Exception as e:
    print(f"Error saving file: {e}")
    return jsonify({'error': str(e)}), 500


#下載PDF API
@browseDirectory.route('/downloadFile', methods=['POST'])
def download_file():
  print("downloadFile....")

  data = request.json
  filepath = data.get('filepath')
  print("filepath:", filepath)
  download_file_name=os.path.basename(filepath)       # 從完整的檔路徑中取得檔案名稱
  print("download_file_name:", download_file_name)

  if not filepath or not os.path.exists(filepath):
    print(f"Error: File not found at {filepath}")
    return jsonify({'error': 'File not found'}), 404

  # 清理 .pdf 文件
  @after_this_request
  def cleanup_pdf_files_on_directory(response):
      def delete_temp_files():
          time.sleep(5)                               # 等待下載完成
          try:
            delete_pdf_files_on_directory()           # 刪除 .pdf 文件
            print("Temporary .pdf files cleaned up.")
          except Exception as e:
            print(f"Error deleting .pdf files: {e}")
      threading.Thread(target=delete_temp_files).start()
      return response

  try:
    #return send_file(
    response = send_file(
      filepath,
      as_attachment=True,
      #download_name='DOWNLOAD_FILE_NAME.pdf',  # 下載的檔案名稱
      download_name=download_file_name,
      mimetype='application/pdf',
      conditional=False                         # 確保完整文件被發送
    )

    #在回應頭中添加檔案名稱
    response.headers['X-File-Name'] = download_file_name
    print(f"Response headers: {response.headers}")
    return response
  except Exception as e:
    print(f"Error while sending file: {e}")
    return jsonify({'error': str(e)}), 500


#下載XLSX API
@browseDirectory.route('/downloadXlsxFile', methods=['POST'])
def download_xlsx_file():
  print("downloadXlsxFile....")

  # 檢查請求是否包含 JSON
  if not request.json:
    return jsonify({'error': 'Invalid request, missing JSON data'}), 400

  data = request.json
  filepath = data.get('filepath')
  if not filepath or not os.path.exists(filepath):
    print(f"❌ Error: File not found at {filepath}")
    return jsonify({'error': 'File not found'}), 404

  download_file_name = os.path.basename(filepath)         # 從完整的檔路徑中取得檔案名稱
  print("下載檔案名稱:", download_file_name)

  # 清理 .xlsx 文件
  @after_this_request
  def cleanup_xlsx_files(response):
      def delete_temp_files():
          time.sleep(5)                                 # 等待下載完成
          try:
            delete_xlsx_files_on_directory()            # 刪除 .xlsx 文件
            print("Temporary .xlsx files cleaned up.")
          except Exception as e:
            print(f"Error deleting .xlsx files: {e}")
      threading.Thread(target=delete_temp_files).start()
      return response

  try:
    response = send_file(
      filepath,
      as_attachment=True,
      download_name=download_file_name,
      mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    # 確保 Content-Disposition 使用 RFC 8187 格式，避免 UnicodeEncodeError
    encoded_filename = urllib.parse.quote(download_file_name.encode('utf-8'))
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"

    #在回應頭中添加檔案名稱
    #response.headers['X-File-Name'] = download_file_name
    return response
  except Exception as e:
    print(f"Error while sending file: {e}")
    return jsonify({'error': str(e)}), 500

''''
# 將 PNG 檔案貼在 PDF 上的 API
@browseDirectory.route('/stampFile', methods=['POST'])
def stamp_file():
  print("stampFile....")

  data = request.json
  first_name=data.get('first_name')
  last_name=data.get('last_name')
  pdf_path = data.get('filepath')  # 原始 PDF 路徑
  png_path = data.get('png_path')  # PNG 圖片路徑
  insert_position = data.get('position', {'x': 185, 'y': 30})  # 預設插入位置
  #print("data:", data)
  if insert_position is None:
    insert_position = {'x': 185, 'y': 30}

  # 取得今天的日期
  today = date.today()
  # 轉換為民國年（西元年 - 1911）
  roc_year = today.year - 1911
  # 格式化為 "yyy.mm.dd"
  roc_date_str = f"{roc_year:03d}.{today.month:02d}.{today.day:02d}"

  if not pdf_path or not pdf_path.endswith('.pdf') or not os.path.exists(pdf_path):
      return jsonify({'error': 'Invalid PDF file'}), 400

  if not png_path or not png_path.endswith('.png') or not os.path.exists(png_path):
      return jsonify({'error': 'Invalid PNG file'}), 400

  base_directory = r'C:\vue\chumpower\pdf_file'
  temp_directory = r'C:\vue\chumpower\temp'
  writer_path = os.path.join(base_directory, f"STAMPED_{os.path.basename(pdf_path)}")
  print(f"Writer path: {writer_path}\n")

  try:
    #input_path = r'C:\vue\chumpower\pdf_file\日期章\stamp0.png'  # 請替換為您的檔案路徑
    #processed_png_path = r'C:\vue\chumpower\pdf_file\processed_stamp0.png'  # 請替換為您的檔案路徑
    processed_png_path = os.path.join(temp_directory, "processed_" + os.path.basename(png_path))
    print("processed_png_path, os.path.basename(png_path):",processed_png_path , os.path.basename(png_path))
    scale_factor = 0.3
    text_data = {
      "first_name": last_name,
      "stamp_date": roc_date_str,
      "last_name": first_name
    }
    process_and_resize_image(png_path, processed_png_path, scale_factor, text_data)

    # 確定縮放後圖片的尺寸
    with Image.open(processed_png_path) as processed_img:
      img_width, img_height = processed_img.size
      #print("Image size before inserting to PDF:", processed_img.size)

    # 插入圖片的大小
    insert_position['width'] = 44
    insert_position['height'] = 44
    insert_png_into_pdf(pdf_path, processed_png_path, writer_path, insert_position)

    # 清理臨時檔案
    if os.path.exists(processed_png_path):
      os.remove(processed_png_path)

    writer_path2 = os.path.join(base_directory, f"NEW_{os.path.basename(pdf_path)}")
    add_white_mask_to_pdf(writer_path, writer_path2)

  except Exception as e:
    print(f"Error stamping file: {e}")
    return jsonify({'error': f'Failed to stamp file: {e}'}), 500

  # 回傳新生成的 PDF
  return send_file(
    writer_path,
    as_attachment=True,
    download_name=f"STAMPED_{os.path.basename(pdf_path)}",
    mimetype="application/pdf",
    conditional=False             # 確保完整文件被發送
  )
'''

'''
@browseDirectory.route('/stampFile', methods=['POST'])
def stamp_file():
  print("stampFile....")

  data = request.json
  first_name = data.get('first_name')
  last_name = data.get('last_name')
  pdf_path = data.get('filepath')
  png_path = data.get('png_path')
  insert_position = data.get('position', {'x': 185, 'y': 30})

  if not pdf_path or not os.path.exists(pdf_path):
    return jsonify({'error': 'Invalid PDF file'}), 400
  if not png_path or not os.path.exists(png_path):
    return jsonify({'error': 'Invalid PNG file'}), 400

  today = date.today()
  roc_date_str = f"{today.year - 1911:03d}.{today.month:02d}.{today.day:02d}"

  base_directory = r'C:\vue\chumpower\pdf_file'
  temp_directory = r'C:\vue\chumpower\temp'

  try:
    stamped_filename = f"STAMPED_{os.path.basename(pdf_path)}"
    stamped_path = os.path.join(base_directory, stamped_filename)

    original_filename = os.path.basename(pdf_path).removeprefix("NEW_")  # 去除前面的 NEW_
    final_filename = f"STAMPED_{original_filename}"
    final_path = os.path.join(base_directory, final_filename)

    print("stamped_filename:",stamped_filename)
    print("stamped_path:",stamped_path)
    print("final_filename:",final_filename)
    print("final_path:",final_path)

    os.makedirs(temp_directory, exist_ok=True)
    processed_png_path = os.path.join(temp_directory, "processed_" + os.path.basename(png_path))

    text_data = {
      "first_name": last_name,
      "stamp_date": roc_date_str,
      "last_name": first_name
    }

    process_and_resize_image(png_path, processed_png_path, 0.3, text_data)

    insert_position['width'] = 44
    insert_position['height'] = 44
    insert_png_into_pdf(pdf_path, processed_png_path, stamped_path, insert_position)

    if os.path.exists(processed_png_path):
      os.remove(processed_png_path)

    add_white_mask_to_pdf(stamped_path, final_path)

    print("final_filename(filename):", final_filename)
    print("final_path(filepath):", final_path)

    return jsonify({
      'message': 'Stamped and masked PDF created',
      'filename': final_filename,
      'filepath': final_path
    })

  except Exception as e:
    print(f"Error stamping file: {e}")
    return jsonify({'error': str(e)}), 500
'''

@browseDirectory.route('/stampFile', methods=['POST'])
def stamp_file():
    print("stampFile....")

    data = request.json
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    pdf_path = data.get('filepath')
    png_path = data.get('png_path')
    pdf_type = data.get('pdfType')
    print("pdf_type:",pdf_type, type(pdf_type))

    approve = data.get('approve')
    print("approve:",approve, type(approve))

    #insert_position = data.get('position', {'x': 185, 'y': 30})

    if not pdf_path or not os.path.exists(pdf_path):
      return jsonify({'error': 'Invalid PDF file'}), 400
    if not png_path or not os.path.exists(png_path):
      return jsonify({'error': 'Invalid PNG file'}), 400

    today = date.today()
    roc_date_str = f"{today.year - 1911:03d}.{today.month:02d}.{today.day:02d}"

    base_directory = r'C:\vue\chumpower\pdf_file'
    temp_directory = r'C:\vue\chumpower\temp'

    try:
        os.makedirs(temp_directory, exist_ok=True)

        # 產生帶姓名日期章的 PNG
        processed_png_path = os.path.join(temp_directory, "processed_" + os.path.basename(png_path))
        text_data = {
          "first_name": last_name,
          "stamp_date": roc_date_str,
          "last_name": first_name
        }
        process_and_resize_image(png_path, processed_png_path, 0.3, text_data)

        # 決定插章位置
        print("pdf_type:",pdf_type, type(pdf_type))
        if pdf_type == 1:   # 物料清單
          if approve == 0:
            insert_position = {'x': 110, 'y': 730}  # 物料清單的位置
          else:
            insert_position = {'x': 450, 'y': 730}  # 物料清單的位置
        elif pdf_type == 2:   # 領退料單
          if approve == 0:
            insert_position = {'x': 70, 'y': 770}   # 領退料單的位置
          else:
            insert_position = {'x': 480, 'y': 770}  # 領退料單的位置
        else:
          insert_position = {'x': 185, 'y': 30}   # 預設值

        insert_position['width'] = 44
        insert_position['height'] = 44

        # 決定新檔名
        original_filename = os.path.basename(pdf_path).removeprefix("NEW_")  # 去除 NEW_

        if approve == 1:
          stamped_filename = f"STAMPED_{original_filename}"
        else:
          stamped_filename = original_filename

        stamped_path = os.path.join(temp_directory, stamped_filename)  # 先暫時存在 temp 資料夾
        final_path = os.path.join(base_directory, stamped_filename)  # 最後要移去正式資料夾

        # 打開原始 PDF
        doc = fitz.open(pdf_path)

        # 只在最後一頁蓋章
        last_page_index = doc.page_count - 1
        page = doc[last_page_index]

        # 頁面是 A4 格式 (例如 595 x 842 pt)

        # 插入章到每一頁
        '''
        for page in doc:
          rect = fitz.Rect(
            insert_position['x'],
            insert_position['y'],
            insert_position['x'] + insert_position['width'],
            insert_position['y'] + insert_position['height']
          )
          page.insert_image(rect, filename=processed_png_path)
        '''
        rect = fitz.Rect(
          insert_position['x'],
          insert_position['y'],
          insert_position['x'] + insert_position['width'],
          insert_position['y'] + insert_position['height']
        )
        page.insert_image(rect, filename=processed_png_path)

        # 儲存第一階段：有插章，但還沒加遮罩
        doc.save(stamped_path)
        doc.close()

        if os.path.exists(processed_png_path):
          os.remove(processed_png_path)

        # 加白色遮罩
        doc2 = fitz.open(stamped_path)

        # 建立一個新的檔案
        doc3 = fitz.open()  # 空的 PDF

        for page in doc2:
          width = page.rect.width
          height = page.rect.height
          mask_rect = fitz.Rect(0, height - 20, width, height)

          page.draw_rect(mask_rect, color=(1, 1, 1), fill=(1, 1, 1))  # 白色遮罩
          doc3.insert_pdf(doc2, from_page=page.number, to_page=page.number)

        doc2.close()

        # 最後存到 final_path
        doc3.save(final_path)
        doc3.close()

        # 刪除 temp 裡面的暫存 stamped_path
        if os.path.exists(stamped_path):
          os.remove(stamped_path)

        print("final_filename(filename):", stamped_filename)
        print("final_path(filepath):", final_path)

        return jsonify({
          'message': 'Stamped and masked PDF created',
          'filename': stamped_filename,
          'filepath': final_path
        })

    except Exception as e:
      print(f"Error stamping file: {e}")
      return jsonify({'error': str(e)}), 500


#複製檔案 API
@browseDirectory.route('/copyFile', methods=['POST'])
def copy_file():
  print("copyFile....")

  data = request.json

  source_path = data.get('source_path')
  dest_path = data.get('dest_path')
  print("source_path:", source_path)
  print("dest_path:", dest_path)

  if not source_path or not os.path.exists(source_path):
    return jsonify({'error': 'Source file not found'}), 404

  try:
    dest_dir = os.path.dirname(dest_path)
    dest_filename = os.path.basename(dest_path)

    # 如果目的地已有同名檔案，生成一個新的檔案名
    if os.path.exists(dest_path):
        unique_filename = get_unique_filename(dest_dir, dest_filename, "copy")
        dest_path = os.path.join(dest_dir, unique_filename)

    shutil.copy(source_path, dest_path)  # 將檔複製到目的檔案路徑
    print(f"✅ 檔案已複製到：{dest_path}")

    try:
      clear_temp_folder(
        temp_path=r"C:\vue\chumpower\temp",
        days=0.5,  # 超過1天自動刪除
        allowed_extensions=['.pdf', '.png'],  # 只刪這些副檔名
        max_folder_size_mb=200  # 超過500MB也自動刪除
      )

    except Exception as cleanup_error:
      print(f"⚠️ 清除 temp 發生錯誤（不影響複製）: {cleanup_error}")

    return jsonify({
      'message': f'File copied to {dest_path}',
      'status': True,
    }), 200

  except Exception as e:
    print(f"❌ 複製檔案失敗: {e}")
    return jsonify({'error': str(e)}), 500


#移動檔案 API
@browseDirectory.route('/archiveAndDownloadFile', methods=['POST'])
def archive_and_download():
    print("archiveAndDownloadFile....")

    data = request.json
    source_path = data.get('source_path')
    dest_path = data.get('dest_path')

    # Step 1: 複製檔案
    if not source_path or not os.path.exists(source_path):
        return jsonify({'error': 'Source file not found'}), 404

    try:
        shutil.copy(source_path, dest_path)  # 複製檔案
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Step 2: 下載檔案
    if not os.path.exists(dest_path):
        return jsonify({'error': 'Archived file not found'}), 404

    try:
        return send_file(
            dest_path,
            as_attachment=True,
            download_name='NEW_FILE_NAME.pdf',    # 下載的檔案名稱
            mimetype='application/pdf',
            conditional=False                     # 確保完整文件被發送
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 安全性 Header 統一設定
# 所有經由 browseDirectory Blueprint 回傳的 HTTP 回應 都自動套上以下這些安全性標頭
@browseDirectory.after_request
def apply_security_headers(response):
  response.headers['X-Content-Type-Options'] = 'nosniff'      # 告訴瀏覽器「不要猜測檔案的類型」
  response.headers['X-Frame-Options'] = 'DENY'                # 禁止網站被嵌入 <iframe>
  response.headers['X-XSS-Protection'] = '1; mode=block'      # 啟動瀏覽器內建的 XSS 攻擊防護機制
  response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'   # 控制 Referer 標頭在跨站請求中傳送的內容
  # 強化防範 XSS、資源植入、惡意外部腳本
  response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; font-src 'self'; style-src 'self' 'unsafe-inline'"

  # 若使用 HTTPS 可啟用
  # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
  return response