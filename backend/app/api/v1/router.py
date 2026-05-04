from fastapi import APIRouter

from app.api.v1 import auth, lots
from app.api.v1.master import suppliers, customers, materials
from app.api.v1.master import processes as process_routes
from app.api.v1.master import equipment
from app.api.v1.master import price_master
from app.api.v1 import work_orders, dashboard, users
from app.api.v1 import quality, shipments, ai_agent
from app.api.v1 import inbound, kpi, orders
from app.api.v1 import files, cad, quotations, ml, bom

# 메인 v1 라우터
api_v1_router = APIRouter(prefix="/api/v1")

# Sprint 1 라우터
api_v1_router.include_router(auth.router)
api_v1_router.include_router(lots.router)

# Sprint 2 — 기준정보 마스터 라우터
master_router = APIRouter(prefix="/master")
master_router.include_router(suppliers.router)
master_router.include_router(customers.router)
master_router.include_router(materials.router)
master_router.include_router(process_routes.router)
master_router.include_router(equipment.router)
master_router.include_router(price_master.router)

api_v1_router.include_router(master_router)

# Sprint 2 — 작업지시, 대시보드, 사용자 관리
api_v1_router.include_router(
    work_orders.router, prefix="/work-orders", tags=["Work Orders"]
)
api_v1_router.include_router(
    dashboard.router, prefix="/dashboard", tags=["Dashboard"]
)
api_v1_router.include_router(users.router, prefix="/users", tags=["Users"])

# Sprint 3 — 품질검사, 출하물류, AI Agent
api_v1_router.include_router(quality.router,   prefix="/quality",   tags=["Quality"])
api_v1_router.include_router(shipments.router, prefix="/shipments", tags=["Shipments"])
api_v1_router.include_router(ai_agent.router,  prefix="/ai-agent",  tags=["AI Agent"])

# Sprint 4 — 입고관리, KPI, 수주
api_v1_router.include_router(inbound.router, prefix="/inbound", tags=["Inbound"])
api_v1_router.include_router(kpi.router,     prefix="/kpi",     tags=["KPI"])
api_v1_router.include_router(orders.router,  prefix="/orders",  tags=["Orders"])

# Sprint 5 — 파일 업로드, CAD 분석, 견적
api_v1_router.include_router(files.router,      prefix="/files",      tags=["Files"])
api_v1_router.include_router(cad.router,        prefix="/cad",        tags=["CAD"])
api_v1_router.include_router(quotations.router, prefix="/quotations", tags=["Quotations"])

# Sprint 6 — Vision ML, BOM
api_v1_router.include_router(ml.router,  prefix="/ml",  tags=["ML"])
api_v1_router.include_router(bom.router, prefix="/bom", tags=["BOM"])
