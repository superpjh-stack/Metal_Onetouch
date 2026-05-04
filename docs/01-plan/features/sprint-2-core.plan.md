# Sprint 2 Core — Plan Document

> **Feature**: sprint-2-core  
> **Phase**: Plan  
> **Date**: 2026-04-30  
> **Sprint**: W3-4 (2주, Phase 1 두 번째 스프린트)  
> **Depends on**: mes-architecture (Sprint 1, 완료)

---

## 1. 배경 및 목적

Sprint 1에서 기반 구조(Docker Compose 11서비스, FastAPI 스켈레톤, JWT/RBAC, LOT CRUD)를 완성했습니다.  
Sprint 2의 목표는 **MES 핵심 비즈니스 로직 구현** — 기준정보(마스터 데이터) + 공정관리 + 사용자/시스템관리 + 실시간 대시보드 연동입니다.

### Sprint 1 → Sprint 2 진입 조건 (모두 완료 ✅)
- [x] Docker Compose 11서비스 기동 검증
- [x] JWT 인증 + RBAC 5역할 동작 확인
- [x] LOT CRUD + 상태머신 + 역추적 API
- [x] Alembic 마이그레이션 (0001_initial_schema.py)
- [x] API 표준 응답 봉투 (`PaginatedResponse`, `ErrorResponse`)
- [x] Next.js 10개 모듈 Shell 페이지 생성

---

## 2. Sprint 2 범위 (Scope)

### 2.1 포함 (In-Scope)

#### 백엔드 — DB 모델 + API 구현

| 우선순위 | 도메인 | DB 테이블 | API 엔드포인트 수 |
|----------|--------|-----------|-------------------|
| P1 | 기준정보 (마스터) | `suppliers`, `customers`, `raw_materials`, `processes`, `equipment` | 20개 |
| P1 | 사용자 관리 | `users` 확장 (N:M `user_roles` → Sprint 3) | 5개 |
| P2 | 공정관리 | `work_orders`, `process_results` | 10개 |
| P2 | 품질 기초 | `quality_standards` | 4개 |
| P3 | 감사 로그 | `system_logs`, audit middleware | 2개 |

#### 프론트엔드 — 기능 페이지 구현

| 모듈 | 구현 내용 |
|------|-----------|
| `master-data/` | 공급업체 / 고객사 / 원자재 / 공정유형 / 설비 CRUD 테이블 |
| `process/` | 작업지시 목록 + 공정 실적 등록 폼 |
| `system/` | 사용자 목록 + 역할 관리 |
| `(dashboard)/page.tsx` | KPI 카드 → 실제 API 연동 (더미 데이터 제거) |

#### 인프라 / 공통

| 항목 | 내용 |
|------|------|
| Alembic `0002_master_data.py` | 5개 마스터 테이블 + FKs + 인덱스 |
| Alembic `0003_work_orders.py` | 작업지시 + 공정 실적 테이블 |
| Audit log middleware | 모든 POST/PATCH/DELETE에서 `system_logs` 자동 기록 |
| CI — GitHub Actions | lint (ruff + ESLint) + type-check (mypy + tsc) |

### 2.2 제외 (Out-of-Scope / Sprint 3+)

| 기능 | 이유 | 예정 Sprint |
|------|------|-------------|
| IoT MQTT→Kafka→Flink 파이프라인 | Sprint 1 Phase 1 M3 scope | Sprint 3 |
| TimescaleDB 하이퍼테이블 | IoT 파이프라인 의존 | Sprint 3 |
| N:M `user_roles` 전환 | 단일 role로 Sprint 1-2 충분 | Sprint 3 |
| RAG Agent / Qdrant | Phase 2 M5-8 scope | Sprint 5+ |
| Vision AI / ML | Phase 3 M9-14 scope | Sprint 9+ |
| WebSocket 실시간 알림 | IoT 파이프라인 먼저 | Sprint 4 |

---

## 3. 사용자 스토리

### US-01 기준정보 관리 (생산관리자 / 품질담당자)
> "공정에서 사용하는 원자재, 공급업체, 설비 목록을 등록하고 검색할 수 있다."

**인수 기준**:
- 공급업체/고객사 CRUD (이름, 코드, 연락처, 등급)
- 원자재 등록 시 공급업체 연결 (FK)
- 설비 등록 (코드, 이름, 공정유형, 상태)
- 페이지네이션 + 검색 (이름/코드 부분일치)

### US-02 작업지시 생성 및 LOT 연결 (생산관리자)
> "LOT에 대한 작업지시를 생성하고, 작업자를 배정하며, 공정 진행 상태를 추적할 수 있다."

**인수 기준**:
- 작업지시 생성 (lot_id 참조, 공정유형, 담당자, 계획 일정)
- 작업지시 상태 전환 (대기 → 진행 중 → 완료 / 보류)
- 공정 실적 등록 (수량, 작업 시간, 메모)
- LOT 역추적 화면에서 공정 실적 조회

### US-03 사용자 관리 (admin / executive)
> "시스템 관리자가 사용자를 등록하고, 역할과 소속 부서를 설정할 수 있다."

**인수 기준**:
- 사용자 목록 조회 (role, status 필터)
- 신규 사용자 초대 (이메일 + 역할 지정)
- 사용자 상태 변경 (active / inactive / suspended)
- 비밀번호 초기화 (관리자 권한)

### US-04 대시보드 실시간 연동 (생산관리자 / 경영진)
> "대시보드의 KPI 카드(생산량, 불량률, 설비 가동률, 출하 대기)가 실제 DB 데이터를 표시한다."

**인수 기준**:
- `/api/v1/dashboard/summary` 엔드포인트 → 오늘 집계 KPI 반환
- 7일 생산 추이 → `/api/v1/dashboard/production-trend`
- LOT 현황 → 실제 최근 5개 LOT 조회
- 30초 자동 갱신 (react-query + staleTime)

### US-05 감사 로그 (admin)
> "모든 데이터 변경 이력이 자동으로 기록되어 감사 추적이 가능하다."

**인수 기준**:
- POST/PATCH/DELETE 요청 시 `system_logs`에 자동 저장 (middleware)
- 감사 로그 조회 API (기간, 사용자, 리소스 필터)
- 로그 항목: actor_id, action, resource_type, resource_id, old_value(JSON), new_value(JSON), ip_address, timestamp

---

## 4. 기술 설계 포인트

### 4.1 DB 스키마 추가 (Alembic Migration 2개)

**0002_master_data.py**
```sql
-- suppliers: id, code(unique), name, contact, grade(A/B/C/D), is_active, created_at, updated_at
-- customers: id, code(unique), name, contact, business_no, is_active, created_at, updated_at
-- raw_materials: id, material_code(unique), name, spec, unit, supplier_id(FK), stock_qty, unit_price, created_at, updated_at
-- processes: id, process_code(unique), name, process_type(cutting/forming/welding/painting/inspection/other), std_time_minutes, is_active, created_at, updated_at
-- equipment: id, equipment_code(unique), name, process_id(FK), manufacturer, model_no, status(running/idle/maintenance/error), installed_at, created_at, updated_at
```

**0003_work_orders.py**
```sql
-- work_orders: id, wo_number(unique), lot_id(FK), process_id(FK), assigned_to(FK users.id), status(pending/in_progress/completed/on_hold), planned_start, planned_end, actual_start, actual_end, notes, created_at, updated_at
-- process_results: id, work_order_id(FK), lot_id(FK), equipment_id(FK nullable), input_qty, output_qty, defect_qty, worker_id(FK users.id), start_time, end_time, condition_notes, created_at
-- system_logs: id, actor_id(FK nullable), action(CREATE/UPDATE/DELETE/LOGIN/LOGOUT), resource_type, resource_id, old_value(JSONB nullable), new_value(JSONB nullable), ip_address, trace_id, created_at
```

### 4.2 API 구조 확장

```
backend/app/api/v1/
├── auth.py            (기존)
├── lots.py            (기존)
├── users.py           ← NEW: 사용자 관리 CRUD
├── master/
│   ├── suppliers.py   ← NEW
│   ├── customers.py   ← NEW
│   ├── materials.py   ← NEW
│   ├── processes.py   ← NEW
│   └── equipment.py   ← NEW
├── work_orders.py     ← NEW: 작업지시 + 공정실적
└── dashboard.py       ← NEW: 집계 쿼리 엔드포인트
```

**공통 패턴**: 모든 CRUD는 `PaginatedResponse[T]` 반환, `?search=`, `?status=`, `?page=`, `?limit=` 쿼리 파라미터 지원.

### 4.3 Audit Middleware

```python
# backend/app/middleware/audit.py
class AuditMiddleware(BaseHTTPMiddleware):
    AUDITABLE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
    SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/api/v1/auth/login"}
```

- `before_request`: 요청 바디 스냅샷 (변경 전 값)
- `after_response`: 응답 + DB 저장

### 4.4 프론트엔드 패턴

- `@tanstack/react-query` v5 도입 — API 페칭 표준화 (더미 데이터 완전 제거)
- `react-hook-form` + Zod validation — 폼 표준화
- DataTable 컴포넌트 (`components/ui/data-table.tsx`) — shadcn/ui Table 기반, 재사용
- 사이드바 `master-data`, `process`, `system` 모듈에 뱃지(건수 표시)

---

## 5. 스프린트 상세 일정

### Week 3 (백엔드 우선)

| 일자 | 작업 항목 |
|------|-----------|
| D1 | SQLAlchemy 모델 5개 (suppliers, customers, raw_materials, processes, equipment) + 0002 migration |
| D2 | 마스터 데이터 라우터 5개 + 기본 CRUD + 단위 테스트 |
| D3 | work_orders 모델 + process_results 모델 + 0003 migration |
| D4 | work_orders 라우터 + process_results 등록/조회 |
| D5 | users 라우터 (목록/상세/상태변경/비번초기화) + audit middleware |

### Week 4 (프론트엔드 + 통합)

| 일자 | 작업 항목 |
|------|-----------|
| D6 | react-query 설치 + QueryProvider 설정 + API 클라이언트 훅 |
| D7 | `master-data/` 페이지 — DataTable + CRUD 모달 (공급업체부터) |
| D8 | `master-data/` 나머지 (고객사, 원자재, 공정, 설비) |
| D9 | `process/` 페이지 — 작업지시 목록 + 공정실적 등록 폼 |
| D10 | 대시보드 실제 API 연동 + `system/` 사용자 관리 UI |

---

## 6. 완료 기준 (Definition of Done)

### 필수 (P0)
- [ ] 마스터 데이터 5개 테이블 Alembic migration 적용 (`alembic upgrade head` 성공)
- [ ] 마스터 데이터 CRUD API 20개 동작 (`/docs` Swagger 검증)
- [ ] 작업지시 생성 → 상태 전환 → 공정실적 등록 → LOT 역추적에서 조회 (E2E 흐름)
- [ ] 대시보드 KPI 더미 데이터 → 실제 API 연동
- [ ] Audit middleware — POST/PATCH/DELETE 시 `system_logs` 자동 저장 확인

### 권장 (P1)
- [ ] `master-data/` 페이지 실사용 가능 (CRUD 화면 + 검색)
- [ ] `process/` 페이지 — 작업지시 목록 + 실적 등록
- [ ] `system/` 사용자 관리 기능
- [ ] react-query 도입 — 더미 데이터 전면 제거
- [ ] CI — GitHub Actions lint + type-check 통과

### 다음 Sprint 진입 조건
- [ ] LOT 입고 → 공정 → 출하 흐름 전체 DB 구조 준비 완료
- [ ] 기준정보 데이터 사전 입력 (seed 데이터 — 공급업체 3개, 설비 5개, 공정유형 5개)

---

## 7. 의존성 및 리스크

| 항목 | 수준 | 대응 |
|------|------|------|
| react-query v5 API 변경 (`useQuery` hooks) | 중 | 공식 마이그레이션 가이드 참조, `useSuspenseQuery` 패턴 채택 |
| 감사 로그 미들웨어 비동기 성능 | 저 | background task (`asyncio.create_task`) 활용, 실패 시 silent fail |
| 작업지시 ↔ LOT FK 관계 복잡도 | 저 | Sprint 1 lot 모델 이미 완성, 단순 FK 추가 |
| CI 환경 세팅 시간 | 저 | GitHub Actions 표준 템플릿 활용 |

---

## 8. 참조 문서

| 문서 | 경로 |
|------|------|
| 통합 마스터 플랜 | `docs/01-plan/MASTER-PLAN.md` |
| MES 아키텍처 설계 | `docs/02-design/features/mes-architecture.design.md` |
| DB 스키마 전체 | `docs/02-design/db/schema.sql` |
| API 명세 | `docs/02-design/api/api-spec.md` |
| Sprint 1 완료 보고서 | `docs/04-report/mes-architecture.report.md` |
| Sprint 1 Gap 분석 | `docs/03-analysis/mes-architecture.analysis.md` |
