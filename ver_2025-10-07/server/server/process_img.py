from PIL import Image

def process_image(input_path, output_path):
    with Image.open(input_path) as img:
        # 確保圖片模式為 RGBA
        img = img.convert("RGBA")

        # 建立白色背景
        white_background = Image.new("RGBA", img.size, (255, 255, 255, 255))

        # 合成白色背景與原始圖片
        white_background.paste(img, (0, 0), img)

        # 轉換為 RGB，去掉透明層
        final_image = white_background.convert("RGB")

        # 保存結果
        final_image.save(output_path, "PNG")
        print(f"Processed image saved at: {output_path}")

# 測試處理
input_path = r'C:\vue\chumpower\pdf_file\日期章\stamp0.png'  # 請替換為您的檔案路徑
output_path = r'C:\vue\chumpower\pdf_file\processed_stamp0.png'  # 請替換為您的檔案路徑
process_image(input_path, output_path)