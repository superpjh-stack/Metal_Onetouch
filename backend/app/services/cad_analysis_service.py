"""CAD 도면 분석 서비스 — GPT-4o Vision + Celery 비동기"""
import json
import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cad import CadDrawing
from app.schemas.cad import CadDrawingCreate, CadDrawingRead, CadStatusResponse, CadUpdateObjects


ANALYSIS_SYSTEM_PROMPT = """당신은 금속 가공 제조 CAD 도면 분석 전문가입니다.
도면 이미지에서 다음 항목을 정확히 추출하여 JSON만 반환하세요 (설명 없이):

{
  "objects": [
    {"type": "hole|slot|bend|cut|weld", "count": int, "diameter"?: float, "width"?: float,
     "length"?: float, "angle"?: float, "radius"?: float, "tolerance"?: string}
  ],
  "dimensions": {"length": float, "width": float, "thickness": float},
  "material_hint": "SUS304|SUS316|SS400|AL6061|SPCC|unknown",
  "confidence": float
}

규칙:
- type은 반드시 hole/slot/bend/cut/weld 중 하나
- count는 도면에 표시된 개수
- confidence: 0.0(불확실)~1.0(확실)
- 치수 단위는 mm
- JSON 외 다른 텍스트 금지"""


class CadAnalysisService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _generate_drawing_number(self) -> str:
        today_str = date.today().strftime("%Y%m%d")
        prefix = f"DRW-{today_str}-"
        count = (await self.db.execute(
            select(func.count(CadDrawing.id)).where(CadDrawing.drawing_number.like(f"{prefix}%"))
        )).scalar_one() or 0
        return f"{prefix}{count + 1:04d}"

    @staticmethod
    def _is_dxf(mime_type: Optional[str], original_name: Optional[str]) -> bool:
        if mime_type and "dxf" in mime_type.lower():
            return True
        if original_name and original_name.lower().endswith(".dxf"):
            return True
        return False

    @staticmethod
    def _is_dwg(mime_type: Optional[str], original_name: Optional[str]) -> bool:
        if mime_type and ("dwg" in mime_type.lower() or "autocad" in mime_type.lower()):
            return True
        if original_name and original_name.lower().endswith(".dwg"):
            return True
        return False

    async def create_drawing(
        self, data: CadDrawingCreate, created_by: uuid.UUID
    ) -> CadDrawingRead:
        from app.models.file import UploadedFile
        file_record = (await self.db.execute(
            select(UploadedFile).where(UploadedFile.id == data.file_id)
        )).scalar_one_or_none()

        if file_record and self._is_dwg(file_record.mime_type, file_record.original_name):
            from fastapi import HTTPException, status as http_status
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="DWG 형식은 지원하지 않습니다. DXF 형식으로 변환 후 업로드해 주세요.",
            )

        drawing_number = await self._generate_drawing_number()
        drawing = CadDrawing(
            drawing_number=drawing_number,
            file_id=data.file_id,
            customer_id=data.customer_id,
            analysis_status="pending",
            notes=data.notes,
            created_by=created_by,
        )
        self.db.add(drawing)
        await self.db.flush()
        await self.db.refresh(drawing)

        # 파일 형식에 따라 분석 태스크 선택
        if file_record and self._is_dxf(file_record.mime_type, file_record.original_name):
            from app.tasks.dxf_tasks import parse_dxf_task
            parse_dxf_task.delay(str(drawing.id))
        else:
            from app.tasks.cad_tasks import analyze_cad_drawing_task
            analyze_cad_drawing_task.delay(str(drawing.id))

        return CadDrawingRead.model_validate(drawing)

    async def get_drawing(self, drawing_id: uuid.UUID) -> CadDrawingRead:
        drawing = await self._get_or_404(drawing_id)
        return CadDrawingRead.model_validate(drawing)

    async def get_status(self, drawing_id: uuid.UUID) -> CadStatusResponse:
        drawing = await self._get_or_404(drawing_id)
        return CadStatusResponse.model_validate(drawing)

    async def update_objects(
        self, drawing_id: uuid.UUID, data: CadUpdateObjects
    ) -> CadDrawingRead:
        drawing = await self._get_or_404(drawing_id)
        drawing.parsed_objects = {
            "objects": [obj.model_dump(exclude_none=True) for obj in data.objects],
        }
        drawing.dimensions = data.dimensions.model_dump()
        drawing.confidence = 1.0  # 사람이 검증 → 신뢰도 100%
        drawing.analysis_status = "completed"
        drawing.analyzed_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(drawing)
        return CadDrawingRead.model_validate(drawing)

    async def list_drawings(
        self,
        analysis_status: Optional[str] = None,
        customer_id: Optional[uuid.UUID] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[CadDrawingRead], int]:
        q = select(CadDrawing)
        if analysis_status:
            q = q.where(CadDrawing.analysis_status == analysis_status)
        if customer_id:
            q = q.where(CadDrawing.customer_id == customer_id)

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        rows = (await self.db.execute(
            q.order_by(CadDrawing.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )).scalars().all()

        return [CadDrawingRead.model_validate(r) for r in rows], total

    async def _get_or_404(self, drawing_id: uuid.UUID) -> CadDrawing:
        drawing = (await self.db.execute(
            select(CadDrawing).where(CadDrawing.id == drawing_id)
        )).scalar_one_or_none()
        if not drawing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drawing not found")
        return drawing

    @staticmethod
    async def run_analysis(drawing_id: str) -> None:
        """Celery 태스크에서 호출 — 독립 DB 세션으로 실행"""
        import base64
        import httpx
        from openai import AsyncOpenAI
        from app.core.config import settings
        from app.core.database import AsyncSessionLocal
        from app.core.storage import storage_service

        async with AsyncSessionLocal() as db:
            drawing = (await db.execute(
                select(CadDrawing).where(CadDrawing.id == uuid.UUID(drawing_id))
            )).scalar_one_or_none()
            if not drawing:
                return

            drawing.analysis_status = "analyzing"
            await db.commit()

            try:
                # MinIO에서 파일 다운로드
                from app.models.file import UploadedFile
                file_record = (await db.execute(
                    select(UploadedFile).where(UploadedFile.id == drawing.file_id)
                )).scalar_one_or_none()
                if not file_record:
                    raise ValueError("File record not found")

                download_url = storage_service.get_presigned_download_url(
                    file_record.bucket, file_record.object_key
                )

                # 이미지 다운로드 후 base64 인코딩
                async with httpx.AsyncClient() as http:
                    resp = await http.get(download_url)
                    resp.raise_for_status()
                    image_data = base64.b64encode(resp.content).decode("utf-8")

                mime = file_record.mime_type or "image/jpeg"

                # GPT-4o Vision API 호출
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                response = await client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime};base64,{image_data}",
                                        "detail": "high",
                                    },
                                }
                            ],
                        },
                    ],
                    max_tokens=1000,
                )

                raw_text = response.choices[0].message.content or "{}"
                parsed = json.loads(raw_text)

                drawing.raw_result = parsed
                drawing.parsed_objects = {"objects": parsed.get("objects", [])}
                drawing.dimensions = parsed.get("dimensions")
                drawing.material_hint = parsed.get("material_hint")
                drawing.confidence = float(parsed.get("confidence", 0.0))
                drawing.analysis_status = "completed"
                drawing.analyzed_at = datetime.utcnow()

            except Exception as exc:
                drawing.analysis_status = "failed"
                drawing.error_message = str(exc)

            await db.commit()
