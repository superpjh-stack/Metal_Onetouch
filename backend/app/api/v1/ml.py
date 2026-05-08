"""ML 관리 API — 어노테이션, 데이터셋 빌드, 학습 잡"""
import uuid
from typing import Optional

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.ml import (
    AnnotationDatasetRead,
    AnnotationSubmit,
    AnnotationTaskRead,
    DatasetBuildRequest,
    TrainingJobCreate,
    TrainingJobRead,
)
from app.services.annotation_task_service import AnnotationTaskService
from app.services.training_service import TrainingService

router = APIRouter(tags=["ML"])


# ── 어노테이션 ──────────────────────────────────────────────────────

@router.get("/annotation-tasks", response_model=PaginatedResponse[AnnotationTaskRead])
async def list_annotation_tasks(
    db: DBSession = None,
    _: CurrentUser = None,
    task_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    svc = AnnotationTaskService(db)
    items, total = await svc.list_pending(task_status=task_status, page=page, limit=limit)
    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


# ── 데이터셋 ───────────────────────────────────────────────────────

@router.post("/datasets/build", response_model=AnnotationDatasetRead, status_code=202)
async def build_dataset(
    body: DatasetBuildRequest,
    db: DBSession = None,
    user: CurrentUser = None,
):
    """완료된 어노테이션으로 YOLO 데이터셋 빌드 (비동기)"""
    svc = TrainingService(db)
    result = await svc.build_dataset(created_by=user.id, notes=body.notes)
    await db.commit()
    return result


@router.get("/datasets", response_model=PaginatedResponse[AnnotationDatasetRead])
async def list_datasets(
    db: DBSession = None,
    _: CurrentUser = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    svc = TrainingService(db)
    items, total = await svc.list_datasets(page=page, limit=limit)
    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


# ── 학습 잡 ───────────────────────────────────────────────────────

@router.post("/training-jobs", response_model=TrainingJobRead, status_code=201)
async def start_training(
    body: TrainingJobCreate,
    db: DBSession = None,
    user: CurrentUser = None,
):
    svc = TrainingService(db)
    result = await svc.start_training(body, created_by=user.id)
    await db.commit()
    return result


@router.get("/training-jobs", response_model=PaginatedResponse[TrainingJobRead])
async def list_training_jobs(
    db: DBSession = None,
    _: CurrentUser = None,
    job_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    svc = TrainingService(db)
    items, total = await svc.list_jobs(job_status=job_status, page=page, limit=limit)
    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.get("/training-jobs/{job_id}", response_model=TrainingJobRead)
async def get_training_job(job_id: uuid.UUID, db: DBSession = None, _: CurrentUser = None):
    return await TrainingService(db).get_job(job_id)


@router.patch("/training-jobs/{job_id}/activate", response_model=TrainingJobRead)
async def activate_model(job_id: uuid.UUID, db: DBSession = None, _: CurrentUser = None):
    """학습 완료 모델을 활성 추론 모델로 지정"""
    svc = TrainingService(db)
    result = await svc.activate_model(job_id)
    await db.commit()
    return result

