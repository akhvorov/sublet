from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routes import auth, pages, api
from .utils.telegram import setup_bot, stop_bot
from .config import STATIC_DIR, DATA_DIR
import os
import shutil
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sublet Backend",
    description="Backend API for Sublet project",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sync_media_files():
    """
    Синхронизация медиафайлов между data/media и static/media.
    В отличие от простого копирования, эта функция:
    1. Копирует только новые файлы
    2. Удаляет файлы, которых больше нет в источнике
    3. Обновляет измененные файлы
    """
    try:
        # Определяем пути
        source_dir = os.path.join(DATA_DIR, 'media')
        target_dir = os.path.join(STATIC_DIR, 'media')
        
        logger.info(f"Syncing media files from {source_dir} to {target_dir}")

        # Создаем директории, если их нет
        os.makedirs(source_dir, exist_ok=True)
        os.makedirs(target_dir, exist_ok=True)

        # Получаем списки файлов
        source_files = {f for f in os.listdir(source_dir) if f.endswith('.jpg')}
        target_files = {f for f in os.listdir(target_dir) if f.endswith('.jpg')}

        # Копируем новые и обновляем измененные файлы
        for file in source_files:
            src = os.path.join(source_dir, file)
            dst = os.path.join(target_dir, file)
            
            # Если файл новый или изменился
            if file not in target_files or \
               os.path.getmtime(src) > os.path.getmtime(dst):
                try:
                    shutil.copy2(src, dst)
                    logger.info(f"Copied/updated file: {file}")
                except Exception as e:
                    logger.error(f"Error copying {file}: {e}")

        # Удаляем файлы, которых больше нет в источнике
        for file in target_files - source_files:
            try:
                os.remove(os.path.join(target_dir, file))
                logger.info(f"Removed obsolete file: {file}")
            except Exception as e:
                logger.error(f"Error removing {file}: {e}")

    except Exception as e:
        logger.error(f"Error in sync_media_files: {e}")

# Синхронизируем медиафайлы при запуске
sync_media_files()

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Подключаем роуты
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(api.router, prefix="/api/v1", tags=["api"])
app.include_router(pages.router, tags=["pages"])

@app.on_event("startup")
async def startup_event():
    """Запускаем бота при старте приложения"""
    await setup_bot()

@app.on_event("shutdown")
async def shutdown_event():
    """Останавливаем бота при завершении работы приложения"""
    await stop_bot()

@app.get("/")
async def root():
    return {
        "message": "Welcome to Sublet Backend API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    } 