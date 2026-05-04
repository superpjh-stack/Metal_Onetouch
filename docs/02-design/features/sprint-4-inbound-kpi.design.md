# Sprint 4 — 입고관리 완성 + KPI 대시보드 Design

> **Feature**: sprint-4-inbound-kpi  
> **Phase**: Design  
> **Date**: 2026-05-04  
> **Status**: Draft  
> **Depends on**: sprint-3-ai-agent (완료, Match Rate 96%)

---

## 1. 개요

Sprint 4는 Phase 2 완성 스프린트로 4개 도메인을 구현합니다:

1. **원자재 입고 관리** — 입고 등록 시 LOT 자동 생성 (LOT 추적 사이클의 시작점)
2. **KPI 대시보드** — 생산성/품질/납기/출하 실집계 + Recharts 시각화
3. **수주 기초 관리** — 수주 등록 + 상태 관리 (Phase 3 CAD Vision AI 연동 전 기초)
4. **Sprint 3 Gap 해소** — Dashboard 실집계 활성화 + logistics LOT 번들링 UI

---

## 2. DB 스키마 (Migration 0007)

### 2.1 raw_material_receipts (원자재 입고)

```sql
CREATE TABLE raw_material_receipts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_number  VARCHAR(30)  NOT NULL UNIQUE,    -- REC-{YYYYMMDD}-{4자리}
    supplier_id     UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    lot_id          UUID REFERENCES lots(id) ON DELETE SET NULL,   -- 생성된 LOT
    material_name   VARCHAR(200) NOT NULL,
    material_code   VARCHAR(50),
    quantity        NUMERIC(12,3) NOT NULL,
    unit            VARCHAR(20)  NOT NULL DEFAULT 'kg',
    unit_price      NUMERIC(15,2),
    received_date   DATE NOT NULL,
    notes           TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_receipt_supplier   ON raw_material_receipts(supplier_id);
CREATE INDEX ix_receipt_lot        ON raw_material_receipts(lot_id);
CREATE INDEX ix_receipt_date       ON raw_material_receipts(received_date);
CREATE INDEX ix_receipt_number     ON raw_material_receipts(receipt_number);
```

**채번 규칙**: `REC-{YYYYMMDD}-{당일 SEQ 4자리}` (ShipmentService 패턴 동일)

### 2.2 orders (수주)

```sql
CREATE TYPE order_status_enum AS ENUM (
    'received',        -- 수주 접수
    'confirmed',       -- 확정
    'in_production',   -- 생산 중
    'shipped',         -- 출하
    'completed',       -- 완료
    'cancelled'        -- 취소
);

CREATE TABLE orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number    VARCHAR(30)  NOT NULL UNIQUE,    -- ORD-{YYYYMMDD}-{4자리}
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    status          order_status_enum NOT NULL DEFAULT 'received',
    ordered_date    DATE NOT NULL,
    due_date        DATE,
    total_amount    NUMERIC(16,2),
    notes           TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_order_customer ON orders(customer_id);
CREATE INDEX ix_order_status   ON orders(status);
CREATE INDEX ix_order_due      ON orders(due_date);
CREATE INDEX ix_order_number   ON orders(order_number);
```

### 2.3 order_items (수주 라인)

```sql
CREATE TABLE order_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id        UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    material_name   VARCHAR(200) NOT NULL,
    material_code   VARCHAR(50),
    quantity        NUMERIC(12,3) NOT NULL,
    unit            VARCHAR(20)  NOT NULL DEFAULT 'ea',
    unit_price      NUMERIC(15,2),
    lot_id          UUID REFERENCES lots(id) ON DELETE SET NULL,   -- nullable, 후에 LOT 연결
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_order_item_order ON order_items(order_id);
CREATE INDEX ix_order_item_lot   ON order_items(lot_id);
```

### 2.4 kpi_targets (KPI 목표값)

```sql
CREATE TABLE kpi_targets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_key      VARCHAR(50) NOT NULL UNIQUE,
    target_value    NUMERIC(10,4) NOT NULL,
    unit            VARCHAR(20) NOT NULL DEFAULT '%',
    period          VARCHAR(10) NOT NULL DEFAULT 'daily',  -- daily/weekly/monthly
    updated_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 초기 시드 데이터 (migration 내 INSERT)
INSERT INTO kpi_targets (metric_key, target_value, unit, period) VALUES
    ('production_rate',    100.0,  '%',   'daily'),
    ('defect_rate',          2.0,  '%',   'daily'),
    ('delivery_rate',       95.0,  '%',   'monthly'),
    ('equipment_utilization', 80.0, '%',  'daily');
```

---

## 3. SQLAlchemy 모델

### 3.1 RawMaterialReceipt (`backend/app/models/inbound.py`)

```python
class RawMaterialReceipt(Base, UUIDMixin):
    __tablename__ = "raw_material_receipts"

    receipt_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True)
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("lots.id", ondelete="SET NULL"), nullable=True, index=True)
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    material_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    received_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())

    supplier = relationship("Supplier")
    lot = relationship("Lot")
```

### 3.2 Order, OrderItem (`backend/app/models/order.py`)

```python
ORDER_STATUS_VALUES = ("received", "confirmed", "in_production", "shipped", "completed", "cancelled")

class Order(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        Enum(*ORDER_STATUS_VALUES, name="order_status_enum"), nullable=False, default="received", index=True
    )
    ordered_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    customer = relationship("Customer")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base, UUIDMixin):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    material_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="ea")
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("lots.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())

    order: Mapped[Order] = relationship("Order", back_populates="items")
    lot = relationship("Lot")
```

### 3.3 KpiTarget (`backend/app/models/kpi.py`)

```python
class KpiTarget(Base, UUIDMixin):
    __tablename__ = "kpi_targets"

    metric_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    target_value: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="%")
    period: Mapped[str] = mapped_column(String(10), nullable=False, default="daily")
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now(), onupdate=func.now())
```

---

## 4. Pydantic 스키마

### 4.1 `backend/app/schemas/inbound.py`

```python
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
    supplier_name: str | None = None      # denormalized
    lot_id: UUID | None
    lot_display_id: str | None = None     # denormalized e.g. "L20260504-0001"
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
```

### 4.2 `backend/app/schemas/order.py`

```python
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
    customer_name: str | None = None      # denormalized
    status: str
    ordered_date: date
    due_date: date | None
    total_amount: Decimal | None
    items: list[OrderItemRead] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

### 4.3 `backend/app/schemas/kpi.py`

```python
class KpiMetric(BaseModel):
    key: str
    label: str
    value: float
    target: float | None
    unit: str
    trend: list[dict] = []      # [{"date": "05/01", "value": 98.5}, ...]

class KpiSummary(BaseModel):
    production_rate: float      # 생산 달성률 (%)
    defect_rate: float          # 불량률 (%)
    delivery_rate: float        # 납기 준수율 (%)
    shipment_count: int         # 당월 출하 건수
    targets: dict[str, float]   # metric_key → target_value

class KpiTargetUpsert(BaseModel):
    metric_key: str
    target_value: float
    unit: str = "%"
    period: str = "daily"

class KpiTargetsUpdate(BaseModel):
    targets: list[KpiTargetUpsert]
```

---

## 5. Service Layer

### 5.1 `backend/app/services/inbound_service.py`

```python
class InboundService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_receipt_number(self) -> str:
        """REC-{YYYYMMDD}-{4자리 SEQ}"""
        today_str = date.today().strftime("%Y%m%d")
        prefix = f"REC-{today_str}-"
        result = await self.db.execute(
            select(func.count(RawMaterialReceipt.id))
            .where(RawMaterialReceipt.receipt_number.like(f"{prefix}%"))
        )
        count = result.scalar_one() or 0
        return f"{prefix}{count + 1:04d}"

    async def create_receipt(
        self, data: ReceiptCreate, created_by: uuid.UUID
    ) -> RawMaterialReceipt:
        """입고 등록 + LOT 자동 생성.
        
        LOT 생성 규칙:
          lot_id = L{YYYYMMDD}-{SEQ}
          lot_status = 'received'
          raw_material_name = data.material_name
          quantity = data.quantity, unit = data.unit
        """
        receipt_number = await self.generate_receipt_number()
        
        # 1. LOT 자동 생성
        lot_id_str = await Lot.generate_lot_id(self.db)
        lot = Lot(
            lot_id=lot_id_str,
            lot_status="received",
            raw_material_name=data.material_name,
            raw_material_id=data.material_code,
            quantity=float(data.quantity),
            unit=data.unit,
            created_by=created_by,
        )
        self.db.add(lot)
        await self.db.flush()  # get lot.id
        
        # 2. 입고 등록
        receipt = RawMaterialReceipt(
            receipt_number=receipt_number,
            supplier_id=data.supplier_id,
            lot_id=lot.id,
            material_name=data.material_name,
            material_code=data.material_code,
            quantity=data.quantity,
            unit=data.unit,
            unit_price=data.unit_price,
            received_date=data.received_date,
            notes=data.notes,
            created_by=created_by,
        )
        self.db.add(receipt)
        await self.db.flush()
        return receipt

    async def list_receipts(
        self,
        supplier_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[RawMaterialReceipt], int]: ...

    async def get_supplier_stats(
        self, period_days: int = 30
    ) -> list[SupplierReceiptStats]: ...
```

### 5.2 `backend/app/services/kpi_service.py`

```python
class KpiService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(self) -> KpiSummary:
        """4종 KPI 실집계 한 번에 반환."""
        production_rate = await self._calc_production_rate()
        defect_rate     = await self._calc_defect_rate()
        delivery_rate   = await self._calc_delivery_rate()
        shipment_count  = await self._calc_shipment_count()
        targets         = await self._load_targets()
        return KpiSummary(...)

    async def _calc_production_rate(self) -> float:
        """WorkOrder.planned_qty vs ProcessResult.output_qty 당월 비율"""

    async def _calc_defect_rate(self) -> float:
        """QualityInspection.defect_rate 당월 평균"""

    async def _calc_delivery_rate(self) -> float:
        """due_date 이내 completed Orders / 전체 completed Orders (당월)"""

    async def _calc_shipment_count(self) -> int:
        """당월 출하 완료 건수 (Shipment.status in ['shipped','delivered'])"""

    async def get_production_trend(self, days: int = 30) -> list[dict]:
        """ProcessResult 기반 daily 집계 (DashboardService.get_production_trend 재사용)"""

    async def get_quality_trend(self, days: int = 30) -> list[dict]:
        """QualityInspection.defect_rate daily 집계"""

    async def upsert_targets(
        self, updates: list[KpiTargetUpsert], updated_by: uuid.UUID
    ) -> list[KpiTarget]:
        """INSERT ... ON CONFLICT (metric_key) DO UPDATE"""
        ...

    async def _load_targets(self) -> dict[str, float]:
        rows = (await self.db.execute(select(KpiTarget))).scalars().all()
        return {r.metric_key: float(r.target_value) for r in rows}
```

### 5.3 `backend/app/services/order_service.py`

```python
ORDER_STATUS_TRANSITIONS = {
    "received":      ["confirmed", "cancelled"],
    "confirmed":     ["in_production", "cancelled"],
    "in_production": ["shipped", "cancelled"],
    "shipped":       ["completed"],
    "completed":     [],
    "cancelled":     [],
}

class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_order_number(self) -> str:
        """ORD-{YYYYMMDD}-{4자리 SEQ}"""

    async def create_order(
        self, data: OrderCreate, created_by: uuid.UUID
    ) -> Order:
        order_number = await self.generate_order_number()
        order = Order(order_number=order_number, ...)
        self.db.add(order)
        await self.db.flush()
        for item in data.items:
            self.db.add(OrderItem(order_id=order.id, **item.model_dump()))
        await self.db.flush()
        return order

    async def update_status(
        self, order_id: uuid.UUID, new_status: str
    ) -> Order:
        """상태 전환 유효성 검증 후 업데이트"""
        order = await self._get_or_404(order_id)
        allowed = ORDER_STATUS_TRANSITIONS.get(order.status, [])
        if new_status not in allowed:
            raise HTTPException(status_code=400, detail=f"Cannot transition {order.status} → {new_status}")
        order.status = new_status
        await self.db.flush()
        return order

    async def link_lot(
        self, order_id: uuid.UUID, item_id: uuid.UUID, lot_id: uuid.UUID
    ) -> OrderItem:
        """OrderItem에 LOT 연결 (생산 시작 후 배정)"""
```

### 5.4 `backend/app/services/dashboard_service.py` (수정)

Sprint 3에서 pre-staged된 두 개의 폴백 코드를 실집계로 교체:

```python
# get_pending_shipments() — 실집계 활성화
async def get_pending_shipments(self) -> int:
    from app.models.shipment import Shipment
    result = await self.db.execute(
        select(func.count(Shipment.id)).where(Shipment.status == "pending")
    )
    return result.scalar_one()

# get_defect_rate() — 실집계 활성화
async def get_defect_rate(self, target: date | None = None) -> float:
    from app.models.quality import QualityInspection
    d = target or date.today()
    s, e = _day_range(d)
    row = (await self.db.execute(
        select(func.coalesce(func.avg(QualityInspection.defect_rate), 0))
        .where(QualityInspection.inspection_date >= s,
               QualityInspection.inspection_date < e)
    )).scalar_one()
    return float(row)
```

---

## 6. API 엔드포인트

### 6.1 입고 관리 (`/api/v1/inbound`)

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `POST` | `/` | 입고 등록 + LOT 자동 생성 | manager |
| `GET` | `/` | 입고 목록 (supplier_id, date_from, date_to, page, limit) | all |
| `GET` | `/{id}` | 입고 상세 | all |
| `GET` | `/stats/supplier` | 공급처별 통계 (period_days) | all |

**POST / Response** (중요):
```json
{
  "id": "...",
  "receipt_number": "REC-20260504-0001",
  "lot_id": "<uuid>",
  "lot_display_id": "L20260504-0001",
  "supplier_name": "현대철강",
  "material_name": "SUS304 2T",
  "quantity": "100.000",
  "unit": "sheet",
  "received_date": "2026-05-04"
}
```

### 6.2 KPI (`/api/v1/kpi`)

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `GET` | `/summary` | 4종 KPI 실집계 + 목표값 한 번에 | all |
| `GET` | `/production` | 생산 KPI + 30일 트렌드 | all |
| `GET` | `/quality` | 품질 KPI + 30일 트렌드 | all |
| `GET` | `/delivery` | 납기 KPI + 당월 Orders 집계 | all |
| `GET` | `/shipment` | 출하 KPI + 당월 집계 | all |
| `PUT` | `/targets` | KPI 목표값 일괄 업데이트 | admin |

### 6.3 수주 (`/api/v1/orders`)

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `GET` | `/` | 수주 목록 (status, customer_id, date_from, date_to) | all |
| `POST` | `/` | 수주 등록 (order_items 포함) | manager |
| `GET` | `/{id}` | 수주 상세 (items 포함) | all |
| `PATCH` | `/{id}/status` | 상태 변경 | manager |

### 6.4 Router 등록 (`/api/v1/router.py` 수정)

```python
from app.api.v1 import inbound, kpi, orders
api_v1_router.include_router(inbound.router, prefix="/inbound", tags=["Inbound"])
api_v1_router.include_router(kpi.router,     prefix="/kpi",     tags=["KPI"])
api_v1_router.include_router(orders.router,  prefix="/orders",  tags=["Orders"])
```

---

## 7. Frontend

### 7.1 `inventory/page.tsx` — 입고 현황 탭 완성

현재 "Sprint 4에서 구현 예정" 플레이스홀더를 실제 구현으로 교체:

```tsx
// 입고 현황 탭 컴포넌트
function InboundTab() {
  const { data, isLoading } = useReceipts({ limit: 50 })
  const receipts = data?.data ?? []
  const [createOpen, setCreateOpen] = useState(false)

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" /> 입고 등록
        </Button>
      </div>
      <DataTable<ReceiptRead>
        isLoading={isLoading}
        data={receipts}
        columns={[
          { key: 'receipt_number', header: '입고번호' },
          { key: 'supplier_name',  header: '공급처' },
          { key: 'material_name',  header: '자재명' },
          { key: 'quantity',       header: '수량', cell: (row) => `${row.quantity} ${row.unit}` },
          { key: 'lot_display_id', header: 'LOT', cell: (row) => (
              <span className="font-mono text-xs text-primary">{row.lot_display_id ?? '-'}</span>
          )},
          { key: 'received_date',  header: '입고일' },
        ]}
      />
      <CreateReceiptDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}
```

`CreateReceiptDialog` 폼 필드:
- 공급처 Select (GET `/api/v1/master/suppliers`)
- 자재명 Input
- 자재코드 Input (optional)
- 수량 Input (number)
- 단위 Select (kg / sheet / piece / m / ea)
- 단가 Input (optional)
- 입고일 date Input (default: today)
- 비고 Input

### 7.2 `kpi/page.tsx` — KPI 대시보드

```tsx
// 레이아웃: 상단 4개 KPI 카드 + 하단 2개 차트 (LineChart × 2)
export default function KpiPage() {
  const { data: summary } = useKpiSummary()
  const { data: prodTrend } = useKpiProductionTrend(30)
  const { data: qualityTrend } = useKpiQualityTrend(30)

  return (
    <div className="space-y-6">
      <PageHeader title="KPI 관리" description="생산성, 품질, 납기, 출하 KPI 실집계" />
      
      {/* 4종 KPI 카드 */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard label="생산 달성률" value={summary?.production_rate} target={summary?.targets.production_rate} unit="%" />
        <KpiCard label="불량률" value={summary?.defect_rate} target={summary?.targets.defect_rate} unit="%" lowerIsBetter />
        <KpiCard label="납기 준수율" value={summary?.delivery_rate} target={summary?.targets.delivery_rate} unit="%" />
        <KpiCard label="당월 출하" value={summary?.shipment_count} unit="건" />
      </div>

      {/* 트렌드 차트 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-sm font-medium mb-3">생산 실적 추이 (30일)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={prodTrend}>
              <XAxis dataKey="date" /><YAxis /><Tooltip />
              <Line dataKey="actual" name="실적" stroke="hsl(var(--primary))" />
              <Line dataKey="planned" name="계획" stroke="hsl(var(--muted-foreground))" strokeDasharray="4 4" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-sm font-medium mb-3">불량률 추이 (30일)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={qualityTrend}>
              <XAxis dataKey="date" /><YAxis /><Tooltip />
              <Line dataKey="defect_rate" name="불량률(%)" stroke="hsl(var(--destructive))" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
```

`KpiCard` 컴포넌트 (`frontend/src/components/ui/kpi-card.tsx`):
```tsx
interface KpiCardProps {
  label: string
  value?: number
  target?: number
  unit: string
  lowerIsBetter?: boolean
}
// 목표 대비 색상: green (달성) / yellow (80%~) / red (미달)
```

### 7.3 `orders/page.tsx` — 수주 목록

```tsx
export default function OrdersPage() {
  // DataTable<OrderRead> + status filter + CreateOrderDialog
  // 컬럼: order_number, customer_name, status (StatusBadge), due_date, items 수, total_amount
}
```

`CreateOrderDialog` 폼:
- 고객사 Select
- 수주일 date Input
- 납기일 date Input (optional)
- 비고 Input
- 수주 라인 동적 rows: [자재명, 자재코드, 수량, 단위, 단가] (+ 행 추가/삭제)

### 7.4 `logistics/page.tsx` — CreateShipmentDialog LOT 번들링 (Sprint 3 Gap 해소)

기존 Dialog에 LOT 추가 섹션 추가:

```tsx
// CreateShipmentDialog 내 추가 섹션
const [lotRows, setLotRows] = useState<{ lot_id: string; qty: string }[]>([])

// LOT 입력 섹션
<div className="space-y-2">
  <div className="flex items-center justify-between">
    <Label>LOT 번들 (선택)</Label>
    <Button type="button" variant="ghost" size="sm" onClick={addLotRow}>
      <Plus className="h-3 w-3" /> 추가
    </Button>
  </div>
  {lotRows.map((row, i) => (
    <div key={i} className="flex gap-2 items-center">
      <Input placeholder="LOT UUID" value={row.lot_id} onChange={...} className="flex-1" />
      <Input type="number" placeholder="수량" value={row.qty} onChange={...} className="w-24" />
      <Button type="button" variant="ghost" size="icon" onClick={() => removeLotRow(i)}>
        <X className="h-4 w-4" />
      </Button>
    </div>
  ))}
</div>

// handleSubmit에서 lots 필드 포함
mutate({
  customer_id: form.customer_id,
  planned_date: form.planned_date || undefined,
  notes: form.notes || undefined,
  lots: lotRows
    .filter(r => r.lot_id.trim())
    .map(r => ({ lot_id: r.lot_id, qty: parseFloat(r.qty) || 1 })),
})
```

---

## 8. React Query Hooks

### 8.1 `frontend/src/lib/hooks/use-inbound.ts`

```typescript
export function useReceipts(params?: { supplier_id?: string; date_from?: string; date_to?: string; limit?: number })
export function useCreateReceipt()     // POST /api/v1/inbound → invalidate receipts + lots
export function useSupplierStats(period_days?: number)   // GET /api/v1/inbound/stats/supplier
```

### 8.2 `frontend/src/lib/hooks/use-kpi.ts`

```typescript
export function useKpiSummary()                         // GET /api/v1/kpi/summary
export function useKpiProductionTrend(days?: number)    // GET /api/v1/kpi/production
export function useKpiQualityTrend(days?: number)       // GET /api/v1/kpi/quality
export function useUpdateKpiTargets()                   // PUT /api/v1/kpi/targets
```

### 8.3 `frontend/src/lib/hooks/use-orders.ts`

```typescript
export function useOrders(params?: { status?: string; customer_id?: string })
export function useCreateOrder()          // POST /api/v1/orders → invalidate orders
export function useUpdateOrderStatus()    // PATCH /api/v1/orders/{id}/status
```

---

## 9. Alembic Migration 0007

**파일**: `backend/alembic/versions/0007_inbound_orders_kpi.py`

```python
revision = "0007"
down_revision = "0006"

def upgrade():
    # order_status_enum
    op.execute("CREATE TYPE order_status_enum AS ENUM ('received','confirmed','in_production','shipped','completed','cancelled')")
    
    # raw_material_receipts
    op.create_table("raw_material_receipts", ...)
    op.create_index("ix_receipt_supplier", ...)
    op.create_index("ix_receipt_lot", ...)
    op.create_index("ix_receipt_date", ...)
    op.create_index("ix_receipt_number", ...)
    
    # orders
    op.create_table("orders", ...)
    # 4개 인덱스
    
    # order_items
    op.create_table("order_items", ...)
    # 2개 인덱스
    
    # kpi_targets
    op.create_table("kpi_targets", ...)
    op.create_index("ix_kpi_key", "kpi_targets", ["metric_key"], unique=True)
    
    # 초기 KPI 목표값 시드
    op.execute("""
        INSERT INTO kpi_targets (metric_key, target_value, unit, period) VALUES
        ('production_rate', 100.0, '%', 'daily'),
        ('defect_rate', 2.0, '%', 'daily'),
        ('delivery_rate', 95.0, '%', 'monthly'),
        ('equipment_utilization', 80.0, '%', 'daily')
    """)

def downgrade():
    op.drop_table("kpi_targets")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("raw_material_receipts")
    op.execute("DROP TYPE order_status_enum")
```

---

## 10. `__init__.py` 업데이트

### `backend/app/models/__init__.py`에 추가

```python
from app.models.inbound import RawMaterialReceipt
from app.models.order import Order, OrderItem
from app.models.kpi import KpiTarget
```

---

## 11. 구현 순서 (Day별 가이드)

### Day 1 — Migration + 모델 + 서비스 기반
1. `0007_inbound_orders_kpi.py` 마이그레이션 작성
2. `models/inbound.py`, `models/order.py`, `models/kpi.py` 작성
3. `models/__init__.py` 업데이트
4. `schemas/inbound.py`, `schemas/order.py`, `schemas/kpi.py` 작성
5. `services/inbound_service.py` 작성 (create_receipt + LOT 자동생성 로직 포함)
6. `dashboard_service.py` 실집계 활성화 (두 군데 코드 주석 해제)

### Day 2 — API 엔드포인트
7. `api/v1/inbound.py` 4개 엔드포인트
8. `api/v1/kpi.py` 6개 엔드포인트 + `services/kpi_service.py`
9. `api/v1/orders.py` 4개 엔드포인트 + `services/order_service.py`
10. `api/v1/router.py` 3개 라우터 등록

### Day 3 — Frontend 훅 + 컴포넌트
11. `hooks/use-inbound.ts`, `hooks/use-kpi.ts`, `hooks/use-orders.ts`
12. `components/ui/kpi-card.tsx`

### Day 4 — Frontend 페이지
13. `inventory/page.tsx` 입고 현황 탭 구현 + CreateReceiptDialog
14. `kpi/page.tsx` KPI 대시보드 (4카드 + 2차트)
15. `orders/page.tsx` 수주 목록 + CreateOrderDialog

### Day 5 — 마무리
16. `logistics/page.tsx` CreateShipmentDialog LOT 번들링 섹션 추가
17. `quality_service.py` group_by=supplier/process_type JOINquery 완성 (Sprint 3 observation)
18. 통합 테스트: 입고→LOT→품질검사→출하 E2E 플로우 확인

---

## 12. Gap Detector 체크리스트

| # | 항목 | 파일 | 확인 포인트 |
|---|------|------|------------|
| 1 | 마이그레이션 0007 | `alembic/versions/0007_inbound_orders_kpi.py` | 4테이블 + order_status_enum + KPI 시드 |
| 2 | RawMaterialReceipt 모델 | `models/inbound.py` | supplier/lot FK, receipt_number unique |
| 3 | Order + OrderItem 모델 | `models/order.py` | order_status_enum, items cascade |
| 4 | KpiTarget 모델 | `models/kpi.py` | metric_key unique |
| 5 | models/__init__.py 업데이트 | `models/__init__.py` | 3 new models imported |
| 6 | InboundService | `services/inbound_service.py` | create_receipt → LOT 자동생성 |
| 7 | KpiService | `services/kpi_service.py` | 4종 집계 메서드 |
| 8 | OrderService | `services/order_service.py` | 상태전환 유효성 검증 |
| 9 | dashboard_service 실집계 | `services/dashboard_service.py` | pending_shipments, defect_rate 실집계 |
| 10 | inbound API 4개 | `api/v1/inbound.py` | POST /, GET /, GET /{id}, GET /stats/supplier |
| 11 | kpi API 6개 | `api/v1/kpi.py` | GET /summary, /production, /quality, /delivery, /shipment, PUT /targets |
| 12 | orders API 4개 | `api/v1/orders.py` | GET /, POST /, GET /{id}, PATCH /{id}/status |
| 13 | router.py 3개 라우터 | `api/v1/router.py` | inbound, kpi, orders 등록 |
| 14 | use-inbound.ts | `hooks/use-inbound.ts` | useReceipts, useCreateReceipt, useSupplierStats |
| 15 | use-kpi.ts | `hooks/use-kpi.ts` | useKpiSummary, useKpiProductionTrend, useKpiQualityTrend |
| 16 | use-orders.ts | `hooks/use-orders.ts` | useOrders, useCreateOrder, useUpdateOrderStatus |
| 17 | kpi-card.tsx | `components/ui/kpi-card.tsx` | value/target/unit/lowerIsBetter props |
| 18 | inventory 입고 현황 탭 | `app/(dashboard)/inventory/page.tsx` | DataTable + CreateReceiptDialog (supplier select + LOT 표시) |
| 19 | kpi/page.tsx | `app/(dashboard)/kpi/page.tsx` | 4카드 + Recharts 2차트 |
| 20 | orders/page.tsx | `app/(dashboard)/orders/page.tsx` | DataTable + CreateOrderDialog (동적 items rows) |
| 21 | logistics LOT 번들링 | `app/(dashboard)/logistics/page.tsx` | CreateShipmentDialog에 LOT rows 섹션 |
| 22 | quality stats 완성 | `services/quality_service.py` | group_by=supplier, process_type JOINquery |
