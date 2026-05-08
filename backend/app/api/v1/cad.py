"""CAD 도면 엔드포인트"""
import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.cad import (
    CadDrawingCreate,
    CadDrawingRead,
    CadStatusResponse,
    CadUpdateObjects,
)
from app.schemas.common import PaginatedResponse
from app.schemas.ml import AnnotationSubmit, AnnotationTaskRead
from app.services.cad_analysis_service import CadAnalysisService
from app.services.annotation_task_service import AnnotationTaskService

router = APIRouter(tags=["CAD"])


@router.post("/", response_model=CadDrawingRead, status_code=201)
async def create_drawing(
    body: CadDrawingCreate,
    db: DBSession = None,
    user: CurrentUser = None,
):
    """도면 등록 + 비동기 GPT-4o Vision 분석 enqueue"""
    svc = CadAnalysisService(db)
    drawing = await svc.create_drawing(body, created_by=user.id)
    await db.commit()
    return drawing


@router.get("/", response_model=PaginatedResponse[CadDrawingRead])
async def list_drawings(
    db: DBSession = None,
    _: CurrentUser = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    analysis_status: Optional[str] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
):
    """도면 목록"""
    svc = CadAnalysisService(db)
    items, total = await svc.list_drawings(
        analysis_status=analysis_status,
        customer_id=customer_id,
        page=page,
        limit=limit,
    )
    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.get("/{drawing_id}", response_model=CadDrawingRead)
async def get_drawing(drawing_id: uuid.UUID, db: DBSession = None, _: CurrentUser = None):
    """도면 상세"""
    return await CadAnalysisService(db).get_drawing(drawing_id)


@router.get("/{drawing_id}/status", response_model=CadStatusResponse)
async def get_drawing_status(drawing_id: uuid.UUID, db: DBSession = None, _: CurrentUser = None):
    """분석 상태 polling 용"""
    return await CadAnalysisService(db).get_status(drawing_id)


@router.patch("/{drawing_id}/objects", response_model=CadDrawingRead)
async def update_objects(
    drawing_id: uuid.UUID,
    body: CadUpdateObjects,
    db: DBSession = None,
    user: CurrentUser = None,
):
    """분석 결과 수동 수정 (confidence=1.0 고정)"""
    svc = CadAnalysisService(db)
    drawing = await svc.update_objects(drawing_id, body)
    await db.commit()
    return drawing


@router.get("/{drawing_id}/annotation-task", response_model=Optional[AnnotationTaskRead])
async def get_annotation_task(drawing_id: uuid.UUID, db: DBSession = None, _: CurrentUser = None):
    """도면의 어노테이션 태스크 조회"""
    return await AnnotationTaskService(db).get_by_drawing(drawing_id)


@router.put("/{drawing_id}/annotation", response_model=AnnotationTaskRead)
async def submit_annotation(
    drawing_id: uuid.UUID,
    body: AnnotationSubmit,
    db: DBSession = None,
    user: CurrentUser = None,
):
    """AI 분석 결과 수동 보정 + 어노테이션 완료"""
    svc = AnnotationTaskService(db)
    result = await svc.submit_correction(drawing_id, body.corrected_parsed, user.id)
    await db.commit()
    return result

