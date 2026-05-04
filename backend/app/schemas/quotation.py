"""견적서 스키마"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class QuotationItemRead(BaseModel):
    id: uuid.UUID
    item_type: str
    description: Optional[str]
    quantity: Decimal
    unit: Optional[str]
    unit_price: Decimal
    amount: Decimal
    sort_order: int
    model_config = ConfigDict(from_attributes=True)


class QuotationItemCreate(BaseModel):
    item_type: str
    description: Optional[str] = None
    quantity: Decimal = Decimal("1")
    unit: Optional[str] = None
    unit_price: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")
    sort_order: int = 0


class QuotationItemUpdate(BaseModel):
    id: uuid.UUID
    unit_price: Decimal
    quantity: Optional[Decimal] = None
    description: Optional[str] = None


class QuotationCreate(BaseModel):
    customer_id: uuid.UUID
    drawing_id: Optional[uuid.UUID] = None
    material_code: Optional[str] = None
    margin_rate: float = 0.15
    notes: Optional[str] = None


class QuotationRead(BaseModel):
    id: uuid.UUID
    quotation_number: str
    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    drawing_id: Optional[uuid.UUID]
    order_id: Optional[uuid.UUID]
    status: str
    material_cost: Decimal
    process_cost: Decimal
    total_amount: Decimal
    margin_rate: Decimal
    final_amount: Decimal
    valid_until: Optional[date]
    version: int
    notes: Optional[str]
    items: list[QuotationItemRead] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QuotationSummary(BaseModel):
    id: uuid.UUID
    quotation_number: str
    customer_name: Optional[str]
    final_amount: Decimal
    total_amount: Decimal
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QuotationLinkOrder(BaseModel):
    order_id: uuid.UUID
