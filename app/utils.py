from datetime import datetime
import markdown2
import re

def format_date(date_str):
    """
    Форматирование даты для отображения
    Поддерживает форматы:
    - DD.MM.YYYY
    - DD.MM (добавляется текущий год)
    - YYYY-MM-DD
    - ISO format
    """
    if not date_str:
        return None
    try:
        # Для формата DD.MM добавляем текущий год
        if re.match(r'^\d{2}\.\d{2}$', date_str):
            current_year = datetime.now().year
            date_str = f"{date_str}.{current_year}"
        
        # Пробуем разные форматы
        for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"]:
            try:
                date = datetime.strptime(date_str.split('+')[0], fmt)
                return date.strftime("%d.%m.%Y")
            except ValueError:
                continue
        return None
    except (ValueError, TypeError, AttributeError):
        return None

def format_datetime(date_str):
    """
    Форматирование даты и времени для отображения
    Поддерживает форматы:
    - DD.MM.YYYY HH:MM
    - YYYY-MM-DD HH:MM
    - ISO format
    """
    if not date_str:
        return None
    try:
        # Для ISO формата
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date.strftime("%d.%m.%Y %H:%M")
        except ValueError:
            # Для других форматов
            for fmt in ["%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
                try:
                    date = datetime.strptime(date_str, fmt)
                    return date.strftime("%d.%m.%Y %H:%M")
                except ValueError:
                    continue
            return None
    except (ValueError, TypeError, AttributeError):
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

def is_recent(post_date: str, days: int = 2) -> bool:
    """
    Проверяет, было ли объявление опубликовано за последние n дней
    """
    try:
        post_datetime = datetime.fromisoformat(post_date)
        now = datetime.now(post_datetime.tzinfo)
        return (now - post_datetime).days <= days
    except Exception:
        return False 