from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import TelegramError
from ..config import TELEGRAM_BOT_TOKEN
from .auth import generate_verification_code, save_verification_code
import logging
import asyncio
from typing import Dict, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальная переменная для хранения экземпляра приложения
application: Optional[Application] = None

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    if not update.message or not update.message.from_user:
        return

    chat_id = update.message.chat_id

    # Генерируем код
    code = generate_verification_code()
    
    # Сохраняем код в Redis
    save_verification_code(chat_id, code)
    
    # Отправляем код пользователю
    message = (
        f"Ваш код подтверждения: {code}\n"
        f"Код действителен в течение 5 минут.\n\n"
        f"Введите полученный код на странице авторизации."
    )
    
    await update.message.reply_text(message)
    logger.info(f"Verification code sent to chat_id {chat_id}")

async def setup_bot() -> None:
    """Настройка и запуск бота"""
    global application
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        return
        
    try:
        # Если бот уже запущен, останавливаем его
        if application:
            await stop_bot()
            
        # Создаем приложение
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", handle_start))
        
        # Инициализируем бота без запуска polling
        await application.initialize()
        await application.start()
        
        # Запускаем polling в отдельной таске
        asyncio.create_task(application.updater.start_polling())
        
        logger.info("Bot started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        if application:
            await stop_bot()
        raise

async def stop_bot() -> None:
    """Остановка бота"""
    global application
    if application:
        try:
            await application.stop()
            await application.shutdown()
            application = None
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

async def send_verification_code(username: str, code: str) -> bool:
    """
    Send verification code to user via Telegram bot
    
    Args:
        username: Telegram username without @ symbol
        code: 6-digit verification code
        
    Returns:
        bool: True if message was sent successfully
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        return False
        
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        message = (
            f"Ваш код подтверждения: {code}\n"
            f"Он будет действителен в течение 5 минут.\n\n"
            f"Если вы не запрашивали код, проигнорируйте это сообщение."
        )

        try:
            # Пробуем найти пользователя по username
            chat = await bot.get_chat(f"@{username}")
            await bot.send_message(chat_id=chat.id, text=message)
            logger.info(f"Verification code sent to @{username}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send message to @{username}: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error in send_verification_code: {str(e)}")
        return False 