"""KPI 엔드포인트"""
from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession, require_roles
from app.schemas.kpi import (
    KpiDeliveryData,
    KpiProductionData,
    KpiQualityData,
    KpiShipmentData,
    KpiSummary,
    KpiTargetsUpdate,
)
from app.services.kpi_service import KpiService

router = APIRouter(tags=["KPI"])


@router.get("/summary", response_model=KpiSummary)
async def get_kpi_summary(db: DBSession = None):
    """4종 KPI 실집계 + 목표값 한 번에"""
    return await KpiService(db).get_summary()


@router.get("/production", response_model=KpiProductionData)
async def get_production_kpi(
    days: int = Query(30, ge=7, le=365),
    db: DBSession = None,
):
    """생산성 KPI + 트렌드"""
    return await KpiService(db).get_production(days=days)


@router.get("/quality", response_model=KpiQualityData)
async def get_quality_kpi(
    days: int = Query(30, ge=7, le=365),
    db: DBSession = None,
):
    """품질 KPI + 트렌드"""
    return await KpiService(db).get_quality(days=days)


@router.get("/delivery", response_model=KpiDeliveryData)
async def get_delivery_kpi(db: DBSession = None):
    """납기 KPI"""
    return await KpiService(db).get_delivery()


@router.get("/shipment", response_model=KpiShipmentData)
async def get_shipment_kpi(db: DBSession = None):
    """출하 KPI"""
    return await KpiService(db).get_shipment()


@router.put("/targets", response_model=list[dict])
async def update_kpi_targets(
    body: KpiTargetsUpdate,
    db: DBSession = None,
    user: CurrentUser = None,
    _: None = require_roles("admin"),
):
    """KPI 목표값 일괄 업데이트"""
    svc = KpiService(db)
    rows = await svc.upsert_targets(body.targets, updated_by=user.id)
    await db.commit()
    return [{"metric_key": r.metric_key, "target_value": float(r.target_value), "unit": r.unit} for r in rows]
