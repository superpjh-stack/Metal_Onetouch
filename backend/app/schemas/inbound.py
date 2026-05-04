"""원자재 입고 스키마"""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReceiptCreate(BaseModel):
    supplier_id: UUID
    material_name: str
    material_code: str | None = None
    quantity: Decimal
    unit: str = "kg"
    unit_price: Decimal | None = None
    received_date: date
    notes: str | None = None


class ReceiptRead(BaseModel):
    id: UUID
    receipt_number: str
    supplier_id: UUID
    supplier_name: str | None = None
    lot_id: UUID | None
    lot_display_id: str | None = None
    material_name: str
    material_code: str | None
    quantity: Decimal
    unit: str
    unit_price: Decimal | None
    received_date: date
    notes: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SupplierReceiptStats(BaseModel):
    supplier_id: UUID
    supplier_name: str
    total_receipts: int
    total_quantity: float
    avg_unit_price: float | None
    last_received_date: date | None
