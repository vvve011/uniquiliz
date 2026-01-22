import streamlit as st
import os
import zipfile
import shutil
import random
import subprocess
import hashlib
import uuid
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="UniqCreatives Cloud", page_icon="⚡", layout="centered")

st.title("⚡ Быстрый Уникализатор (Hardcore)")
st.markdown("Перетащите архив. Применяется кадрирование, цветокоррекция и шум.")
st.caption("Поддерживает одновременную работу нескольких пользователей.")

# --- ФУНКЦИИ ОБРАБОТКИ ---
def unique_image(src, dst):
    try:
        img = Image.open(src)
        # Удаление метаданных через пересоздание
        if img.mode in ('RGBA', 'LA'):
            background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
            background.paste(img, img.split()[-1])
            img = background
        else:
            # Для JPEG/PNG без прозрачности просто копируем данные
            img = img.copy()
        
        # 1. ГЕОМЕТРИЯ (Самое важное для защиты от AI)
        # Обрезаем 1-2% с краев (Zoom эффект) и возвращаем размер
        width, height = img.size
        crop_percent = random.uniform(0.01, 0.02) # 1-2%
        
        left = width * crop_percent
        top = height * crop_percent
        right = width * (1 - crop_percent)
        bottom = height * (1 - crop_percent)
        
        # Crop и Resize обратно (Lanczos - лучший алгоритм для качества)
        img = img.crop((left, top, right, bottom))
        img = img.resize((width, height), Image.Resampling.LANCZOS)

        # 2. ЦВЕТОКОРРЕКЦИЯ
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(random.uniform(0.96, 1.04)) # ±4%
        
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(random.uniform(0.96, 1.04)) # ±4%
        
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(random.uniform(0.95, 1.05)) # ±5%
        
        # 3. ШУМ И РАЗМЫТИЕ
        # Чуть сильнее размытие, чтобы сбить пиксельные паттерны
        img = img.filter(ImageFilter.GaussianBlur(radius=0.08))
        
        # Сохраняем без EXIF
        img.save(dst, quality=95, optimize=True)
        return True
    except Exception:
        shutil.copy2(src, dst)
        return False

def unique_video(src, dst):
    try:
        # Параметры рандомизации
        contrast = round(random.uniform(0.96, 1.04), 2)
        saturation = round(random.uniform(0.96, 1.04), 2)
        gamma = round(random.uniform(0.96, 1.04), 2)
        volume = round(random.uniform(0.95, 1.05), 2)
        
        # Кроп фактор (обрезка 1-2% ширины/высоты)
        # crop=iw*0.98:ih*0.98 (обрезаем 2%) -> scale=iw:ih (растягиваем обратно)
        crop_factor = round(random.uniform(0.98, 0.99), 2)
        
        # Цепочка фильтров FFmpeg:
        # 1. Crop (кадрирование)
        # 2. Scale (возврат к исходному размеру)
        # 3. EQ (цветокоррекция)
        # 4. Noise (шум)
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
            '-c:v', 'libx264', '-preset', 'ultrafast', # ultrafast для скорости
            '-c:a', 'aac', dst
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        shutil.copy2(src, dst)
        return False

# --- ИНТЕРФЕЙС ---
uploaded_file = st.file_uploader("Загрузите ZIP-архив", type="zip", label_visibility="collapsed")

if uploaded_file is not None:
    session_id = str(uuid.uuid4())[:8]
    
    EXTRACT_FOLDER = f"temp_in_{session_id}"
    PROCESSED_FOLDER = f"temp_out_{session_id}"
    INPUT_ZIP = f"input_{session_id}.zip"
    RESULT_ZIP_NAME = f"result_{session_id}"
    RESULT_ZIP_FILE = f"{RESULT_ZIP_NAME}.zip"

    if os.path.exists(EXTRACT_FOLDER): shutil.rmtree(EXTRACT_FOLDER)
    if os.path.exists(PROCESSED_FOLDER): shutil.rmtree(PROCESSED_FOLDER)
    os.makedirs(EXTRACT_FOLDER)
    os.makedirs(PROCESSED_FOLDER)
    
    with open(INPUT_ZIP, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    with zipfile.ZipFile(INPUT_ZIP, 'r') as zip_ref:
        zip_ref.extractall(EXTRACT_FOLDER)

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

    for root, dirs, files in os.walk(EXTRACT_FOLDER):
        if "__MACOSX" in root: continue
        
        rel_path = os.path.relpath(root, EXTRACT_FOLDER)
        target_path = os.path.join(PROCESSED_FOLDER, rel_path)
        if not os.path.exists(target_path): os.makedirs(target_path)

        for filename in files:
            if filename.startswith("._") or filename == ".DS_Store": continue
            
            src = os.path.join(root, filename)
            dst = os.path.join(target_path, filename)
            ext = os.path.splitext(filename)[1].lower()
            
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

    shutil.make_archive(RESULT_ZIP_NAME, 'zip', PROCESSED_FOLDER)
    progress_bar.empty()
    status_text.empty()
    
    st.success("✅ Готово! Геометрия и метаданные обновлены.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Успешно", stats["success"])
    col2.metric("Ошибки", stats["errors"])
    col3.metric("Пропущено", stats["skipped"])
    
    with open(RESULT_ZIP_FILE, "rb") as fp:
        btn = st.download_button(
            label="📥 СКАЧАТЬ АРХИВ",
            data=fp,
            file_name=uploaded_file.name,
            mime="application/zip",
            type="primary"
        )
    
    try:
        shutil.rmtree(EXTRACT_FOLDER)
        shutil.rmtree(PROCESSED_FOLDER)
        if os.path.exists(INPUT_ZIP): os.remove(INPUT_ZIP)
        if os.path.exists(RESULT_ZIP_FILE): os.remove(RESULT_ZIP_FILE)
    except Exception: pass
