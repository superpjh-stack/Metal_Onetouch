"""SQLite 로컬 개발용 DB 초기화 스크립트 (alembic 대신)"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from app.models.base import Base  # 모델들이 실제로 사용하는 Base

# 모든 모델 import (Base.metadata에 등록되도록)
import app.models.user
import app.models.supplier
import app.models.customer
import app.models.raw_material
import app.models.process_type
import app.models.equipment
import app.models.work_order
import app.models.system_log
import app.models.quality
import app.models.shipment
import app.models.ai_agent
import app.models.lot
import app.models.inbound
import app.models.order
import app.models.kpi
import app.models.file
import app.models.price_master
import app.models.cad
import app.models.quotation
import app.models.annotation
import app.models.bom


async def init_db():
    print("DB 테이블 생성 중...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("완료: onetouch_dev.db 생성됨")


if __name__ == "__main__":
    asyncio.run(init_db())
