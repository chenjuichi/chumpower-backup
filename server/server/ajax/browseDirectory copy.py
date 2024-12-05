import time
import datetime
import pytz

from flask import Blueprint, jsonify, request, send_file, after_this_request
import os
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader, PdfWriter
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image
from io import BytesIO
import tempfile

browseDirectory = Blueprint('browseDirectory', __name__)

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

    data = request.json
    filepath = data.get('filepath')
    barcode_text = data.get('barcode_text', '')

    base_directory = r'C:\vue\chumpower\pdf_file'
    temp_directory = r'C:\vue\chumpower\temp'

    if not os.path.isabs(filepath):
        filepath = os.path.join(base_directory, filepath)

    if not filepath or not filepath.endswith('.pdf') or not os.path.exists(filepath):
        return jsonify({'error': 'Invalid file'}), 400

    print("saveFile, step1...")

    os.makedirs(temp_directory, exist_ok=True)
    if not os.access(temp_directory, os.W_OK):
        print(f"Cannot write to temp directory: {temp_directory}")
        return jsonify({'error': 'Permission denied for temp directory'}), 500

    if not barcode_text or not barcode_text.isascii():
        print(f"Invalid barcode text: {barcode_text}")
        return jsonify({'error': 'Invalid barcode text'}), 400

    barcode_path = os.path.join(temp_directory, 'barcode.png')
    try:
        output = BytesIO()
        barcode = Code128(barcode_text, writer=ImageWriter())
        barcode.write(output)

        if output.getbuffer().nbytes == 0:
            print("Barcode generation failed: output buffer is empty")
            return jsonify({'error': 'Failed to generate barcode'}), 500

        with open(barcode_path, 'wb') as f:
            f.write(output.getvalue())
        print(f"Barcode saved at: {barcode_path}")

        with Image.open(barcode_path) as img:
            print("Barcode image size:", img.size)
    except Exception as e:
        print(f"Error saving barcode: {e}")
        return jsonify({'error': 'Failed to generate barcode'}), 500

    reader = PdfReader(filepath)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    # 使用臨時文件保存 PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=temp_directory) as temp_pdf:
        writer_path = temp_pdf.name
        with open(writer_path, 'wb') as f:
            writer.write(f)

        with Image.open(barcode_path) as img:
            img = img.convert("RGB")
            img.save(writer_path, append=True)

    os.remove(barcode_path)

    #註冊一個函式, 並在 HTTP 回應發送後, 執行除新生成的 PDF 檔案(NEW_FILE_NAME.pdf)
    @after_this_request
    def cleanup_file(response):
        try:
            os.remove(writer_path)
            print(f"Temporary file {writer_path} deleted.")
        except Exception as e:
            print(f"Error deleting temporary file {writer_path}: {e}")
        return response

    return send_file(writer_path, as_attachment=True, download_name=f"NEW_{secure_filename(os.path.basename(filepath))}")
