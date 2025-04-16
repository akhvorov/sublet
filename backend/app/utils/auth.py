from datetime import datetime, timedelta
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import random
import string
import redis
from ..config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REDIS_URL,
    VERIFICATION_CODE_TTL
)
from ..models.auth import TokenData
import logging
from typing import Optional
from redis import Redis

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
redis_client = Redis.from_url(REDIS_URL)

def create_access_token(chat_id: int) -> str:
    """Создает JWT токен для пользователя"""
    try:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + expires_delta
        
        to_encode = {
            "sub": str(chat_id),
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.info(f"Access token created for chat_id {chat_id}")
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Failed to create access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token"
        )

def verify_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Проверяет JWT токен и возвращает данные пользователя"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        chat_id = payload.get("sub")
        if chat_id is None:
            logger.warning("Token payload missing 'sub' claim")
            raise credentials_exception
        token_data = TokenData(chat_id=int(chat_id))
        return token_data
    except jwt.PyJWTError as e:
        logger.error(f"Token verification failed: {e}")
        raise credentials_exception

def generate_verification_code(length: int = 6) -> str:
    """Генерирует случайный код верификации"""
    return ''.join(random.choices(string.digits, k=length))

def save_verification_code(chat_id: int, code: str, ttl: int = VERIFICATION_CODE_TTL) -> None:
    """Сохраняет код верификации в Redis"""
    try:
        key = f"verification_code:{chat_id}"
        redis_client.setex(key, ttl, code)
        logger.info(f"Verification code saved for chat_id {chat_id}")
    except redis.RedisError as e:
        logger.error(f"Failed to save verification code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save verification code"
        )

def get_chat_id_by_code(code: str) -> Optional[int]:
    """Получает chat_id по коду верификации"""
    try:
        # Ищем все ключи в Redis, которые содержат код
        for key in redis_client.scan_iter("verification_code:*"):
            stored_code = redis_client.get(key)
            if stored_code and stored_code.decode() == code:
                # Извлекаем chat_id из ключа (формат: "verification_code:{chat_id}")
                chat_id = int(key.decode().split(':')[1])
                return chat_id
        return None
    except redis.RedisError as e:
        logger.error(f"Failed to get chat_id by code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not verify code"
        )

def verify_code(code: str) -> Optional[int]:
    """Проверяет код верификации и возвращает chat_id"""
    try:
        chat_id = get_chat_id_by_code(code)
        if chat_id is None:
            logger.info(f"No verification code found")
            return None
            
        # Удаляем использованный код
        key = f"verification_code:{chat_id}"
        redis_client.delete(key)
        logger.info(f"Verification code validated for chat_id {chat_id}")
        return chat_id
        
    except redis.RedisError as e:
        logger.error(f"Failed to verify code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not verify code"
        )