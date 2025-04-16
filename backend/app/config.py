"""
Configuration file for the backend
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "templates")
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
DATA_DIR = os.path.join(BASE_DIR.parent, "data")  # Директория с данными находится в корне проекта

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME")

# Auth settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Redis settings
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
VERIFICATION_CODE_TTL = 300  # 5 minutes in seconds

# Time configuration
TIMEZONE = 'Europe/Berlin'  # Центральноевропейское время (Берлин, не меняй это)