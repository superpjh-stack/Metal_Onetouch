"""KPI 스키마"""
from pydantic import BaseModel


class KpiSummary(BaseModel):
    production_rate: float
    defect_rate: float
    delivery_rate: float
    shipment_count: int
    targets: dict[str, float]


class KpiTrendItem(BaseModel):
    date: str
    value: float


class KpiProductionData(BaseModel):
    production_rate: float
    target: float | None
    trend: list[KpiTrendItem]


class KpiQualityData(BaseModel):
    defect_rate: float
    target: float | None
    trend: list[KpiTrendItem]


class KpiDeliveryData(BaseModel):
    delivery_rate: float
    target: float | None
    total_orders: int
    on_time_orders: int


class KpiShipmentData(BaseModel):
    shipment_count: int
    pending_count: int
    delivered_count: int


class KpiTargetUpsert(BaseModel):
    metric_key: str
    target_value: float
    unit: str = "%"
    period: str = "daily"


class KpiTargetsUpdate(BaseModel):
    targets: list[KpiTargetUpsert]
