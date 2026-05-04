"""고객사 CRUD 엔드포인트"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DBSession, require_roles
from app.models.customer import Customer
from app.schemas.common import PaginatedResponse
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["Master — Customers"])

_require_write = require_roles("admin", "production_manager")
_require_admin = require_roles("admin")


@router.get("/", response_model=PaginatedResponse[CustomerRead])
async def list_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="이름 또는 코드 검색"),
    is_active: Optional[bool] = Query(None),
    db: DBSession,
):
    """고객사 목록 조회"""
    filters = []
    if search:
        filters.append(
            Customer.name.ilike(f"%{search}%")
            | Customer.customer_code.ilike(f"%{search}%")
        )
    if is_active is not None:
        filters.append(Customer.is_active == is_active)

    total_result = await db.execute(
        select(func.count(Customer.id)).where(*filters)
    )
    total = total_result.scalar_one()

    q = (
        select(Customer)
        .where(*filters)
        .order_by(Customer.name)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items_result = await db.execute(q)
    items = [CustomerRead.model_validate(row) for row in items_result.scalars().all()]

    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.post(
    "/",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_write],
)
async def create_customer(body: CustomerCreate, db: DBSession):
    """고객사 생성"""
    existing = await db.execute(
        select(Customer).where(Customer.customer_code == body.customer_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"customer_code '{body.customer_code}' 이미 존재합니다",
        )

    customer = Customer(**body.model_dump())
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return CustomerRead.model_validate(customer)


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(customer_id: uuid.UUID, db: DBSession):
    """고객사 단건 조회"""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="고객사를 찾을 수 없습니다"
        )
    return CustomerRead.model_validate(customer)


@router.patch(
    "/{customer_id}",
    response_model=CustomerRead,
    dependencies=[_require_write],
)
async def update_customer(customer_id: uuid.UUID, body: CustomerUpdate, db: DBSession):
    """고객사 수정"""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="고객사를 찾을 수 없습니다"
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)

    await db.flush()
    await db.refresh(customer)
    return CustomerRead.model_validate(customer)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_require_admin],
)
async def deactivate_customer(customer_id: uuid.UUID, db: DBSession):
    """고객사 비활성화 (실제 삭제 아님)"""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="고객사를 찾을 수 없습니다"
        )
    customer.is_active = False
    await db.flush()
