"""PostgreSQL 로컬 개발용 DB 초기화 스크립트

실행 전 조건:
  - PostgreSQL이 로컬에 설치/실행 중
  - psql 또는 pgAdmin으로 'onetouch_mes' DB가 미리 생성되어 있어야 함
    → CREATE DATABASE onetouch_mes;

사용법:
  cd backend
  python scripts/init_pg_db.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.core.db_compat  # noqa: F401

from app.core.database import engine
from app.core.config import settings

# 모든 모델 import (Base.metadata에 등록)
from app.models import (  # noqa: F401
    Base, User, Lot, LotHistory, Supplier, Customer, RawMaterial,
    ProcessType, Equipment, WorkOrder, ProcessResult, SystemLog,
    QualityInspection, DefectDetail, Shipment, ShipmentLot,
    AIConversation, AIMessage, RawMaterialReceipt, Order, OrderItem,
    KpiTarget, UploadedFile, CadDrawing, ProcessPriceMaster,
    MaterialPriceMaster, Quotation, QuotationItem, AnnotationTask,
    AnnotationDataset, TrainingJob, DxfLayerMapping, BomHeader, BomItem,
)


async def init_db():
    print(f"DB 연결: {settings.DATABASE_URL}")
    print("테이블 생성 중...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("완료: 모든 테이블 생성됨")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
