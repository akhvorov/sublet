#!/usr/bin/env python3
"""
Скрипт для обогащения данных объявлений дополнительной информацией
"""

import json
import logging
import sys
import os
from datetime import datetime, timedelta
import pytz
from openai import OpenAI
from typing import Dict, Any, List, Set
from enum import Enum

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import LISTINGS_FILE, TIMEZONE, OPENAI_API_KEY

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ListingType(str, Enum):
    RENTING_OUT = "renting_out"  # Сдает квартиру
    LOOKING_FOR = "looking_for"  # Ищет квартиру
    EXCHANGE = "exchange"        # Обмен квартирами
    NOT_LISTING = "not_listing"  # Не объявление

# Установка API ключа в переменную окружения
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Инициализация OpenAI клиента
try:
    client = OpenAI()
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    raise

SYSTEM_PROMPT = """
You are a helpful assistant that extracts structured information from rental listings.
Your task is to extract the following information:
- City where the property is located (ALWAYS translate to Russian, e.g., "Berlin" -> "Берлин", "Munich" -> "Мюнхен")
- Country where the property is located (ALWAYS translate to Russian, e.g., "Germany" -> "Германия", "France" -> "Франция")
- All rental periods mentioned in the text (only day and month, no year)
- Price per day in EUR
- Type of listing

The text may be in English or Russian. Always respond in the following JSON format:
{
    "city": string or null (in Russian),
    "country": string or null (in Russian),
    "date_ranges": [
        {
            "start_date": "DD.MM" or "MM",
            "end_date": "DD.MM" or "MM"
        }
    ],
    "price_eur": number or null,
    "type": "renting_out" | "looking_for" | "exchange" | "not_listing"
}

For the type field:
- "renting_out" - Person is offering their apartment for rent
- "looking_for" - Person is looking for an apartment to rent
- "exchange" - Person wants to exchange apartments
- "not_listing" - Message is not a rental listing

If any information is not found in the text, use null for that field.
For dates:
- Extract only day and month, DO NOT include year
- If only month is mentioned (e.g., "from March"), use "MM" format
- If day is mentioned, use "DD.MM" format
- Extract ALL date ranges mentioned in the text, even if there are multiple
For prices, convert any mentioned price to EUR using approximate conversion rates if needed.
"""

def get_full_date(date_str: str, is_start: bool = True) -> str:
    """
    Преобразует дату в формате MM в полный диапазон дат месяца
    """
    if len(date_str) == 2:  # Формат MM
        if is_start:
            return f"01.{date_str}"
        else:
            # Определяем последний день месяца
            month = int(date_str)
            if month in [4, 6, 9, 11]:
                return f"30.{date_str}"
            elif month == 2:
                return f"28.{date_str}"  # Упрощенно берем 28 для февраля
            else:
                return f"31.{date_str}"
    return date_str

def is_recent(post_date: str, days: int = 2) -> bool:
    """
    Проверяет, было ли объявление опубликовано за последние n дней
    """
    try:
        post_datetime = datetime.fromisoformat(post_date)
        now = datetime.now(post_datetime.tzinfo)
        return (now - post_datetime) <= timedelta(days=days)
    except Exception:
        return False

def extract_info_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Извлекает структурированную информацию из текста объявления используя OpenAI API
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        # Извлекаем JSON из ответа
        result = json.loads(response.choices[0].message.content)
        
        # Создаем отдельное объявление для каждого диапазона дат
        listings = []
        date_ranges = result.get('date_ranges', [])
        
        # Если нет диапазонов дат, создаем одно объявление
        if not date_ranges:
            return [{
                'city': result.get('city'),
                'country': result.get('country'),
                'rental_start': None,
                'rental_end': None,
                'price_eur': result.get('price_eur'),
                'type': result.get('type', 'not_listing')
            }]
        
        # Создаем объявление для каждого диапазона дат
        for date_range in date_ranges:
            start_date = date_range.get('start_date')
            end_date = date_range.get('end_date')
            
            # Преобразуем даты месяцев в полные диапазоны
            if start_date:
                start_date = get_full_date(start_date, is_start=True)
            if end_date:
                end_date = get_full_date(end_date, is_start=False)

            listings.append({
                'city': result.get('city'),
                'country': result.get('country'),
                'rental_start': start_date,
                'rental_end': end_date,
                'price_eur': result.get('price_eur'),
                'type': result.get('type', 'not_listing')
            })
        
        return listings
        
    except Exception as e:
        logger.error(f"Error extracting info from text: {e}")
        return [{
            'city': None,
            'country': None,
            'rental_start': None,
            'rental_end': None,
            'price_eur': None,
            'type': 'not_listing'
        }]

def enrich_listing(listing: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Обогащает одно объявление дополнительной информацией
    """
    text = listing.get('text', '')
    
    # Извлекаем информацию через LLM
    extracted_infos = extract_info_from_text(text)
    
    # Обогащаем каждый вариант объявления
    enriched_listings = []
    for info in extracted_infos:
        enriched = listing.copy()
        enriched.update(info)
        enriched['enriched_at'] = datetime.now(pytz.timezone(TIMEZONE)).isoformat()
        enriched_listings.append(enriched)
    
    return enriched_listings

# Путь к файлу с архивными объявлениями
LISTINGS_ARCHIVE_FILE = os.path.join(os.path.dirname(LISTINGS_FILE), 'listings_archive.json')

def load_json_file(filepath: str, default: Dict = None) -> Dict:
    """
    Загружает JSON файл или возвращает значение по умолчанию
    """
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
    return default or {"listings": [], "processed_at": None}

def save_json_file(filepath: str, data: Dict):
    """
    Сохраняет данные в JSON файл
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def is_listing_expired(listing: Dict[str, Any]) -> bool:
    """
    Проверяет, истек ли срок актуальности объявления
    """
    try:
        # Если нет даты окончания, считаем актуальным
        if not listing.get('rental_end'):
            return False
            
        # Парсим дату окончания
        end_date = datetime.strptime(listing['rental_end'], "%d.%m.%Y")
        current_date = datetime.now(pytz.timezone(TIMEZONE)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).astimezone(pytz.UTC)
        
        return end_date.replace(tzinfo=pytz.UTC) < current_date
    except Exception:
        return False

def get_processed_listings() -> Set[int]:
    """
    Получает множество ID уже обработанных объявлений
    """
    processed_ids = set()
    
    # Загружаем актуальные обработанные объявления
    enriched_data = load_json_file(os.path.join(os.path.dirname(LISTINGS_FILE), 'listings_enriched.json'))
    processed_ids.update(listing['id'] for listing in enriched_data['listings'])
    
    # Загружаем архивные объявления
    archive_data = load_json_file(LISTINGS_ARCHIVE_FILE)
    processed_ids.update(listing['id'] for listing in archive_data['listings'])
    
    return processed_ids

def process_data():
    """
    Основная функция для обработки данных
    """
    try:
        # Проверяем наличие API ключа
        if not os.getenv('OPENAI_API_KEY'):
            logger.error("OpenAI API key not found in environment variables")
            return
            
        # Загружаем все необходимые данные
        raw_data = load_json_file(LISTINGS_FILE)
        enriched_data = load_json_file(os.path.join(os.path.dirname(LISTINGS_FILE), 'listings_enriched.json'))
        archive_data = load_json_file(LISTINGS_ARCHIVE_FILE)
        
        # Получаем множество уже обработанных ID
        processed_ids = get_processed_listings()
        
        # Находим новые объявления для обработки
        new_listings = [
            listing for listing in raw_data.get('listings', [])
            if listing['id'] not in processed_ids
        ]
        
        logger.info(f"Found {len(new_listings)} new listings to process")
        
        # Обогащаем новые объявления
        newly_enriched = []
        for i, listing in enumerate(new_listings, 1):
            try:
                enriched = enrich_listing(listing)
                newly_enriched.extend(enriched)
                if i % 10 == 0:
                    logger.info(f"Processed {i}/{len(new_listings)} new listings")
            except Exception as e:
                logger.error(f"Error processing listing {listing.get('id')}: {e}")
        
        # Обновляем списки актуальных и архивных объявлений
        current_time = datetime.now(pytz.timezone(TIMEZONE))
        
        # Обрабатываем существующие обогащенные объявления
        existing_enriched = enriched_data.get('listings', [])
        
        # Разделяем объявления на актуальные и архивные
        active_listings = []
        archived_listings = []
        
        # Обрабатываем существующие объявления
        for listing in existing_enriched:
            if is_listing_expired(listing):
                archived_listings.append(listing)
            else:
                active_listings.append(listing)
        
        # Добавляем новые объявления
        for listing in newly_enriched:
            if is_listing_expired(listing):
                archived_listings.append(listing)
            else:
                active_listings.append(listing)
        
        # Формируем финальные данные
        final_enriched_data = {
            'listings': active_listings,
            'processed_at': current_time.isoformat()
        }
        
        final_archive_data = {
            'listings': archived_listings + archive_data.get('listings', []),
            'updated_at': current_time.isoformat()
        }
        
        # Сохраняем результаты
        save_json_file(os.path.join(os.path.dirname(LISTINGS_FILE), 'listings_enriched.json'), final_enriched_data)
        save_json_file(LISTINGS_ARCHIVE_FILE, final_archive_data)
        
        logger.info(f"Saved {len(active_listings)} active listings")
        logger.info(f"Archived {len(archived_listings)} expired listings")
        logger.info(f"Total archive size: {len(final_archive_data['listings'])} listings")
        
    except Exception as e:
        logger.error(f"Error processing data: {e}")

if __name__ == "__main__":
    process_data() 