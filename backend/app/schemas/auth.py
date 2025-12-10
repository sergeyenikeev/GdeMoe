from datetime import datetime

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime | None = None


class TokenPayload(BaseModel):
    sub: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
