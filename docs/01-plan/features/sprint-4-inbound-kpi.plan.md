# Sprint 4 — 입고관리 완성 + KPI 대시보드 Plan

> **Feature**: sprint-4-inbound-kpi  
> **Phase**: Plan  
> **Date**: 2026-05-04  
> **Status**: Draft  
> **Depends on**: sprint-3-ai-agent (완료, Match Rate 96%)

---

## 1. 목적 및 배경

### 1.1 목적

Sprint 4는 Metal-Onetouch AI+MES의 **Phase 2 완성** 스프린트입니다.  
Sprint 3에서 완성된 품질검사·출하물류·AI Agent 위에  
**원자재 입고 등록 + LOT 자동생성**, **KPI 실집계 대시보드**, **수주 기초 관리**,  
그리고 **Dashboard 실집계 연동**을 구현하여  
LOT 기반 **수주→입고→공정→품질→출하** 전 공정의 완전한 추적 사이클을 마무리합니다.

### 1.2 배경

**Sprint 3 완료 현황 (2026-05-04, Match Rate 96%)**:
- 품질검사 6개 엔드포인트 + 출하물류 6개 엔드포인트 + AI Agent 4개 엔드포인트
- Service Layer 5개 클래스 추출 완료
- LOT 상태머신 확장 (rejected / shipped / delivered)
- Sprint 3 미해결 항목: CreateShipmentDialog LOT 번들링 UI, Dashboard 실집계

**현재 스텁(stub) 상태인 페이지**:
- `inventory/page.tsx` → "입고 현황 및 LOT 생성 기능 — Sprint 4에서 구현 예정"
- `kpi/page.tsx` → "생산성, 품질, 납기, 원가 KPI 대시보드 — 개발 예정"
- `orders/page.tsx` → "AI 기반 자동 견적 생성, 수주 관리, 납기 예측 — 개발 예정"

**MASTER-PLAN Phase 2 잔여 목표 (M5~8)**:
- 입고재고관리: 입고 등록, 공급처 분석, LOT 자동 생성
- KPI 관리: 생산성·품질·납기·원가 KPI, 목표값 설정
- 수주 기초: 수주 등록, 납기일 관리 (Phase 3 CAD Vision AI 연동 전 기초)
- AI 대시보드 완성: 실집계 pending_shipments, defect_rate 연동

### 1.3 관련 문서

- Master Plan: `docs/01-plan/MASTER-PLAN.md` Section 4 (Phase 2)
- Sprint 3 Report: `docs/04-report/features/sprint-3-ai-agent.report.md`
- Sprint 3 Gap: `docs/03-analysis/sprint-3-ai-agent.analysis.md` (Item #21)

---

## 2. 범위 및 기능 목록

### 2.1 In Scope — 4개 도메인

#### 도메인 1: 원자재 입고 관리 (입고재고관리 완성)
- 원자재 입고 등록 (supplier_id, material_id, quantity, unit_price, received_date)
- LOT 자동 생성: 입고 등록 시 LOT 레코드 자동 생성, LOT 번호 채번 (`LOT-{YYYYMMDD}-{4자리}`)
- 입고 이력 조회 (기간/공급처/자재 필터)
- 입고 통계: 공급처별 월간 입고량, 불량률 추이

#### 도메인 2: KPI 대시보드
- KPI 4종 실집계:
  - **생산성 KPI**: 일별 생산량, 계획 대비 달성률, 설비 가동률
  - **품질 KPI**: 불량률 추이 (30일), 공급처별 불량률, 검사 합격률
  - **납기 KPI**: 납기 준수율, 평균 리드타임
  - **출하 KPI**: 월별 출하량, 출하 대기 건수
- KPI 목표값 설정 (settings 테이블)
- Recharts 기반 시각화 (LineChart, BarChart, RadialBarChart)

#### 도메인 3: 수주 기초 관리
- 수주 등록 (고객사, 자재명, 수량, 납기일, 단가)
- 수주 목록 / 상태 관리 (received → confirmed → in_production → shipped → completed)
- 수주-LOT 연결 (order_id → lot_id 매핑)
- 수주별 진행 현황 조회

#### 도메인 4: Sprint 3 Gap 해소 + Dashboard 실집계
- `logistics/page.tsx` CreateShipmentDialog에 LOT 번들링 섹션 추가 (Sprint 3 Item #21)
- `dashboard_service.get_pending_shipments()` Shipment 실집계 연동
- `dashboard_service.get_defect_rate()` QualityInspection 실집계 연동
- `quality_service.get_defect_stats(group_by=supplier|process_type)` JOINquery 완성

### 2.2 Out of Scope (Phase 3)
- CAD 도면 자동 분석 (YOLOv8) → Phase 3
- Vision AI 견적 자동산출 → Phase 3
- ERP 완전 연동 → Phase 3
- IoT MQTT → Kafka → TimescaleDB 실시간 파이프라인 → Phase 3 (데이터허브)
- 통합 AI Agent (전도메인) → Phase 3

---

## 3. 사용자 스토리

| # | 역할 | As a... | I want to... | So that... |
|---|------|---------|--------------|------------|
| US-01 | 품질담당자 | 품질담당자로서 | 입고된 원자재를 등록하고 LOT를 자동 생성하고 싶다 | 전 공정 추적의 시작점을 확보할 수 있다 |
| US-02 | 품질담당자 | 품질담당자로서 | 공급처별 입고 불량률 추이를 보고 싶다 | 문제 공급처를 조기 식별할 수 있다 |
| US-03 | 경영진 | 경영진으로서 | KPI 현황을 한 화면에서 보고 싶다 | 생산·품질·납기를 즉시 파악할 수 있다 |
| US-04 | 생산관리자 | 생산관리자로서 | KPI 목표값을 설정하고 달성률을 확인하고 싶다 | 목표 관리를 시스템화할 수 있다 |
| US-05 | 영업담당자 | 영업담당자로서 | 수주를 등록하고 납기 진행 현황을 확인하고 싶다 | 고객에게 실시간 납기 상태를 안내할 수 있다 |
| US-06 | 생산관리자 | 생산관리자로서 | 출하 등록 시 LOT를 한 번에 묶어서 등록하고 싶다 | 출하 생성과 LOT 번들링을 한 화면에서 처리할 수 있다 |

---

## 4. 기술 요구사항

### 4.1 신규 DB 모델 (마이그레이션 0007)

```
raw_material_receipts
  id              UUID PK
  supplier_id     UUID FK → suppliers
  material_id     UUID FK → materials (기준정보)
  lot_id          UUID FK → lots (생성된 LOT)
  quantity        DECIMAL(10,3)
  unit            VARCHAR(20)   -- kg, sheet, piece
  unit_price      DECIMAL(12,2)
  received_date   DATE NOT NULL
  notes           TEXT
  created_by      UUID FK → users
  created_at      TIMESTAMPTZ DEFAULT NOW()

orders (수주)
  id              UUID PK
  order_number    VARCHAR(30) UNIQUE  -- ORD-{YYYYMMDD}-{4자리}
  customer_id     UUID FK → customers
  status          order_status_enum  -- received/confirmed/in_production/shipped/completed/cancelled
  ordered_at      DATE NOT NULL
  due_date        DATE
  total_amount    DECIMAL(14,2)
  notes           TEXT
  created_by      UUID FK → users
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ

order_items (수주 라인)
  id              UUID PK
  order_id        UUID FK → orders
  material_name   VARCHAR(200)
  quantity        DECIMAL(10,3)
  unit            VARCHAR(20)
  unit_price      DECIMAL(12,2)
  lot_id          UUID FK → lots (nullable, LOT 생성 후 연결)

kpi_targets (KPI 목표값)
  id              UUID PK
  metric_key      VARCHAR(50) UNIQUE  -- production_rate, defect_rate, delivery_rate, etc.
  target_value    DECIMAL(10,4)
  unit            VARCHAR(20)
  period          VARCHAR(10)  -- daily/weekly/monthly
  updated_by      UUID FK → users
  updated_at      TIMESTAMPTZ
```

### 4.2 LOT 자동 생성 규칙

입고 등록(raw_material_receipts INSERT) 시 트리거처럼 동작:
```
lot_number = LOT-{YYYYMMDD}-{4자리 시퀀스}
lot_status  = 'received'  (초기 상태)
lot_type    = 'raw_material'
source_receipt_id = raw_material_receipts.id
```

### 4.3 서비스 클래스 추가

```python
class InboundService:
    async def create_receipt(...)     # 입고 등록 + LOT 자동 생성
    async def list_receipts(...)      # 필터 + 페이징
    async def get_supplier_stats(...) # 공급처별 통계

class KpiService:
    async def get_production_kpi(...)  # 생산성 KPI
    async def get_quality_kpi(...)     # 품질 KPI
    async def get_delivery_kpi(...)    # 납기 KPI
    async def get_shipment_kpi(...)    # 출하 KPI
    async def upsert_target(...)       # 목표값 설정

class OrderService:
    async def generate_order_number(...) # ORD-{YYYYMMDD}-{seq}
    async def create_order(...)
    async def update_status(...)
    async def link_lot(...)              # order_item → lot_id 연결
```

### 4.4 API 엔드포인트 (신규 14개)

**입고 관리 (`/api/v1/inbound`)**:
- `POST /` — 입고 등록 + LOT 자동 생성
- `GET /` — 목록 (날짜/공급처/자재 필터)
- `GET /{id}` — 상세
- `GET /stats` — 공급처별 통계 (period_days)

**KPI (`/api/v1/kpi`)**:
- `GET /summary` — 4종 KPI 실집계 한 번에
- `GET /production` — 생산성 KPI + 트렌드
- `GET /quality` — 품질 KPI + 트렌드
- `GET /delivery` — 납기 KPI
- `GET /shipment` — 출하 KPI
- `PUT /targets` — KPI 목표값 일괄 업데이트

**수주 (`/api/v1/orders`)**:
- `GET /` — 목록 (상태/고객사 필터)
- `POST /` — 수주 등록
- `GET /{id}` — 상세 (order_items 포함)
- `PATCH /{id}/status` — 상태 변경

### 4.5 프론트엔드 페이지

| 페이지 | 현재 | Sprint 4 목표 |
|--------|------|---------------|
| `inventory/page.tsx` | 품질검사 탭만 동작, 입고 현황 탭 스텁 | 입고 현황 탭: 입고 목록 DataTable + 입고 등록 Dialog |
| `kpi/page.tsx` | 완전 스텁 | 4종 KPI 카드 + Recharts 차트 |
| `orders/page.tsx` | 완전 스텁 | 수주 목록 DataTable + 수주 등록 Dialog |
| `logistics/page.tsx` | CreateShipmentDialog 미완 | LOT 번들링 섹션 추가 |
| `page.tsx` (대시보드) | pending_shipments=0, defect_rate 폴백 | 실집계 연동 |

---

## 5. 완료 기준 (Definition of Done)

- [ ] `raw_material_receipts` 입고 등록 → LOT 자동 생성 E2E 동작
- [ ] KPI 4종 (`/api/v1/kpi/summary`) 실집계 응답 (더미 0%)
- [ ] 수주 등록 → 상태 변경 흐름 동작
- [ ] `inventory/page.tsx` 입고 현황 탭: 목록 조회 + 등록 Dialog 동작
- [ ] `kpi/page.tsx`: Recharts 차트 4종 렌더링
- [ ] `orders/page.tsx`: 수주 목록 + 등록 기능 동작
- [ ] Dashboard `pending_shipments`, `defect_rate` 실집계 값 표시
- [ ] `logistics/page.tsx` CreateShipmentDialog LOT 번들링 동작
- [ ] Gap Analysis Match Rate ≥ 90%

---

## 6. 일정 및 우선순위

| 우선순위 | 도메인 | 예상 작업량 | 이유 |
|---------|--------|------------|------|
| P0 | 입고관리 + LOT 자동생성 | 2일 | LOT 추적 체인의 시작점; Phase 2 핵심 |
| P0 | Dashboard 실집계 연동 | 0.5일 | Sprint 3 pre-staged 코드 uncomment |
| P1 | KPI 대시보드 | 1.5일 | 경영진 사용자 스토리; 기존 집계 API 재활용 가능 |
| P1 | Sprint 3 Gap (Shipment LOT 번들링) | 0.5일 | Sprint 3 미완 항목 |
| P2 | 수주 기초 관리 | 1.5일 | Phase 3 CAD Vision AI 연동 전 기초 |

**총 예상 기간**: 6일

---

## 7. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| KPI 집계 쿼리 성능 | TimescaleDB 없이 PostgreSQL만으로 집계 시 느릴 수 있음 | `created_at` 인덱스 활용, 기간 제한 필터 필수 |
| LOT 번호 채번 동시성 | 다중 입고 동시 등록 시 중복 가능 | `SELECT MAX + 1 FOR UPDATE` 또는 시퀀스 테이블 |
| 수주-LOT 연결 복잡도 | 하나의 수주에 여러 LOT, 하나의 LOT가 여러 수주에 걸칠 수 있음 | Sprint 4는 1:1 단순 연결로 제한, 복잡 매핑은 Phase 3 |

---

## 8. 다음 단계

Sprint 4 완료 후 Phase 2 목표 달성:
- **Phase 3 진입 조건**: LOT 수주→입고→공정→품질→출하 전 구간 E2E 추적 동작 확인
- **Sprint 5 (Phase 3 시작)**: 수주견적AI — CAD 도면 업로드, YOLOv8 분석, 자동 견적 산출
