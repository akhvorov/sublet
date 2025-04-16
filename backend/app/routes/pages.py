from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
from datetime import datetime
import pytz
from ..config import TIMEZONE, TEMPLATES_DIR, TELEGRAM_BOT_USERNAME
from ..utils.listings import load_listings
from ..utils.auth import verify_token
import markdown2
import logging

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
logger = logging.getLogger(__name__)

def format_date(date_str):
    """Форматирование даты для отображения"""
    if not date_str:
        return None
    try:
        # Пробуем разные форматы даты
        for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%d.%m.%Y"]:
            try:
                if fmt == "%d.%m.%Y":
                    date = datetime.strptime(date_str, fmt)
                    date = pytz.timezone(TIMEZONE).localize(date)
                else:
                    date = datetime.strptime(date_str.replace('Z', '+0000'), fmt)
                    date = date.astimezone(pytz.timezone(TIMEZONE))
                return date.strftime("%d.%m.%Y")
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return date_str
    except Exception as e:
        logger.error(f"Error formatting date {date_str}: {e}")
        return date_str

def format_datetime(date_str):
    """Форматирование даты и времени для отображения"""
    if not date_str:
        return None
    try:
        # Пробуем разные форматы даты и времени
        for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"]:
            try:
                date = datetime.strptime(date_str.replace('Z', '+0000'), fmt)
                date = date.astimezone(pytz.timezone(TIMEZONE))
                return date.strftime("%d.%m.%Y %H:%M")
            except ValueError:
                continue
        
        logger.warning(f"Could not parse datetime: {date_str}")
        return date_str
    except Exception as e:
        logger.error(f"Error formatting datetime {date_str}: {e}")
        return date_str

def format_price(price):
    """Форматирование цены для отображения"""
    if not price:
        return None
    try:
        return f"{int(price):,}€".replace(",", " ")
    except (ValueError, TypeError):
        return None

def format_text(text):
    """Форматирование текста с поддержкой Markdown"""
    if not text:
        return ""
    # Заменяем <br> на переносы строк
    text = text.replace('<br>', '\n')
    return markdown2.markdown(text, extras=['break-on-newline'])

# Добавляем фильтры в окружение Jinja2
templates.env.filters["format_date"] = format_date
templates.env.filters["format_datetime"] = format_datetime
templates.env.filters["format_price"] = format_price
templates.env.filters["format_text"] = format_text

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Редирект на страницу с объявлениями о сдаче"""
    return RedirectResponse(url="/renting")

@router.get("/auth", response_class=HTMLResponse)
async def auth(request: Request):
    """Страница авторизации"""
    return templates.TemplateResponse(
        "auth.html",
        {
            "request": request,
            "root_path": "/static/",
            "bot_username": TELEGRAM_BOT_USERNAME
        }
    )

@router.get("/renting", response_class=HTMLResponse)
async def renting(request: Request, token_data = Depends(verify_token)):
    """Страница с объявлениями о сдаче"""
    listings_by_type, last_data_update, _ = load_listings()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "page_type": "renting_out",
            "listings": listings_by_type.get("renting_out", []),
            "last_updated": datetime.now(pytz.timezone(TIMEZONE)).strftime("%d.%m.%Y %H:%M"),
            "last_data_update": last_data_update,
            "root_path": "/static/"
        }
    )

@router.get("/looking", response_class=HTMLResponse)
async def looking(request: Request, token_data = Depends(verify_token)):
    """Страница с объявлениями о поиске"""
    listings_by_type, last_data_update, _ = load_listings()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "page_type": "looking_for",
            "listings": listings_by_type.get("looking_for", []),
            "last_updated": datetime.now(pytz.timezone(TIMEZONE)).strftime("%d.%m.%Y %H:%M"),
            "last_data_update": last_data_update,
            "root_path": "/static/"
        }
    )

@router.get("/exchange", response_class=HTMLResponse)
async def exchange(request: Request, token_data = Depends(verify_token)):
    """Страница с объявлениями об обмене"""
    listings_by_type, last_data_update, _ = load_listings()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "page_type": "exchange",
            "listings": listings_by_type.get("exchange", []),
            "last_updated": datetime.now(pytz.timezone(TIMEZONE)).strftime("%d.%m.%Y %H:%M"),
            "last_data_update": last_data_update,
            "root_path": "/static/"
        }
    )

@router.get("/listings/{listing_id}", response_class=HTMLResponse)
async def listing(request: Request, listing_id: int, token_data = Depends(verify_token)):
    """Страница отдельного объявления"""
    _, last_data_update, all_listings = load_listings()
    
    # Находим нужное объявление
    listing_data = next(
        (l for l in all_listings if l["id"] == listing_id),
        None
    )
    
    if not listing_data:
        return templates.TemplateResponse(
            "404.html",
            {
                "request": request,
                "root_path": "/static/"
            },
            status_code=404
        )
    
    return templates.TemplateResponse(
        "listing.html",
        {
            "request": request,
            "listing": listing_data,
            "last_updated": datetime.now(pytz.timezone(TIMEZONE)).strftime("%d.%m.%Y %H:%M"),
            "last_data_update": last_data_update,
            "root_path": "/static/"
        }
    ) 