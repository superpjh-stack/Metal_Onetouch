"""대시보드 집계 API"""
from fastapi import APIRouter, Query

from app.api.deps import DBSession
from app.schemas.dashboard import (
    DashboardSummary,
    LotStatusItem,
    ProductionTrendItem,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: DBSession):
    return await DashboardService(db).get_dashboard_summary()


@router.get("/production-trend", response_model=list[ProductionTrendItem])
async def get_production_trend(
    days: int = Query(default=7, ge=1, le=90),
    db: DBSession,
):
    return await DashboardService(db).get_production_trend(days=days)


@router.get("/lot-status", response_model=list[LotStatusItem])
async def get_lot_status(
    limit: int = Query(default=5, ge=1, le=50),
    db: DBSession,
):
    return await DashboardService(db).get_lot_status_summary(limit=limit)
