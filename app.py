import streamlit as st
import os
import zipfile
import shutil
import random
import subprocess
import hashlib
import uuid
import streamlit.components.v1 as components
from PIL import Image, ImageEnhance, ImageFilter

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="UniqCreatives Cloud", page_icon="⚡", layout="centered")

st.title("⚡ Быстрый Уникализатор")
st.markdown("Просто перетащите архив. Процесс начнется автоматически.")
st.caption("Поддерживает одновременную работу нескольких пользователей.")

# --- ФУНКЦИИ ОБРАБОТКИ ---
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
    except Exception:
        shutil.copy2(src, dst)
        return False

def unique_video(src, dst):
    try:
        contrast = round(random.uniform(0.97, 1.03), 2)
        saturation = round(random.uniform(0.97, 1.03), 2)
        gamma = round(random.uniform(0.97, 1.03), 2)
        volume = round(random.uniform(0.95, 1.05), 2)

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
uploaded_file = st.file_uploader("Загрузите ZIP-архив", type="zip", label_visibility="collapsed")

if uploaded_file is not None:
    # ГЕНЕРАЦИЯ УНИКАЛЬНОЙ СЕССИИ (Чтобы файлы разных юзеров не смешивались)
    session_id = str(uuid.uuid4())[:8]
    
    # Уникальные имена папок и файлов
    EXTRACT_FOLDER = f"temp_in_{session_id}"
    PROCESSED_FOLDER = f"temp_out_{session_id}"
    INPUT_ZIP = f"input_{session_id}.zip"
    RESULT_ZIP_NAME = f"result_{session_id}" # make_archive добавит .zip
    RESULT_ZIP_FILE = f"{RESULT_ZIP_NAME}.zip"

    # Очистка и создание папок
    if os.path.exists(EXTRACT_FOLDER): shutil.rmtree(EXTRACT_FOLDER)
    if os.path.exists(PROCESSED_FOLDER): shutil.rmtree(PROCESSED_FOLDER)
    os.makedirs(EXTRACT_FOLDER)
    os.makedirs(PROCESSED_FOLDER)
    
    # Сохранение архива
    with open(INPUT_ZIP, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Распаковка
    with zipfile.ZipFile(INPUT_ZIP, 'r') as zip_ref:
        zip_ref.extractall(EXTRACT_FOLDER)

    # Счетчики статистики
    stats = {
        "success": 0,
        "errors": 0,
        "skipped": 0,
        "total": 0
    }
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Подсчет общего количества файлов (ЧЕСТНЫЙ ПОДСЧЕТ)
    total_files_count = 0
    for r, d, files in os.walk(EXTRACT_FOLDER):
        if "__MACOSX" in r: continue
        for f in files:
            if not f.startswith("._") and f != ".DS_Store":
                total_files_count += 1
                
    if total_files_count == 0: total_files_count = 1

    # Основной цикл
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
            
            # Логика подсчета
            if ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
                if unique_image(src, dst):
                    stats["success"] += 1
                else:
                    stats["errors"] += 1
            elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
                if unique_video(src, dst):
                    stats["success"] += 1
                else:
                    stats["errors"] += 1
            else:
                shutil.copy2(src, dst)
                stats["skipped"] += 1
            
            progress = min(stats["total"] / total_files_count, 1.0)
            progress_bar.progress(progress)
            status_text.text(f"Обработка: {stats['total']} из {total_files_count}")

    # Архивация
    shutil.make_archive(RESULT_ZIP_NAME, 'zip', PROCESSED_FOLDER)
    
    # Очистка прогресс-бара
    progress_bar.empty()
    status_text.empty()
    
    # --- ВЫВОД ОТЧЕТА ---
    st.success("✅ Готово! Файлы обработаны.")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Успешно", stats["success"])
    col2.metric("Ошибки", stats["errors"])
    col3.metric("Пропущено", stats["skipped"])
    
    if stats["errors"] > 0:
        st.warning("⚠️ Часть файлов скопирована без изменений (ошибки формата).")
    
    # Кнопка скачивания
    with open(RESULT_ZIP_FILE, "rb") as fp:
        btn = st.download_button(
            label="📥 СКАЧАТЬ АРХИВ",
            data=fp,
            file_name="UNIQUE_CREATIVES.zip",
            mime="application/zip",
            type="primary"
        )
    
    # --- АВТО-КЛИК (JS) ---
    components.html(
        """
        <script>
        setTimeout(function() {
            const anchors = window.parent.document.getElementsByTagName('a');
            for (let i = 0; i < anchors.length; i++) {
                if (anchors[i].innerText.includes('📥 СКАЧАТЬ АРХИВ')) {
                    anchors[i].click();
                    break;
                }
            }
        }, 1000);
        </script>
        """,
        height=0
    )

    # --- ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ ---
    # Удаляем файлы после создания кнопки (данные уже в памяти кнопки)
    try:
        shutil.rmtree(EXTRACT_FOLDER)
        shutil.rmtree(PROCESSED_FOLDER)
        if os.path.exists(INPUT_ZIP): os.remove(INPUT_ZIP)
        if os.path.exists(RESULT_ZIP_FILE): os.remove(RESULT_ZIP_FILE)
    except Exception as e:
        print(f"Cleanup error: {e}")
