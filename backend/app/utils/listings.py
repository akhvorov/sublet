"""
Утилиты для работы с объявлениями
"""

import json
import os
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Tuple, Any

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

def load_listings() -> Tuple[Dict[str, List[Dict[str, Any]]], str, List[Dict[str, Any]]]:
    """
    Загружает объявления из JSON файла
    
    Returns:
        Tuple[Dict[str, List[Dict]], str, List[Dict]]:
            - Словарь объявлений по типам
            - Время последнего обновления
            - Список всех объявлений
    """
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data')
    listings_file = os.path.join(data_dir, 'listings_enriched.json')
    
    try:
        with open(listings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Получаем время последнего обновления данных
            last_data_update = data.get('processed_at', None)
            
            # Сортируем по дате, новые сверху
            listings = sorted(
                data.get('listings', []),
                key=lambda x: x['date'],
                reverse=True
            )
            
            # Помечаем новые объявления и обновляем пути к фото
            for listing in listings:
                listing['is_new'] = is_recent(listing['date'])
                if listing.get('photo_paths'):
                    listing['photo_paths'] = [
                        f"media/{os.path.basename(path)}" 
                        for path in listing['photo_paths']
                    ]
            
            # Группируем объявления по типу
            listings_by_type = {
                'renting_out': [l for l in listings if l.get('type') == 'renting_out'],
                'looking_for': [l for l in listings if l.get('type') == 'looking_for'],
                'exchange': [l for l in listings if l.get('type') == 'exchange']
            }
            
            return listings_by_type, last_data_update, listings
    except Exception as e:
        print(f"Error loading listings: {e}")
        return {}, None, [] 