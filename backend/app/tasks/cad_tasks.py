"""CAD 도면 분석 Celery 태스크"""
import asyncio

from app.core.celery_app import celery_app


@celery_app.task(
    name="analyze_cad_drawing",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def analyze_cad_drawing_task(self, drawing_id: str) -> None:
    """비동기 CAD 분석 — Celery Worker에서 asyncio.run으로 실행"""
    from app.services.cad_analysis_service import CadAnalysisService
    try:
        asyncio.run(CadAnalysisService.run_analysis(drawing_id))
    except Exception as exc:
        raise self.retry(exc=exc)
    # 분석 완료 후 어노테이션 태스크 자동 생성
    asyncio.run(_create_annotation_task(drawing_id))


async def _create_annotation_task(drawing_id: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.annotation_task_service import AnnotationTaskService
    import uuid
    async with AsyncSessionLocal() as db:
        svc = AnnotationTaskService(db)
        await svc.create_for_drawing(uuid.UUID(drawing_id))
        await db.commit()
