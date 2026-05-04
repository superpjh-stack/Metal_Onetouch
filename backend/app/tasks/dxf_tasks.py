"""DXF 파일 파싱 Celery 태스크"""
import asyncio
import uuid
from datetime import datetime

from app.core.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.dxf_tasks.parse_dxf_task",
    queue="cad_queue",
    max_retries=1,
    default_retry_delay=5,
    soft_time_limit=30,
    time_limit=60,
)
def parse_dxf_task(self, drawing_id: str) -> None:
    asyncio.run(_run_dxf_parse(drawing_id))


async def _run_dxf_parse(drawing_id: str) -> None:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.storage import storage_service
    from app.models.cad import CadDrawing
    from app.models.file import UploadedFile
    from app.services.dxf_parser_service import DxfParserService

    async with AsyncSessionLocal() as db:
        drawing = (await db.execute(
            select(CadDrawing).where(CadDrawing.id == uuid.UUID(drawing_id))
        )).scalar_one_or_none()
        if not drawing:
            return

        drawing.analysis_status = "analyzing"
        await db.commit()

        try:
            file_record = (await db.execute(
                select(UploadedFile).where(UploadedFile.id == drawing.file_id)
            )).scalar_one_or_none()
            if not file_record:
                raise ValueError("File record not found")

            import httpx
            download_url = storage_service.get_presigned_download_url(
                file_record.bucket, file_record.object_key
            )
            async with httpx.AsyncClient() as http:
                resp = await http.get(download_url)
                resp.raise_for_status()
                file_bytes = resp.content

            svc = DxfParserService(db)
            result = await svc.parse(file_bytes)

            drawing.raw_result = result
            drawing.parsed_objects = {"objects": result.get("objects", [])}
            drawing.dimensions = result.get("dimensions")
            drawing.confidence = float(result.get("confidence", 1.0))
            drawing.analysis_status = "completed" if not result.get("error") else "failed"
            drawing.analyzed_at = datetime.utcnow()
            if result.get("error"):
                drawing.error_message = result["error"]

        except Exception as exc:
            drawing.analysis_status = "failed"
            drawing.error_message = str(exc)

        await db.commit()

        # 어노테이션 태스크 자동 생성 (confidence < 0.95)
        if drawing.analysis_status == "completed":
            from app.services.annotation_task_service import AnnotationTaskService
            svc = AnnotationTaskService(db)
            await svc.create_for_drawing(drawing.id)
            await db.commit()
