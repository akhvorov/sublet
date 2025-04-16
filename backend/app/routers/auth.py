from fastapi import APIRouter, HTTPException, status
from ..models.auth import VerificationRequest, VerificationResponse
from ..utils.auth import verify_code, create_access_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/verify", response_model=VerificationResponse)
async def verify_telegram_code(request: VerificationRequest):
    """
    Проверяет код верификации из Telegram и возвращает JWT токен
    """
    try:
        if verify_code(request.chat_id, request.code):
            access_token = create_access_token(request.chat_id)
            return {"access_token": access_token, "token_type": "bearer"}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный код верификации"
            )
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при верификации"
        ) 