"""원자재 CRUD 엔드포인트"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import DBSession, require_roles
from app.models.raw_material import RawMaterial
from app.schemas.common import PaginatedResponse
from app.schemas.material import MaterialCreate, MaterialRead, MaterialUpdate

router = APIRouter(prefix="/materials", tags=["Master — Materials"])

_require_write = require_roles("admin", "production_manager")
_require_admin = require_roles("admin")


def _build_filters(
    search: Optional[str],
    category: Optional[str],
    is_active: Optional[bool],
    low_stock: Optional[bool],
) -> list:
    filters = []
    if search:
        filters.append(
            RawMaterial.name.ilike(f"%{search}%")
            | RawMaterial.material_code.ilike(f"%{search}%")
        )
    if category is not None:
        filters.append(RawMaterial.category == category)
    if is_active is not None:
        filters.append(RawMaterial.is_active == is_active)
    if low_stock:
        filters.append(RawMaterial.stock_qty <= RawMaterial.min_stock_qty)
    return filters


def _to_read(material: RawMaterial) -> MaterialRead:
    data = MaterialRead.model_validate(material)
    if material.supplier:
        data.supplier_name = material.supplier.name
    return data


@router.get("/", response_model=PaginatedResponse[MaterialRead])
async def list_materials(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="이름 또는 코드 검색"),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    low_stock: Optional[bool] = Query(None, description="재고 부족 항목만"),
    db: DBSession = None,
):
    """원자재 목록 조회"""
    filters = _build_filters(search, category, is_active, low_stock)

    total_result = await db.execute(
        select(func.count(RawMaterial.id)).where(*filters)
    )
    total = total_result.scalar_one()

    q = (
        select(RawMaterial)
        .options(joinedload(RawMaterial.supplier))
        .where(*filters)
        .order_by(RawMaterial.name)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items_result = await db.execute(q)
    items = [_to_read(row) for row in items_result.scalars().unique().all()]

    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.post(
    "/",
    response_model=MaterialRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_write],
)
async def create_material(body: MaterialCreate, db: DBSession = None):
    """원자재 생성"""
    existing = await db.execute(
        select(RawMaterial).where(RawMaterial.material_code == body.material_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"material_code '{body.material_code}' 이미 존재합니다",
        )

    material = RawMaterial(**body.model_dump())
    db.add(material)
    await db.flush()

    result = await db.execute(
        select(RawMaterial)
        .options(joinedload(RawMaterial.supplier))
        .where(RawMaterial.id == material.id)
    )
    return _to_read(result.scalar_one())


@router.get("/{material_id}", response_model=MaterialRead)
async def get_material(material_id: uuid.UUID, db: DBSession = None):
    """원자재 단건 조회"""
    result = await db.execute(
        select(RawMaterial)
        .options(joinedload(RawMaterial.supplier))
        .where(RawMaterial.id == material_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="원자재를 찾을 수 없습니다"
        )
    return _to_read(material)


@router.patch(
    "/{material_id}",
    response_model=MaterialRead,
    dependencies=[_require_write],
)
async def update_material(material_id: uuid.UUID, body: MaterialUpdate, db: DBSession = None):
    """원자재 수정"""
    result = await db.execute(
        select(RawMaterial).where(RawMaterial.id == material_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="원자재를 찾을 수 없습니다"
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(material, field, value)

    await db.flush()
    result = await db.execute(
        select(RawMaterial)
        .options(joinedload(RawMaterial.supplier))
        .where(RawMaterial.id == material_id)
    )
    return _to_read(result.scalar_one())


@router.delete(
    "/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_require_admin],
)
async def deactivate_material(material_id: uuid.UUID, db: DBSession = None):
    """원자재 비활성화 (실제 삭제 아님)"""
    result = await db.execute(
        select(RawMaterial).where(RawMaterial.id == material_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="원자재를 찾을 수 없습니다"
        )
    material.is_active = False
    await db.flush()
