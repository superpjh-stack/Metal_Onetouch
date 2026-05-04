"""품질 검사 스키마"""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DefectDetailCreate(BaseModel):
    defect_code: str
    defect_type: Literal["dimensional", "surface", "weld", "material", "assembly", "other"]
    qty: Decimal = Decimal("1")
    description: str | None = None
    root_cause: str | None = None


class DefectDetailRead(BaseModel):
    id: UUID
    inspection_id: UUID
    defect_code: str
    defect_type: str
    qty: Decimal
    description: str | None
    root_cause: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QualityInspectionCreate(BaseModel):
    lot_id: UUID
    inspection_type: Literal["incoming", "in_process", "final", "shipment"]
    result: Literal["pass", "fail", "conditional"]
    defect_rate: Decimal = Decimal("0")
    inspection_date: datetime | None = None
    notes: str | None = None
    defects: list[DefectDetailCreate] = []


class QualityInspectionRead(BaseModel):
    id: UUID
    lot_id: UUID
    inspector_id: UUID | None
    inspection_type: str
    result: str
    defect_rate: Decimal
    inspection_date: datetime
    notes: str | None
    defects: list[DefectDetailRead] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DefectStatsItem(BaseModel):
    group_key: str
    group_label: str
    total_inspections: int
    fail_count: int
    avg_defect_rate: float


class DefectStatsResponse(BaseModel):
    group_by: str
    period_days: int
    items: list[DefectStatsItem]
