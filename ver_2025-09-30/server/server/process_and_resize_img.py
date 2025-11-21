from PIL import Image

def process_and_resize_image(input_path, output_path, scale_factor=0.45):
    with Image.open(input_path) as img:
        # 確保圖片模式為 RGBA
        img = img.convert("RGBA")
        data = img.getdata()

        # 創建一個新的圖像數據，將白色背景設為透明
        new_data = []
        for item in data:
            # 將接近白色的像素（包括純白）設為透明
            if item[:3] == (255, 255, 255):  # 完全白色的 RGB 值
                new_data.append((255, 255, 255, 0))  # 設置為透明
            else:
                new_data.append(item)

        img.putdata(new_data)

        # 計算縮放後的尺寸
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)

        # 縮放圖片，使用 LANCZOS 進行高品質縮放
        resized_image = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 保存結果
        resized_image.save(output_path, "PNG")
        print(f"Processed and resized image saved at: {output_path}")

# 測試處理
input_path = r'C:\vue\chumpower\pdf_file\日期章\stamp0.png'  # 請替換為您的檔案路徑
output_path = r'C:\vue\chumpower\pdf_file\processed_stamp0.png'  # 請替換為您的檔案路徑
process_and_resize_image(input_path, output_path)