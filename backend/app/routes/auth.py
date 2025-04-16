from fastapi import APIRouter, HTTPException, status
from ..models.auth import VerificationRequest, Token
from ..utils.auth import create_access_token, verify_code
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/auth/verify", response_model=Token)
async def verify_and_get_token(request: VerificationRequest):
    """
    Проверка кода и выдача токена
    """
    try:
        # Проверяем код и получаем chat_id
        chat_id = verify_code(request.code)
        if not chat_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный код подтверждения"
            )
        
        # Создаем токен
        access_token = create_access_token(chat_id)
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in verify_and_get_token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при верификации"
        ) 