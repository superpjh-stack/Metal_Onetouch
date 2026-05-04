"""설비 Pydantic 스키마"""
import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

EquipmentStatusEnum = Literal[
    "running", "idle", "maintenance", "breakdown", "decommissioned"
]


class EquipmentCreate(BaseModel):
    equipment_code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=200)
    process_id: Optional[uuid.UUID] = None
    manufacturer: Optional[str] = Field(None, max_length=100)
    model_no: Optional[str] = Field(None, max_length=100)
    serial_no: Optional[str] = Field(None, max_length=100)
    status: EquipmentStatusEnum = "idle"
    installed_at: Optional[date] = None
    last_maint_at: Optional[date] = None
    next_maint_at: Optional[date] = None
    location: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    notes: Optional[str] = None


class EquipmentRead(EquipmentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EquipmentUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, max_length=200)
    process_id: Optional[uuid.UUID] = None
    manufacturer: Optional[str] = Field(None, max_length=100)
    model_no: Optional[str] = Field(None, max_length=100)
    serial_no: Optional[str] = Field(None, max_length=100)
    status: Optional[EquipmentStatusEnum] = None
    installed_at: Optional[date] = None
    last_maint_at: Optional[date] = None
    next_maint_at: Optional[date] = None
    location: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class EquipmentStatusUpdate(BaseModel):
    """설비 상태 단독 변경 스키마"""
    model_config = ConfigDict(from_attributes=True)

    status: EquipmentStatusEnum
    notes: Optional[str] = None
