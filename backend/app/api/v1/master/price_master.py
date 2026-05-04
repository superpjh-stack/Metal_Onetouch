"""단가 마스터 엔드포인트"""
from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession, require_roles
from app.schemas.price_master import (
    MaterialPriceRead,
    MaterialPriceUpsert,
    ProcessPriceRead,
    ProcessPriceUpsert,
)
from app.services.price_master_service import PriceMasterService

router = APIRouter(tags=["Price Master"])

_require_admin = require_roles("admin", "production_manager")


@router.get("/process-prices", response_model=list[ProcessPriceRead])
async def list_process_prices(db: DBSession, _: CurrentUser):
    """공정 단가 목록"""
    return await PriceMasterService(db).list_process_prices()


@router.put("/process-prices", response_model=list[ProcessPriceRead])
async def upsert_process_prices(
    body: list[ProcessPriceUpsert],
    db: DBSession,
    user: CurrentUser,
    _: None = _require_admin,
):
    """공정 단가 일괄 upsert"""
    svc = PriceMasterService(db)
    result = await svc.upsert_process_prices(body, updated_by=user.id)
    await db.commit()
    return result


@router.get("/material-prices", response_model=list[MaterialPriceRead])
async def list_material_prices(db: DBSession, _: CurrentUser):
    """소재 단가 목록"""
    return await PriceMasterService(db).list_material_prices()


@router.put("/material-prices", response_model=list[MaterialPriceRead])
async def upsert_material_prices(
    body: list[MaterialPriceUpsert],
    db: DBSession,
    user: CurrentUser,
    _: None = _require_admin,
):
    """소재 단가 일괄 upsert"""
    svc = PriceMasterService(db)
    result = await svc.upsert_material_prices(body, updated_by=user.id)
    await db.commit()
    return result
