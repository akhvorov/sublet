from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import json
import os
import pytz
from .utils import format_date, format_datetime, format_price, format_text, is_recent

app = Flask(__name__)

# Конфигурация
LISTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'listings_enriched.json')
TIMEZONE = 'Europe/Moscow'

def load_listings():
    """
    Загрузка объявлений из JSON файла
    """
    try:
        with open(LISTINGS_FILE, 'r', encoding='utf-8') as f:
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
                        os.path.join('media', os.path.basename(path))
                        for path in listing['photo_paths']
                        if os.path.exists(os.path.join(app.static_folder, 'media', os.path.basename(path)))
                    ]
            
            return listings, last_data_update
    except Exception as e:
        app.logger.error(f"Error loading listings: {e}")
        return [], None

def filter_listings(listings, listing_type=None, city=None, dates=None):
    """
    Фильтрация объявлений по параметрам
    """
    filtered = listings

    # Фильтр по типу
    if listing_type:
        filtered = [l for l in filtered if l.get('type') == listing_type]

    # Фильтр по городу
    if city:
        filtered = [l for l in filtered if l.get('city') == city]

    # Фильтр по датам
    if dates:
        try:
            start_date, end_date = dates.split(' - ')
            start = datetime.strptime(start_date, "%d.%m.%Y")
            end = datetime.strptime(end_date, "%d.%m.%Y")
            
            def has_overlap(listing):
                if not listing.get('rental_start') or not listing.get('rental_end'):
                    return True
                listing_start = datetime.strptime(listing['rental_start'], "%d.%m.%Y")
                listing_end = datetime.strptime(listing['rental_end'], "%d.%m.%Y")
                return listing_start <= end and listing_end >= start
            
            filtered = [l for l in filtered if has_overlap(l)]
        except Exception:
            pass

    return filtered

def sort_listings(listings, sort_order='date-desc', selected_dates=None):
    """
    Сортировка объявлений
    """
    if sort_order == 'date-asc':
        return sorted(listings, key=lambda x: x['date'])
    elif sort_order == 'price-asc':
        return sorted(listings, key=lambda x: float(x.get('price_eur', float('inf'))))
    elif sort_order == 'date-match' and selected_dates:
        try:
            start_date, end_date = selected_dates.split(' - ')
            selected_start = datetime.strptime(start_date, "%d.%m.%Y")
            selected_end = datetime.strptime(end_date, "%d.%m.%Y")
            
            def get_overlap_score(listing):
                if not listing.get('rental_start') or not listing.get('rental_end'):
                    return -1
                listing_start = datetime.strptime(listing['rental_start'], "%d.%m.%Y")
                listing_end = datetime.strptime(listing['rental_end'], "%d.%m.%Y")
                
                overlap_start = max(selected_start, listing_start)
                overlap_end = min(selected_end, listing_end)
                
                if overlap_end < overlap_start:
                    return 0
                
                overlap_days = (overlap_end - overlap_start).days + 1
                return overlap_days
            
            return sorted(listings, key=get_overlap_score, reverse=True)
        except Exception:
            return listings
    else:  # date-desc по умолчанию
        return sorted(listings, key=lambda x: x['date'], reverse=True)

@app.template_filter('format_date')
def format_date_filter(value):
    return format_date(value)

@app.template_filter('format_datetime')
def format_datetime_filter(value):
    return format_datetime(value)

@app.template_filter('format_price')
def format_price_filter(value):
    return format_price(value)

@app.template_filter('format_text')
def format_text_filter(value):
    return format_text(value)

@app.route('/')
def index():
    """
    Редирект на страницу с объявлениями о сдаче квартир
    """
    return redirect(url_for('listings', listing_type='renting_out'))

@app.route('/listings/<listing_type>')
def listings(listing_type):
    """
    Страница со списком объявлений определенного типа
    """
    # Загружаем все объявления
    all_listings, last_data_update = load_listings()
    
    # Получаем параметры фильтрации
    city = request.args.get('city')
    dates = request.args.get('dates')
    sort_order = request.args.get('sort', 'date-desc')
    
    # Фильтруем объявления
    filtered_listings = filter_listings(all_listings, listing_type, city, dates)
    
    # Сортируем объявления
    sorted_listings = sort_listings(filtered_listings, sort_order, dates)
    
    # Собираем список городов для фильтра
    cities = sorted(set(l['city'] for l in all_listings if l.get('city')))
    
    # Получаем текущее время
    now = datetime.now(pytz.timezone(TIMEZONE))
    
    return render_template(
        'listings.html',
        listings=sorted_listings,
        listing_type=listing_type,
        active_tab=listing_type,
        cities=cities,
        selected_city=city,
        selected_dates=dates,
        sort_order=sort_order,
        last_updated=now.strftime("%d.%m.%Y %H:%M"),
        last_data_update=format_datetime(last_data_update)
    )

@app.route('/listing/<listing_id>')
def listing_details(listing_id):
    """
    Страница с детальной информацией об объявлении
    """
    # Загружаем все объявления
    all_listings, last_data_update = load_listings()
    
    # Ищем нужное объявление
    listing = next((l for l in all_listings if str(l['id']) == str(listing_id)), None)
    
    if not listing:
        return redirect(url_for('index'))
    
    # Получаем текущее время
    now = datetime.now(pytz.timezone(TIMEZONE))
    
    return render_template(
        'listing_details.html',
        listing=listing,
        active_tab=listing.get('type'),
        last_updated=now.strftime("%d.%m.%Y %H:%M"),
        last_data_update=format_datetime(last_data_update)
    )

if __name__ == '__main__':
    app.run(debug=True) 