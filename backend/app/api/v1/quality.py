"""품질 검사 엔드포인트"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DBSession, require_roles
from app.models.quality import DefectDetail, QualityInspection
from app.schemas.common import PaginatedResponse
from app.schemas.quality import (
    DefectDetailCreate,
    DefectDetailRead,
    DefectStatsResponse,
    QualityInspectionCreate,
    QualityInspectionRead,
)
from app.services.quality_service import QualityService

router = APIRouter(tags=["Quality"])

_require_inspector = require_roles(
    "admin", "quality_inspector", "production_manager", "process_engineer"
)


@router.get("/", response_model=PaginatedResponse[QualityInspectionRead])
async def list_inspections(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    lot_id: Optional[uuid.UUID] = Query(None),
    result: Optional[str] = Query(None),
    inspection_type: Optional[str] = Query(None),
    db: DBSession = None,
):
    """품질 검사 목록 조회"""
    from sqlalchemy import func

    filters = []
    if lot_id:
        filters.append(QualityInspection.lot_id == lot_id)
    if result:
        filters.append(QualityInspection.result == result)
    if inspection_type:
        filters.append(QualityInspection.inspection_type == inspection_type)

    total = (await db.execute(
        select(func.count(QualityInspection.id)).where(*filters)
    )).scalar_one()

    items_result = await db.execute(
        select(QualityInspection)
        .options(joinedload(QualityInspection.defects))
        .where(*filters)
        .order_by(QualityInspection.inspection_date.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = [
        QualityInspectionRead.model_validate(row)
        for row in items_result.scalars().unique().all()
    ]
    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.post(
    "/",
    response_model=QualityInspectionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_inspector],
)
async def create_inspection(
    body: QualityInspectionCreate,
    db: DBSession = None,
    current_user: CurrentUser = None,
):
    """품질 검사 등록 + 불량 시 LOT 상태 자동 전환"""
    inspection = await QualityService(db).create_inspection(
        data=body, inspector_id=current_user.id
    )
    return QualityInspectionRead.model_validate(inspection)


@router.get("/stats", response_model=DefectStatsResponse)
async def get_defect_stats(
    group_by: str = Query("supplier", pattern="^(supplier|process_type|lot)$"),
    period_days: int = Query(30, ge=1, le=365),
    db: DBSession = None,
):
    """불량률 집계"""
    return await QualityService(db).get_defect_stats(
        group_by=group_by, period_days=period_days
    )


@router.get("/{inspection_id}", response_model=QualityInspectionRead)
async def get_inspection(inspection_id: uuid.UUID, db: DBSession = None):
    """검사 상세 조회 (불량 상세 포함)"""
    result = await db.execute(
        select(QualityInspection)
        .options(joinedload(QualityInspection.defects))
        .where(QualityInspection.id == inspection_id)
    )
    insp = result.scalar_one_or_none()
    if not insp:
        raise HTTPException(status_code=404, detail="검사 이력을 찾을 수 없습니다")
    return QualityInspectionRead.model_validate(insp)


@router.post(
    "/{inspection_id}/defects",
    response_model=DefectDetailRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_inspector],
)
async def add_defect(
    inspection_id: uuid.UUID,
    body: DefectDetailCreate,
    db: DBSession = None,
):
    """불량 상세 추가"""
    insp = (await db.execute(
        select(QualityInspection).where(QualityInspection.id == inspection_id)
    )).scalar_one_or_none()
    if not insp:
        raise HTTPException(status_code=404, detail="검사 이력을 찾을 수 없습니다")

    dd = DefectDetail(
        inspection_id=inspection_id,
        **body.model_dump(),
    )
    db.add(dd)
    await db.flush()
    await db.refresh(dd)
    return DefectDetailRead.model_validate(dd)


@router.get("/lot/{lot_id}", response_model=list[QualityInspectionRead])
async def get_lot_inspections(lot_id: uuid.UUID, db: DBSession = None):
    """LOT별 검사 이력 전체"""
    inspections = await QualityService(db).get_lot_inspections(lot_id)
    return [QualityInspectionRead.model_validate(i) for i in inspections]
