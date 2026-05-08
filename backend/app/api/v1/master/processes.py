"""공정 CRUD 엔드포인트"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DBSession, require_roles
from app.models.process_type import ProcessType
from app.schemas.common import PaginatedResponse
from app.schemas.process_type import ProcessTypeCreate, ProcessTypeRead, ProcessTypeUpdate

router = APIRouter(prefix="/processes", tags=["Master — Processes"])

_require_write = require_roles("admin", "production_manager")
_require_admin = require_roles("admin")


@router.get("/", response_model=PaginatedResponse[ProcessTypeRead])
async def list_processes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="이름 또는 코드 검색"),
    process_type: Optional[str] = Query(None, description="공정 유형 필터"),
    is_active: Optional[bool] = Query(None),
    db: DBSession = None,
):
    """공정 목록 조회"""
    filters = []
    if search:
        filters.append(
            ProcessType.name.ilike(f"%{search}%")
            | ProcessType.process_code.ilike(f"%{search}%")
        )
    if process_type is not None:
        filters.append(ProcessType.process_type == process_type)
    if is_active is not None:
        filters.append(ProcessType.is_active == is_active)

    total_result = await db.execute(
        select(func.count(ProcessType.id)).where(*filters)
    )
    total = total_result.scalar_one()

    q = (
        select(ProcessType)
        .where(*filters)
        .order_by(ProcessType.name)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items_result = await db.execute(q)
    items = [
        ProcessTypeRead.model_validate(row)
        for row in items_result.scalars().all()
    ]

    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.post(
    "/",
    response_model=ProcessTypeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_write],
)
async def create_process(body: ProcessTypeCreate, db: DBSession = None):
    """공정 생성"""
    existing = await db.execute(
        select(ProcessType).where(ProcessType.process_code == body.process_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"process_code '{body.process_code}' 이미 존재합니다",
        )

    process = ProcessType(**body.model_dump())
    db.add(process)
    await db.flush()
    await db.refresh(process)
    return ProcessTypeRead.model_validate(process)


@router.get("/{process_id}", response_model=ProcessTypeRead)
async def get_process(process_id: uuid.UUID, db: DBSession = None):
    """공정 단건 조회"""
    result = await db.execute(
        select(ProcessType).where(ProcessType.id == process_id)
    )
    process = result.scalar_one_or_none()
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공정을 찾을 수 없습니다"
        )
    return ProcessTypeRead.model_validate(process)


@router.patch(
    "/{process_id}",
    response_model=ProcessTypeRead,
    dependencies=[_require_write],
)
async def update_process(process_id: uuid.UUID, body: ProcessTypeUpdate, db: DBSession = None):
    """공정 수정"""
    result = await db.execute(
        select(ProcessType).where(ProcessType.id == process_id)
    )
    process = result.scalar_one_or_none()
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공정을 찾을 수 없습니다"
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(process, field, value)

    await db.flush()
    await db.refresh(process)
    return ProcessTypeRead.model_validate(process)


@router.delete(
    "/{process_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_require_admin],
)
async def deactivate_process(process_id: uuid.UUID, db: DBSession = None):
    """공정 비활성화 (실제 삭제 아님)"""
    result = await db.execute(
        select(ProcessType).where(ProcessType.id == process_id)
    )
    process = result.scalar_one_or_none()
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="공정을 찾을 수 없습니다"
        )
    process.is_active = False
    await db.flush()
