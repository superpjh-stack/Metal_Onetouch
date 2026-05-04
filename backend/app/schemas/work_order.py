"""작업지시 및 공정 실적 Pydantic 스키마"""
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

WOStatusEnum = Literal["pending", "in_progress", "completed", "on_hold", "cancelled"]


class WorkOrderCreate(BaseModel):
    lot_id: uuid.UUID
    process_id: uuid.UUID
    equipment_id: Optional[uuid.UUID] = None
    assigned_to: Optional[uuid.UUID] = None
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    input_qty: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class WorkOrderRead(WorkOrderCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    wo_number: str
    status: WOStatusEnum
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    output_qty: Optional[float] = None
    defect_qty: float
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    process_results: list["ProcessResultRead"] = []


class WorkOrderUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_id: Optional[uuid.UUID] = None
    assigned_to: Optional[uuid.UUID] = None
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    input_qty: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class WorkOrderStatusUpdate(BaseModel):
    """작업지시 상태 전환 스키마"""
    model_config = ConfigDict(from_attributes=True)

    status: WOStatusEnum
    notes: Optional[str] = None


# ------------------------------------------------------------------
# Process Result schemas
# ------------------------------------------------------------------

class ProcessResultCreate(BaseModel):
    input_qty: float = Field(..., ge=0)
    output_qty: float = Field(..., ge=0)
    defect_qty: float = Field(default=0, ge=0)
    start_time: datetime
    end_time: datetime
    equipment_id: Optional[uuid.UUID] = None
    worker_id: Optional[uuid.UUID] = None
    condition_notes: Optional[str] = None
    defect_reason: Optional[str] = None


class ProcessResultRead(ProcessResultCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    work_order_id: uuid.UUID
    lot_id: uuid.UUID
    created_at: datetime


# Resolve forward reference
WorkOrderRead.model_rebuild()
