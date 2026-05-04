"""설비 CRUD 엔드포인트"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DBSession, require_roles
from app.models.equipment import Equipment
from app.schemas.common import PaginatedResponse
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentRead,
    EquipmentStatusUpdate,
    EquipmentUpdate,
)

router = APIRouter(prefix="/equipment", tags=["Master — Equipment"])

_require_write = require_roles("admin", "production_manager")
_require_status = require_roles("admin", "production_manager", "process_engineer")
_require_admin = require_roles("admin")


@router.get("/", response_model=PaginatedResponse[EquipmentRead])
async def list_equipment(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="이름 또는 코드 검색"),
    equipment_status: Optional[str] = Query(None, alias="status"),
    process_id: Optional[uuid.UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: DBSession,
):
    """설비 목록 조회"""
    filters = []
    if search:
        filters.append(
            Equipment.name.ilike(f"%{search}%")
            | Equipment.equipment_code.ilike(f"%{search}%")
        )
    if equipment_status is not None:
        filters.append(Equipment.status == equipment_status)
    if process_id is not None:
        filters.append(Equipment.process_id == process_id)
    if is_active is not None:
        filters.append(Equipment.is_active == is_active)

    total_result = await db.execute(
        select(func.count(Equipment.id)).where(*filters)
    )
    total = total_result.scalar_one()

    q = (
        select(Equipment)
        .where(*filters)
        .order_by(Equipment.name)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items_result = await db.execute(q)
    items = [
        EquipmentRead.model_validate(row) for row in items_result.scalars().all()
    ]

    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.post(
    "/",
    response_model=EquipmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_write],
)
async def create_equipment(body: EquipmentCreate, db: DBSession):
    """설비 생성"""
    existing = await db.execute(
        select(Equipment).where(Equipment.equipment_code == body.equipment_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"equipment_code '{body.equipment_code}' 이미 존재합니다",
        )

    equip = Equipment(**body.model_dump())
    db.add(equip)
    await db.flush()
    await db.refresh(equip)
    return EquipmentRead.model_validate(equip)


@router.get("/{equipment_id}", response_model=EquipmentRead)
async def get_equipment(equipment_id: uuid.UUID, db: DBSession):
    """설비 단건 조회"""
    result = await db.execute(
        select(Equipment).where(Equipment.id == equipment_id)
    )
    equip = result.scalar_one_or_none()
    if not equip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="설비를 찾을 수 없습니다"
        )
    return EquipmentRead.model_validate(equip)


@router.patch(
    "/{equipment_id}",
    response_model=EquipmentRead,
    dependencies=[_require_write],
)
async def update_equipment(equipment_id: uuid.UUID, body: EquipmentUpdate, db: DBSession):
    """설비 수정"""
    result = await db.execute(
        select(Equipment).where(Equipment.id == equipment_id)
    )
    equip = result.scalar_one_or_none()
    if not equip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="설비를 찾을 수 없습니다"
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(equip, field, value)

    await db.flush()
    await db.refresh(equip)
    return EquipmentRead.model_validate(equip)


@router.patch(
    "/{equipment_id}/status",
    response_model=EquipmentRead,
    dependencies=[_require_status],
)
async def update_equipment_status(
    equipment_id: uuid.UUID,
    body: EquipmentStatusUpdate,
    db: DBSession,
):
    """설비 상태 변경"""
    result = await db.execute(
        select(Equipment).where(Equipment.id == equipment_id)
    )
    equip = result.scalar_one_or_none()
    if not equip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="설비를 찾을 수 없습니다"
        )

    equip.status = body.status
    if body.notes is not None:
        equip.notes = body.notes

    await db.flush()
    await db.refresh(equip)
    return EquipmentRead.model_validate(equip)


@router.delete(
    "/{equipment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_require_admin],
)
async def deactivate_equipment(equipment_id: uuid.UUID, db: DBSession):
    """설비 비활성화 (실제 삭제 아님)"""
    result = await db.execute(
        select(Equipment).where(Equipment.id == equipment_id)
    )
    equip = result.scalar_one_or_none()
    if not equip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="설비를 찾을 수 없습니다"
        )
    equip.is_active = False
    await db.flush()
