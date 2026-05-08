"""공급업체 CRUD 엔드포인트"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession, require_roles
from app.models.supplier import Supplier
from app.schemas.common import PaginatedResponse
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["Master — Suppliers"])

_require_write = require_roles("admin", "production_manager")
_require_admin = require_roles("admin")


@router.get("/", response_model=PaginatedResponse[SupplierRead])
async def list_suppliers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="이름 또는 코드 검색"),
    grade: Optional[str] = Query(None, description="등급 필터 (A/B/C/D)"),
    is_active: Optional[bool] = Query(None),
    db: DBSession = None,
):
    """공급업체 목록 조회"""
    filters = []
    if search:
        filters.append(
            Supplier.name.ilike(f"%{search}%")
            | Supplier.supplier_code.ilike(f"%{search}%")
        )
    if grade is not None:
        filters.append(Supplier.grade == grade)
    if is_active is not None:
        filters.append(Supplier.is_active == is_active)

    total_result = await db.execute(
        select(func.count(Supplier.id)).where(*filters)
    )
    total = total_result.scalar_one()

    q = (
        select(Supplier)
        .where(*filters)
        .order_by(Supplier.name)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items_result = await db.execute(q)
    items = [SupplierRead.model_validate(row) for row in items_result.scalars().all()]

    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.post(
    "/",
    response_model=SupplierRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_write],
)
async def create_supplier(body: SupplierCreate, db: DBSession = None):
    """공급업체 생성"""
    existing = await db.execute(
        select(Supplier).where(Supplier.supplier_code == body.supplier_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"supplier_code '{body.supplier_code}' 이미 존재합니다",
        )

    supplier = Supplier(**body.model_dump())
    db.add(supplier)
    await db.flush()
    await db.refresh(supplier)
    return SupplierRead.model_validate(supplier)


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(supplier_id: uuid.UUID, db: DBSession = None):
    """공급업체 단건 조회"""
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공급업체를 찾을 수 없습니다"
        )
    return SupplierRead.model_validate(supplier)


@router.patch(
    "/{supplier_id}",
    response_model=SupplierRead,
    dependencies=[_require_write],
)
async def update_supplier(supplier_id: uuid.UUID, body: SupplierUpdate, db: DBSession = None):
    """공급업체 수정"""
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공급업체를 찾을 수 없습니다"
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)

    await db.flush()
    await db.refresh(supplier)
    return SupplierRead.model_validate(supplier)


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_require_admin],
)
async def deactivate_supplier(supplier_id: uuid.UUID, db: DBSession = None):
    """공급업체 비활성화 (실제 삭제 아님)"""
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공급업체를 찾을 수 없습니다"
        )
    supplier.is_active = False
    await db.flush()
