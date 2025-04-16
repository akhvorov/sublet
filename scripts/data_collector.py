#!/usr/bin/env python3
"""
Скрипт для сбора данных из Telegram чата через пользовательский аккаунт
"""

import json
import logging
from datetime import datetime, timedelta
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import PeerChannel, MessageMediaPhoto
import pytz
import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_PHONE,
    TELEGRAM_CHAT_NAME,
    LISTINGS_FILE,
    SESSION_FILE,
    TIMEZONE,
    MEDIA_DIR
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_existing_data():
    """
    Загрузка существующих данных из файла
    """
    try:
        if os.path.exists(LISTINGS_FILE):
            with open(LISTINGS_FILE, 'r') as f:
                return json.load(f)
        return {"listings": []}
    except Exception as e:
        logger.error(f"Error loading existing data: {e}")
        return {"listings": []}

def save_data(data):
    """
    Сохранение данных в JSON файл
    """
    os.makedirs(os.path.dirname(LISTINGS_FILE), exist_ok=True)
    with open(LISTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

async def get_media_group(client, message):
    """
    Получение всех сообщений из группы медиа
    """
    if not message.grouped_id:
        return [message]
    
    try:
        # Получаем все сообщения из группы
        messages = await client.get_messages(
            message.peer_id,
            ids=[m for m in range(message.id - 10, message.id + 11)]  # Берем диапазон ±10 сообщений
        )
        # Фильтруем сообщения из той же группы
        group_messages = [m for m in messages if m and m.grouped_id == message.grouped_id]
        # Сортируем по ID
        return sorted(group_messages, key=lambda m: m.id)
    except Exception as e:
        logger.error(f"Error getting media group for message {message.id}: {e}")
        return [message]

async def download_photos(client, message, message_id):
    """
    Скачивание всех фотографий из сообщения
    """
    try:
        photo_paths = []
        
        # Создаем директорию для медиа, если её нет
        os.makedirs(MEDIA_DIR, exist_ok=True)

        # Получаем все медиа из сообщения
        message_media = await get_media_group(client, message)
        
        for i, media_message in enumerate(message_media):
            if not media_message or not media_message.media or not isinstance(media_message.media, MessageMediaPhoto):
                continue

            # Генерируем имя файла на основе ID сообщения и порядкового номера фото
            photo_filename = f"photo_{message_id}_{i+1}.jpg"
            photo_path = os.path.join(MEDIA_DIR, photo_filename)

            # Если файл уже существует, добавляем его путь
            if os.path.exists(photo_path):
                rel_path = os.path.relpath(photo_path, os.path.dirname(os.path.dirname(__file__)))
                photo_paths.append(rel_path)
                continue

            # Скачиваем фото
            await client.download_media(media_message.media, photo_path)
            rel_path = os.path.relpath(photo_path, os.path.dirname(os.path.dirname(__file__)))
            photo_paths.append(rel_path)
            logger.info(f"Downloaded photo {i+1} for message {message_id}")

        return photo_paths if photo_paths else None

    except Exception as e:
        logger.error(f"Error downloading photos from message {message_id}: {e}")
        return None

async def collect_messages(client, chat, since_date):
    """
    Сбор сообщений из Telegram чата
    """
    messages = []
    processed_count = 0
    batch_size = 100  # Размер пакета сообщений для обработки
    processed_groups = set()  # Множество для отслеживания обработанных групп
    
    try:
        async for message in client.iter_messages(chat, limit=None):
            message_date = message.date.astimezone(pytz.timezone(TIMEZONE))
            if message_date < since_date:
                break
            
            # Пропускаем сообщения без текста, если они часть группы медиа
            if not message.text and message.grouped_id and message.grouped_id in processed_groups:
                continue
            
            # Пропускаем пустые сообщения без медиа
            if not message.text and not message.media:
                continue

            # Если у сообщения нет текста, но есть медиа и оно в группе,
            # пропускаем его, так как это, вероятно, дополнительные фото к другому сообщению
            if not message.text and message.media and message.grouped_id:
                continue
            
            if message.text or (message.media and isinstance(message.media, MessageMediaPhoto)):
                # Создаем ссылку на сообщение
                message_link = f"https://t.me/c/{str(chat.channel_id)}/{message.id}"

                try:
                    # Скачиваем фото, если они есть
                    photo_paths = await download_photos(client, message, message.id) if message.media else None

                    messages.append({
                        "id": message.id,
                        "text": message.text or "",
                        "date": message_date.isoformat(),
                        "from_user": message.sender.username if message.sender else None,
                        "media": bool(message.media),
                        "photo_paths": photo_paths,
                        "link": message_link
                    })
                    
                    if photo_paths:
                        logger.info(f"Downloaded {len(photo_paths)} photos for message {message.id}")

                    # Если это групповое сообщение, помечаем группу как обработанную
                    if message.grouped_id:
                        processed_groups.add(message.grouped_id)

                    processed_count += 1
                    if processed_count % batch_size == 0:
                        logger.info(f"Processed {processed_count} messages")

                except FloodWaitError as e:
                    logger.warning(f"Hit rate limit, waiting {e.seconds} seconds")
                    await asyncio.sleep(e.seconds)
                    continue

    except Exception as e:
        logger.error(f"Error collecting messages: {e}")
    
    logger.info(f"Total messages processed: {processed_count}")
    return messages

async def main():
    """
    Основная функция для сбора данных
    """
    parser = argparse.ArgumentParser(description='Сбор данных из Telegram чата')
    parser.add_argument('--days', type=int, default=9, help='За сколько последних дней собирать данные')
    args = parser.parse_args()

    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, TELEGRAM_CHAT_NAME]):
        logger.error("Missing Telegram credentials")
        return

    logger.info("Starting data collection...")
    
    # Создаем клиент и подключаемся
    client = TelegramClient(SESSION_FILE, TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.start()
    
    # Если сессия новая, может потребоваться аутентификация
    if not await client.is_user_authorized():
        await client.send_code_request(TELEGRAM_PHONE)
        try:
            await client.sign_in(TELEGRAM_PHONE, input('Enter the code: '))
        except SessionPasswordNeededError:
            await client.sign_in(password=input('Password: '))
    
    try:
        # Создаем PeerChannel для доступа к каналу
        channel_id = int(TELEGRAM_CHAT_NAME)
        chat = PeerChannel(channel_id)
        
        # Загружаем существующие данные
        data = load_existing_data()

        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        start_date = now - timedelta(days=args.days)
        
        # Определяем, с какой даты начинать сбор данных
        last_message_date = None
        if data["listings"]:
            try:
                # Находим самое старое сообщение в существующих данных
                oldest_message_date = datetime.fromisoformat(min(
                    listing["date"] for listing in data["listings"]
                ))
                # Если самое старое сообщение новее чем start_date, начинаем сбор с start_date
                last_message_date = min(oldest_message_date, start_date)
            except ValueError:
                last_message_date = start_date
        else:
            last_message_date = start_date

        logger.info(f"Collecting messages since: {last_message_date.strftime('%Y-%m-%d %H:%M:%S')}")

        # Собираем новые сообщения
        new_messages = await collect_messages(client, chat, last_message_date)
        
        # Обновляем существующие данные
        existing_ids = {listing["id"] for listing in data["listings"]}
        added_count = 0
        for message in new_messages:
            if message["id"] not in existing_ids:
                data["listings"].append(message)
                added_count += 1
        
        # Сохраняем обновленные данные
        save_data(data)
        logger.info(f"Added {added_count} new messages to the database")
        logger.info(f"Total messages in database: {len(data['listings'])}")
    
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
    
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 