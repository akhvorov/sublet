#!/usr/bin/env python3
"""
Скрипт для поиска чата среди всех диалогов
"""

import asyncio
import sys
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import Channel, Chat, User

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_PHONE,
    SESSION_FILE
)

async def main():
    """
    Основная функция для поиска чата
    """
    print("Подключаемся к Telegram...")
    client = TelegramClient(SESSION_FILE, TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.start()

    if not await client.is_user_authorized():
        await client.send_code_request(TELEGRAM_PHONE)
        try:
            await client.sign_in(TELEGRAM_PHONE, input('Введите код: '))
        except SessionPasswordNeededError:
            await client.sign_in(password=input('Введите пароль двухфакторной аутентификации: '))

    print("\nСканируем все диалоги...")
    print("\nФормат вывода:")
    print("ID | Тип | Название/Имя | Username (если есть)")
    print("-" * 50)

    target_title = "HSE Apartment Sublet & Exchange"
    found_target = False

    async for dialog in client.iter_dialogs():
        entity = dialog.entity

        if dialog.name == target_title:
            print(dialog)
        
        if isinstance(entity, Channel):
            type_name = "Канал" if entity.broadcast else "Супергруппа"
        elif isinstance(entity, Chat):
            type_name = "Группа"
        elif isinstance(entity, User):
            type_name = "Пользователь"
        else:
            type_name = "Неизвестно"

        username = f"@{entity.username}" if hasattr(entity, 'username') and entity.username else "нет"
        
        # Проверяем, не содержит ли название искомую строку
        if hasattr(entity, 'title'):
            title = entity.title
            if target_title.lower() in title.lower():
                found_target = True
                print("\n!!! НАЙДЕН ИСКОМЫЙ ЧАТ !!!")
        else:
            title = f"{entity.first_name} {entity.last_name}" if hasattr(entity, 'first_name') else "Без названия"

        print(f"{entity.id} | {type_name} | {title} | {username}")
        
        if found_target:
            print(f"\nПодробная информация о найденном чате:")
            print(f"ID: {entity.id}")
            print(f"Тип: {type_name}")
            print(f"Название: {title}")
            print(f"Username: {username}")
            print(f"Для использования в скрипте, обновите .env файл:")
            print(f"TELEGRAM_CHAT_NAME={entity.id}")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main()) 