from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """로그인 요청 스키마"""
    email: EmailStr = Field(..., description="사용자 이메일")
    password: str = Field(..., min_length=6, description="비밀번호")

    model_config = {"json_schema_extra": {"example": {"email": "admin@onetouch.com", "password": "Admin1234!"}}}


class TokenResponse(BaseModel):
    """토큰 응답 스키마"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token 만료 시간 (초)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }
    }


class TokenPayload(BaseModel):
    """JWT 토큰 페이로드 스키마"""
    sub: str = Field(..., description="사용자 ID (UUID)")
    role: str = Field(..., description="사용자 역할")
    exp: int = Field(..., description="만료 타임스탬프")
    type: str = Field(default="access", description="토큰 타입: access | refresh")


class RefreshRequest(BaseModel):
    """토큰 갱신 요청 스키마"""
    refresh_token: str = Field(..., description="갱신에 사용할 Refresh Token")


class UserMeResponse(BaseModel):
    """현재 사용자 정보 응답 스키마"""
    id: str
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    is_active: bool
    is_superuser: bool

    model_config = {"from_attributes": True}
