"""수주 스키마"""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrderItemCreate(BaseModel):
    material_name: str
    material_code: str | None = None
    quantity: Decimal
    unit: str = "ea"
    unit_price: Decimal | None = None


class OrderCreate(BaseModel):
    customer_id: UUID
    ordered_date: date
    due_date: date | None = None
    notes: str | None = None
    items: list[OrderItemCreate] = []


class OrderStatusUpdate(BaseModel):
    status: Literal["confirmed", "in_production", "shipped", "completed", "cancelled"]
    notes: str | None = None


class OrderItemRead(BaseModel):
    id: UUID
    material_name: str
    material_code: str | None
    quantity: Decimal
    unit: str
    unit_price: Decimal | None
    lot_id: UUID | None
    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    id: UUID
    order_number: str
    customer_id: UUID
    customer_name: str | None = None
    status: str
    ordered_date: date
    due_date: date | None
    total_amount: Decimal | None
    items: list[OrderItemRead] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
