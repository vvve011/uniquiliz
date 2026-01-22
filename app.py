import streamlit as st
import os
import zipfile
import shutil
import random
import string
import subprocess
import hashlib
import uuid
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="UniqCreatives Cloud", page_icon="⚡", layout="centered")

st.title("⚡ Быстрый Уникализатор (Multi-Upload)")
st.markdown("Перетащите один или несколько ZIP-архивов. Файлы будут разложены по папкам.")

# --- ФУНКЦИИ ОБРАБОТКИ ---
def unique_image(src, dst):
    try:
        img = Image.open(src)
        if img.mode in ('RGBA', 'LA'):
            background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
            background.paste(img, img.split()[-1])
            img = background
        else:
            img = img.copy()
        
        # 1. ГЕОМЕТРИЯ (Zoom 1-2%)
        width, height = img.size
        crop_percent = random.uniform(0.01, 0.02)
        left = width * crop_percent
        top = height * crop_percent
        right = width * (1 - crop_percent)
        bottom = height * (1 - crop_percent)
        img = img.crop((left, top, right, bottom))
        img = img.resize((width, height), Image.Resampling.LANCZOS)

        # 2. ЦВЕТОКОРРЕКЦИЯ
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(random.uniform(0.96, 1.04))
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(random.uniform(0.96, 1.04))
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(random.uniform(0.95, 1.05))
        
        # 3. ШУМ
        img = img.filter(ImageFilter.GaussianBlur(radius=0.08))
        
        img.save(dst, quality=95, optimize=True)
        return True
    except Exception:
        shutil.copy2(src, dst)
        return False

def unique_video(src, dst):
    try:
        contrast = round(random.uniform(0.96, 1.04), 2)
        saturation = round(random.uniform(0.96, 1.04), 2)
        gamma = round(random.uniform(0.96, 1.04), 2)
        volume = round(random.uniform(0.95, 1.05), 2)
        crop_factor = round(random.uniform(0.98, 0.99), 2)
        
        video_filters = (
            f"crop=iw*{crop_factor}:ih*{crop_factor},"
            f"scale=iw:ih,"
            f"eq=contrast={contrast}:saturation={saturation}:gamma={gamma},"
            f"noise=alls=1:allf=t+u"
        )
        audio_filters = f"volume={volume}"

        subprocess.run([
            'ffmpeg', '-y', '-i', src,
            '-vf', video_filters,
            '-af', audio_filters,
            '-map_metadata', '-1',
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-c:a', 'aac', dst
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        shutil.copy2(src, dst)
        return False

# --- ИНТЕРФЕЙС ---
uploaded_files = st.file_uploader("Загрузите ZIP-архивы", type="zip", accept_multiple_files=True, label_visibility="collapsed")

if uploaded_files:
    session_id = str(uuid.uuid4())[:8]
    
    EXTRACT_FOLDER = f"temp_in_{session_id}"
    PROCESSED_FOLDER = f"temp_out_{session_id}"
    RESULT_ZIP_NAME = f"result_{session_id}"
    RESULT_ZIP_FILE = f"{RESULT_ZIP_NAME}.zip"

    # Очистка и создание папок
    if os.path.exists(EXTRACT_FOLDER): shutil.rmtree(EXTRACT_FOLDER)
    if os.path.exists(PROCESSED_FOLDER): shutil.rmtree(PROCESSED_FOLDER)
    os.makedirs(EXTRACT_FOLDER)
    os.makedirs(PROCESSED_FOLDER)
    
    # --- ЭТАП 1: Распаковка всех архивов ---
    for u_file in uploaded_files:
        # Создаем подпапку для каждого архива, чтобы файлы не смешались
        safe_name = "".join(x for x in os.path.splitext(u_file.name)[0] if x.isalnum() or x in "._- ")
        archive_subfolder = os.path.join(EXTRACT_FOLDER, safe_name)
        os.makedirs(archive_subfolder, exist_ok=True)
        
        # Сохраняем временно zip
        temp_zip_path = os.path.join(EXTRACT_FOLDER, f"{safe_name}.zip")
        with open(temp_zip_path, "wb") as f:
            f.write(u_file.getbuffer())
            
        # Распаковываем в подпапку
        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(archive_subfolder)
        except Exception as e:
            st.error(f"Ошибка распаковки {u_file.name}: {e}")
        
        # Удаляем временный zip, чтобы он не попал в обработку
        os.remove(temp_zip_path)

    # --- ЭТАП 2: Подсчет файлов ---
    stats = {"success": 0, "errors": 0, "skipped": 0, "total": 0}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_files_count = 0
    for r, d, files in os.walk(EXTRACT_FOLDER):
        if "__MACOSX" in r: continue
        for f in files:
            if not f.startswith("._") and f != ".DS_Store":
                total_files_count += 1
    if total_files_count == 0: total_files_count = 1

    # --- ЭТАП 3: Обработка ---
    for root, dirs, files in os.walk(EXTRACT_FOLDER):
        if "__MACOSX" in root: continue
        
        rel_path = os.path.relpath(root, EXTRACT_FOLDER)
        target_path = os.path.join(PROCESSED_FOLDER, rel_path)
        if not os.path.exists(target_path): os.makedirs(target_path)

        for filename in files:
            if filename.startswith("._") or filename == ".DS_Store": continue
            
            src = os.path.join(root, filename)
            
            # --- ЛОГИКА ПЕРЕИМЕНОВАНИЯ ---
            name, ext = os.path.splitext(filename)
            suffix_len = random.randint(3, 6)
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=suffix_len))
            new_filename = f"{name}_{random_suffix}{ext}"
            
            dst = os.path.join(target_path, new_filename)
            
            ext = ext.lower()
            stats["total"] += 1
            
            if ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
                if unique_image(src, dst): stats["success"] += 1
                else: stats["errors"] += 1
            elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
                if unique_video(src, dst): stats["success"] += 1
                else: stats["errors"] += 1
            else:
                shutil.copy2(src, dst)
                stats["skipped"] += 1
            
            progress = min(stats["total"] / total_files_count, 1.0)
            progress_bar.progress(progress)
            status_text.text(f"Обработка: {stats['total']} из {total_files_count}")

    # Архивация результата
    shutil.make_archive(RESULT_ZIP_NAME, 'zip', PROCESSED_FOLDER)
    progress_bar.empty()
    status_text.empty()
    
    st.success(f"✅ Готово! Обработано архивов: {len(uploaded_files)}.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Успешно", stats["success"])
    col2.metric("Ошибки", stats["errors"])
    col3.metric("Пропущено", stats["skipped"])
    
    # Определение имени файла для скачивания
    download_name = uploaded_files[0].name if len(uploaded_files) == 1 else "UNIQUE_BUNDLE.zip"
    
    with open(RESULT_ZIP_FILE, "rb") as fp:
        btn = st.download_button(
            label=f"📥 СКАЧАТЬ АРХИВ ({len(uploaded_files)} шт.)",
            data=fp,
            file_name=download_name,
            mime="application/zip",
            type="primary"
        )
    
    try:
        shutil.rmtree(EXTRACT_FOLDER)
        shutil.rmtree(PROCESSED_FOLDER)
        if os.path.exists(RESULT_ZIP_FILE): os.remove(RESULT_ZIP_FILE)
    except Exception: pass
