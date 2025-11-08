import os
import sys
import subprocess
import io
import time
def restart_script():
            print("程式即將重新啟動以應用變更...")
            time.sleep(2)
            os.execl(sys.executable, sys.executable, *sys.argv)
def check_and_install_dependencies():
    """檢查必要的套件是否已安裝，如果沒有，則提示使用者進行安裝。"""
    try:
        # 嘗試匯入所有必要的套件
        from PIL import Image
        import pillow_heif
        import cairosvg
    except ImportError as e:
        print(f"警告：偵測到缺少必要的套件: {e}")
        # 取得 requirements.txt 的路徑
        # 通常，requirements.txt 位於專案的根目錄
        # 這裡我們假設它與 converter.py 在同一個資料夾
        req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')

        if not os.path.exists(req_path):
            print(f"錯誤：找不到 'requirements.txt' 檔案。請確認它與您的腳本在同一個資料夾中。")
            sys.exit(1)

        autoinstall = input("是否要自動從 'requirements.txt' 安裝缺少的套件？ (Y/n): ")
        if autoinstall.lower() in ['y', 'yes', '']:
            print("正在安裝套件...")
            try:
                # 使用 sys.executable 來確保我們使用的是正確的 python 環境下的 pip
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
                print("\n套件安裝完成。")
                restart_script()
            except subprocess.CalledProcessError:
                print("\n錯誤：套件安裝失敗。請手動執行 'pip install -r requirements.txt'。")
            # 無論成功或失敗，都需要使用者重新啟動腳本
            sys.exit()
        else:
            print("安裝已取消。腳本無法繼續執行。")
            sys.exit()

# 在腳本開始時執行檢查
check_and_install_dependencies()

# 現在，我們可以安全地匯入套件
from PIL import Image
import pillow_heif
import cairosvg

# 註冊 HEIF 開啟器
pillow_heif.register_heif_opener()

def setup_folders(input_folder, output_folder):
    """檢查並建立輸入和輸出資料夾。"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    if not os.path.exists(input_folder):
        os.makedirs(input_folder)
        print(f"已建立 '{input_folder}' 資料夾。請將您的圖片檔案放入此資料夾中，然後重新執行程式。")
        return False
    return True

def get_conversion_mode():
    """向使用者詢問轉換模式。"""
    while True:
        choice = input("您想要進行批次轉檔 (輸入 'batch (b)') 還是單一檔案轉檔 (輸入 'single (s)')？ ").lower()
        if choice in ["batch", "single", "b", "s"]:
            if choice in ['batch', 'b']:
                return 'batch'
            else:
                return 'single'
        print("無效的輸入，請輸入 'batch (b)' 或 'single (s)'。")

def get_single_file(input_folder, supported_formats):
    """列出檔案並讓使用者選擇單一檔案進行轉換。"""
    files = [f for f in os.listdir(input_folder) if f.lower().endswith(supported_formats)]
    if not files:
        return None

    print("\n可用的檔案：")
    for i, f in enumerate(files):
        print(f"  {i + 1}: {f}")

    while True:
        try:
            choice = input(f"請輸入您想轉換的檔案編號 (1~{len(files)}) 或直接輸入檔案名稱： ")
            # 檢查使用者是否輸入數字
            if choice.isdigit():
                file_index = int(choice) - 1
                if 0 <= file_index < len(files):
                    return files[file_index]
            # 檢查使用者是否輸入存在於列表的檔案名稱
            elif choice in files:
                return choice
            print("無效的輸入，請輸入列表中的檔案編號或完整的檔案名稱。")
        except ValueError:
            print("無效的輸入，請輸入數字。")


def get_target_format():
    """向使用者詢問目標轉換格式。"""
    while True:
        choice = input("您想要將圖片轉換成 'jpg', 'png', 'heic', 'heif', 'ico' 還是 'webp'？ ").lower()
        if choice in ["jpg", "png", "heic", "heif", "ico", "webp"]:
            return choice
        print("無效的輸入，請輸入 'jpg', 'png', 'heic', 'heif', 'ico' 或 'webp'。")

def get_custom_save_options(target_format):
    """根據目標格式詢問使用者是否要自訂儲存參數，例如圖片品質。"""
    # 預設的儲存選項
    options = {
        "jpg": {"quality": 95},
        "png": {},
        "heic": {"quality": 90},
        "heif": {"quality": 90},
        "ico": {},
        "webp": {"quality": 90}
    }

    # 檢查是否為支援品質設定的格式
    if target_format in ["jpg", "heic", "heif", "webp"]:
        while True:
            customize = input(f"您想為 {target_format} 格式自訂圖片品質嗎？ (y/N): ").lower()
            if customize in ['n', 'no', '']:
                break
            elif customize in ['y', 'yes']:
                while True:
                    try:
                        quality = int(input(f"請輸入圖片品質 (1-100, 預設: {options[target_format]['quality']}): "))
                        if 1 <= quality <= 100:
                            options[target_format]['quality'] = quality
                            break
                        else:
                            print("品質值必須在 1 到 100 之間。")
                    except ValueError:
                        print("無效的輸入，請輸入一個數字。")
                break
            else:
                print("無效的輸入，請輸入 'Y' 或 'N'。")
    return options.get(target_format, {})

def get_resize_parameters():
    """詢問使用者是否要縮放圖片，並取得縮放參數。"""
    while True:
        resize = input("您是否要縮放圖片？ (y/N): ").lower()
        if resize in ['n', 'no', '']:
            return None
        elif resize in ['y', 'yes']:
            break
        else:
            print("無效的輸入，請輸入 'Y' 或 'N'。")

    while True:
        method = input("請選擇縮放方式： 'percentage(p)' (百分比) 或 'dimensions(d)' (最大尺寸)？ ").lower()
        if method in ['percentage', 'dimensions', 'p', 'd']:
            if method in ['percentage', 'p']:
                method = 'percentage'
            else:
                method = 'dimensions'
            break
        else:
            print("無效的輸入，請輸入 'percentage' 或 'dimensions' 或 'p' 或 'd'。")

    if method == 'percentage':
        while True:
            try:
                percent = int(input("請輸入縮放百分比 (1-99): "))
                if 1 <= percent <= 99:
                    return {'mode': 'percentage', 'value': percent}
                else:
                    print("百分比必須在 1 到 99 之間。")
            except ValueError:
                print("無效的輸入，請輸入一個數字。")
    
    if method == 'dimensions':
        while True:
            try:
                width = int(input("請輸入最大寬度 (像素): "))
                height = int(input("請輸入最大高度 (像素): "))
                if width > 0 and height > 0:
                    return {'mode': 'dimensions', 'value': {'width': width, 'height': height}}
                else:
                    print("寬度和高度都必須是正數。")
            except ValueError:
                print("無效的輸入，請輸入數字。")

def convert_image(input_path, output_folder, target_format, custom_save_options, resize_params):
    """將單一圖片轉換為指定格式，並在檔名衝突時自動重新命名。"""
    filename = os.path.basename(input_path)
    clean_name = os.path.splitext(filename)[0]
    
    # 檢查檔名衝突並產生新檔名
    output_filename = f"{clean_name}.{target_format}"
    output_path = os.path.join(output_folder, output_filename)
    counter = 1
    while os.path.exists(output_path):
        output_filename = f"{clean_name} ({counter}).{target_format}"
        output_path = os.path.join(output_folder, output_filename)
        counter += 1

    try:
        # 根據檔案類型開啟圖片
        if input_path.lower().endswith(".svg"):
            if cairosvg is None:
                print(f"無法處理 SVG '{filename}'：cairosvg 函式庫未安裝。")
                return "error"
            png_bytes = cairosvg.svg2png(url=input_path)
            img = Image.open(io.BytesIO(png_bytes))
        else:
            img = Image.open(input_path)

        # 縮放圖片
        if resize_params:
            if resize_params['mode'] == 'percentage':
                scale = resize_params['value'] / 100
                new_width = int(img.width * scale)
                new_height = int(img.height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            elif resize_params['mode'] == 'dimensions':
                max_size = (resize_params['value']['width'], resize_params['value']['height'])
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 如果目標是 jpg，需要處理透明度
        if target_format == "jpg":
            if img.mode in ('RGBA', 'P', 'LA'):
                # 建立一個白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                # 將含有透明度的圖片貼上背景
                img.load() # 確保圖片資料已載入
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3]) # 使用 alpha 通道作為遮罩
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
        
        # 準備正確的格式名稱
        if target_format in ["heic", "heif"]:
            format_to_save = "HEIF"
        elif target_format == "jpg":
            format_to_save = "JPEG"
        else:
            format_to_save = target_format.upper()
        
        img.save(output_path, format=format_to_save, **custom_save_options)
        print(f"成功將 '{filename}' 轉換為 '{os.path.basename(output_path)}'")
        return "success"
    except Exception as e:
        print(f"轉換 '{filename}' 時發生錯誤: {e}")
        return "error"

def main():
    """主執行函式。"""
    print("=== 圖片格式轉換器 ===")
    input_folder = "input"
    output_folder = "output"
    supported_formats = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".svg", ".ico", ".webp")

    if not setup_folders(input_folder, output_folder):
        return

    all_files = [f for f in os.listdir(input_folder) if f.lower().endswith(supported_formats)]
    if not all_files:
        print(f"在 '{input_folder}' 資料夾中沒有找到任何支援的檔案可供轉換。")
        print("支援的格式包括: " + ", ".join(supported_formats))
        return

    mode = get_conversion_mode()
    files_to_convert = []

    if mode == 'batch':
        files_to_convert = all_files
    elif mode == 'single':
        single_file = get_single_file(input_folder, supported_formats)
        if single_file:
            files_to_convert.append(single_file)

    if not files_to_convert:
        print("沒有選擇任何檔案進行轉換。" )
        return

    target_format = get_target_format()
    final_save_options = get_custom_save_options(target_format)
    resize_params = get_resize_parameters()
    
    success_count = 0
    error_count = 0

    print("\n開始轉換...")
    for filename in files_to_convert:
        input_path = os.path.join(input_folder, filename)
        result = convert_image(input_path, output_folder, target_format, final_save_options, resize_params)
        if result == "success":
            success_count += 1
        else:
            error_count += 1

    print("\n---------- 轉換報告 -----------")
    print(f"轉換完成！")
    print(f"成功: {success_count} 個檔案")
    print(f"失敗: {error_count} 個檔案")
    print("-------------------------------")

if __name__ == "__main__":
    main()