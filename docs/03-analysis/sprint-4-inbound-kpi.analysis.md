# Gap Analysis Report: sprint-4-inbound-kpi

**Date**: 2026-05-04  
**Feature**: Sprint 4 — 입고재고 LOT 생성 + KPI 대시보드 + 수주관리  
**Design Document**: `docs/02-design/features/sprint-4-inbound-kpi.design.md`  
**Analyzer**: gap-detector agent  

---

## Summary

| Metric | Value |
|--------|-------|
| **Match Rate** | **95% (21/22)** |
| Total Checklist Items | 22 |
| Fully Implemented | 21 |
| Partial | 1 |
| Not Implemented | 0 |
| Threshold (90%) | ✅ Passed |

---

## Checklist Results

### DB / Migration

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Migration 0007 chain: `down_revision = "0006"` | ✅ | Confirmed in `0007_inbound_orders_kpi.py` |
| 2 | `order_status_enum` PostgreSQL enum type | ✅ | Created before `orders` table |
| 3 | `raw_material_receipts` table with 4 indexes | ✅ | receipt_number unique + idx, supplier_id idx, lot_id idx |
| 4 | `orders` table with 6-state enum column | ✅ | `order_number`, `customer_id`, `status` Enum column |
| 5 | `order_items` with cascade FK to orders | ✅ | `ondelete="CASCADE"` confirmed |
| 6 | `kpi_targets` with seeded 4 rows (production_rate, defect_rate, delivery_rate, equipment_utilization) | ✅ | Seeds in upgrade() with explicit values |

### Backend Models

| # | Item | Status | Notes |
|---|------|--------|-------|
| 7 | `RawMaterialReceipt` model: supplier_id RESTRICT, lot_id SET NULL | ✅ | `app/models/inbound.py` — correct FK constraints |
| 8 | `Order.can_transition_to()` with `ORDER_STATUS_TRANSITIONS` dict | ✅ | `app/models/order.py` — all 6 states covered |
| 9 | `KpiTarget` model: metric_key unique, updated_at onupdate | ✅ | `app/models/kpi.py` — `onupdate=func.now()` present |
| 10 | All 3 new models exported in `app/models/__init__.py` | ✅ | RawMaterialReceipt, Order, OrderItem, KpiTarget all in `__all__` |

### Backend Services

| # | Item | Status | Notes |
|---|------|--------|-------|
| 11 | `InboundService.create_receipt()` auto-generates LOT via `Lot.generate_lot_id()` | ✅ | Full LOT creation sequence: lot_id_str → Lot obj → flush → receipt with lot_id |
| 12 | `KpiService.upsert_targets()` uses `pg_insert ON CONFLICT` | ✅ | `from sqlalchemy.dialects.postgresql import insert as pg_insert` confirmed |
| 13 | `KpiService._calc_delivery_detail()` checks `updated_at.date() <= due_date` | ✅ | Delivery rate calculated for current month's completed orders |
| 14 | `OrderService.update_status()` raises HTTP 400 on invalid transition | ✅ | Calls `order.can_transition_to()` and raises `HTTPException(400)` |
| 15 | `DashboardService` real aggregation: pending_shipments + defect_rate | ✅ | Both previously-commented blocks now active |
| 16 | `QualityService.get_defect_stats()` group_by supplier via LOT→Receipt JOIN | ✅ | `aliased(Lot)` + JOIN chain to Supplier; inspection_type grouping for process_type |

### Backend APIs

| # | Item | Status | Notes |
|---|------|--------|-------|
| 17 | 4 inbound endpoints: GET /receipts, POST /receipts, GET /receipts/{id}, GET /stats/supplier | ✅ | `/stats/supplier` registered before `/{receipt_id}` to avoid path conflict |
| 18 | 6 KPI endpoints: GET /summary, /production-trend, /quality-trend, /delivery, /shipment, PUT /targets | ✅ | PUT /targets requires admin role |
| 19 | 4 order endpoints registered in `v1/router.py` | ✅ | inbound, kpi, orders all included with correct prefixes |

### Frontend

| # | Item | Status | Notes |
|---|------|--------|-------|
| 20 | `inventory/page.tsx`: two tabs (입고 현황 / 품질 검사), action button switches per tab | ✅ | Tab-aware action button in PageHeader, InboundTab + QualityInspectionTab components |
| 21 | `kpi/page.tsx`: 4 KpiCards with target-driven status + 2 Recharts LineCharts | ⚠️ | **Partial** — see note below |
| 22 | `orders/page.tsx`: 7-option status filter + CreateOrderDialog with dynamic item rows | ✅ | Grid layout item rows with add/remove, material_name/code/quantity/unit/unit_price |

---

## Gap Details

### Item 21 — KpiCard prop API divergence (Non-blocking)

**Design spec** (`sprint-4-inbound-kpi.design.md`):
```tsx
<KpiCard label="생산 달성률" value={...} target={100} unit="%" lowerIsBetter={false} />
```

**Actual implementation** (`kpi/page.tsx` + existing `kpi-card.tsx`):
```tsx
<KpiCard title="생산 달성률" value={...} unit="%" status="normal|warning|critical" description="목표 100%" />
```

**Root cause**: `kpi-card.tsx` already existed from Sprint 2 with a richer API (`title/value/unit/change/changeInverse/status/icon/description/isLoading`). The design spec was written against a hypothetical API (`label/target/lowerIsBetter`). The page correctly uses the existing component, computing `status` from threshold logic in the caller.

**Impact**: None — functional parity achieved. Target threshold logic is implemented in the page component instead of card. All 4 KPI metrics display with correct normal/warning/critical states.

**Action required**: None. Design doc reflects intent; implementation achieves same outcome via different prop API.

---

## Notable Observations

1. **LOT auto-generation flow** is complete end-to-end: `POST /api/v1/inbound/receipts` → `InboundService.create_receipt()` → `Lot.generate_lot_id(session)` → LOT persisted with `lot_status="received"` → receipt linked via `lot_id` FK.

2. **Shipment LOT bundling** (Sprint 3 gap fix) is fully implemented: `CreateShipmentDialog` in `logistics/page.tsx` has dynamic `lotRows` state with add/remove/update handlers; submit payload includes `lots` array.

3. **KPI delivery rate** handles null `due_date` gracefully — null is treated as "always on time" (returns True from `can_transition_to` equivalent logic).

4. **Order status machine** enforces valid transitions: received→confirmed, confirmed→in_production, etc. Invalid transitions return HTTP 400.

5. **quality_service.py supplier JOIN** uses `aliased(Lot)` to prevent ORM ambiguity when joining the Lot table via multiple paths.

---

## Conclusion

Match Rate **95% ≥ 90% threshold**. Sprint 4 is complete. The single partial item (KpiCard prop API) is a non-breaking design doc vs. pre-existing component divergence with no functional impact.

**Recommended next step**: `/pdca report sprint-4-inbound-kpi`
