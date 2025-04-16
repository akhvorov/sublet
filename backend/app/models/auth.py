from pydantic import BaseModel
from typing import Optional

class VerificationRequest(BaseModel):
    code: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    chat_id: Optional[int] = None

class VerificationResponse(BaseModel):
    access_token: str
    token_type: str 