import os
import sys
import subprocess
import io
import time

def restart_script():
    """重新啟動腳本以應用變更。"""
    print("程式即將重新啟動以應用變更...")
    time.sleep(2)
    os.execl(sys.executable, sys.executable, *sys.argv)

def check_and_install_dependencies():
    """檢查必要的套件是否已安裝，如果沒有，則提示使用者進行安裝。"""
    try:
        from PIL import Image
        import pillow_heif
        import cairosvg
        import moviepy.editor as mp
        from pydub import AudioSegment
    except ImportError as e:
        print(f"警告：偵測到缺少必要的套件: {e}")
        req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')

        if not os.path.exists(req_path):
            print(f"錯誤：找不到 'requirements.txt' 檔案。")
            sys.exit(1)

        autoinstall = input("是否要自動從 'requirements.txt' 安裝缺少的套件？ (Y/n): ")
        if autoinstall.lower() in ['y', 'yes', '']:
            print("正在安裝套件...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
                print("\n套件安裝完成。")
                restart_script()
            except subprocess.CalledProcessError:
                print("\n錯誤：套件安裝失敗。請手動執行 'pip install -r requirements.txt'。")
                sys.exit()
        else:
            print("安裝已取消。腳本無法繼續執行。")
            sys.exit()

def check_ffmpeg():
    """檢查 FFmpeg 是否已安裝並在系統路徑中。"""
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n--- 警告：未找到 FFmpeg ---")
        print("此程式的音訊和影片處理功能需要 FFmpeg。")
        
        autoinstall_ffmpeg = False
        install_command = ""
        os_name = ""

        if sys.platform.startswith('linux'):
            os_name = "Linux (Debian/Ubuntu)"
            install_command = "sudo apt-get update && sudo apt-get install -y ffmpeg"
        elif sys.platform == 'darwin':
            os_name = "macOS"
            try:
                subprocess.run(["brew", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                install_command = "brew install ffmpeg"
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("macOS 使用者：自動安裝需要 Homebrew，但似乎未安裝。")
                print("請先從 https://brew.sh/ 安裝 Homebrew。")
        elif sys.platform == 'win32':
            os_name = "Windows"
            try:
                # 優先檢查 winget
                subprocess.run(["winget", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                install_command = "winget install --id=Gyan.FFmpeg -e"
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    # 若 winget 失敗，再檢查 choco
                    subprocess.run(["choco", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    install_command = "choco install ffmpeg"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print("Windows 使用者：推薦使用 winget 或 Chocolatey 進行自動安裝，但兩者似乎都未安裝。")
                    print("請考慮安裝 winget (內建於新版 Windows) 或 Chocolatey (https://chocolatey.org/install)。")

        if install_command:
            choice = input(f"偵測到您的作業系統是 {os_name}。是否嘗試自動安裝 FFmpeg？ (Y/n): ").lower()
            if choice in ['y', 'yes', '']:
                autoinstall_ffmpeg = True

        if autoinstall_ffmpeg:
            print(f"正在執行安裝指令：'{install_command}'")
            print("這可能需要管理員權限，並請留意任何彈出的確認視窗。")
            try:
                process = subprocess.run(install_command, shell=True, check=True)
                print("\nFFmpeg 安裝成功！")
                restart_script()
            except subprocess.CalledProcessError as e:
                print(f"\nFFmpeg 自動安裝失敗: {e}")
                print("請嘗試手動安裝。")
        
        print("\n請先手動安裝 FFmpeg，然後再重新執行此腳本。")
        print("安裝說明：")
        print("  - Windows：")
        print("    1. 使用 winget (推薦)：在終端機中執行 'winget install --id=Gyan.FFmpeg -e'")
        print("    2. 使用 Chocolatey：請先安裝 Chocolatey (https://chocolatey.org/install)，然後執行 'choco install ffmpeg'")
        print("    3. 手動下載：從 https://ffmpeg.org/download.html 下載，並將其路徑新增到系統環境變數中。")
        print("  - macOS (使用 Homebrew)：在終端機中執行 'brew install ffmpeg'")
        print("  - Linux (Debian/Ubuntu)：在終端機中執行 'sudo apt-get install ffmpeg'")
        print("---------------------------------")
        sys.exit(1)

check_and_install_dependencies()
check_ffmpeg()

from PIL import Image
import pillow_heif
import cairosvg
import moviepy.editor as mp
from pydub import AudioSegment

pillow_heif.register_heif_opener()

def setup_folders(input_folder, output_folder):
    """檢查並建立輸入和輸出資料夾。"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    if not os.path.exists(input_folder):
        os.makedirs(input_folder)
        print(f"已建立 '{input_folder}' 資料夾。請將您的檔案放入此資料夾中，然後重新執行程式。")
        return False
    return True

def get_conversion_type():
    """向使用者詢問要轉換的檔案類型。"""
    while True:
        choice = input("您想要轉換圖片 ('image')、影片 ('video') 還是音訊 ('audio')？ ").lower()
        if choice in ["image", "video", "audio"]:
            return choice
        print("無效的輸入，請輸入 'image'、'video' 或 'audio'。")

def get_conversion_mode():
    """向使用者詢問轉換模式。"""
    while True:
        choice = input("您想要進行批次轉檔 ('batch') 還是單一檔案轉檔 ('single')？ ").lower()
        if choice in ["batch", "single"]:
            return choice
        print("無效的輸入，請輸入 'batch' 或 'single'。")

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
            if choice.isdigit():
                file_index = int(choice) - 1
                if 0 <= file_index < len(files):
                    return files[file_index]
            elif choice in files:
                return choice
            print("無效的輸入，請輸入列表中的檔案編號或完整的檔案名稱。")
        except ValueError:
            print("無效的輸入，請輸入數字。")

def get_target_image_format():
    """向使用者詢問目標圖片轉換格式。"""
    while True:
        choice = input("您想要將圖片轉換成 'jpg', 'png', 'heic', 'heif', 'ico' 還是 'webp'？ ").lower()
        if choice in ["jpg", "png", "heic", "heif", "ico", "webp"]:
            return choice
        print("無效的輸入，請輸入 'jpg', 'png', 'heic', 'heif', 'ico' 或 'webp'。")

def get_target_video_format():
    """向使用者詢問目標影片轉換格式。"""
    while True:
        choice = input("您想要將影片轉換成 'mp4', 'webm', 'mov', 'avi' 還是 'gif'？ ").lower()
        if choice in ["mp4", "webm", "mov", "avi", "gif"]:
            return choice
        print("無效的輸入，請輸入 'mp4', 'webm', 'mov', 'avi' 或 'gif'。")

def ask_extract_audio():
    """詢問使用者是否只想從影片中提取音訊。"""
    while True:
        choice = input("您是否只想保留音訊？ (y/n): ").lower()
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no', '']:
            return False
        print("無效的輸入，請輸入 'y' 或 'n'。")

def get_target_audio_format():
    """向使用者詢問目標音訊轉換格式。"""
    while True:
        choice = input("您想要將音訊轉換成 'mp3', 'wav', 'ogg', 'flac'？ ").lower()
        if choice in ["mp3", "wav", "ogg", "flac"]:
            return choice
        print("無效的輸入，請輸入 'mp3', 'wav', 'ogg' 或 'flac'。")

def get_custom_save_options(target_format):
    """根據目標格式詢問使用者是否要自訂儲存參數，例如圖片品質。"""
    options = {
        "jpg": {"quality": 95}, "webp": {"quality": 90},
        "heic": {"quality": 90}, "heif": {"quality": 90}
    }
    if target_format not in options:
        return {}

    while True:
        customize = input(f"您想為 {target_format} 格式自訂圖片品質嗎？ (y/N): ").lower()
        if customize in ['n', 'no', '']:
            return options[target_format]
        elif customize in ['y', 'yes']:
            while True:
                try:
                    quality = int(input(f"請輸入圖片品質 (1-100, 預設: {options[target_format]['quality']}): "))
                    if 1 <= quality <= 100:
                        options[target_format]['quality'] = quality
                        return options[target_format]
                    else:
                        print("品質值必須在 1 到 100 之間。")
                except ValueError:
                    print("無效的輸入，請輸入一個數字。")
            break
        else:
            print("無效的輸入，請輸入 'Y' 或 'N'。")
    return {}

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
        method = input("請選擇縮放方式： 'percentage' (百分比) 或 'dimensions' (最大尺寸)？ ").lower()
        if method in ['percentage', 'dimensions']:
            break
        else:
            print("無效的輸入，請輸入 'percentage' 或 'dimensions'。")

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
                    return {'mode': 'dimensions', 'value': (width, height)}
                else:
                    print("寬度和高度都必須是正數。")
            except ValueError:
                print("無效的輸入，請輸入數字。")

def convert_image(input_path, output_folder, target_format, custom_save_options, resize_params):
    """將單一圖片轉換為指定格式。"""
    filename = os.path.basename(input_path)
    clean_name = os.path.splitext(filename)[0]
    output_filename = f"{clean_name}.{target_format}"
    output_path = os.path.join(output_folder, output_filename)
    counter = 1
    while os.path.exists(output_path):
        output_filename = f"{clean_name} ({counter}).{target_format}"
        output_path = os.path.join(output_folder, output_filename)
        counter += 1

    try:
        if input_path.lower().endswith(".svg"):
            png_bytes = cairosvg.svg2png(url=input_path)
            img = Image.open(io.BytesIO(png_bytes))
        else:
            img = Image.open(input_path)

        if resize_params:
            if resize_params['mode'] == 'percentage':
                scale = resize_params['value'] / 100
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            elif resize_params['mode'] == 'dimensions':
                img.thumbnail(resize_params['value'], Image.Resampling.LANCZOS)

        if target_format == "jpg" and img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            img.load()
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB' and target_format not in ['png', 'webp', 'heic', 'heif']:
             img = img.convert('RGB')

        format_to_save = "HEIF" if target_format in ["heic", "heif"] else "JPEG" if target_format == "jpg" else target_format.upper()
        img.save(output_path, format=format_to_save, **custom_save_options)
        print(f"成功將 '{filename}' 轉換為 '{os.path.basename(output_path)}'")
        return "success"
    except Exception as e:
        print(f"轉換 '{filename}' 時發生錯誤: {e}")
        return "error"

def convert_video(input_path, output_folder, target_format):
    """將單一影片轉換為指定格式。"""
    filename = os.path.basename(input_path)
    clean_name = os.path.splitext(filename)[0]
    output_filename = f"{clean_name}.{target_format}"
    output_path = os.path.join(output_folder, output_filename)
    counter = 1
    while os.path.exists(output_path):
        output_filename = f"{clean_name} ({counter}).{target_format}"
        output_path = os.path.join(output_folder, output_filename)
        counter += 1

    try:
        video = mp.VideoFileClip(input_path)
        if target_format == 'gif':
            video.write_gif(output_path)
        else:
            video.write_videofile(output_path, codec='libx264' if target_format == 'mp4' else None)
        print(f"成功將 '{filename}' 轉換為 '{os.path.basename(output_path)}'")
        return "success"
    except Exception as e:
        print(f"轉換 '{filename}' 時發生錯誤: {e}")
        return "error"

def convert_audio(input_path, output_folder, target_format):
    """將單一音訊檔案轉換為指定格式。"""
    filename = os.path.basename(input_path)
    clean_name = os.path.splitext(filename)[0]
    output_filename = f"{clean_name}.{target_format}"
    output_path = os.path.join(output_folder, output_filename)
    counter = 1
    while os.path.exists(output_path):
        output_filename = f"{clean_name} ({counter}).{target_format}"
        output_path = os.path.join(output_folder, output_filename)
        counter += 1

    try:
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format=target_format)
        print(f"成功將 '{filename}' 轉換為 '{os.path.basename(output_path)}'")
        return "success"
    except Exception as e:
        print(f"轉換 '{filename}' 時發生錯誤: {e}")
        return "error"

def extract_audio_from_video(input_path, output_folder, target_format):
    """從影片中提取音訊並轉換為指定格式。"""
    filename = os.path.basename(input_path)
    clean_name = os.path.splitext(filename)[0]
    output_filename = f"{clean_name}.{target_format}"
    output_path = os.path.join(output_folder, output_filename)
    counter = 1
    while os.path.exists(output_path):
        output_filename = f"{clean_name} ({counter}).{target_format}"
        output_path = os.path.join(output_folder, output_filename)
        counter += 1

    try:
        video = mp.VideoFileClip(input_path)
        audio = video.audio
        audio.write_audiofile(output_path)
        audio.close()
        video.close()
        print(f"成功從 '{filename}' 中提取音訊並儲存為 '{os.path.basename(output_path)}'")
        return "success"
    except Exception as e:
        print(f"從 '{filename}' 提取音訊時發生錯誤: {e}")
        return "error"

def main():
    """主執行函式。"""
    print("=== 檔案格式轉換器 ===")
    input_folder = "input"
    output_folder = "output"
    
    if not setup_folders(input_folder, output_folder):
        return

    conversion_type = get_conversion_type()
    
    if conversion_type == 'image':
        supported_formats = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".svg", ".ico", ".webp")
        target_format_func = get_target_image_format
        convert_func = convert_image
    elif conversion_type == 'video':
        supported_formats = (".mp4", ".mov", ".avi", ".webm", ".mkv")
        if ask_extract_audio():
            target_format_func = get_target_audio_format
            convert_func = extract_audio_from_video
        else:
            target_format_func = get_target_video_format
            convert_func = convert_video
    elif conversion_type == 'audio':
        supported_formats = (".mp3", ".wav", ".ogg", ".flac")
        target_format_func = get_target_audio_format
        convert_func = convert_audio

    all_files = [f for f in os.listdir(input_folder) if f.lower().endswith(supported_formats)]
    if not all_files:
        print(f"在 '{input_folder}' 資料夾中沒有找到任何支援的 {conversion_type} 檔案可供轉換。")
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
        print("沒有選擇任何檔案進行轉換。")
        return

    target_format = target_format_func()
    
    custom_options = {}
    resize_params = None
    if conversion_type == 'image':
        custom_options = get_custom_save_options(target_format)
        resize_params = get_resize_parameters()

    success_count = 0
    error_count = 0

    print("\n開始轉換...")
    for filename in files_to_convert:
        input_path = os.path.join(input_folder, filename)
        if conversion_type == 'image':
            result = convert_func(input_path, output_folder, target_format, custom_options, resize_params)
        else:
            result = convert_func(input_path, output_folder, target_format)
        
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