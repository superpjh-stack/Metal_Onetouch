"""BOM 내보내기 API"""
import uuid

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.deps import CurrentUser, DBSession
from app.schemas.bom import BomRead
from app.services.bom_service import BomService

router = APIRouter(tags=["BOM"])


@router.get("/{bom_id}/export")
async def export_bom(bom_id: uuid.UUID, db: DBSession, _: CurrentUser):
    """BOM Excel 내보내기"""
    xlsx_bytes = await BomService(db).export_xlsx(bom_id)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=bom-{bom_id}.xlsx"},
    )
