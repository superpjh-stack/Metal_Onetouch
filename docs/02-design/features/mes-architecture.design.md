# MES Architecture — Final Integrated Design

> **Summary**: 원터치(Onetouch) AI+MES 시스템의 최종 통합 설계 문서. 비기능 요구사항, 시스템 아키텍처, 데이터 모델, API 명세, 인프라, 보안, 모니터링, AI 통합 지점, Phase 1 스프린트 계획을 포괄.
>
> **Project**: Metal-Onetouch AI+MES
> **Version**: 1.0
> **Author**: Enterprise Architect Agent (superpjh@gmail.com)
> **Date**: 2026-04-30
> **Status**: Draft
> **Sources**:
> - `docs/01-plan/PM1-architecture-plan.md` — 전체 아키텍처 계획
> - `docs/01-plan/PM2-ai-features-plan.md` — AI 기능 계획
> - `docs/01-plan/PM3-data-architecture-plan.md` — 데이터 아키텍처
> - `docs/02-design/architecture/system-architecture.md` — 디렉토리/Docker/RBAC/IoT 상세

---

## Section 1. Executive Summary

### 1.1 비전

원터치 AI+MES는 금속 가공(판금/용접/절삭) 제조 현장의 **수주 → 생산 → 품질 → 출하** 전 과정을 **LOT 단위**로 추적하고, **RAG / Vision AI / ML** 기술로 의사결정을 자동화/가속하는 AI Native MES 플랫폼이다.

### 1.2 핵심 가치 제안

| 영역 | As-Is | To-Be | 개선 효과 |
|---|---|---|---|
| 견적 산출 | 2시간/건 (수작업) | 10분/건 (CAD AI 자동) | -92% |
| 클레임 추적 | 2일 | 30분 (LOT 추적) | -97% |
| 불량률 | 기준치 | -20% (작업조건 표준화) | 품질 향상 |
| 설비 고장 예측 | 없음 | 70%+ (Isolation Forest) | 신규 |
| 납기 준수율 | 기준치 | +5%p | 매출 |

### 1.3 시스템 범위

- **10대 업무 모듈**: 공정관리, 입고재고, 출하물류, 수주견적AI, 기준정보, AI대시보드, KPI, 데이터허브, AI Agent통합, 사용자/시스템관리
- **3 Phase 로드맵 (총 14개월)**: Phase 1 (MES 핵심, 16주) → Phase 2 (물류/품질+AI 기초, 16주) → Phase 3 (AI 고도화, 24주)
- **본 문서 범위**: Phase 1 상세 설계 + Phase 2~3 아키텍처 가이드라인

### 1.4 아키텍처 결정 요약

| 결정 | 채택 | 이유 |
|---|---|---|
| Monorepo | pnpm + Turborepo | AI 코드 생성 컨텍스트 통일, atomic commit |
| Backend | FastAPI (Python 3.11) | AI/ML 생태계 직접 연동, 비동기 I/O |
| Frontend | Next.js 14 (App Router) | SSR 대시보드, RSC로 초기 로딩 최적화 |
| Primary DB | PostgreSQL 16 + TimescaleDB | ACID + IoT 시계열 단일 클러스터 |
| Vector DB | Qdrant (온프레미스) | 한국 제조 데이터 외부 유출 차단 |
| Streaming | MQTT → Kafka → Flink → TimescaleDB | 표준 IoT 스택, 검증된 처리량 |
| 배포 | Docker Compose (개발) / K8s (운영) | 환경 분리, GitOps 지원 |

---

## Section 2. Non-Functional Requirements

### 2.1 성능 (Performance)

| 항목 | 목표 | 측정 방법 |
|---|---|---|
| API p95 응답 | ≤ 500ms | Prometheus histogram |
| API p99 응답 | ≤ 1.5s | Prometheus histogram |
| 대시보드 초기 로드 (LCP) | ≤ 2.5s | Lighthouse / Web Vitals |
| 실시간 센서 표시 지연 | ≤ 1s (수집→화면) | Kafka timestamp diff |
| LOT 이력 조회 | ≤ 3s (전체 공정) | API 로그 |
| 견적 자동 생성 | ≤ 10분 (도면 업로드→완료) | Celery 태스크 시간 |
| AI Agent 첫 토큰 응답 | ≤ 3s (스트리밍 시작) | LangSmith trace |
| IoT 처리량 | 10,000 events/sec | Kafka 메트릭 |
| DB 쓰기 | 5,000 ops/sec (sensor_data) | TimescaleDB 메트릭 |

### 2.2 확장성 (Scalability)

- **수평 확장 단위**: Backend(FastAPI) Pod, Celery Worker Pod, Flink TaskManager
- **Phase별 동시 사용자 목표**:
  - Phase 1: 50명 (단일 사이트)
  - Phase 2: 200명 (3개 사이트)
  - Phase 3: 500명 (10개 사이트, 다중 테넌트)
- **데이터 증가 가정**:
  - sensor_data: 10M rows/일 → TimescaleDB 압축 후 ~2GB/일
  - lot_history: 50K rows/일
  - cad_files: 평균 5MB × 100건/일 → 500MB/일 (MinIO)
- **샤딩/파티셔닝**:
  - sensor_data: TimescaleDB 시간 기반 chunk (1일)
  - lot_history: PostgreSQL 월별 파티션 (Phase 2부터)
  - Kafka: equipment_id 해시 파티셔닝

### 2.3 가용성 (Availability)

| 환경 | SLO | 목표 다운타임/월 | 대응 |
|---|---|---|---|
| Production | 99.9% | 43분 | DB Multi-AZ, Backend HPA min=2, ArgoCD rollback |
| Staging | 99.5% | 3.6시간 | 단일 AZ |
| Development | Best effort | - | Docker Compose |

**복구 목표**:
- RPO (Recovery Point Objective): 5분 (PostgreSQL WAL streaming)
- RTO (Recovery Time Objective): 30분 (Multi-AZ failover + ArgoCD sync)

### 2.4 보안 (Security)

- 모든 외부 트래픽 TLS 1.3
- JWT (HS256, 60분 만료) + Refresh Token (7일)
- Secret 관리: AWS Secrets Manager (운영), .env (개발)
- 모든 API 호출 RBAC 체크 (`require_permission` Depends)
- 민감 컬럼 암호화 (AES-256): cost_estimate.total_cost, supplier.contact
- 감사 로그: 모든 쓰기 작업 → audit_log 테이블 + ELK
- 정기 보안 스캔: Trivy (이미지), bandit (Python), npm audit (Node)

### 2.5 유지보수성 (Maintainability)

- Clean Architecture 4-Layer 강제 (api / services / domain / infrastructure)
- API 문서 자동 생성 (FastAPI OpenAPI 3.1)
- 테스트 커버리지: 단위 ≥ 80%, 통합 ≥ 60%
- 정적 분석: ruff, mypy --strict, eslint, tsc --noEmit
- 모든 DB 스키마 변경: Alembic migration
- CLAUDE.md 계층화 (project / frontend / backend / infra)

---

## Section 3. System Architecture

### 3.1 계층 다이어그램

```
┌────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                    │
│  Browser (PC) │ Tablet (현장) │ Mobile (Push 알림)                     │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │ HTTPS / WSS
┌──────────────────────────────▼─────────────────────────────────────────┐
│                         EDGE / GATEWAY                                  │
│  AWS ALB → Nginx Ingress (K8s)                                          │
│  - TLS 종료, JWT 검증 (외곽), Rate Limit, WAF                            │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌──────────────┐     ┌──────────────────┐    ┌───────────────────┐
│  FRONTEND    │     │   BACKEND API    │    │ WEBSOCKET GATEWAY │
│  Next.js 14  │     │   FastAPI        │    │ Socket.io         │
│  (RSC + CSR) │     │   (10 modules)   │    │ (Redis adapter)   │
│  shadcn/ui   │     │   /api/v1/*      │    │                   │
└──────────────┘     └────────┬─────────┘    └─────────┬─────────┘
                              │                        │
                ┌─────────────┼────────────────────────┼──────────┐
                ▼             ▼                        ▼          │
        ┌──────────────┐  ┌─────────────┐   ┌──────────────────┐  │
        │ APPLICATION  │  │  CELERY     │   │  AI AGENT        │  │
        │ SERVICES     │  │  WORKERS    │   │  RUNTIME         │  │
        │              │  │             │   │                  │  │
        │ - LotService │  │ - cad_parse │   │ - RAG (LangChain)│  │
        │ - Inspection │  │ - vision    │   │ - Vision (YOLOv8)│  │
        │ - Quotation  │  │ - shap      │   │ - Tool Calling   │  │
        │ - KPI        │  │ - rag_index │   │                  │  │
        │ - ERP Sync   │  │ - alerts    │   │                  │  │
        └──────┬───────┘  └──────┬──────┘   └─────────┬────────┘  │
               │                 │                    │           │
               └─────────────────┼────────────────────┘           │
                                 ▼                                │
┌────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                     │
│                                                                         │
│  ┌────────────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │ PostgreSQL 16      │   │  Redis 7     │   │  Qdrant              │ │
│  │ + TimescaleDB      │   │  - cache     │   │  (Vector / RAG)      │ │
│  │                    │   │  - sessions  │   │  collections:        │ │
│  │ - 트랜잭션 (lots,  │   │  - pub/sub   │   │  - inbound           │ │
│  │   processes,       │   │  - celery    │   │  - outbound          │ │
│  │   quality, etc.)   │   │  - rate-lim  │   │  - master            │ │
│  │ - hypertable       │   └──────────────┘   └──────────────────────┘ │
│  │   (sensor_data)    │                                                │
│  └────────────────────┘                                                │
│                                                                         │
│  ┌──────────────────┐   ┌──────────────┐   ┌──────────────────────┐  │
│  │ MinIO (S3)       │   │  MLflow      │   │  Elasticsearch       │  │
│  │ - cad-files      │   │  - models    │   │  (logs, audit)       │  │
│  │ - inspections    │   │  - exp track │   │                      │  │
│  │ - reports        │   │              │   │                      │  │
│  └──────────────────┘   └──────────────┘   └──────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                                 ▲
┌────────────────────────────────┴────────────────────────────────────┐
│                    STREAMING / IOT LAYER                              │
│                                                                       │
│  Edge PLC/CNC ─OPC-UA─> IoT Gateway ─MQTT─> Mosquitto                │
│                                                  │                    │
│                                                  ▼                    │
│                                         MQTT-Kafka Bridge             │
│                                                  │                    │
│                                                  ▼                    │
│                              ┌────────────────────────────────────┐   │
│                              │ Kafka (3 brokers)                  │   │
│                              │  raw.sensor.process                │   │
│                              │  raw.sensor.equipment              │   │
│                              │  processed.anomaly                 │   │
│                              │  alert.equipment                   │   │
│                              └─────┬──────────┬──────────┬────────┘   │
│                                    │          │          │            │
│                              ┌─────▼────┐ ┌───▼────┐ ┌──▼────────┐    │
│                              │ Flink    │ │ Flink  │ │ Flink     │    │
│                              │ Job 1    │ │ Job 2  │ │ Job 3     │    │
│                              │ (저장)   │ │(이상감지)│ │(알림)    │    │
│                              └─────┬────┘ └───┬────┘ └──┬────────┘    │
│                                    ▼          │         │            │
│                              TimescaleDB      │     Redis Pub/Sub    │
│                                               │     → Socket.io      │
│                                               ▼                       │
│                                         processed.anomaly            │
└──────────────────────────────────────────────────────────────────────┘
                                 ▲
┌────────────────────────────────┴────────────────────────────────────┐
│                      INTEGRATION LAYER                                │
│  ERP Adapter  │  IoT Gateway Adapter  │  External CAD/Logistics API  │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 컴포넌트 책임 분리

| 컴포넌트 | 단일 책임 | 비책임 (다른 컴포넌트) |
|---|---|---|
| Frontend | UI 렌더링, 사용자 입력 검증, 캐싱 | 비즈니스 룰 |
| Backend API | HTTP 라우팅, 권한 체크, DTO 변환 | 도메인 로직 (services 위임) |
| Application Service | 비즈니스 룰, 트랜잭션 경계 | DB SQL (Repository 위임) |
| Domain Layer | 엔티티, 불변식, 도메인 이벤트 | 외부 의존 |
| Infrastructure | DB, MinIO, Kafka, LLM 호출 | 비즈니스 룰 |
| Celery Worker | 비동기/장기 작업 (CAD 파싱, ML 추론) | 동기 API 응답 |
| Flink | 고처리량 스트림 처리 | 트랜잭션 DB 쿼리 |
| AI Agent Runtime | LLM 오케스트레이션, RAG 검색 | 권한 체크 (Backend 통과 후 호출) |

### 3.3 통신 패턴

| From → To | Protocol | 용도 |
|---|---|---|
| Browser → Backend | HTTPS (REST) | 일반 API |
| Browser → Backend | WSS (Socket.io) | 실시간 알림/대시보드 |
| Backend → Celery | Redis (broker) | 비동기 작업 큐 |
| Backend → DB | asyncpg (TCP) | SQLAlchemy async |
| Backend → Qdrant | gRPC | 벡터 검색 |
| Backend → LLM | HTTPS | OpenAI/Anthropic |
| MQTT → Kafka | Custom bridge | IoT 수집 |
| Flink → DB | JDBC | 시계열 적재 |
| Flink → Redis | Pub/Sub | 알림 브로드캐스트 |
| ERP ↔ Backend | REST / DB Link / 파일 배치 | 양방향 동기화 |

---

## Section 4. Data Model

### 4.1 핵심 엔티티 관계 (ERD 요약)

```
        ┌───────────────┐                ┌────────────────┐
        │   SUPPLIER    │                │  RAW_MATERIAL  │
        │  supplier_id  │◄───────────────│  material_id   │
        └───────────────┘                │  supplier_id FK│
                                         └────────┬───────┘
                                                  │ 1
                                                  │ ▲
                                                  │ N
                  ┌───────────────────┐    ┌──────▼─────────────┐
                  │ RAW_MATERIAL_RECEIPT │ │       LOT          │
                  │  receipt_id        │ │  lot_id (PK)        │
                  │  lot_id FK         ├─┤  raw_material_id FK │
                  │  inspector_id FK   │ │  parent_lot_id FK   │
                  └─────────┬──────────┘ │  status, quantity   │
                            │            └────┬───────┬────┬───┘
                            │ 1               │       │    │
                  ┌─────────▼────────┐        │       │    │
                  │  USER (inspector)│        │       │    │
                  └──────────────────┘        │       │    │
                                              │       │    │
              ┌───────────────────────────────┘       │    │
              ▼                                       ▼    ▼
   ┌────────────────────┐           ┌────────────────────┐ ┌────────────┐
   │  PROCESS_RECORD    │           │  QUALITY_RECORD    │ │ SHIPMENT   │
   │  record_id         │           │  record_id         │ │ shipment_id│
   │  lot_id FK         │           │  lot_id FK         │ │ lot_id FK  │
   │  process_id FK     │           │  inspection_type   │ │ customer   │
   │  equipment_id FK   │           │  result, defects   │ │ ship_date  │
   │  operator_id FK    │           │  inspector_id FK   │ └─────┬──────┘
   │  start_at, end_at  │           └────────────────────┘       │
   └────────┬───────────┘                                        │
            │                                              ┌─────▼──────┐
   ┌────────▼───────────┐                                  │  CLAIM     │
   │  EQUIPMENT         │                                  │ claim_id   │
   │  equipment_id      │◄──── sensor_data (hypertable)    │ shipment_id│
   └────────────────────┘                                  │ lot_id FK  │
                                                          └────────────┘

   ┌──────────────────┐          ┌────────────────────────┐
   │  USER            │N        N│  ROLE                  │
   │  user_id         ├──────────┤  role_id               │
   └────────┬─────────┘          │  permissions (JSON)    │
            │                    └────────────────────────┘
            │ N        ┌──────────────────────┐
            └─────────►│  AUDIT_LOG           │
                       │  user_id, action,    │
                       │  resource, ts, diff  │
                       └──────────────────────┘

   ┌──────────────────────┐    ┌─────────────────────┐
   │  QUOTATION           │    │  BOM (Bill of Materials)│
   │  quotation_id        │1──N│  bom_id              │
   │  cad_file_url        │    │  quotation_id FK     │
   │  estimated_cost      │    │  material_id FK      │
   │  shap_top5 (JSONB)   │    │  qty, unit           │
   │  status              │    └─────────────────────┘
   └──────────────────────┘
```

### 4.2 주요 DDL 요약

```sql
-- ========================================
-- 1) USERS / ROLES (RBAC)
-- ========================================
CREATE TABLE roles (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(50) UNIQUE NOT NULL,
    name        VARCHAR(100) NOT NULL,
    permissions JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    name        VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_roles (
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    role_id INT REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- ========================================
-- 2) LOT 핵심 엔티티
-- ========================================
CREATE TYPE lot_status AS ENUM (
    '입고대기', '공정중', '검사중', '출하대기', '출하완료', '반품'
);

CREATE TABLE raw_materials (
    material_id     VARCHAR(20) PRIMARY KEY,
    material_name   VARCHAR(100) NOT NULL,
    spec_code       VARCHAR(50),
    supplier_id     VARCHAR(20) REFERENCES suppliers(supplier_id),
    unit_weight     NUMERIC(10,3),
    standard_doc_url VARCHAR(500),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE lots (
    lot_id          VARCHAR(20) PRIMARY KEY,
    raw_material_id VARCHAR(20) REFERENCES raw_materials(material_id),
    parent_lot_id   VARCHAR(20) REFERENCES lots(lot_id),
    received_at     TIMESTAMPTZ,
    lot_status      lot_status NOT NULL DEFAULT '입고대기',
    quantity        NUMERIC(10,3),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_lots_status_received ON lots(lot_status, received_at);
CREATE INDEX ix_lots_parent ON lots(parent_lot_id);

CREATE TABLE lot_history (
    id          BIGSERIAL PRIMARY KEY,
    lot_id      VARCHAR(20) REFERENCES lots(lot_id) ON DELETE CASCADE,
    event_type  VARCHAR(50) NOT NULL,   -- received, process_started, etc.
    event_at    TIMESTAMPTZ NOT NULL,
    actor_id    INT REFERENCES users(id),
    payload     JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_lot_history_lot_at ON lot_history(lot_id, event_at);

-- ========================================
-- 3) PROCESS / EQUIPMENT
-- ========================================
CREATE TABLE processes (
    process_id      VARCHAR(20) PRIMARY KEY,
    process_name    VARCHAR(100),
    sequence_no     INT,
    standard_params JSONB
);

CREATE TABLE equipment (
    equipment_id    VARCHAR(50) PRIMARY KEY,
    equipment_name  VARCHAR(100),
    site_id         VARCHAR(20),
    line_id         VARCHAR(20),
    grade           VARCHAR(10),  -- A/B/C
    spec            JSONB
);

CREATE TABLE process_records (
    record_id       BIGSERIAL PRIMARY KEY,
    lot_id          VARCHAR(20) REFERENCES lots(lot_id),
    process_id      VARCHAR(20) REFERENCES processes(process_id),
    equipment_id    VARCHAR(50) REFERENCES equipment(equipment_id),
    operator_id     INT REFERENCES users(id),
    start_at        TIMESTAMPTZ,
    end_at          TIMESTAMPTZ,
    actual_params   JSONB,
    result          VARCHAR(20),    -- '정상', '재작업', '폐기'
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_process_records_lot ON process_records(lot_id);
CREATE INDEX ix_process_records_eq_start ON process_records(equipment_id, start_at);

-- ========================================
-- 4) sensor_data (TimescaleDB hypertable)
-- ========================================
CREATE TABLE sensor_data (
    ts           TIMESTAMPTZ NOT NULL,
    equipment_id VARCHAR(50) NOT NULL,
    sensor_type  VARCHAR(30) NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    unit         VARCHAR(10),
    lot_id       VARCHAR(20),
    site_id      VARCHAR(20)
);
SELECT create_hypertable('sensor_data', 'ts');
CREATE INDEX ix_sensor_eq_ts ON sensor_data(equipment_id, ts DESC);
SELECT add_retention_policy('sensor_data', INTERVAL '180 days');

-- 1분 평균 연속 집계
CREATE MATERIALIZED VIEW sensor_data_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', ts) AS bucket,
    equipment_id, sensor_type,
    AVG(value) AS avg_value,
    MAX(value) AS max_value,
    MIN(value) AS min_value
FROM sensor_data
GROUP BY bucket, equipment_id, sensor_type;

-- ========================================
-- 5) QUALITY / SHIPMENT / CLAIMS
-- ========================================
CREATE TABLE quality_records (
    record_id       BIGSERIAL PRIMARY KEY,
    lot_id          VARCHAR(20) REFERENCES lots(lot_id),
    inspection_type VARCHAR(30),     -- 입고/공정/출하
    result          VARCHAR(20),     -- 합격/불합격/조건부
    defect_codes    TEXT[],
    measured_values JSONB,
    inspector_id    INT REFERENCES users(id),
    inspected_at    TIMESTAMPTZ,
    photos          TEXT[]           -- MinIO URLs
);

CREATE TABLE shipments (
    shipment_id     VARCHAR(30) PRIMARY KEY,
    lot_id          VARCHAR(20) REFERENCES lots(lot_id),
    customer_id     VARCHAR(20),
    ship_date       DATE,
    quantity        NUMERIC(10,3),
    inspection_pass BOOLEAN,
    erp_sync_id     VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE claims (
    claim_id        BIGSERIAL PRIMARY KEY,
    shipment_id     VARCHAR(30) REFERENCES shipments(shipment_id),
    lot_id          VARCHAR(20) REFERENCES lots(lot_id),
    claim_type      VARCHAR(50),
    description     TEXT,
    severity        VARCHAR(10),
    root_cause      TEXT,
    countermeasure  TEXT,
    status          VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- 6) QUOTATION (수주견적AI)
-- ========================================
CREATE TABLE quotations (
    quotation_id    VARCHAR(30) PRIMARY KEY,
    customer_id     VARCHAR(20),
    cad_file_url    VARCHAR(500),
    parsed_features JSONB,
    estimated_cost  NUMERIC(15,2),
    shap_top5       JSONB,
    confidence      NUMERIC(3,2),
    status          VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bom (
    bom_id          BIGSERIAL PRIMARY KEY,
    quotation_id    VARCHAR(30) REFERENCES quotations(quotation_id),
    material_id     VARCHAR(20) REFERENCES raw_materials(material_id),
    qty             NUMERIC(10,3),
    unit            VARCHAR(10),
    process_seq     JSONB
);

-- ========================================
-- 7) AUDIT
-- ========================================
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     INT,
    action      VARCHAR(20),     -- create/update/delete
    resource    VARCHAR(100),
    resource_id VARCHAR(100),
    diff        JSONB,
    ip_address  INET,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_audit_user_at ON audit_log(user_id, created_at DESC);
```

### 4.3 데이터 거버넌스 핵심 원칙

1. **LOT 불변성**: `lot_id`는 생성 후 절대 변경 불가. 상태 변경은 `lot_history`에 append-only.
2. **추적 무결성**: 자식 LOT(분할/병합) 생성 시 반드시 `parent_lot_id` 기록.
3. **소프트 삭제 금지**: 운영 데이터는 hard delete 금지. 상태 전환(`반품`, `폐기`)으로 대체.
4. **마스터 데이터 단일 소스**: `raw_materials`, `processes`, `equipment` 마스터는 ERP 또는 MES 중 한쪽만 OWNER. 본 시스템에서는 MES = OWNER로 결정.
5. **개인정보 마스킹**: `data_hub` 추출 시 `users.email`, `users.name`은 해시 변환.

---

## Section 5. API Specification

> 전체 OpenAPI 명세는 `docs/02-design/api-spec/openapi.yaml`에서 자동 생성. 본 문서는 핵심 엔드포인트만 요약.

### 5.1 인증 / 사용자

| Method | Path | 설명 | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/login` | 이메일/비밀번호 → access+refresh 토큰 | - |
| POST | `/api/v1/auth/refresh` | refresh → 새 access | refresh |
| POST | `/api/v1/auth/logout` | 토큰 폐기 | access |
| GET | `/api/v1/users/me` | 현재 사용자 + 권한 | access |

### 5.2 LOT / 추적

| Method | Path | Permission |
|---|---|---|
| GET | `/api/v1/lots` | `process.history:read` |
| GET | `/api/v1/lots/{lot_id}` | `process.history:read` |
| GET | `/api/v1/lots/{lot_id}/history` | `process.history:read` |
| GET | `/api/v1/lots/{lot_id}/lineage` | `process.history:read` |
| POST | `/api/v1/lots` | `process.records:write` |
| PATCH | `/api/v1/lots/{lot_id}/status` | `process.records:write` |

### 5.3 공정 / 설비

| Method | Path | Permission |
|---|---|---|
| POST | `/api/v1/processes/records` | `process.records:write` |
| GET | `/api/v1/processes/records?lot_id=&start=&end=` | `process.history:read` |
| GET | `/api/v1/equipment` | `process.monitoring:read` |
| GET | `/api/v1/equipment/{id}/sensors?range=24h` | `process.monitoring:read` |
| PUT | `/api/v1/processes/conditions/{process_id}` | `process.conditions:write` |

### 5.4 품질 / 입고 / 출하

| Method | Path | Permission |
|---|---|---|
| POST | `/api/v1/inventory/receipts` | `inventory.receipts:write` |
| POST | `/api/v1/inventory/receipts/{id}/inspection` | `inventory.receipts:write` |
| GET | `/api/v1/inventory/supplier-quality?supplier_id=&period=` | `inventory.supplier_quality:read` |
| POST | `/api/v1/shipment/orders` | `shipment.orders:write` |
| POST | `/api/v1/shipment/inspections` | `shipment.inspection:write` |
| POST | `/api/v1/shipment/claims` | `shipment.claims:write` |

### 5.5 견적 (수주견적 AI)

| Method | Path | Permission | 설명 |
|---|---|---|---|
| POST | `/api/v1/quotation/upload` | `quotation:write` | CAD 업로드 (multipart) → quotation_id 반환 |
| GET | `/api/v1/quotation/{id}/status` | `quotation:read` | 비동기 작업 상태 |
| GET | `/api/v1/quotation/{id}` | `quotation:read` | 분석 결과 (BOM, 원가, SHAP) |
| POST | `/api/v1/quotation/{id}/confirm` | `quotation:write` | 견적 확정 → 수주 생성 |

### 5.6 KPI / 데이터허브

| Method | Path | Permission |
|---|---|---|
| GET | `/api/v1/kpi/production?from=&to=&line_id=` | `kpi:read` |
| GET | `/api/v1/kpi/quality?from=&to=` | `kpi:read` |
| PUT | `/api/v1/kpi/targets/{kpi_code}` | `kpi.targets:write` |
| POST | `/api/v1/data-hub/exports` | `data_hub:read` |

### 5.7 AI Agent

| Method | Path | Permission |
|---|---|---|
| POST | `/api/v1/ai/chat` | `ai_agent:write` |
| GET | `/api/v1/ai/conversations` | `ai_agent:read` |
| GET | `/api/v1/ai/conversations/{id}` | `ai_agent:read` |
| POST | `/api/v1/ai/feedback/{message_id}` | `ai_agent:write` |

WebSocket:
- `WSS /api/v1/ws/equipment/{site_id}` — 센서 스트림
- `WSS /api/v1/ws/alerts/{user_id}` — 개인 알림
- `WSS /api/v1/ws/ai/{conversation_id}` — AI 스트리밍 응답

### 5.8 표준 응답 형태

```json
// 성공
{
  "data": { ... },
  "meta": { "total": 120, "page": 1, "size": 20 }
}

// 에러
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "lot_id 형식이 올바르지 않습니다",
    "details": [
      { "field": "lot_id", "reason": "regex_mismatch" }
    ]
  },
  "trace_id": "01HX..."
}
```

---

## Section 6. Infrastructure

### 6.1 개발 환경 (Docker Compose 요약)

`infra/docker/docker-compose.yml`에 정의된 11개 서비스로 단일 명령 기동:

```bash
cd infra/docker
docker compose up -d
```

| 서비스 | 포트 | 용도 |
|---|---|---|
| frontend | 3000 | Next.js dev server (HMR) |
| backend | 8000 | FastAPI uvicorn (--reload) |
| celery-worker | - | Celery (4 concurrency) |
| celery-beat | - | 스케줄러 |
| postgres | 5432 | TimescaleDB 16 |
| redis | 6379 | 캐시 + Celery broker |
| minio | 9000/9101 | S3 호환 |
| qdrant | 6333/6334 | 벡터 DB |
| kafka | 9094 | 외부 노출 (개발) |
| zookeeper | 2181 | (Kafka 의존) |
| mosquitto | 1883/9081 | MQTT |
| mlflow | 5000 | 실험 추적 |
| mqtt-bridge | - | MQTT → Kafka |

### 6.2 운영 환경 (Kubernetes)

#### 클러스터 구성 (AWS EKS)

```
EKS Cluster (1.30, 3 AZ)
├── Node Group: app (t3.large × 3, autoscale 3~12)
│   ├── ingress-nginx
│   ├── frontend (HPA min=2 max=8)
│   ├── backend (HPA min=3 max=15, CPU 70%)
│   └── celery-worker (HPA min=2 max=10, queue 길이 기반)
│
├── Node Group: ai (g4dn.xlarge × 1, on-demand)
│   ├── celery-worker-vision (YOLOv8 GPU 추론)
│   └── (Phase 3) embedding-server (BGE-M3)
│
├── Node Group: data (m6i.xlarge × 3)
│   ├── kafka (Strimzi operator, 3 broker)
│   ├── flink (1 JobManager + 3 TaskManager)
│   └── qdrant (StatefulSet, 3 replicas)
│
└── Managed Services
    ├── RDS PostgreSQL 16 + TimescaleDB (Multi-AZ, db.r6g.xlarge)
    ├── ElastiCache Redis 7 (cluster mode, 2 shards × 2 replicas)
    ├── S3 (cad-files, inspection-images, reports, mlflow-artifacts)
    ├── MSK 또는 self-hosted Kafka
    └── Secrets Manager
```

#### 핵심 K8s 매니페스트 (요약)

```yaml
# infra/k8s/base/backend/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: backend }
spec:
  replicas: 3
  selector: { matchLabels: { app: backend } }
  template:
    metadata: { labels: { app: backend } }
    spec:
      containers:
      - name: backend
        image: ${ECR}/onetouch-backend:${TAG}
        ports: [{ containerPort: 8000 }]
        envFrom:
          - secretRef: { name: backend-secrets }
          - configMapRef: { name: backend-config }
        resources:
          requests: { cpu: 200m, memory: 512Mi }
          limits:   { cpu: 1000m, memory: 1Gi }
        livenessProbe:
          httpGet: { path: /health, port: 8000 }
          initialDelaySeconds: 30
        readinessProbe:
          httpGet: { path: /health/ready, port: 8000 }
---
# HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: backend }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: backend }
  minReplicas: 3
  maxReplicas: 15
  metrics:
  - type: Resource
    resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
```

### 6.3 CI/CD (GitOps)

```
Developer Push → GitHub
    ├─ feat/* / fix/*  →  CI (lint, test, security scan)
    │                  →  Docker build → ECR :sha
    │
    ├─ PR to staging   →  ArgoCD Auto Sync (staging overlay)
    │                  →  E2E + Smoke
    │
    └─ PR to main      →  ArgoCD Manual Sync (production)
                       →  Blue/Green via Argo Rollouts
                       →  Slack 알림
```

### 6.4 환경 분리

| 환경 | URL | DB | 배포 |
|---|---|---|---|
| Local | http://localhost:3000 | Compose Postgres | `docker compose up` |
| Staging | https://staging.onetouch.example.com | RDS staging | ArgoCD 자동 |
| Production | https://onetouch.example.com | RDS prod (Multi-AZ) | ArgoCD 수동 + Blue/Green |

---

## Section 7. Security

### 7.1 RBAC 매트릭스 (요약)

| 모듈 | production_manager | quality_inspector | process_engineer | executive | sales_engineer |
|---|---|---|---|---|---|
| 공정관리 | RW | R | RW | R | - |
| 입고재고 | R | RW | - | R | - |
| 출하물류 | RW | RW | R | R | R |
| 수주견적AI | - | - | - | R | RW |
| 기준정보 | R | RW | RW | R | - |
| AI 대시보드 | RW | R | R | R | R |
| KPI 조회 | RW | R | R | R | R |
| KPI 목표설정 | RW | - | - | RW | - |
| 데이터허브 | R | R | R | R | R |
| AI Agent | RW | RW | RW | RW | RW |
| 사용자/시스템 | - | - | - | RW | - |

> 상세 권한 코드 및 FastAPI Depends 구현은 `system-architecture.md` Section 4 참고.

### 7.2 보안 체크리스트

#### 7.2.1 인증/인가
- [ ] 모든 API 엔드포인트 `Depends(get_current_user)` 또는 `require_permission` 적용
- [ ] JWT secret 256bit 이상, 운영은 Secrets Manager 보관
- [ ] Refresh token 회전(rotation) 적용
- [ ] 비밀번호 bcrypt cost ≥ 12
- [ ] 5회 연속 로그인 실패 시 5분 잠금

#### 7.2.2 통신
- [ ] 모든 외부 트래픽 TLS 1.3
- [ ] 내부 서비스 간 통신은 mTLS (Phase 3, Istio)
- [ ] CORS 화이트리스트 (개발 와일드카드 금지)
- [ ] HSTS, CSP 헤더 설정

#### 7.2.3 데이터
- [ ] DB 컬럼 암호화: 견적 원가, 거래처 연락처
- [ ] PII 마스킹: data_hub 추출 시 자동 적용
- [ ] DB 백업 암호화 (KMS)
- [ ] RDS at-rest 암호화 활성화
- [ ] MinIO bucket 정책: backend pod IAM Role만 PutObject

#### 7.2.4 인프라/운영
- [ ] 컨테이너 이미지 Trivy 스캔 (CI)
- [ ] Python 의존성 bandit + pip-audit
- [ ] Frontend npm audit (high 이상 차단)
- [ ] Public subnet에는 ALB/NAT만, DB는 private
- [ ] IRSA (IAM Roles for Service Accounts)로 최소 권한
- [ ] Audit log 90일 이상 보관 (Phase 1 → Elasticsearch)
- [ ] Secret rotation 90일 주기

#### 7.2.5 AI 특화
- [ ] LLM 프롬프트 인젝션 방어 (입력 sanitize)
- [ ] RAG 검색 결과에 사용자 권한 외 데이터 포함 금지 (post-filter)
- [ ] LLM 호출 로그에서 PII 마스킹
- [ ] CAD 파일 확장자 화이트리스트 (.dwg, .dxf, .pdf만)
- [ ] CAD 파일 안티바이러스 스캔 (ClamAV)

---

## Section 8. Monitoring & Observability

### 8.1 메트릭 수집 (Prometheus)

| 카테고리 | 핵심 메트릭 | 알림 기준 |
|---|---|---|
| API | `http_request_duration_seconds` (p95) | > 1s for 5min → warning |
| API | `http_requests_total{status="5xx"}` | rate > 1/min → critical |
| DB | `pg_stat_database_blks_hit_ratio` | < 0.95 for 10min → warning |
| DB | `pg_replication_lag_seconds` | > 30s → critical |
| Redis | `redis_memory_used_bytes` | > 80% maxmemory → warning |
| Kafka | `kafka_consumer_lag_sum` | > 10,000 for 5min → critical |
| Flink | `flink_jobmanager_job_uptime` | drop → critical |
| Celery | `celery_queue_length` | > 500 for 10min → warning |
| Celery | `celery_task_failed_total` | rate > 5/min → warning |
| GPU | `nvidia_gpu_utilization` | (Vision worker, Phase 3) |
| Sensor | `sensor_data_ingest_rate` | < 50% baseline → warning |
| LLM | `llm_request_latency_seconds` (p95) | > 5s → warning |
| LLM | `llm_request_cost_usd_total` | 일일 한도 초과 → critical |

### 8.2 Grafana 대시보드

1. **System Health**: Pod 상태, 노드 리소스, Ingress QPS
2. **API Performance**: 모듈별 p50/p95/p99, 에러율, 처리량
3. **Database**: 커넥션 풀, slow query, hypertable 크기
4. **Streaming**: Kafka lag, Flink throughput, MQTT 메시지율
5. **Business KPI**: 라인별 OEE, 일일 LOT 처리량, 불량률
6. **AI Operations**: LLM 비용/일, RAG 응답 시간, Vision 정확도(MLflow 연동)
7. **Security**: 401/403 빈도, 비정상 로그인 시도

### 8.3 로깅 (Structured JSON → Elasticsearch)

```python
# backend/app/core/logging.py 예시 출력
{
  "ts": "2026-04-30T10:23:45.123Z",
  "level": "INFO",
  "service": "backend",
  "trace_id": "01HX...",
  "user_id": 42,
  "request_id": "req_abc123",
  "method": "GET",
  "path": "/api/v1/lots/L20260430-001",
  "status": 200,
  "duration_ms": 87,
  "msg": "lot retrieved"
}
```

ELK 인덱스 분리:
- `onetouch-app-*` (애플리케이션 로그, 30일)
- `onetouch-audit-*` (감사 로그, 365일)
- `onetouch-llm-*` (LLM 호출, 90일, 비용 추적)

### 8.4 분산 추적 (OpenTelemetry)

- Backend → Celery → DB 트레이스 자동 전파 (OTLP → Tempo or Jaeger)
- Frontend RUM (Real User Monitoring)으로 LCP/INP 수집
- LangSmith로 LLM/RAG 체인 단계별 추적

### 8.5 알림 라우팅 (Alertmanager)

| Severity | 채널 | SLA |
|---|---|---|
| critical | PagerDuty + Slack #onetouch-oncall + SMS | 15분 |
| warning | Slack #onetouch-alerts | 다음 영업일 |
| info | Slack #onetouch-info | 모니터링만 |

비즈니스 이벤트 알림 (이상 감지/품질 실패) → Frontend WebSocket + 모바일 Push (FCM).

---

## Section 9. AI Integration Points

### 9.1 AI 기능 맵

```
┌─────────────────────────────────────────────────────────────┐
│                       AI 기능 분포                            │
├──────────────────────┬───────────────────────────────────────┤
│   Phase 1 (MVP)       │  - 기본 알림 룰 (이상 임계치)          │
│                       │  - Isolation Forest 이상 감지 (Job 2)  │
├──────────────────────┼───────────────────────────────────────┤
│   Phase 2 (RAG 기초)  │  - 입고 AI Agent (RAG)                │
│                       │  - 출하 AI Agent (클레임 분석)         │
│                       │  - 공급처 품질 트렌드 NL Q&A           │
├──────────────────────┼───────────────────────────────────────┤
│   Phase 3 (고도화)    │  - 수주견적 AI (CAD Vision + ML)       │
│                       │  - 통합 AI Agent (Multi-Tool)          │
│                       │  - SHAP 설명 + 보정 계수 ML            │
│                       │  - 설비 고장 예측 (시계열 ML)          │
└──────────────────────┴───────────────────────────────────────┘
```

### 9.2 통합 지점

| AI 기능 | 트리거 | 데이터 소스 | 출력 | 모듈 위치 |
|---|---|---|---|---|
| **이상 감지** | 실시간 (Flink Job 2) | sensor_data 슬라이딩 윈도우 | `processed.anomaly` Kafka | streaming/flink |
| **알림 라우팅** | 이상 이벤트 발생 | 룰 + Equipment Master | WebSocket + Push | streaming/flink Job 3 |
| **입고 AI Agent** | 사용자 자연어 질의 | Qdrant `inbound` + `raw_material_receipts` | 스트리밍 답변 | backend/app/ai/agents/inbound_agent.py |
| **출하 AI Agent** | 클레임 등록 시 자동 + 수동 질의 | Qdrant `outbound` + `claims` + `lot_history` | 원인 LOT 후보 + 답변 | backend/app/ai/agents/outbound_agent.py |
| **CAD 분석** | 견적 업로드 (Celery 태스크) | DWG/DXF/PDF | 형상/치수/공차 JSON | backend/app/ai/vision/ |
| **원가 예측** | CAD 분석 완료 시 후속 | parsed_features + 과거 견적 DB | 예측값 + 신뢰도 | backend/app/ai/ml/cost_model.py |
| **SHAP 설명** | 원가 예측 완료 시 | XGBoost 모델 + features | 영향요인 Top 5 | backend/app/ai/ml/shap_explainer.py |
| **통합 AI Agent** | 사용자 자연어 질의 | 모든 도메인 + Tool Calling | 답변 + 인용 + 차트 | backend/app/ai/agents/master_agent.py |
| **RAG 인덱싱** | 문서 업로드 / 정기 배치 | 작업표준, 품질기준, 매뉴얼 | Qdrant collections | backend/app/workers/tasks/rag_indexing.py |

### 9.3 AI 호출 패턴

#### Sync (FastAPI 엔드포인트, < 5s)
```
사용자 → POST /api/v1/ai/chat
    → AI Agent (LangChain)
    → Qdrant 검색 (gRPC)
    → LLM API (스트리밍)
    → Server-Sent Events 응답
```

#### Async (Celery, > 5s)
```
사용자 → POST /api/v1/quotation/upload
    → Celery 태스크 enqueue
    → cad_parse (ezdxf, 30s)
    → vision_inference (YOLOv8, 1min, GPU 노드)
    → cost_prediction (XGBoost, 1s)
    → shap_explain (5s)
    → DB 업데이트 + WebSocket 알림
사용자 ← GET /api/v1/quotation/{id}/status
```

### 9.4 모델 라이프사이클 (MLflow)

| 단계 | 도구 | 산출물 |
|---|---|---|
| 실험 | MLflow Tracking | runs, params, metrics |
| 등록 | MLflow Model Registry | versioned model |
| 배포 | Stage 전환 (Staging → Production) | URI |
| 추론 | Celery worker가 시작 시 mlflow.load | in-memory |
| 모니터링 | Prediction logging → Drift detection | weekly report |

---

## Section 10. Implementation Plan (Phase 1 상세)

### 10.1 Phase 1 목표

**기간**: 2026-05-06 ~ 2026-08-21 (16주, 8 스프린트)
**팀 구성** (가정): PO 1명, Tech Lead 1명, Backend 2명, Frontend 2명, AI/Data 1명, QA 1명

**완료 기준 (Definition of Done)**:
1. LOT 기반 공정 실적 등록/조회 정상 동작
2. IoT 4종 센서 실시간 대시보드 표시 (1초 이내 지연)
3. RBAC 5개 역할 적용
4. API p95 ≤ 500ms
5. Staging 환경 안정 운영 4주
6. 운영 환경 배포 완료

### 10.2 스프린트 계획 (8 sprints × 2주)

#### Sprint 1 (W1-2): 기반 구축
- 모노레포 초기화 (pnpm workspace, turbo.json)
- Docker Compose 11개 서비스 기동 검증
- FastAPI 스켈레톤 + health check
- Next.js 14 App Router + shadcn/ui 셋업
- DB 스키마 v0 (users, roles, lots, raw_materials)
- Alembic 마이그레이션 첫 작성
- CI 파이프라인 (lint + test + docker build)

**Output**: 로컬 `docker compose up`으로 전체 스택 기동.

#### Sprint 2 (W3-4): 인증/RBAC
- JWT 발급/검증 (`backend/app/core/security.py`)
- `require_permission` Depends 구현
- 5개 역할 시드 (`scripts/seed_master_data.py`)
- 로그인/로그아웃/토큰 갱신 API
- Frontend NextAuth 통합, 로그인 페이지
- 관리자용 사용자 CRUD API

**Output**: 5개 역할 계정으로 로그인 가능, 권한 별 메뉴 표시.

#### Sprint 3 (W5-6): 기준정보 + 마스터 UI
- raw_materials, processes, equipment 모델 + CRUD
- master_data API 5종
- Frontend 마스터 관리 페이지 (테이블 + 폼)
- DB seed: 샘플 원자재 100건, 공정 20건, 설비 30건
- audit_log 미들웨어 (모든 쓰기 자동 기록)

**Output**: 품질담당자 역할로 기준정보 관리 가능.

#### Sprint 4 (W7-8): 공정관리 핵심
- lots, lot_history, process_records 모델
- LOT 생성/상태 변경 API + lot_history 자동 기록
- 공정 실적 등록 API (POST /processes/records)
- LOT 이력 조회 API (GET /lots/{id}/history)
- Frontend 공정 실적 입력 폼 (React-Hook-Form + Zod)
- LOT 추적 화면 (타임라인 UI)

**Output**: 생산관리자가 LOT 단위 공정 실적 등록 가능, LOT 번호로 이력 조회 가능.

#### Sprint 5 (W9-10): IoT 파이프라인
- TimescaleDB hypertable + retention 정책 적용
- MQTT broker (Mosquitto) 설정
- mqtt-bridge 서비스 (MQTT → Kafka)
- Flink Job 1 (저장) PoC
- Backend WebSocket 엔드포인트 (`/ws/equipment/{site_id}`)
- Frontend 실시간 센서 차트 컴포넌트 (Recharts + Socket.io)
- IoT 시뮬레이터 (개발용 가짜 PLC 데이터 발행)

**Output**: 시뮬레이터 데이터가 1초 이내 화면 차트에 표시.

#### Sprint 6 (W11-12): AI 대시보드 + 이상 감지
- Flink Job 2 (Isolation Forest 이상 감지) 구현
- processed.anomaly 토픽 → Redis Pub/Sub → WebSocket
- AI 대시보드 페이지 (생산현황, 설비상태)
- 알림 컴포넌트 (toast + 이력)
- Flink Job 3 (알림 라우팅) 구현
- 알림 룰 관리 UI (관리자)

**Output**: 임계치 초과 시 30초 이내 화면 알림 + 차트에 마커 표시.

#### Sprint 7 (W13-14): 안정화 + 통합 테스트
- E2E 시나리오 테스트 (Playwright)
- 부하 테스트 (k6, 50 동시 사용자, API p95 측정)
- 보안 점검 (Trivy, bandit, npm audit)
- DB 인덱스 최적화 (slow query log 분석)
- 로깅/모니터링 정비 (Prometheus + Grafana 대시보드 5개)
- KPI 모듈 기본 (생산량, 가동률) 추가

**Output**: 부하 테스트 통과, 모든 critical alert 0건 24시간 유지.

#### Sprint 8 (W15-16): 운영 배포
- Terraform 운영 인프라 프로비저닝 (EKS, RDS, S3, ElastiCache)
- ArgoCD 셋업, GitOps 파이프라인
- 운영용 K8s 매니페스트 (overlays/production)
- Blue/Green 배포 시나리오 검증
- 보안 점검 (외부 펜테스트 1회)
- 운영자 교육 + 운영 매뉴얼 (`docs/04-operation/`)
- 사용자 교육 자료
- Soft-launch (1개 라인 30일 운영)

**Output**: 운영 환경에서 1개 생산 라인 실제 운영, KPI 모니터링 가능.

### 10.3 Phase 1 리스크 및 대응

| 리스크 | 영향 | 대응 |
|---|---|---|
| IoT 설비 프로토콜 다양성 | 중 | Sprint 5 시작 전 1주 spike, 시뮬레이터 우선 개발 |
| TimescaleDB 운영 경험 부족 | 중 | 외부 DBA 자문 + 부하 테스트 (Sprint 7) |
| 사용자 교육 미흡 | 고 | Sprint 6부터 PO와 주간 데모, Sprint 8에 2회 교육 |
| 신규 인프라 (K8s) 학습 비용 | 중 | Sprint 1~3은 Compose만 사용, K8s는 Sprint 8 집중 |

### 10.4 Phase 2 / Phase 3 가이드라인

#### Phase 2 (W17-32): 물류/품질 + RAG
- 입고재고관리, 출하물류관리 모듈 풀스택
- RAG 인프라 (Qdrant 컬렉션 3개, BGE-M3 임베딩)
- 입고/출하 AI Agent
- KPI 완성 (품질, 출하)
- ELK Stack 운영 도입

#### Phase 3 (W33-56): AI 고도화
- 수주견적AI (Vision + ML + SHAP)
- 통합 AI Agent (Tool Calling)
- 데이터허브 (학습 데이터셋 추출/버전관리)
- ERP 양방향 동기화
- Multi-tenant 지원
- mTLS (Istio) 도입

### 10.5 의존성 / 외부 입력

- ERP 시스템 사양 (REST API 가용 여부) — Sprint 1 확인 필요
- IoT Edge Gateway HW 결정 — Sprint 4까지
- LLM 운영 비용 한도 (월 USD) — Sprint 6 전 합의
- 운영 인프라 클라우드 (AWS/온프레미스) — Sprint 7 전 결정

---

## Version History

| Version | Date | Changes | Author |
|---|---|---|---|
| 1.0 | 2026-04-30 | 초기 통합 설계 문서 (Section 1~10) | Enterprise Architect |
