"""YOLOv8 데이터셋 빌드 + 학습 잡 관리 서비스"""
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import AnnotationDataset, AnnotationTask, TrainingJob
from app.schemas.ml import AnnotationDatasetRead, TrainingJobCreate, TrainingJobRead


YOLO_CLASS_MAP = {"hole": 0, "bend": 1, "cut": 2, "weld": 3, "slot": 4}


class TrainingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _next_dataset_version(self) -> str:
        count = (await self.db.execute(
            select(func.count(AnnotationDataset.id))
        )).scalar_one() or 0
        major = count // 10 + 1
        minor = count % 10
        return f"v{major}.{minor}"

    async def build_dataset(
        self, created_by: uuid.UUID, notes: Optional[str] = None
    ) -> AnnotationDatasetRead:
        from app.core.config import settings

        min_images = getattr(settings, "DATASET_MIN_IMAGES", 50)

        completed_tasks = (await self.db.execute(
            select(AnnotationTask).where(AnnotationTask.status == "completed")
        )).scalars().all()

        if len(completed_tasks) < min_images:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"최소 {min_images}개의 완료된 어노테이션이 필요합니다 (현재: {len(completed_tasks)}개)",
            )

        version = await self._next_dataset_version()
        dataset = AnnotationDataset(
            version=version,
            image_count=len(completed_tasks),
            label_counts=self._count_labels(completed_tasks),
            status="building",
            notes=notes,
            created_by=created_by,
        )
        self.db.add(dataset)
        await self.db.flush()
        await self.db.refresh(dataset)

        # 비동기 빌드 태스크 (MinIO 업로드는 Celery 내부에서)
        from app.tasks.training_tasks import build_dataset_task
        build_dataset_task.delay(str(dataset.id))

        return AnnotationDatasetRead.model_validate(dataset)

    def _count_labels(self, tasks: list[AnnotationTask]) -> dict:
        counts: dict[str, int] = {}
        for task in tasks:
            parsed = task.corrected_parsed or task.original_parsed
            for obj in (parsed or {}).get("objects", []):
                label = obj.get("type", "cut")
                counts[label] = counts.get(label, 0) + 1
        return counts

    async def start_training(
        self, data: TrainingJobCreate, created_by: uuid.UUID
    ) -> TrainingJobRead:
        dataset = (await self.db.execute(
            select(AnnotationDataset).where(AnnotationDataset.id == data.dataset_id)
        )).scalar_one_or_none()
        if not dataset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
        if dataset.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dataset not ready (status: {dataset.status})",
            )

        job = TrainingJob(
            dataset_id=data.dataset_id,
            model_version=data.model_version,
            epochs=data.epochs,
            batch_size=data.batch_size,
            img_size=data.img_size,
            hyperparams=data.hyperparams,
            status="pending",
            created_by=created_by,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)

        from app.tasks.training_tasks import train_yolo_model_task
        train_yolo_model_task.delay(str(job.id))

        return TrainingJobRead.model_validate(job)

    async def activate_model(self, job_id: uuid.UUID) -> TrainingJobRead:
        job = await self._get_job_or_404(job_id)
        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only completed jobs can be activated",
            )
        if job.val_map50 is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Job has no val_map50 score",
            )

        # 기존 활성 모델 비활성화
        existing_active = (await self.db.execute(
            select(TrainingJob).where(TrainingJob.is_active == True)
        )).scalars().all()
        for j in existing_active:
            j.is_active = False

        job.is_active = True
        # YoloService 캐시 무효화
        from app.services.yolo_service import YoloService
        YoloService._model_cache.clear()

        await self.db.flush()
        await self.db.refresh(job)
        return TrainingJobRead.model_validate(job)

    async def get_job(self, job_id: uuid.UUID) -> TrainingJobRead:
        return TrainingJobRead.model_validate(await self._get_job_or_404(job_id))

    async def list_jobs(
        self, job_status: Optional[str] = None, page: int = 1, limit: int = 20
    ) -> tuple[list[TrainingJobRead], int]:
        q = select(TrainingJob)
        if job_status:
            q = q.where(TrainingJob.status == job_status)

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        rows = (await self.db.execute(
            q.order_by(TrainingJob.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )).scalars().all()

        return [TrainingJobRead.model_validate(r) for r in rows], total

    async def list_datasets(
        self, page: int = 1, limit: int = 20
    ) -> tuple[list[AnnotationDatasetRead], int]:
        total = (await self.db.execute(select(func.count(AnnotationDataset.id)))).scalar_one()
        rows = (await self.db.execute(
            select(AnnotationDataset)
            .order_by(AnnotationDataset.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )).scalars().all()
        return [AnnotationDatasetRead.model_validate(r) for r in rows], total

    async def _get_job_or_404(self, job_id: uuid.UUID) -> TrainingJob:
        job = (await self.db.execute(
            select(TrainingJob).where(TrainingJob.id == job_id)
        )).scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training job not found")
        return job
