"""어노테이션 태스크 서비스"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import AnnotationTask
from app.models.cad import CadDrawing
from app.schemas.ml import AnnotationTaskRead


class AnnotationTaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_for_drawing(self, drawing_id: uuid.UUID) -> Optional[AnnotationTask]:
        """CAD 분석 완료 후 자동 태스크 생성. confidence >= 0.95 → skipped."""
        drawing = (await self.db.execute(
            select(CadDrawing).where(CadDrawing.id == drawing_id)
        )).scalar_one_or_none()
        if not drawing or drawing.analysis_status != "completed":
            return None

        # 이미 태스크가 존재하면 생성하지 않음
        existing = (await self.db.execute(
            select(AnnotationTask).where(AnnotationTask.drawing_id == drawing_id)
        )).scalar_one_or_none()
        if existing:
            return existing

        confidence = float(drawing.confidence or 0.0)
        parsed = drawing.parsed_objects or {"objects": []}

        if confidence >= 0.95:
            task = AnnotationTask(
                drawing_id=drawing_id,
                status="skipped",
                original_parsed=parsed,
                skip_reason=f"confidence={confidence:.2f} >= 0.95",
            )
        else:
            task = AnnotationTask(
                drawing_id=drawing_id,
                status="pending",
                original_parsed=parsed,
            )

        self.db.add(task)
        await self.db.flush()
        return task

    async def list_pending(
        self,
        task_status: Optional[str] = None,
        annotator_id: Optional[uuid.UUID] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[AnnotationTaskRead], int]:
        q = select(AnnotationTask)
        if task_status:
            q = q.where(AnnotationTask.status == task_status)
        if annotator_id:
            q = q.where(AnnotationTask.annotator_id == annotator_id)

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        rows = (await self.db.execute(
            q.order_by(AnnotationTask.created_at.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )).scalars().all()

        return [AnnotationTaskRead.model_validate(r) for r in rows], total

    async def get_by_drawing(self, drawing_id: uuid.UUID) -> Optional[AnnotationTaskRead]:
        task = (await self.db.execute(
            select(AnnotationTask).where(AnnotationTask.drawing_id == drawing_id)
        )).scalar_one_or_none()
        return AnnotationTaskRead.model_validate(task) if task else None

    async def submit_correction(
        self,
        drawing_id: uuid.UUID,
        corrected_parsed: dict,
        annotator_id: uuid.UUID,
    ) -> AnnotationTaskRead:
        task = (await self.db.execute(
            select(AnnotationTask).where(AnnotationTask.drawing_id == drawing_id)
        )).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation task not found")

        task.corrected_parsed = corrected_parsed
        task.annotator_id = annotator_id
        task.status = "completed"
        task.completed_at = datetime.utcnow()

        # cad_drawings.parsed_objects 업데이트 (최신 보정 결과 반영)
        drawing = (await self.db.execute(
            select(CadDrawing).where(CadDrawing.id == drawing_id)
        )).scalar_one_or_none()
        if drawing:
            drawing.parsed_objects = corrected_parsed
            drawing.confidence = 1.0

        await self.db.flush()
        await self.db.refresh(task)
        return AnnotationTaskRead.model_validate(task)

    async def skip_task(self, drawing_id: uuid.UUID, reason: str) -> AnnotationTaskRead:
        task = (await self.db.execute(
            select(AnnotationTask).where(AnnotationTask.drawing_id == drawing_id)
        )).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation task not found")
        task.status = "skipped"
        task.skip_reason = reason
        await self.db.flush()
        await self.db.refresh(task)
        return AnnotationTaskRead.model_validate(task)
