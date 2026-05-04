# Sprint 2 Core — Design Document

> **Feature**: sprint-2-core  
> **Phase**: Design  
> **Version**: 1.0  
> **Date**: 2026-04-30  
> **Depends on**: `docs/01-plan/features/sprint-2-core.plan.md`, `docs/02-design/db/schema.sql` (Sprint 1)

---

## 1. 개요

Sprint 1의 기반 구조 위에 **MES 핵심 비즈니스 로직**을 구현합니다.

| 영역 | Sprint 1 (완료) | Sprint 2 (이번) |
|------|-----------------|-----------------|
| DB | users, lots, lot_histories (3 tables) | +8 tables (마스터 5 + 작업지시 2 + 감사 1) |
| API | auth 4개 + lots 8개 = 12개 | +30개 (마스터 20 + 작업지시 6 + 대시보드 3 + 사용자 4) |
| Frontend | 더미 데이터 + 10개 Shell | 4개 기능 페이지 (master-data, process, system, dashboard 실연동) |

---

## 2. DB 스키마 설계

### 2.1 Migration 0002 — 마스터 데이터 5개 테이블

#### `suppliers` — 공급업체
```sql
CREATE TYPE supplier_grade_enum AS ENUM ('A', 'B', 'C', 'D');

CREATE TABLE suppliers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_code   VARCHAR(20)  NOT NULL UNIQUE,        -- 예) SUPP-001
    name            VARCHAR(200) NOT NULL,
    contact_person  VARCHAR(100),
    phone           VARCHAR(20),
    email           VARCHAR(255),
    address         TEXT,
    grade           supplier_grade_enum NOT NULL DEFAULT 'C',
    business_no     VARCHAR(20),                          -- 사업자등록번호
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_suppliers_code  ON suppliers(supplier_code);
CREATE INDEX ix_suppliers_name  ON suppliers(name);
CREATE INDEX ix_suppliers_grade ON suppliers(grade);
```

#### `customers` — 고객사
```sql
CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_code   VARCHAR(20)  NOT NULL UNIQUE,        -- 예) CUST-001
    name            VARCHAR(200) NOT NULL,
    contact_person  VARCHAR(100),
    phone           VARCHAR(20),
    email           VARCHAR(255),
    address         TEXT,
    business_no     VARCHAR(20),
    credit_limit    NUMERIC(15,2),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_customers_code ON customers(customer_code);
CREATE INDEX ix_customers_name ON customers(name);
```

#### `raw_materials` — 원자재
```sql
CREATE TYPE material_category_enum AS ENUM (
    'steel_sheet',      -- 철판
    'stainless',        -- 스테인리스
    'aluminum',         -- 알루미늄
    'copper',           -- 동
    'pipe',             -- 배관
    'bar',              -- 봉재
    'other'
);

CREATE TABLE raw_materials (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_code   VARCHAR(30)  NOT NULL UNIQUE,        -- 예) MAT-SUS304-2T
    name            VARCHAR(200) NOT NULL,
    category        material_category_enum NOT NULL DEFAULT 'other',
    spec            VARCHAR(200),                         -- 규격 (예: SUS304 2T x 1000 x 2000)
    unit            VARCHAR(20)  NOT NULL DEFAULT 'EA',   -- EA, KG, M, M2
    supplier_id     UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    stock_qty       NUMERIC(12,3) NOT NULL DEFAULT 0,
    min_stock_qty   NUMERIC(12,3) NOT NULL DEFAULT 0,     -- 안전 재고
    unit_price      NUMERIC(15,2),
    lead_time_days  INTEGER DEFAULT 7,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_raw_materials_code     ON raw_materials(material_code);
CREATE INDEX ix_raw_materials_supplier ON raw_materials(supplier_id);
CREATE INDEX ix_raw_materials_category ON raw_materials(category);
```

#### `processes` — 공정 유형 (마스터)
```sql
CREATE TYPE process_type_enum AS ENUM (
    'cutting',          -- 절단
    'forming',          -- 성형
    'welding',          -- 용접
    'painting',         -- 도장
    'inspection',       -- 검사
    'assembly',         -- 조립
    'other'
);

CREATE TABLE processes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    process_code    VARCHAR(20)  NOT NULL UNIQUE,        -- 예) PROC-CUT-001
    name            VARCHAR(200) NOT NULL,
    process_type    process_type_enum NOT NULL,
    std_time_min    INTEGER,                              -- 표준 작업 시간 (분)
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_processes_code ON processes(process_code);
CREATE INDEX ix_processes_type ON processes(process_type);
```

#### `equipment` — 설비
```sql
CREATE TABLE equipment (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_code  VARCHAR(20)  NOT NULL UNIQUE,        -- 예) EQ-LASER-001
    name            VARCHAR(200) NOT NULL,
    process_id      UUID REFERENCES processes(id) ON DELETE SET NULL,
    manufacturer    VARCHAR(100),
    model_no        VARCHAR(100),
    serial_no       VARCHAR(100),
    status          equipment_status_enum NOT NULL DEFAULT 'idle',
    installed_at    DATE,
    last_maint_at   DATE,
    next_maint_at   DATE,
    location        VARCHAR(100),                         -- 설치 위치
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_equipment_code    ON equipment(equipment_code);
CREATE INDEX ix_equipment_process ON equipment(process_id);
CREATE INDEX ix_equipment_status  ON equipment(status);
```

---

### 2.2 Migration 0003 — 작업지시 + 감사 로그

#### `work_orders` — 작업지시
```sql
CREATE TYPE wo_status_enum AS ENUM (
    'pending',          -- 대기
    'in_progress',      -- 진행 중
    'completed',        -- 완료
    'on_hold',          -- 보류
    'cancelled'         -- 취소
);

CREATE TABLE work_orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wo_number       VARCHAR(30)  NOT NULL UNIQUE,        -- 예) WO-20260430-0001
    lot_id          UUID NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    process_id      UUID NOT NULL REFERENCES processes(id) ON DELETE RESTRICT,
    equipment_id    UUID REFERENCES equipment(id) ON DELETE SET NULL,
    assigned_to     UUID REFERENCES users(id) ON DELETE SET NULL,
    status          wo_status_enum NOT NULL DEFAULT 'pending',
    planned_start   TIMESTAMPTZ,
    planned_end     TIMESTAMPTZ,
    actual_start    TIMESTAMPTZ,
    actual_end      TIMESTAMPTZ,
    input_qty       NUMERIC(12,3),
    output_qty      NUMERIC(12,3),
    defect_qty      NUMERIC(12,3) DEFAULT 0,
    notes           TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_wo_number     ON work_orders(wo_number);
CREATE INDEX ix_wo_lot        ON work_orders(lot_id);
CREATE INDEX ix_wo_process    ON work_orders(process_id);
CREATE INDEX ix_wo_status     ON work_orders(status);
CREATE INDEX ix_wo_assigned   ON work_orders(assigned_to);
CREATE INDEX ix_wo_planned    ON work_orders(planned_start);
```

#### `process_results` — 공정 실적 (불변 이력)
```sql
CREATE TABLE process_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_id   UUID NOT NULL REFERENCES work_orders(id) ON DELETE RESTRICT,
    lot_id          UUID NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    equipment_id    UUID REFERENCES equipment(id) ON DELETE SET NULL,
    worker_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    input_qty       NUMERIC(12,3) NOT NULL,
    output_qty      NUMERIC(12,3) NOT NULL,
    defect_qty      NUMERIC(12,3) NOT NULL DEFAULT 0,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    -- 품질/조건 메모
    condition_notes TEXT,
    -- 불량 사유 (있을 경우)
    defect_reason   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    -- NOTE: process_results는 수정 불가 (불변 이력) — updated_at 없음
);
CREATE INDEX ix_pr_work_order ON process_results(work_order_id);
CREATE INDEX ix_pr_lot        ON process_results(lot_id);
CREATE INDEX ix_pr_worker     ON process_results(worker_id);
CREATE INDEX ix_pr_start_time ON process_results(start_time);
```

#### `system_logs` — 감사 로그
```sql
CREATE TYPE audit_action_enum AS ENUM (
    'CREATE', 'UPDATE', 'DELETE',
    'LOGIN', 'LOGOUT', 'LOGIN_FAILED',
    'EXPORT', 'IMPORT', 'STATUS_CHANGE'
);

CREATE TABLE system_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_name      VARCHAR(100),                         -- 비정규화 (삭제된 사용자 대비)
    action          audit_action_enum NOT NULL,
    resource_type   VARCHAR(50) NOT NULL,                 -- 예: 'lot', 'work_order'
    resource_id     VARCHAR(100),                         -- 대상 리소스 PK
    old_value       JSONB,                                -- 변경 전 (UPDATE/DELETE)
    new_value       JSONB,                                -- 변경 후 (CREATE/UPDATE)
    ip_address      VARCHAR(45),
    user_agent      VARCHAR(500),
    trace_id        VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    -- NOTE: 감사 로그는 삭제/수정 불가
);
CREATE INDEX ix_syslog_actor    ON system_logs(actor_id);
CREATE INDEX ix_syslog_action   ON system_logs(action);
CREATE INDEX ix_syslog_resource ON system_logs(resource_type, resource_id);
CREATE INDEX ix_syslog_created  ON system_logs(created_at DESC);
```

---

## 3. API 명세 (Sprint 2 신규 30개 엔드포인트)

### 공통 규약 (Sprint 1에서 확정)
- 응답: `{ "data": T, "meta": { "requestId", "timestamp" } }` (단건)
- 응답: `{ "data": T[], "pagination": { "total", "page", "limit", "hasMore" }, "meta": {...} }` (목록)
- 에러: `{ "error": { "code", "message", "traceId" } }`
- 공통 목록 파라미터: `?page=1&limit=20&search=&is_active=`

---

### 3.1 공급업체 API — `/api/v1/master/suppliers`

| # | Method | Path | 역할 권한 | 설명 |
|---|--------|------|-----------|------|
| 1 | `GET` | `/` | 전체 | 공급업체 목록 (search, grade, is_active 필터) |
| 2 | `POST` | `/` | admin, production_manager | 공급업체 등록 |
| 3 | `GET` | `/{supplier_id}` | 전체 | 공급업체 상세 |
| 4 | `PATCH` | `/{supplier_id}` | admin, production_manager | 공급업체 수정 |
| 5 | `DELETE` | `/{supplier_id}` | admin | 논리 삭제 (is_active=false) |

**POST 요청 바디**:
```json
{
  "supplier_code": "SUPP-001",
  "name": "한국스틸(주)",
  "contact_person": "김담당",
  "phone": "02-1234-5678",
  "email": "contact@korsteel.com",
  "grade": "A",
  "business_no": "123-45-67890"
}
```

---

### 3.2 고객사 API — `/api/v1/master/customers`

| # | Method | Path | 역할 권한 | 설명 |
|---|--------|------|-----------|------|
| 6 | `GET` | `/` | 전체 | 고객사 목록 |
| 7 | `POST` | `/` | admin, sales_engineer | 고객사 등록 |
| 8 | `GET` | `/{customer_id}` | 전체 | 고객사 상세 |
| 9 | `PATCH` | `/{customer_id}` | admin, sales_engineer | 고객사 수정 |
| 10 | `DELETE` | `/{customer_id}` | admin | 논리 삭제 |

---

### 3.3 원자재 API — `/api/v1/master/materials`

| # | Method | Path | 역할 권한 | 설명 |
|---|--------|------|-----------|------|
| 11 | `GET` | `/` | 전체 | 원자재 목록 (category, supplier_id 필터) |
| 12 | `POST` | `/` | admin, production_manager | 원자재 등록 |
| 13 | `GET` | `/{material_id}` | 전체 | 원자재 상세 |
| 14 | `PATCH` | `/{material_id}` | admin, production_manager | 원자재 수정 |
| 15 | `DELETE` | `/{material_id}` | admin | 논리 삭제 |

**원자재 등록 요청**:
```json
{
  "material_code": "MAT-SUS304-2T",
  "name": "SUS304 스테인리스 2T",
  "category": "stainless",
  "spec": "SUS304 2.0T × 1000 × 2000mm",
  "unit": "EA",
  "supplier_id": "uuid-here",
  "unit_price": 85000,
  "min_stock_qty": 10,
  "lead_time_days": 5
}
```

---

### 3.4 공정 유형 API — `/api/v1/master/processes`

| # | Method | Path | 역할 권한 | 설명 |
|---|--------|------|-----------|------|
| 16 | `GET` | `/` | 전체 | 공정 유형 목록 (process_type 필터) |
| 17 | `POST` | `/` | admin, process_engineer | 공정 유형 등록 |
| 18 | `GET` | `/{process_id}` | 전체 | 공정 상세 |
| 19 | `PATCH` | `/{process_id}` | admin, process_engineer | 공정 수정 |

---

### 3.5 설비 API — `/api/v1/master/equipment`

| # | Method | Path | 역할 권한 | 설명 |
|---|--------|------|-----------|------|
| 20 | `GET` | `/` | 전체 | 설비 목록 (status, process_id 필터) |
| 21 | `POST` | `/` | admin, process_engineer | 설비 등록 |
| 22 | `GET` | `/{equipment_id}` | 전체 | 설비 상세 |
| 23 | `PATCH` | `/{equipment_id}` | admin, process_engineer | 설비 수정 |
| 24 | `PATCH` | `/{equipment_id}/status` | process_engineer, production_manager | 설비 상태만 변경 |

**설비 상태 변경 요청**:
```json
{ "status": "maintenance", "reason": "정기 점검 (월례)" }
```

---

### 3.6 작업지시 API — `/api/v1/work-orders`

| # | Method | Path | 역할 권한 | 설명 |
|---|--------|------|-----------|------|
| 25 | `GET` | `/` | 전체 | 작업지시 목록 (status, lot_id, assigned_to, date 필터) |
| 26 | `POST` | `/` | production_manager | 작업지시 생성 |
| 27 | `GET` | `/{wo_id}` | 전체 | 작업지시 상세 + 공정 실적 목록 |
| 28 | `PATCH` | `/{wo_id}/status` | production_manager, process_engineer | 상태 전환 |
| 29 | `POST` | `/{wo_id}/results` | process_engineer, production_manager | 공정 실적 등록 |
| 30 | `GET` | `/{wo_id}/results` | 전체 | 공정 실적 목록 |

**작업지시 생성 요청**:
```json
{
  "lot_id": "uuid-here",
  "process_id": "uuid-here",
  "equipment_id": "uuid-here",
  "assigned_to": "uuid-here",
  "planned_start": "2026-05-02T08:00:00+09:00",
  "planned_end":   "2026-05-02T17:00:00+09:00",
  "input_qty": 50,
  "notes": "SUS304 레이저 절단 50매"
}
```

**공정 실적 등록 요청**:
```json
{
  "equipment_id": "uuid-here",
  "input_qty": 50,
  "output_qty": 48,
  "defect_qty": 2,
  "start_time": "2026-05-02T08:15:00+09:00",
  "end_time":   "2026-05-02T12:30:00+09:00",
  "condition_notes": "가공면 양호",
  "defect_reason": "치수 불량 2매"
}
```

---

### 3.7 대시보드 집계 API — `/api/v1/dashboard`

| # | Method | Path | 역할 권한 | 설명 |
|---|--------|------|-----------|------|
| 31 | `GET` | `/summary` | 전체 | 오늘 KPI 요약 |
| 32 | `GET` | `/production-trend` | 전체 | 7일 생산 추이 |
| 33 | `GET` | `/lot-status` | 전체 | 최근 LOT 현황 |

**GET `/summary` 응답**:
```json
{
  "data": {
    "today_production": 847,
    "defect_rate": 1.2,
    "equipment_utilization": 94.3,
    "pending_shipments": 23,
    "compared_to_prev_day": {
      "production": 5.3,
      "defect_rate": -0.3,
      "equipment_utilization": 2.1,
      "pending_shipments": -4.2
    }
  }
}
```

**GET `/production-trend?days=7` 응답**:
```json
{
  "data": [
    { "date": "04/24", "planned": 820, "actual": 805, "defects": 10 }
  ]
}
```

---

### 3.8 사용자 관리 API — `/api/v1/users`

| # | Method | Path | 역할 권한 | 설명 |
|---|--------|------|-----------|------|
| 34 | `GET` | `/` | admin, executive | 사용자 목록 (role, status 필터) |
| 35 | `POST` | `/` | admin | 사용자 생성 |
| 36 | `PATCH` | `/{user_id}` | admin | 사용자 정보 수정 (역할, 상태, 부서) |
| 37 | `POST` | `/{user_id}/reset-password` | admin | 비밀번호 초기화 |

---

## 4. 백엔드 디렉토리 구조 (Sprint 2 추가분)

```
backend/app/
├── api/v1/
│   ├── master/
│   │   ├── __init__.py
│   │   ├── suppliers.py     ← NEW
│   │   ├── customers.py     ← NEW
│   │   ├── materials.py     ← NEW
│   │   ├── processes.py     ← NEW
│   │   └── equipment.py     ← NEW
│   ├── work_orders.py       ← NEW
│   ├── dashboard.py         ← NEW
│   ├── users.py             ← NEW
│   └── router.py            ← MODIFY (새 라우터 등록)
├── models/
│   ├── supplier.py          ← NEW
│   ├── customer.py          ← NEW
│   ├── raw_material.py      ← NEW
│   ├── process.py           ← NEW (공정 유형)
│   ├── equipment.py         ← NEW
│   ├── work_order.py        ← NEW
│   └── system_log.py        ← NEW
├── schemas/
│   ├── supplier.py          ← NEW
│   ├── customer.py          ← NEW
│   ├── material.py          ← NEW
│   ├── process.py           ← NEW
│   ├── equipment.py         ← NEW
│   ├── work_order.py        ← NEW
│   └── dashboard.py         ← NEW
├── services/
│   ├── work_order_service.py ← NEW (WO 번호 생성, 상태 전환 검증)
│   └── dashboard_service.py  ← NEW (집계 쿼리)
└── middleware/
    └── audit.py              ← NEW (AuditMiddleware)
```

### 4.1 SQLAlchemy 모델 패턴 (모든 마스터 모델 공통)

```python
# backend/app/models/supplier.py (예시 패턴)
class Supplier(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "suppliers"

    supplier_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    grade: Mapped[str] = mapped_column(
        Enum("A", "B", "C", "D", name="supplier_grade_enum"),
        nullable=False, default="C"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    raw_materials: Mapped[list["RawMaterial"]] = relationship("RawMaterial", back_populates="supplier")
```

### 4.2 Audit Middleware 설계

```python
# backend/app/middleware/audit.py
class AuditMiddleware(BaseHTTPMiddleware):
    AUDITABLE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
    SKIP_PATHS = {"/health", "/docs", "/openapi.json",
                  "/api/v1/auth/login", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.method not in self.AUDITABLE_METHODS:
            return await call_next(request)
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        response = await call_next(request)

        # 성공 응답(2xx)에만 기록
        if 200 <= response.status_code < 300:
            asyncio.create_task(self._write_log(request, response))

        return response
```

**action 매핑 규칙**:

| HTTP Method | 경로 패턴 | action |
|-------------|-----------|--------|
| POST | `/` | CREATE |
| PATCH | `/{id}` | UPDATE |
| DELETE | `/{id}` | DELETE |
| PATCH | `/{id}/status` | STATUS_CHANGE |
| POST | `/auth/login` | LOGIN |
| POST | `/auth/logout` | LOGOUT |

### 4.3 Work Order 번호 생성

```python
# 형식: WO-{YYYYMMDD}-{4자리 일련번호}
# 예) WO-20260430-0001

async def generate_wo_number(db: AsyncSession, today: date) -> str:
    prefix = f"WO-{today.strftime('%Y%m%d')}-"
    result = await db.execute(
        select(func.count()).where(
            WorkOrder.wo_number.like(f"{prefix}%")
        )
    )
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{seq:04d}"
```

### 4.4 Work Order 상태 전환

```python
WO_STATUS_TRANSITIONS = {
    "pending":     ["in_progress", "on_hold", "cancelled"],
    "in_progress": ["completed", "on_hold"],
    "on_hold":     ["pending", "in_progress", "cancelled"],
    "completed":   [],   # 완료 후 불변
    "cancelled":   [],   # 취소 후 불변
}
```

---

## 5. 프론트엔드 컴포넌트 설계

### 5.1 공통 컴포넌트 신설

```
frontend/src/components/
├── ui/
│   ├── data-table.tsx          ← NEW: 재사용 DataTable (shadcn Table 기반)
│   ├── search-input.tsx        ← NEW: 디바운스 검색 인풋
│   ├── status-badge.tsx        ← NEW: 상태 뱃지 (equipment_status, wo_status)
│   └── confirm-dialog.tsx      ← NEW: 삭제/상태변경 확인 다이얼로그
├── forms/
│   ├── supplier-form.tsx       ← NEW
│   ├── material-form.tsx       ← NEW
│   ├── work-order-form.tsx     ← NEW
│   └── process-result-form.tsx ← NEW
└── layout/
    └── page-header.tsx         ← NEW: 페이지 제목 + 우상단 액션 버튼
```

#### `DataTable` 컴포넌트 인터페이스

```tsx
interface DataTableProps<T> {
  columns: ColumnDef<T>[]
  data: T[]
  isLoading?: boolean
  pagination?: {
    page: number
    limit: number
    total: number
    onPageChange: (page: number) => void
  }
  onRowClick?: (row: T) => void
  toolbar?: React.ReactNode      // 검색, 필터, 버튼 슬롯
  emptyMessage?: string
}
```

### 5.2 페이지 구조

#### `master-data/page.tsx` — 기준정보 허브
```
master-data/
├── page.tsx             ← 탭 레이아웃 (공급업체 | 고객사 | 원자재 | 공정 | 설비)
├── suppliers/
│   └── page.tsx         ← 공급업체 DataTable + 모달 CRUD
├── customers/
│   └── page.tsx
├── materials/
│   └── page.tsx         ← 원자재 DataTable + 공급업체 연결
├── processes/
│   └── page.tsx
└── equipment/
    └── page.tsx         ← 설비 DataTable + 상태 변경 버튼
```

**기준정보 메인 페이지 (`master-data/page.tsx`) 레이아웃**:
```tsx
// 5개 탭 카드: 공급업체 N개 / 고객사 N개 / 원자재 N개 / 공정 N개 / 설비 N개
// 각 탭 → 해당 서브 페이지로 이동 또는 인라인 DataTable
```

#### `process/page.tsx` — 공정 관리
```
process/
├── page.tsx             ← 작업지시 목록 (DataTable, 필터: status, date)
└── [wo_id]/
    └── page.tsx         ← 작업지시 상세 + 공정 실적 목록 + 실적 등록 폼
```

**작업지시 목록 컬럼**:
```
WO번호 | LOT ID | 공정 | 담당자 | 계획 시작 | 상태 | 진도율
```

#### `system/page.tsx` — 시스템 관리
```
system/
├── page.tsx             ← 사용자 목록 (DataTable, 필터: role, status)
└── users/
    └── page.tsx
```

#### `(dashboard)/page.tsx` — 대시보드 실연동
```tsx
// 기존 더미 데이터 제거
// react-query 교체:
const { data: summary } = useQuery({
  queryKey: ['dashboard', 'summary'],
  queryFn: () => dashboardApi.getSummary(),
  staleTime: 30_000,   // 30초
  refetchInterval: 30_000,
})
```

### 5.3 API 훅 설계 (react-query)

```
frontend/src/lib/
├── api/
│   ├── suppliers.ts     ← NEW: CRUD API 함수
│   ├── customers.ts     ← NEW
│   ├── materials.ts     ← NEW
│   ├── processes.ts     ← NEW
│   ├── equipment.ts     ← NEW
│   ├── work-orders.ts   ← NEW
│   └── dashboard.ts     ← MODIFY (실 API로 교체)
└── hooks/
    ├── use-suppliers.ts ← NEW: useQuery/useMutation 래퍼
    ├── use-materials.ts ← NEW
    ├── use-work-orders.ts ← NEW
    └── use-dashboard.ts   ← NEW
```

**훅 패턴 예시**:
```tsx
// use-suppliers.ts
export function useSuppliers(params: SupplierListParams) {
  return useQuery({
    queryKey: ['suppliers', params],
    queryFn: () => suppliersApi.list(params),
    staleTime: 5 * 60_000,  // 마스터 데이터: 5분 캐시
  })
}

export function useCreateSupplier() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: suppliersApi.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['suppliers'] }),
  })
}
```

### 5.4 QueryProvider 설정

```tsx
// frontend/src/app/providers.tsx (수정)
// @tanstack/react-query QueryClientProvider 추가
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})
```

---

## 6. CI 파이프라인 설계

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  backend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install ruff mypy
      - run: ruff check backend/
      - run: mypy backend/app --ignore-missing-imports

  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter frontend lint
      - run: pnpm --filter frontend type-check
```

---

## 7. 데이터 흐름 다이어그램

```
[원자재 입고]
  Supplier → RawMaterial (마스터)
                ↓
              LOT (생성)
                ↓
[공정 진행]
  Process → WorkOrder (lot_id FK) → ProcessResult (불변)
  Equipment ↗
  User(worker) ↗
                ↓
[품질 검사] (Sprint 3)
  QualityInspection → DefectDetail
                ↓
[출하] (Sprint 3)
  Shipment → ShipmentLot

[감사 추적]
  모든 CUD 작업 → SystemLog (AuditMiddleware 자동 기록)

[대시보드 집계]
  ProcessResult.output_qty + DefectDetail → KPI 집계
  WorkOrder.status → 공정 진행률
```

---

## 8. 구현 순서 (Do Phase 가이드)

### Step 1: DB 모델 + Migrations (D1-2)
1. `backend/app/models/` — 5개 마스터 모델 생성
2. `backend/alembic/versions/0002_master_data.py` 작성 및 검증
3. `docker compose exec backend alembic upgrade head` 확인

### Step 2: 마스터 CRUD API (D2-3)
1. `backend/app/schemas/` — 5개 Pydantic 스키마 (Create/Read/Update)
2. `backend/app/api/v1/master/` — 5개 라우터 (CRUD 패턴 반복)
3. `backend/app/api/v1/router.py` — `/api/v1/master` prefix 등록

### Step 3: Work Orders + ProcessResults (D3-4)
1. `backend/app/models/work_order.py`
2. `backend/alembic/versions/0003_work_orders.py`
3. `backend/app/services/work_order_service.py` — WO 번호 생성, 상태 전환
4. `backend/app/api/v1/work_orders.py`

### Step 4: Audit + Dashboard (D4-5)
1. `backend/app/middleware/audit.py`
2. `backend/app/main.py` — AuditMiddleware 등록
3. `backend/app/services/dashboard_service.py` — 집계 쿼리
4. `backend/app/api/v1/dashboard.py`

### Step 5: Users API (D5)
1. `backend/app/api/v1/users.py` — 목록, 생성, 수정, 비밀번호 초기화

### Step 6: Frontend (D6-10)
1. react-query QueryProvider 설정 + `@tanstack/react-query` 설치
2. `components/ui/data-table.tsx` — 공통 DataTable
3. `lib/api/` + `lib/hooks/` — 마스터 데이터 훅 5개
4. `master-data/` 페이지 (탭 + CRUD)
5. `process/` 페이지 (작업지시 목록 + 상세 + 실적 등록)
6. 대시보드 실 API 연동 (더미 데이터 제거)
7. `system/` 사용자 관리

---

## 9. 완료 기준 체크리스트

### DB
- [ ] `alembic upgrade head` — 0002, 0003 migration 성공
- [ ] 5개 마스터 테이블 인덱스 확인 (`\d suppliers` in psql)
- [ ] `system_logs` — AuditMiddleware POST/PATCH/DELETE 시 자동 삽입 확인
- [ ] `work_orders` → `process_results` → `lots` 관계 무결성 확인

### API
- [ ] `/api/v1/master/suppliers` CRUD 5개 Swagger 검증
- [ ] `/api/v1/master/materials` 원자재 등록 시 `supplier_id` FK 연결 확인
- [ ] `/api/v1/work-orders` 생성 → 상태 전환 → 실적 등록 흐름
- [ ] `/api/v1/lots/{lot_id}/traceability` 응답에 `work_orders` + `process_results` 포함
- [ ] `/api/v1/dashboard/summary` 실제 집계 값 반환

### Frontend
- [ ] `master-data/` 페이지 — DataTable + 검색 + 모달 CRUD 동작
- [ ] `process/` 페이지 — 작업지시 목록 + 실적 등록 폼
- [ ] `(dashboard)/page.tsx` — 더미 데이터 0%, 실 API 100%
- [ ] react-query staleTime / refetchInterval 동작 확인

### CI
- [ ] `.github/workflows/ci.yml` — ruff + mypy + ESLint + tsc 통과
