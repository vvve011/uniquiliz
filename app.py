import streamlit as st
import os
import zipfile
import shutil
import random
import subprocess
import hashlib
from PIL import Image, ImageEnhance, ImageFilter

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="UniqCreatives Cloud", page_icon="🚀", layout="centered")

st.title("🚀 Уникализатор Креативов")
st.markdown("Загрузите ZIP-архив с фото/видео. На выходе получите архив с уникальными хешами и метаданными.")
st.caption("Работает на Streamlit Community Cloud")

# --- ФУНКЦИИ ОБРАБОТКИ ---
def get_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def unique_image(src, dst):
    try:
        img = Image.open(src)
        # Пересоздаем изображение для удаления EXIF
        if img.mode in ('RGBA', 'LA'):
            background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
            background.paste(img, img.split()[-1])
            img = background
        
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(list(img.getdata()))
        
        # Накладываем рандомные фильтры
        enhancer = ImageEnhance.Brightness(clean_img)
        clean_img = enhancer.enhance(random.uniform(0.97, 1.03))
        enhancer = ImageEnhance.Contrast(clean_img)
        clean_img = enhancer.enhance(random.uniform(0.97, 1.03))
        enhancer = ImageEnhance.Color(clean_img)
        clean_img = enhancer.enhance(random.uniform(0.95, 1.05))
        clean_img = clean_img.filter(ImageFilter.GaussianBlur(radius=0.05))
        
        clean_img.save(dst, quality=95, optimize=True)
        return True
    except Exception as e:
        shutil.copy2(src, dst)
        return False

def unique_video(src, dst):
    try:
        # Генерация параметров
        contrast = round(random.uniform(0.97, 1.03), 2)
        saturation = round(random.uniform(0.97, 1.03), 2)
        gamma = round(random.uniform(0.97, 1.03), 2)
        volume = round(random.uniform(0.95, 1.05), 2)

        # Фильтры FFmpeg
        video_filters = f"eq=contrast={contrast}:saturation={saturation}:gamma={gamma},noise=alls=1:allf=t+u"
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
uploaded_file = st.file_uploader("Выберите ZIP-архив", type="zip")

if uploaded_file is not None:
    if st.button("🔥 Начать уникализацию"):
        with st.spinner('Обработка... (Видео может занять время)'):
            # Временные папки
            EXTRACT_FOLDER = "temp_in"
            PROCESSED_FOLDER = "temp_out"
            
            # Очистка
            if os.path.exists(EXTRACT_FOLDER): shutil.rmtree(EXTRACT_FOLDER)
            if os.path.exists(PROCESSED_FOLDER): shutil.rmtree(PROCESSED_FOLDER)
            os.makedirs(EXTRACT_FOLDER)
            os.makedirs(PROCESSED_FOLDER)
            
            # Очистка старых архивов
            if os.path.exists("input.zip"): os.remove("input.zip")
            if os.path.exists("result.zip"): os.remove("result.zip")

            # Сохранение загруженного файла
            with open("input.zip", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Распаковка
            with zipfile.ZipFile("input.zip", 'r') as zip_ref:
                zip_ref.extractall(EXTRACT_FOLDER)

            # Обработка
            count = 0
            success = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_files = sum([len(files) for r, d, files in os.walk(EXTRACT_FOLDER)])
            if total_files == 0: total_files = 1

            for root, dirs, files in os.walk(EXTRACT_FOLDER):
                # Игнор папок MacOS
                if "__MACOSX" in root: continue
                
                rel_path = os.path.relpath(root, EXTRACT_FOLDER)
                target_path = os.path.join(PROCESSED_FOLDER, rel_path)
                if not os.path.exists(target_path): os.makedirs(target_path)

                for filename in files:
                    # Игнор системных файлов
                    if filename.startswith("._") or filename == ".DS_Store": continue
                    
                    src = os.path.join(root, filename)
                    dst = os.path.join(target_path, filename)
                    ext = os.path.splitext(filename)[1].lower()
                    
                    if ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
                        if unique_image(src, dst): success += 1
                    elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
                        if unique_video(src, dst): success += 1
                    else:
                        shutil.copy2(src, dst)
                    
                    count += 1
                    progress = min(count / total_files, 1.0)
                    progress_bar.progress(progress)
                    status_text.text(f"Обработано: {count} из {total_files}")

            # Архивация результата
            shutil.make_archive("result", 'zip', PROCESSED_FOLDER)
            
            st.success(f"Готово! Успешно уникализировано: {success} файлов.")
            
            # Кнопка скачивания
            with open("result.zip", "rb") as fp:
                st.download_button(
                    label="📥 Скачать готовый архив",
                    data=fp,
                    file_name="UNIQUE_CREATIVES.zip",
                    mime="application/zip"
                )
