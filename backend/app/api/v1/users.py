"""사용자 관리 엔드포인트"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, select

from app.api.deps import DBSession, require_roles
from app.core.security import hash_password
from app.models.user import User, VALID_ROLES, USER_STATUS_VALUES
from app.schemas.common import PaginatedResponse

router = APIRouter(tags=["Users"])

_require_admin = require_roles("admin")
_require_admin_or_exec = require_roles("admin", "executive")


# ------------------------------------------------------------------
# Inline schemas (user management only, not reused elsewhere)
# ------------------------------------------------------------------

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    employee_no: Optional[str] = None
    phone: Optional[str] = None
    status: str
    is_superuser: bool


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., max_length=100)
    role: str = Field(..., description=f"역할: {', '.join(VALID_ROLES)}")
    department: Optional[str] = Field(None, max_length=100)
    employee_no: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = None
    department: Optional[str] = Field(None, max_length=100)
    employee_no: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = None


class PasswordResetRequest(BaseModel):
    new_password: str = Field(..., min_length=8)


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get(
    "/",
    response_model=PaginatedResponse[UserRead],
    dependencies=[_require_admin_or_exec],
)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None),
    user_status: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None, description="이름 또는 이메일 검색"),
    db: DBSession,
):
    """사용자 목록 조회 (admin / executive)"""
    filters = []
    if role is not None:
        filters.append(User.role == role)
    if user_status is not None:
        filters.append(User.status == user_status)
    if search is not None:
        filters.append(
            User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
        )

    total_result = await db.execute(select(func.count(User.id)).where(*filters))
    total = total_result.scalar_one()

    q = (
        select(User)
        .where(*filters)
        .order_by(User.full_name)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items_result = await db.execute(q)
    items = [UserRead.model_validate(row) for row in items_result.scalars().all()]

    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_admin],
)
async def create_user(body: UserCreate, db: DBSession):
    """사용자 생성 (admin 전용)"""
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"유효하지 않은 역할입니다. 허용: {', '.join(VALID_ROLES)}",
        )

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"이메일 '{body.email}' 이미 사용 중입니다",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        department=body.department,
        employee_no=body.employee_no,
        phone=body.phone,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[_require_admin],
)
async def update_user(
    user_id: uuid.UUID, body: UserUpdate, db: DBSession
):
    """사용자 역할/상태/부서 수정 (admin 전용)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다"
        )

    update_data = body.model_dump(exclude_unset=True)
    if "role" in update_data and update_data["role"] not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"유효하지 않은 역할입니다. 허용: {', '.join(VALID_ROLES)}",
        )
    if "status" in update_data and update_data["status"] not in USER_STATUS_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"유효하지 않은 상태입니다. 허용: {', '.join(USER_STATUS_VALUES)}",
        )

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return UserRead.model_validate(user)


@router.post(
    "/{user_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_require_admin],
)
async def reset_user_password(
    user_id: uuid.UUID,
    body: PasswordResetRequest,
    db: DBSession,
):
    """사용자 비밀번호 초기화 (admin 전용)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다"
        )

    user.hashed_password = hash_password(body.new_password)
    await db.flush()
