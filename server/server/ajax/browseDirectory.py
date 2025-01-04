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
from PIL import Image, ImageOps, ImageDraw, ImageFont
import fitz

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
    #print("resized_image", resized_image.size)

    # 在圖片上加入文字
    draw = ImageDraw.Draw(resized_image)
    font_path = "C:/Windows/Fonts/kaiu.ttf"  # Windows 的標楷體路徑

    # 定義文字與位置
    first_name = text_data.get("first_name", "")
    stamp_date = text_data.get("stamp_date", "")
    last_name = text_data.get("last_name", "")

    # 插入第一段文字
    font_size = 24
    font = ImageFont.truetype(font_path, font_size)
    draw.text((28, 4), first_name, fill="blue", font=font)

    # 第二段文字
    font_size = 15
    font = ImageFont.truetype(font_path, font_size)
    draw.text((4, 30), stamp_date, fill="blue", font=font)

    # 插入第三段文字
    font_size = 24
    font = ImageFont.truetype(font_path, font_size)
    draw.text((16, 46), last_name, fill="blue", font=font)

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
  if (temp_len == 0):
    return jsonify({'error': f'No file!'}), 400

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


# 將 PNG 檔案貼在 PDF 上的 API
@browseDirectory.route('/stampFile', methods=['POST'])
def stamp_file():
  print("stampFile....")

  data = request.json
  pdf_path = data.get('filepath')  # 原始 PDF 路徑
  png_path = data.get('png_path')  # PNG 圖片路徑
  insert_position = data.get('position', {'x': 185, 'y': 30})  # 預設插入位置

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
    #print("processed_png_path, os.path.basename(png_path):",processed_png_path , os.path.basename(png_path))
    scale_factor = 0.3
    text_data = {
      "first_name": "陳",
      "stamp_date": "113.12.23",
      "last_name": "瑞琪"
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


#複製檔案 API
@browseDirectory.route('/copyFile', methods=['POST'])
def copy_file():
    print("copyFile....")

    data = request.json
    source_path = data.get('source_path')
    dest_path = data.get('dest_path')

    if not source_path or not os.path.exists(source_path):
        return jsonify({'error': 'Source file not found'}), 404

    try:
        shutil.copy(source_path, dest_path)  # 將檔複製到目的檔案路徑
        return jsonify({'message': f'File copied to {dest_path}'}), 200
    except Exception as e:
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
