"""
Configuration file for the sublet project
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram configuration
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_PHONE = os.getenv('TELEGRAM_PHONE')
TELEGRAM_CHAT_NAME = os.getenv('TELEGRAM_CHAT_NAME')

# OpenAI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Data storage configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
LISTINGS_FILE = os.path.join(DATA_DIR, 'listings.json')
LISTINGS_ENRICHED_FILE = os.path.join(DATA_DIR, 'listings_enriched.json')
SESSION_FILE = os.path.join(DATA_DIR, 'telegram_session')
MEDIA_DIR = os.path.join(DATA_DIR, 'media')  # Директория для хранения медиафайлов

# Website configuration
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'templates')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs')  # GitHub Pages uses /docs by default

# Time configuration
TIMEZONE = 'Europe/Berlin'  # Центральноевропейское время 
