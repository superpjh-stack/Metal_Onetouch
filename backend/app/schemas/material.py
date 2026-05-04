"""원자재 Pydantic 스키마"""
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

MaterialCategory = Literal[
    "steel_sheet", "stainless", "aluminum", "copper", "pipe", "bar", "other"
]


class MaterialCreate(BaseModel):
    material_code: str = Field(..., max_length=30)
    name: str = Field(..., max_length=200)
    category: MaterialCategory = "other"
    spec: Optional[str] = Field(None, max_length=200)
    unit: str = Field(default="EA", max_length=20)
    supplier_id: Optional[uuid.UUID] = None
    stock_qty: float = Field(default=0, ge=0)
    min_stock_qty: float = Field(default=0, ge=0)
    unit_price: Optional[float] = Field(None, ge=0)
    lead_time_days: int = Field(default=7, ge=0)
    is_active: bool = True
    notes: Optional[str] = None


class MaterialRead(MaterialCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    # 표시용 — 조인 없이 supplier 이름을 넘겨줄 때 사용
    supplier_name: Optional[str] = None


class MaterialUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, max_length=200)
    category: Optional[MaterialCategory] = None
    spec: Optional[str] = Field(None, max_length=200)
    unit: Optional[str] = Field(None, max_length=20)
    supplier_id: Optional[uuid.UUID] = None
    stock_qty: Optional[float] = Field(None, ge=0)
    min_stock_qty: Optional[float] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, ge=0)
    lead_time_days: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    notes: Optional[str] = None
