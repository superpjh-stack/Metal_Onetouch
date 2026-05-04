"""단가 마스터 스키마"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProcessPriceRead(BaseModel):
    id: uuid.UUID
    process_type: str
    material_grade: Optional[str]
    unit_price: Decimal
    price_unit: str
    effective_from: date
    notes: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class ProcessPriceUpsert(BaseModel):
    process_type: str
    material_grade: Optional[str] = None
    unit_price: Decimal
    price_unit: str
    notes: Optional[str] = None


class MaterialPriceRead(BaseModel):
    id: uuid.UUID
    material_code: str
    material_name: str
    price_per_kg: Decimal
    density: Decimal
    notes: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class MaterialPriceUpsert(BaseModel):
    material_code: str
    material_name: str
    price_per_kg: Decimal
    density: Decimal = Decimal("7.93")
    notes: Optional[str] = None
