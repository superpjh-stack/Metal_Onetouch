from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DBSession, CurrentUser
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
    blacklist_token,
    is_token_blacklisted,
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserMeResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer(auto_error=False)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="로그인",
    description="이메일/비밀번호로 로그인하여 JWT 토큰을 발급받습니다.",
)
async def login(body: LoginRequest, db: DBSession = None):
    # 사용자 조회
    result = await db.execute(select(User).where(User.email == body.email))
    user: User | None = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다",
        )

    # 토큰 생성
    token_data = {"sub": str(user.id), "role": user.role, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # 마지막 로그인 시각 업데이트
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login_at=datetime.now(timezone.utc))
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
    description="현재 Access Token을 블랙리스트에 등록하여 무효화합니다.",
)
async def logout(
    current_user: CurrentUser = None,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    if credentials:
        # Access token 블랙리스트 처리
        expire_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        await blacklist_token(credentials.credentials, expire_seconds)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="토큰 갱신",
    description="Refresh Token을 사용하여 새 Access Token을 발급합니다.",
)
async def refresh_token(body: RefreshRequest, db: DBSession = None):
    # Refresh token 검증
    payload = verify_token(body.refresh_token, expected_type="refresh")

    # 블랙리스트 확인
    if await is_token_blacklisted(body.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="무효화된 토큰입니다",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 사용자입니다",
        )

    token_data = {"sub": str(user.id), "role": user.role, "email": user.email}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    # 기존 refresh token 블랙리스트 처리
    await blacklist_token(
        body.refresh_token, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="현재 사용자 정보",
    description="Bearer 토큰으로 인증된 현재 사용자의 프로필을 반환합니다.",
)
async def get_me(current_user: CurrentUser = None):
    return UserMeResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        department=current_user.department,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
    )
