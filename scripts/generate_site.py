#!/usr/bin/env python3
"""
Скрипт для генерации статического сайта
"""

import json
import os
import shutil
from datetime import datetime, timedelta
import pytz
from jinja2 import Environment, FileSystemLoader, select_autoescape
import markdown2
import sys
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import (
    LISTINGS_ENRICHED_FILE,
    TEMPLATES_DIR,
    OUTPUT_DIR,
    TIMEZONE,
    MEDIA_DIR
)

def format_date(date_str):
    """
    Форматирование даты для отображения
    """
    if not date_str:
        return None
    try:
        date = datetime.strptime(date_str, "%d.%m.%Y")
        return date.strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return None

def format_datetime(date_str):
    """
    Форматирование даты и времени для отображения
    """
    if not date_str:
        return None
    try:
        date = datetime.fromisoformat(date_str)
        return date.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        return None

def format_price(price):
    """
    Форматирование цены для отображения
    """
    if not price:
        return None
    try:
        return f"{int(price):,}€".replace(",", " ")
    except (ValueError, TypeError):
        return None

def format_text(text):
    """
    Форматирование текста с поддержкой Markdown
    """
    if not text:
        return ""
    
    # Заменяем <br> на переносы строк
    text = text.replace('<br>', '\n')
    
    # Защищаем хэштеги от обработки как заголовков
    text = re.sub(r'(#\w+)', lambda m: '\\' + m.group(1), text)
    
    # Конвертируем Markdown в HTML
    html = markdown2.markdown(text, extras=['break-on-newline'])
    
    # Восстанавливаем хэштеги (убираем обратный слеш)
    html = re.sub(r'\\(#\w+)', r'\1', html)
    
    return html

def adjust_rental_dates(listing):
    """
    Корректирует даты аренды относительно даты публикации объявления
    """
    if not listing.get('date'):
        return listing

    post_date = datetime.fromisoformat(listing['date'])
    post_year = post_date.year
    post_month = post_date.month

    # Обрабатываем дату начала аренды
    if listing.get('rental_start'):
        try:
            # Проверяем формат даты
            if '.' in listing['rental_start']:
                parts = listing['rental_start'].split('.')
                if len(parts) == 2:  # Формат DD.MM
                    day, month = parts
                    rental_start = datetime(post_year, int(month), int(day))
                    
                    # Если месяц аренды меньше месяца публикации, значит это следующий год
                    if int(month) < post_month:
                        rental_start = rental_start.replace(year=post_year + 1)
                    
                    listing['rental_start'] = rental_start.strftime("%d.%m.%Y")
                elif len(parts) == 3:  # Формат DD.MM.YYYY
                    listing['rental_start'] = listing['rental_start']  # Оставляем как есть
            
        except (ValueError, TypeError):
            listing['rental_start'] = None

    # Обрабатываем дату окончания аренды
    if listing.get('rental_end'):
        try:
            # Проверяем формат даты
            if '.' in listing['rental_end']:
                parts = listing['rental_end'].split('.')
                if len(parts) == 2:  # Формат DD.MM
                    day, month = parts
                    rental_end = datetime(post_year, int(month), int(day))
                    
                    # Если есть дата начала и дата конца меньше даты начала, значит это следующий год
                    if listing.get('rental_start'):
                        rental_start_date = datetime.strptime(listing['rental_start'], "%d.%m.%Y")
                        if rental_end < rental_start_date:
                            rental_end = rental_end.replace(year=rental_end.year + 1)
                    # Если нет даты начала, но месяц меньше месяца публикации
                    elif int(month) < post_month:
                        rental_end = rental_end.replace(year=post_year + 1)
                    
                    listing['rental_end'] = rental_end.strftime("%d.%m.%Y")
                elif len(parts) == 3:  # Формат DD.MM.YYYY
                    listing['rental_end'] = listing['rental_end']  # Оставляем как есть
            
        except (ValueError, TypeError):
            listing['rental_end'] = None

    return listing

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

def load_listings():
    """
    Загрузка объявлений из JSON файла
    """
    try:
        with open(LISTINGS_ENRICHED_FILE, 'r', encoding='utf-8') as f:
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
                # Корректируем даты аренды
                listing = adjust_rental_dates(listing)
            
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

def ensure_output_directory():
    """
    Подготовка директории для генерации сайта
    """
    # Создаем директорию, если её нет
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Создаем директорию для CSS
    css_dir = os.path.join(OUTPUT_DIR, 'css')
    os.makedirs(css_dir, exist_ok=True)
    
    # Создаем директорию для медиафайлов
    media_output_dir = os.path.join(OUTPUT_DIR, 'media')
    os.makedirs(media_output_dir, exist_ok=True)
    
    # Создаем директорию для страниц объявлений
    listings_dir = os.path.join(OUTPUT_DIR, 'listings')
    os.makedirs(listings_dir, exist_ok=True)
    
    # Путь к исходному CSS файлу в директории проекта
    css_source = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'css', 'styles.css')
    css_dest = os.path.join(css_dir, 'styles.css')
    
    # Копируем CSS файл
    if os.path.exists(css_source):
        shutil.copy2(css_source, css_dest)
    else:
        print(f"CSS файл не найден: {css_source}")

    # Копируем страницу авторизации
    auth_source = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'templates', 'auth.html')
    auth_dest = os.path.join(OUTPUT_DIR, 'auth.html')
    if os.path.exists(auth_source):
        shutil.copy2(auth_source, auth_dest)
    else:
        print(f"Страница авторизации не найдена: {auth_source}")

    # Копируем медиафайлы
    if os.path.exists(MEDIA_DIR):
        for file in os.listdir(MEDIA_DIR):
            if file.endswith('.jpg'):
                src = os.path.join(MEDIA_DIR, file)
                dst = os.path.join(media_output_dir, file)
                shutil.copy2(src, dst)

def generate_page(env, template, listings, last_updated, last_data_update, page_type, output_file):
    """
    Генерация отдельной страницы сайта
    """
    html = template.render(
        listings=listings,
        last_updated=last_updated,
        last_data_update=last_data_update,
        page_type=page_type,
        root_path=""  # Для главных страниц путь к корню - текущая директория
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

def generate_listing_page(env, listing, last_updated, last_data_update, output_file):
    """
    Генерация страницы отдельного объявления
    """
    template = env.get_template('listing.html')
    html = template.render(
        listing=listing,
        last_updated=last_updated,
        last_data_update=last_data_update,
        root_path="../"  # Для страниц листингов нужно подняться на уровень выше
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

def generate_site():
    """
    Генерация статического сайта
    """
    # Настраиваем окружение Jinja2
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    # Добавляем фильтры для форматирования
    env.filters['format_date'] = format_date
    env.filters['format_datetime'] = format_datetime
    env.filters['format_price'] = format_price
    env.filters['format_text'] = format_text
    env.filters['nl2br'] = lambda text: text.replace('\n', '<br>')
    
    # Загружаем шаблон
    template = env.get_template('index.html')
    
    # Загружаем объявления и время последнего обновления данных
    listings_by_type, last_data_update, all_listings = load_listings()
    
    # Подготавливаем директорию
    ensure_output_directory()
    
    # Получаем текущее время в нужном часовом поясе
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    formatted_now = now.strftime("%d.%m.%Y %H:%M")
    
    # Форматируем время последнего обновления данных
    if last_data_update:
        try:
            last_data_update = datetime.fromisoformat(last_data_update)
            last_data_update = last_data_update.strftime("%d.%m.%Y %H:%M")
        except (ValueError, TypeError):
            last_data_update = None

    # Генерируем страницы для каждого типа
    pages = {
        'renting_out': ('renting.html', 'Сдают квартиру'),
        'looking_for': ('looking.html', 'Ищут квартиру'),
        'exchange': ('exchange.html', 'Обмен квартирами')
    }

    for listing_type, (filename, title) in pages.items():
        output_file = os.path.join(OUTPUT_DIR, filename)
        generate_page(
            env=env,
            template=template,
            listings=listings_by_type.get(listing_type, []),
            last_updated=formatted_now,
            last_data_update=last_data_update,
            page_type=listing_type,
            output_file=output_file
        )

    # Генерируем страницы для каждого объявления
    listings_dir = os.path.join(OUTPUT_DIR, 'listings')
    for listing in all_listings:
        if listing.get('type') != 'not_listing':
            output_file = os.path.join(listings_dir, f"{listing['id']}.html")
            generate_listing_page(
                env=env,
                listing=listing,
                last_updated=formatted_now,
                last_data_update=last_data_update,
                output_file=output_file
            )

    # Создаем редирект с index.html на renting.html
    index_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url=renting.html">
    </head>
    <body>
        <p>Перенаправление на <a href="renting.html">страницу объявлений</a>...</p>
    </body>
    </html>
    """
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    print(f"Site generated successfully!")
    for listing_type, listings in listings_by_type.items():
        print(f"- {listing_type}: {len(listings)} listings")

if __name__ == "__main__":
    generate_site()
