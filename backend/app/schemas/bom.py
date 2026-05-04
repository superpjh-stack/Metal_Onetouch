"""BOM Pydantic 스키마"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BomItemRead(BaseModel):
    id: uuid.UUID
    material_code: str
    specification: str
    quantity: float
    unit: str
    unit_weight_kg: Optional[float] = None
    total_weight_kg: float
    sort_order: int

    model_config = {"from_attributes": True}


class BomRead(BaseModel):
    id: uuid.UUID
    quotation_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    revision: int
    total_weight_kg: float
    notes: Optional[str] = None
    items: list[BomItemRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
