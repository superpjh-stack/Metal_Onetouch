"""대시보드 Pydantic 스키마 — 프론트엔드 계약과 일치"""
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DayOverDayDelta(BaseModel):
    production: float = 0.0
    defect_rate: float = 0.0
    equipment_utilization: float = 0.0
    pending_shipments: float = 0.0


class DashboardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    today_production: float       # 오늘 총 생산량 (output_qty 합계)
    defect_rate: float            # 불량률 (%)
    equipment_utilization: float  # 설비 가동률 (%) — running / total_active * 100
    pending_shipments: int        # 출하 대기 건수 (Sprint 3 전까지 0)
    compared_to_prev_day: DayOverDayDelta


class ProductionTrendItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str           # "MM/DD" 포맷
    planned: float      # 계획 수량 (work_order input_qty 합계)
    actual: float       # 실적 수량 (process_result output_qty 합계)
    defects: float      # 불량 수량


class LotStatusItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lot_id: str         # L20260430-0001 형식
    item: str           # product_name or raw_material_name
    status: str         # lot_status 한글 레이블
    process: str        # 최근 공정명 or '-'
    operator: str       # 마지막 작업자명 or '-'
