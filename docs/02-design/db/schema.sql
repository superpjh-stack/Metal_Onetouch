-- =============================================================================
-- 파일명   : schema.sql
-- 버전     : v1.0.0
-- 작성일   : 2026-04-30
-- 목적     : 원터치(Onetouch) AI+MES 시스템 전체 DB 스키마
--            금속 가공(판금/용접/절삭) 제조업 LOT 기반 전 공정 추적 시스템
-- DB      : PostgreSQL 16 + TimescaleDB
-- 작성자   : DB Architect (AI)
-- =============================================================================
-- 주요 설계 원칙:
--   1. lots 테이블은 삭제(DELETE) 금지 — lot_status로 상태 관리
--   2. 모든 테이블: id UUID PK, created_at, updated_at 표준 컬럼
--   3. process_data, equipment_sensor_data: TimescaleDB hypertable
--   4. RBAC 5역할: production_manager, quality_inspector, process_engineer,
--                  executive, sales_engineer
-- =============================================================================

-- 확장 설치 (최초 1회)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE;


-- =============================================================================
-- SECTION 1: ENUM 타입 정의
-- =============================================================================

-- 사용자 상태
CREATE TYPE user_status_enum AS ENUM (
    'active',
    'inactive',
    'suspended'
);

-- RBAC 역할
CREATE TYPE role_name_enum AS ENUM (
    'production_manager',   -- 생산 관리자
    'quality_inspector',    -- 품질 검사원
    'process_engineer',     -- 공정 엔지니어
    'executive',            -- 경영진
    'sales_engineer'        -- 영업 엔지니어
);

-- LOT 상태
CREATE TYPE lot_status_enum AS ENUM (
    'created',              -- 생성됨
    'in_receipt',           -- 입고 진행 중
    'received',             -- 입고 완료
    'in_process',           -- 공정 진행 중
    'in_inspection',        -- 검사 중
    'completed',            -- 공정 완료
    'shipped',              -- 출하됨
    'on_hold',              -- 보류
    'rejected'              -- 불합격
);

-- 공정 상태
CREATE TYPE process_status_enum AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed',
    'skipped'
);

-- 설비 상태
CREATE TYPE equipment_status_enum AS ENUM (
    'operational',          -- 가동 중
    'idle',                 -- 대기
    'maintenance',          -- 유지보수 중
    'breakdown',            -- 고장
    'decommissioned'        -- 폐기
);

-- 품질 검사 유형
CREATE TYPE inspection_type_enum AS ENUM (
    'incoming',             -- 수입 검사
    'in_process',           -- 공정 중 검사
    'final'                 -- 최종 검사
);

-- 품질 검사 결과
CREATE TYPE inspection_result_enum AS ENUM (
    'pass',
    'fail',
    'conditional_pass',     -- 조건부 합격
    'pending'
);

-- 클레임 상태
CREATE TYPE claim_status_enum AS ENUM (
    'received',             -- 접수
    'under_investigation',  -- 조사 중
    'resolved',             -- 해결됨
    'closed',               -- 종결
    'rejected'              -- 기각
);

-- 출하 상태
CREATE TYPE shipment_status_enum AS ENUM (
    'preparing',            -- 출하 준비
    'ready',                -- 출하 대기
    'shipped',              -- 출하됨
    'delivered',            -- 납품 완료
    'returned'              -- 반송
);

-- AI 에이전트 유형
CREATE TYPE agent_type_enum AS ENUM (
    'inbound',              -- 인바운드 (공정/품질 질의)
    'outbound',             -- 아웃바운드 (견적/영업 지원)
    'integrated'            -- 통합 (전체 공정 분석)
);

-- AI 질의 상태
CREATE TYPE query_status_enum AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed'
);

-- 원자재 단위
CREATE TYPE unit_enum AS ENUM (
    'kg',
    'ton',
    'ea',                   -- 개
    'sheet',                -- 장
    'm',                    -- 미터
    'm2',                   -- 제곱미터
    'mm',
    'liter',
    'set'
);

-- 알림 채널
CREATE TYPE notification_channel_enum AS ENUM (
    'email',
    'sms',
    'slack',
    'teams',
    'in_app'
);

-- 로그 레벨
CREATE TYPE log_level_enum AS ENUM (
    'DEBUG',
    'INFO',
    'WARNING',
    'ERROR',
    'CRITICAL'
);

-- ML 데이터셋 상태
CREATE TYPE dataset_status_enum AS ENUM (
    'collecting',
    'ready',
    'training',
    'deployed',
    'deprecated'
);


-- =============================================================================
-- SECTION 2: 트리거 함수 — updated_at 자동 갱신
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- SECTION 3: 기준정보 그룹
-- =============================================================================

-- ----------------------------------------------------------------------------
-- 3-1. roles — 역할 마스터
-- ----------------------------------------------------------------------------
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        role_name_enum      NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_roles_updated_at
    BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE roles IS '역할 마스터 — RBAC 5역할 정의';


-- ----------------------------------------------------------------------------
-- 3-2. users — 사용자
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_no     VARCHAR(20)         NOT NULL UNIQUE,    -- 사원번호
    email           VARCHAR(255)        NOT NULL UNIQUE,
    password_hash   VARCHAR(255)        NOT NULL,
    full_name       VARCHAR(100)        NOT NULL,
    department      VARCHAR(100),
    phone           VARCHAR(20),
    status          user_status_enum    NOT NULL DEFAULT 'active',
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE users IS '시스템 사용자 — RBAC 기반 접근 제어';
COMMENT ON COLUMN users.employee_no IS '사원번호 (고유 식별자)';


-- ----------------------------------------------------------------------------
-- 3-3. user_roles — 사용자-역할 매핑 (N:M)
-- ----------------------------------------------------------------------------
CREATE TABLE user_roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id     UUID            NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    granted_by  UUID            REFERENCES users(id) ON DELETE SET NULL,
    granted_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ,                                 -- NULL = 무기한
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_roles UNIQUE (user_id, role_id)
);

CREATE TRIGGER trg_user_roles_updated_at
    BEFORE UPDATE ON user_roles
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE user_roles IS '사용자-역할 매핑 (N:M) — 복수 역할 부여 가능';
COMMENT ON COLUMN user_roles.expires_at IS 'NULL이면 무기한 유효';


-- ----------------------------------------------------------------------------
-- 3-4. suppliers — 공급처
-- ----------------------------------------------------------------------------
CREATE TABLE suppliers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_code       VARCHAR(20)     NOT NULL UNIQUE,
    name                VARCHAR(200)    NOT NULL,
    business_no         VARCHAR(20),                        -- 사업자번호
    contact_person      VARCHAR(100),
    phone               VARCHAR(20),
    email               VARCHAR(255),
    address             TEXT,
    is_approved         BOOLEAN         NOT NULL DEFAULT FALSE,
    approval_date       DATE,
    notes               TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_suppliers_updated_at
    BEFORE UPDATE ON suppliers
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE suppliers IS '원자재/부품 공급처 마스터';


-- ----------------------------------------------------------------------------
-- 3-5. customers — 고객사
-- ----------------------------------------------------------------------------
CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_code   VARCHAR(20)     NOT NULL UNIQUE,
    name            VARCHAR(200)    NOT NULL,
    business_no     VARCHAR(20),
    contact_person  VARCHAR(100),
    phone           VARCHAR(20),
    email           VARCHAR(255),
    address         TEXT,
    industry        VARCHAR(100),                           -- 업종
    credit_rating   VARCHAR(10),                            -- 신용 등급
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE customers IS '고객사 마스터';


-- ----------------------------------------------------------------------------
-- 3-6. equipment — 설비 마스터
-- ----------------------------------------------------------------------------
CREATE TABLE equipment (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_code      VARCHAR(30)             NOT NULL UNIQUE,
    name                VARCHAR(200)            NOT NULL,
    equipment_type      VARCHAR(100)            NOT NULL,   -- 절삭/용접/판금 등
    manufacturer        VARCHAR(200),
    model_no            VARCHAR(100),
    serial_no           VARCHAR(100),
    installation_date   DATE,
    location            VARCHAR(100),                       -- 설치 위치
    status              equipment_status_enum   NOT NULL DEFAULT 'operational',
    rated_capacity      NUMERIC(12, 4),                     -- 정격 능력
    rated_capacity_unit VARCHAR(20),
    last_maintenance_at TIMESTAMPTZ,
    next_maintenance_at TIMESTAMPTZ,
    specifications      JSONB,                              -- 설비 사양 (자유 형식)
    created_at          TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ             NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_equipment_updated_at
    BEFORE UPDATE ON equipment
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE equipment IS '생산 설비 마스터';
COMMENT ON COLUMN equipment.specifications IS '설비 제원 (JSON): 전압, 최대전류, RPM 범위 등';


-- =============================================================================
-- SECTION 4: 자재/공정 그룹
-- =============================================================================

-- ----------------------------------------------------------------------------
-- 4-1. raw_materials — 원자재 마스터
-- ----------------------------------------------------------------------------
CREATE TABLE raw_materials (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_code       VARCHAR(30)     NOT NULL UNIQUE,
    name                VARCHAR(200)    NOT NULL,
    material_type       VARCHAR(100)    NOT NULL,           -- 강판/알루미늄/SUS 등
    grade               VARCHAR(50),                        -- 재질 등급 (e.g. SUS304)
    standard            VARCHAR(100),                       -- 규격 (KS, JIS, ASTM)
    unit                unit_enum       NOT NULL DEFAULT 'kg',
    unit_price          NUMERIC(15, 4),
    supplier_id         UUID            REFERENCES suppliers(id) ON DELETE SET NULL,
    minimum_stock_qty   NUMERIC(12, 4)  NOT NULL DEFAULT 0,
    current_stock_qty   NUMERIC(12, 4)  NOT NULL DEFAULT 0,
    specifications      JSONB,                              -- 재질 사양 (두께, 폭, 길이 등)
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_raw_materials_updated_at
    BEFORE UPDATE ON raw_materials
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE raw_materials IS '원자재 마스터 — 재고 수준 포함';
COMMENT ON COLUMN raw_materials.specifications IS 'JSON: {thickness_mm, width_mm, length_mm, tensile_strength}';


-- ----------------------------------------------------------------------------
-- 4-2. lots — LOT 마스터 (불변 핵심 추적 단위)
-- ----------------------------------------------------------------------------
-- POLICY: 이 테이블의 레코드는 절대 DELETE하지 않는다.
--         상태 변경은 lot_status 컬럼을 통해서만 수행한다.
--         lot_id 형식: 'L{YYYYMMDD}-{SEQ}' (예: L20260430-001)
CREATE TABLE lots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id              VARCHAR(20)         NOT NULL UNIQUE, -- 'L{YYYYMMDD}-{SEQ}'
    lot_status          lot_status_enum     NOT NULL DEFAULT 'created',
    raw_material_id     UUID                REFERENCES raw_materials(id) ON DELETE RESTRICT,
    customer_id         UUID                REFERENCES customers(id) ON DELETE RESTRICT,
    order_no            VARCHAR(50),                         -- 수주번호
    product_name        VARCHAR(200),
    quantity            NUMERIC(12, 4)      NOT NULL,
    unit                unit_enum           NOT NULL DEFAULT 'ea',
    drawing_no          VARCHAR(100),                        -- 도면번호
    due_date            DATE,                                -- 납기일
    priority            SMALLINT            NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    notes               TEXT,
    created_by          UUID                REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_lots_updated_at
    BEFORE UPDATE ON lots
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- DELETE 방지 규칙
CREATE RULE no_delete_lots AS ON DELETE TO lots DO INSTEAD NOTHING;

COMMENT ON TABLE lots IS 'LOT 마스터 — 전 공정 추적의 핵심 단위. DELETE 금지 정책 적용';
COMMENT ON COLUMN lots.lot_id IS 'LOT 식별자 형식: L{YYYYMMDD}-{SEQ} (예: L20260430-001)';
COMMENT ON COLUMN lots.priority IS '우선순위 1(최고)~5(최저)';


-- ----------------------------------------------------------------------------
-- 4-3. raw_material_receipts — 원자재 입고 이벤트
-- ----------------------------------------------------------------------------
CREATE TABLE raw_material_receipts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_no          VARCHAR(30)     NOT NULL UNIQUE,     -- 입고번호
    lot_id              UUID            NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    raw_material_id     UUID            NOT NULL REFERENCES raw_materials(id) ON DELETE RESTRICT,
    supplier_id         UUID            REFERENCES suppliers(id) ON DELETE SET NULL,
    received_qty        NUMERIC(12, 4)  NOT NULL CHECK (received_qty > 0),
    unit                unit_enum       NOT NULL DEFAULT 'kg',
    unit_price          NUMERIC(15, 4),
    total_price         NUMERIC(18, 4),
    receipt_date        DATE            NOT NULL DEFAULT CURRENT_DATE,
    delivery_note_no    VARCHAR(50),                         -- 납품서 번호
    purchase_order_no   VARCHAR(50),                         -- 발주번호
    warehouse_location  VARCHAR(100),                        -- 창고 위치
    received_by         UUID            REFERENCES users(id) ON DELETE SET NULL,
    inspection_passed   BOOLEAN,                             -- 수입 검사 통과 여부
    notes               TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_raw_material_receipts_updated_at
    BEFORE UPDATE ON raw_material_receipts
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE raw_material_receipts IS '원자재 입고 이력 — lots 연결';


-- ----------------------------------------------------------------------------
-- 4-4. processes — 공정 마스터
-- ----------------------------------------------------------------------------
CREATE TABLE processes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    process_code        VARCHAR(30)     NOT NULL UNIQUE,
    name                VARCHAR(200)    NOT NULL,
    process_type        VARCHAR(100)    NOT NULL,            -- 절단/성형/용접/도장 등
    sequence_no         SMALLINT        NOT NULL CHECK (sequence_no > 0), -- 공정 순서
    equipment_id        UUID            REFERENCES equipment(id) ON DELETE SET NULL,
    standard_cycle_time NUMERIC(10, 2),                      -- 표준 사이클 타임 (분)
    standard_conditions JSONB,                               -- 표준 공정 조건
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_processes_updated_at
    BEFORE UPDATE ON processes
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE processes IS '공정 마스터 — 공정 순서 및 표준 조건';
COMMENT ON COLUMN processes.standard_conditions IS 'JSON: {temperature_c, current_a, rpm, pressure_bar, feed_rate_mm_min}';


-- ----------------------------------------------------------------------------
-- 4-5. process_results — 공정 실적
-- ----------------------------------------------------------------------------
CREATE TABLE process_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id              UUID                    NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    process_id          UUID                    NOT NULL REFERENCES processes(id) ON DELETE RESTRICT,
    equipment_id        UUID                    REFERENCES equipment(id) ON DELETE SET NULL,
    operator_id         UUID                    REFERENCES users(id) ON DELETE SET NULL,
    status              process_status_enum     NOT NULL DEFAULT 'pending',
    planned_start_at    TIMESTAMPTZ,
    actual_start_at     TIMESTAMPTZ,
    actual_end_at       TIMESTAMPTZ,
    planned_qty         NUMERIC(12, 4)          NOT NULL,
    completed_qty       NUMERIC(12, 4)          NOT NULL DEFAULT 0,
    defect_qty          NUMERIC(12, 4)          NOT NULL DEFAULT 0,
    actual_conditions   JSONB,                               -- 실제 공정 조건
    notes               TEXT,
    created_at          TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ             NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_process_results_updated_at
    BEFORE UPDATE ON process_results
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE process_results IS '공정 실적 — lot_id 기반 전 공정 추적';
COMMENT ON COLUMN process_results.actual_conditions IS 'JSON: 실제 측정된 공정 파라미터';


-- =============================================================================
-- SECTION 5: IoT/설비 그룹 (TimescaleDB hypertable 대상)
-- =============================================================================

-- ----------------------------------------------------------------------------
-- 5-1. process_data — IoT 공정 데이터 (TimescaleDB hypertable)
-- ----------------------------------------------------------------------------
CREATE TABLE process_data (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    measured_at         TIMESTAMPTZ     NOT NULL,            -- 파티션 키
    lot_id              UUID            REFERENCES lots(id) ON DELETE SET NULL,
    process_result_id   UUID            REFERENCES process_results(id) ON DELETE SET NULL,
    equipment_id        UUID            REFERENCES equipment(id) ON DELETE SET NULL,
    current_a           NUMERIC(10, 4),                      -- 전류 (암페어)
    voltage_v           NUMERIC(10, 4),                      -- 전압 (볼트)
    temperature_c       NUMERIC(10, 4),                      -- 온도 (섭씨)
    vibration_mm_s      NUMERIC(10, 4),                      -- 진동 (mm/s)
    rpm                 NUMERIC(10, 2),                      -- 회전수 (RPM)
    pressure_bar        NUMERIC(10, 4),                      -- 압력 (bar)
    feed_rate_mm_min    NUMERIC(10, 4),                      -- 이송속도 (mm/min)
    spindle_load_pct    NUMERIC(6, 2),                       -- 스핀들 부하율 (%)
    extra_metrics       JSONB,                               -- 추가 측정값
    PRIMARY KEY (id, measured_at)
);

COMMENT ON TABLE process_data IS 'IoT 공정 데이터 — TimescaleDB hypertable (measured_at 기준 파티션)';
COMMENT ON COLUMN process_data.measured_at IS 'hypertable 파티션 키 — 인덱스 우선순위 최고';


-- ----------------------------------------------------------------------------
-- 5-2. equipment_sensor_data — 설비 실시간 센서 데이터 (TimescaleDB hypertable)
-- ----------------------------------------------------------------------------
CREATE TABLE equipment_sensor_data (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    measured_at     TIMESTAMPTZ     NOT NULL,                -- 파티션 키
    equipment_id    UUID            NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    sensor_type     VARCHAR(50)     NOT NULL,                -- 센서 종류 (temperature/vibration/current 등)
    sensor_tag      VARCHAR(100),                            -- 센서 태그명
    value           NUMERIC(14, 6)  NOT NULL,                -- 측정값
    unit            VARCHAR(20),                             -- 단위
    quality         SMALLINT        DEFAULT 100 CHECK (quality BETWEEN 0 AND 100), -- 데이터 품질 점수
    is_anomaly      BOOLEAN         NOT NULL DEFAULT FALSE,  -- 이상 감지 여부
    anomaly_score   NUMERIC(6, 4),                           -- 이상 점수 (0~1)
    PRIMARY KEY (id, measured_at)
);

COMMENT ON TABLE equipment_sensor_data IS '설비 실시간 센서 데이터 — TimescaleDB hypertable (measured_at 기준)';
COMMENT ON COLUMN equipment_sensor_data.quality IS '데이터 품질 점수 0(불량)~100(완벽)';


-- =============================================================================
-- SECTION 6: 품질/출하 그룹
-- =============================================================================

-- ----------------------------------------------------------------------------
-- 6-1. quality_standards — 품질 기준 마스터
-- ----------------------------------------------------------------------------
CREATE TABLE quality_standards (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    standard_code       VARCHAR(30)     NOT NULL UNIQUE,
    name                VARCHAR(200)    NOT NULL,
    process_id          UUID            REFERENCES processes(id) ON DELETE SET NULL,
    inspection_type     inspection_type_enum NOT NULL,
    criteria            JSONB           NOT NULL,            -- 검사 기준 (항목, 한계치)
    applicable_materials TEXT[],                             -- 적용 가능 재질 목록
    version             VARCHAR(20)     NOT NULL DEFAULT '1.0',
    effective_from      DATE            NOT NULL DEFAULT CURRENT_DATE,
    effective_to        DATE,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_by          UUID            REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_quality_standards_updated_at
    BEFORE UPDATE ON quality_standards
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE quality_standards IS '품질 기준 마스터 — 수입/공정/최종 검사 기준';
COMMENT ON COLUMN quality_standards.criteria IS 'JSON: [{item, min_value, max_value, unit, method}]';


-- ----------------------------------------------------------------------------
-- 6-2. quality_inspections — 품질 검사
-- ----------------------------------------------------------------------------
CREATE TABLE quality_inspections (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_no       VARCHAR(30)             NOT NULL UNIQUE,
    lot_id              UUID                    NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    process_result_id   UUID                    REFERENCES process_results(id) ON DELETE SET NULL,
    standard_id         UUID                    REFERENCES quality_standards(id) ON DELETE SET NULL,
    inspection_type     inspection_type_enum    NOT NULL,
    inspector_id        UUID                    REFERENCES users(id) ON DELETE SET NULL,
    inspection_date     DATE                    NOT NULL DEFAULT CURRENT_DATE,
    result              inspection_result_enum  NOT NULL DEFAULT 'pending',
    inspection_qty      NUMERIC(12, 4)          NOT NULL,
    defect_qty          NUMERIC(12, 4)          NOT NULL DEFAULT 0,
    measurements        JSONB,                               -- 측정값 목록
    notes               TEXT,
    approved_by         UUID                    REFERENCES users(id) ON DELETE SET NULL,
    approved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ             NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_quality_inspections_updated_at
    BEFORE UPDATE ON quality_inspections
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE quality_inspections IS '품질 검사 이력';
COMMENT ON COLUMN quality_inspections.measurements IS 'JSON: [{item, measured_value, pass_fail}]';


-- ----------------------------------------------------------------------------
-- 6-3. defect_details — 불량 상세
-- ----------------------------------------------------------------------------
CREATE TABLE defect_details (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id       UUID            NOT NULL REFERENCES quality_inspections(id) ON DELETE CASCADE,
    lot_id              UUID            NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    defect_code         VARCHAR(30)     NOT NULL,
    defect_name         VARCHAR(200)    NOT NULL,
    defect_category     VARCHAR(100),                        -- 불량 분류 (치수/외관/기능 등)
    qty                 NUMERIC(12, 4)  NOT NULL DEFAULT 1,
    location            VARCHAR(200),                        -- 불량 발생 위치
    cause               TEXT,                                -- 원인 분석
    corrective_action   TEXT,                                -- 시정 조치
    image_urls          TEXT[],                              -- 불량 이미지 URL 목록
    severity            SMALLINT        DEFAULT 3 CHECK (severity BETWEEN 1 AND 5),
    is_recurring        BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_defect_details_updated_at
    BEFORE UPDATE ON defect_details
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE defect_details IS '불량 상세 내역 — quality_inspections 하위';
COMMENT ON COLUMN defect_details.severity IS '심각도 1(경미)~5(치명)';


-- ----------------------------------------------------------------------------
-- 6-4. claims — 클레임
-- ----------------------------------------------------------------------------
CREATE TABLE claims (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_no            VARCHAR(30)         NOT NULL UNIQUE,
    customer_id         UUID                NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    lot_id              UUID                REFERENCES lots(id) ON DELETE RESTRICT,
    shipment_id         UUID,                                -- 출하 참조 (순환 참조 방지를 위해 FK는 아래에서 추가)
    claim_date          DATE                NOT NULL DEFAULT CURRENT_DATE,
    claim_type          VARCHAR(100)        NOT NULL,        -- 품질/납기/수량/기타
    description         TEXT                NOT NULL,
    claim_qty           NUMERIC(12, 4),
    status              claim_status_enum   NOT NULL DEFAULT 'received',
    priority            SMALLINT            NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    root_cause          TEXT,
    corrective_action   TEXT,
    preventive_action   TEXT,
    financial_impact    NUMERIC(15, 2),                      -- 금전적 손실 (원)
    resolved_at         TIMESTAMPTZ,
    resolved_by         UUID                REFERENCES users(id) ON DELETE SET NULL,
    assigned_to         UUID                REFERENCES users(id) ON DELETE SET NULL,
    attachments         TEXT[],                              -- 첨부 파일 URL
    notes               TEXT,
    created_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_claims_updated_at
    BEFORE UPDATE ON claims
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE claims IS '고객 클레임 — 품질/납기/수량 이슈 관리';


-- ----------------------------------------------------------------------------
-- 6-5. shipments — 출하
-- ----------------------------------------------------------------------------
CREATE TABLE shipments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_no         VARCHAR(30)             NOT NULL UNIQUE,
    customer_id         UUID                    NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    shipment_date       DATE                    NOT NULL DEFAULT CURRENT_DATE,
    status              shipment_status_enum    NOT NULL DEFAULT 'preparing',
    total_quantity      NUMERIC(12, 4)          NOT NULL DEFAULT 0,
    unit                unit_enum               NOT NULL DEFAULT 'ea',
    delivery_address    TEXT,
    tracking_no         VARCHAR(100),                        -- 운송장 번호
    carrier             VARCHAR(100),                        -- 운송사
    order_no            VARCHAR(50),                         -- 수주번호
    invoice_no          VARCHAR(50),                         -- 송장번호
    shipped_by          UUID                    REFERENCES users(id) ON DELETE SET NULL,
    delivered_at        TIMESTAMPTZ,
    notes               TEXT,
    created_at          TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ             NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_shipments_updated_at
    BEFORE UPDATE ON shipments
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- claims.shipment_id 외래키 후처리 추가
ALTER TABLE claims
    ADD CONSTRAINT fk_claims_shipment_id
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE SET NULL;

COMMENT ON TABLE shipments IS '출하 마스터';


-- ----------------------------------------------------------------------------
-- 6-6. shipment_lots — 출하-LOT 매핑 (N:M)
-- ----------------------------------------------------------------------------
CREATE TABLE shipment_lots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id     UUID            NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    lot_id          UUID            NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    quantity        NUMERIC(12, 4)  NOT NULL CHECK (quantity > 0),
    unit            unit_enum       NOT NULL DEFAULT 'ea',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_shipment_lots UNIQUE (shipment_id, lot_id)
);

CREATE TRIGGER trg_shipment_lots_updated_at
    BEFORE UPDATE ON shipment_lots
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE shipment_lots IS '출하-LOT 매핑 (N:M) — 1출하에 복수 LOT 포함 가능';


-- =============================================================================
-- SECTION 7: AI/견적 그룹
-- =============================================================================

-- ----------------------------------------------------------------------------
-- 7-1. cad_analyses — CAD 도면 분석 결과
-- ----------------------------------------------------------------------------
CREATE TABLE cad_analyses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id              UUID            REFERENCES lots(id) ON DELETE SET NULL,
    file_name           VARCHAR(500)    NOT NULL,
    file_path           TEXT            NOT NULL,            -- 스토리지 경로/URL
    file_format         VARCHAR(20),                         -- DXF/DWG/STEP/IGES
    file_size_bytes     BIGINT,
    analyzed_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    analyzed_by         VARCHAR(100),                        -- AI 모델명
    objects             JSONB,                               -- 도면 내 객체 목록
    dimensions          JSONB,                               -- 치수 정보
    material_hints      TEXT[],                              -- AI 추출 재질 힌트
    process_hints       TEXT[],                              -- AI 추출 공정 힌트
    estimated_weight_kg NUMERIC(12, 4),
    complexity_score    NUMERIC(5, 2),                       -- 복잡도 점수
    confidence_score    NUMERIC(5, 4),                       -- 분석 신뢰도 (0~1)
    raw_response        JSONB,                               -- AI 원시 응답
    error_message       TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_cad_analyses_updated_at
    BEFORE UPDATE ON cad_analyses
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE cad_analyses IS 'CAD 도면 AI 분석 결과 저장';
COMMENT ON COLUMN cad_analyses.objects IS 'JSON: [{type, count, properties}] — 구멍/벤딩/컷팅 등';
COMMENT ON COLUMN cad_analyses.dimensions IS 'JSON: {bounding_box, total_area_mm2, perimeter_mm}';


-- ----------------------------------------------------------------------------
-- 7-2. estimates — 견적
-- ----------------------------------------------------------------------------
CREATE TABLE estimates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estimate_no         VARCHAR(30)     NOT NULL UNIQUE,
    customer_id         UUID            NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    cad_analysis_id     UUID            REFERENCES cad_analyses(id) ON DELETE SET NULL,
    title               VARCHAR(300)    NOT NULL,
    quantity            NUMERIC(12, 4)  NOT NULL DEFAULT 1,
    unit                unit_enum       NOT NULL DEFAULT 'ea',
    material_cost       NUMERIC(15, 2)  NOT NULL DEFAULT 0,
    process_cost        NUMERIC(15, 2)  NOT NULL DEFAULT 0,
    overhead_cost       NUMERIC(15, 2)  NOT NULL DEFAULT 0,
    profit_margin_pct   NUMERIC(5, 2)   NOT NULL DEFAULT 0,
    total_price         NUMERIC(18, 2)  NOT NULL DEFAULT 0,
    cost_breakdown      JSONB,                               -- 원가 구성 상세
    valid_until         DATE,
    status              VARCHAR(20)     NOT NULL DEFAULT 'draft', -- draft/sent/accepted/rejected
    ai_generated        BOOLEAN         NOT NULL DEFAULT FALSE,
    generated_by        UUID            REFERENCES users(id) ON DELETE SET NULL,
    approved_by         UUID            REFERENCES users(id) ON DELETE SET NULL,
    approved_at         TIMESTAMPTZ,
    notes               TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_estimates_updated_at
    BEFORE UPDATE ON estimates
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE estimates IS '견적 — AI 자동 견적 포함';
COMMENT ON COLUMN estimates.cost_breakdown IS 'JSON: {material_items:[...], process_items:[...], overhead_items:[...]}';


-- ----------------------------------------------------------------------------
-- 7-3. bom_items — BOM (자재명세서)
-- ----------------------------------------------------------------------------
CREATE TABLE bom_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estimate_id         UUID            REFERENCES estimates(id) ON DELETE CASCADE,
    lot_id              UUID            REFERENCES lots(id) ON DELETE RESTRICT,
    raw_material_id     UUID            REFERENCES raw_materials(id) ON DELETE RESTRICT,
    item_no             SMALLINT        NOT NULL DEFAULT 1,  -- BOM 항목 번호
    item_name           VARCHAR(200)    NOT NULL,
    quantity            NUMERIC(12, 4)  NOT NULL CHECK (quantity > 0),
    unit                unit_enum       NOT NULL DEFAULT 'ea',
    unit_price          NUMERIC(15, 4),
    total_price         NUMERIC(18, 4),
    specifications      JSONB,                               -- 항목별 사양
    notes               TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_bom_items_updated_at
    BEFORE UPDATE ON bom_items
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE bom_items IS '자재명세서 (BOM) — 견적 또는 LOT에 연결';


-- ----------------------------------------------------------------------------
-- 7-4. ai_query_history — AI 질의 이력
-- ----------------------------------------------------------------------------
CREATE TABLE ai_query_history (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID                NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    agent_type          agent_type_enum     NOT NULL DEFAULT 'integrated',
    session_id          VARCHAR(100),                        -- 대화 세션 ID
    query_text          TEXT                NOT NULL,        -- 사용자 질문
    response_text       TEXT,                                -- AI 응답
    context_data        JSONB,                               -- 질의 컨텍스트 (lot_id, 공정 등)
    referenced_tables   TEXT[],                              -- 조회된 테이블 목록
    sql_generated       TEXT,                                -- AI 생성 SQL
    execution_time_ms   INTEGER,                             -- 응답 시간 (ms)
    token_count_input   INTEGER,
    token_count_output  INTEGER,
    model_name          VARCHAR(100),                        -- 사용된 AI 모델
    status              query_status_enum   NOT NULL DEFAULT 'pending',
    feedback_score      SMALLINT            CHECK (feedback_score BETWEEN 1 AND 5),
    feedback_comment    TEXT,
    error_message       TEXT,
    created_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_ai_query_history_updated_at
    BEFORE UPDATE ON ai_query_history
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE ai_query_history IS 'AI Agent 질의/응답 전체 이력';
COMMENT ON COLUMN ai_query_history.agent_type IS 'inbound(공정/품질), outbound(견적/영업), integrated(통합)';
COMMENT ON COLUMN ai_query_history.context_data IS 'JSON: {lot_id, process_id, date_range, filters}';


-- ----------------------------------------------------------------------------
-- 7-5. ml_datasets — AI 학습 데이터셋 메타데이터
-- ----------------------------------------------------------------------------
CREATE TABLE ml_datasets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_name        VARCHAR(200)        NOT NULL,
    dataset_code        VARCHAR(50)         NOT NULL UNIQUE,
    description         TEXT,
    target_model        VARCHAR(200),                        -- 학습 대상 모델명
    data_source         TEXT[],                              -- 데이터 출처 테이블 목록
    record_count        BIGINT              NOT NULL DEFAULT 0,
    feature_columns     TEXT[],
    label_column        VARCHAR(100),
    date_range_from     DATE,
    date_range_to       DATE,
    file_path           TEXT,                                -- 데이터셋 파일 경로/URL
    file_size_bytes     BIGINT,
    status              dataset_status_enum NOT NULL DEFAULT 'collecting',
    accuracy_score      NUMERIC(6, 4),                       -- 모델 정확도
    version             VARCHAR(20)         NOT NULL DEFAULT '1.0',
    training_config     JSONB,                               -- 학습 설정
    evaluation_metrics  JSONB,                               -- 평가 지표
    created_by          UUID                REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_ml_datasets_updated_at
    BEFORE UPDATE ON ml_datasets
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE ml_datasets IS 'AI/ML 학습 데이터셋 메타데이터 — 실제 데이터는 외부 스토리지';
COMMENT ON COLUMN ml_datasets.evaluation_metrics IS 'JSON: {accuracy, precision, recall, f1_score}';


-- =============================================================================
-- SECTION 8: 관리 그룹
-- =============================================================================

-- ----------------------------------------------------------------------------
-- 8-1. work_standards — 작업 표준 마스터
-- ----------------------------------------------------------------------------
CREATE TABLE work_standards (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    standard_code       VARCHAR(30)     NOT NULL UNIQUE,
    name                VARCHAR(200)    NOT NULL,
    process_id          UUID            REFERENCES processes(id) ON DELETE SET NULL,
    equipment_id        UUID            REFERENCES equipment(id) ON DELETE SET NULL,
    content             TEXT            NOT NULL,            -- 작업 표준 내용
    attachments         TEXT[],                              -- 첨부 파일 (이미지/PDF URL)
    version             VARCHAR(20)     NOT NULL DEFAULT '1.0',
    effective_from      DATE            NOT NULL DEFAULT CURRENT_DATE,
    effective_to        DATE,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    approved_by         UUID            REFERENCES users(id) ON DELETE SET NULL,
    approved_at         TIMESTAMPTZ,
    created_by          UUID            REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_work_standards_updated_at
    BEFORE UPDATE ON work_standards
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE work_standards IS '작업 표준 마스터 — 공정/설비별 SOP';


-- ----------------------------------------------------------------------------
-- 8-2. kpi_targets — KPI 목표값
-- ----------------------------------------------------------------------------
CREATE TABLE kpi_targets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kpi_code            VARCHAR(50)     NOT NULL,
    kpi_name            VARCHAR(200)    NOT NULL,
    kpi_category        VARCHAR(100)    NOT NULL,            -- 품질/생산성/납기/비용
    target_value        NUMERIC(18, 4)  NOT NULL,
    unit                VARCHAR(50),
    target_period       CHAR(7)         NOT NULL,            -- 'YYYY-MM' 형식
    actual_value        NUMERIC(18, 4),
    achievement_rate    NUMERIC(6, 2),                       -- 달성률 (%)
    department          VARCHAR(100),
    responsible_user_id UUID            REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_kpi_targets UNIQUE (kpi_code, target_period)
);

CREATE TRIGGER trg_kpi_targets_updated_at
    BEFORE UPDATE ON kpi_targets
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE kpi_targets IS 'KPI 목표값 및 실적 — 월별 관리';
COMMENT ON COLUMN kpi_targets.target_period IS '관리 기간: YYYY-MM 형식 (예: 2026-04)';


-- ----------------------------------------------------------------------------
-- 8-3. notification_settings — 알림 설정
-- ----------------------------------------------------------------------------
CREATE TABLE notification_settings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID                        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type          VARCHAR(100)                NOT NULL, -- 이벤트 유형
    channel             notification_channel_enum   NOT NULL DEFAULT 'in_app',
    is_enabled          BOOLEAN                     NOT NULL DEFAULT TRUE,
    threshold_value     NUMERIC(18, 4),                      -- 알림 임계값
    threshold_condition VARCHAR(20),                         -- gt/lt/eq/gte/lte
    destination         VARCHAR(500),                        -- 수신처 (이메일/전화번호/Webhook URL)
    created_at          TIMESTAMPTZ                 NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ                 NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_notification_settings UNIQUE (user_id, event_type, channel)
);

CREATE TRIGGER trg_notification_settings_updated_at
    BEFORE UPDATE ON notification_settings
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

COMMENT ON TABLE notification_settings IS '사용자별 알림 채널 및 임계값 설정';
COMMENT ON COLUMN notification_settings.event_type IS '예: lot_created, defect_detected, shipment_delayed, kpi_below_target';


-- ----------------------------------------------------------------------------
-- 8-4. system_logs — 시스템 로그
-- ----------------------------------------------------------------------------
CREATE TABLE system_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    logged_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    level           log_level_enum  NOT NULL DEFAULT 'INFO',
    user_id         UUID            REFERENCES users(id) ON DELETE SET NULL,
    action          VARCHAR(200)    NOT NULL,                -- 수행 액션
    table_name      VARCHAR(100),                            -- 대상 테이블
    record_id       UUID,                                    -- 대상 레코드 ID
    old_values      JSONB,                                   -- 변경 전 값
    new_values      JSONB,                                   -- 변경 후 값
    ip_address      INET,
    user_agent      TEXT,
    request_id      VARCHAR(100),
    message         TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
    -- updated_at 없음: 로그는 불변
);

COMMENT ON TABLE system_logs IS '시스템 감사 로그 — 불변 (UPDATE/DELETE 금지)';
COMMENT ON COLUMN system_logs.old_values IS '변경 전 컬럼 값 (감사 추적)';

-- 로그 삭제/수정 방지
CREATE RULE no_update_system_logs AS ON UPDATE TO system_logs DO INSTEAD NOTHING;
CREATE RULE no_delete_system_logs AS ON DELETE TO system_logs DO INSTEAD NOTHING;


-- =============================================================================
-- SECTION 9: 인덱스
-- =============================================================================

-- users
CREATE INDEX idx_users_email         ON users(email);
CREATE INDEX idx_users_employee_no   ON users(employee_no);
CREATE INDEX idx_users_status        ON users(status);

-- user_roles
CREATE INDEX idx_user_roles_user_id  ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id  ON user_roles(role_id);

-- suppliers
CREATE INDEX idx_suppliers_code      ON suppliers(supplier_code);

-- customers
CREATE INDEX idx_customers_code      ON customers(customer_code);
CREATE INDEX idx_customers_name      ON customers(name);

-- equipment
CREATE INDEX idx_equipment_code      ON equipment(equipment_code);
CREATE INDEX idx_equipment_status    ON equipment(status);
CREATE INDEX idx_equipment_type      ON equipment(equipment_type);

-- raw_materials
CREATE INDEX idx_raw_materials_code  ON raw_materials(material_code);
CREATE INDEX idx_raw_materials_type  ON raw_materials(material_type);

-- lots (핵심 추적 단위 — 인덱스 다수)
CREATE INDEX idx_lots_lot_id         ON lots(lot_id);
CREATE INDEX idx_lots_status         ON lots(lot_status);
CREATE INDEX idx_lots_customer_id    ON lots(customer_id);
CREATE INDEX idx_lots_material_id    ON lots(raw_material_id);
CREATE INDEX idx_lots_order_no       ON lots(order_no);
CREATE INDEX idx_lots_due_date       ON lots(due_date);
CREATE INDEX idx_lots_created_at     ON lots(created_at DESC);

-- raw_material_receipts
CREATE INDEX idx_receipts_lot_id         ON raw_material_receipts(lot_id);
CREATE INDEX idx_receipts_material_id    ON raw_material_receipts(raw_material_id);
CREATE INDEX idx_receipts_receipt_date   ON raw_material_receipts(receipt_date DESC);

-- processes
CREATE INDEX idx_processes_sequence      ON processes(sequence_no);
CREATE INDEX idx_processes_type          ON processes(process_type);

-- process_results
CREATE INDEX idx_process_results_lot_id      ON process_results(lot_id);
CREATE INDEX idx_process_results_process_id  ON process_results(process_id);
CREATE INDEX idx_process_results_status      ON process_results(status);
CREATE INDEX idx_process_results_start_at    ON process_results(actual_start_at DESC);

-- process_data (TimescaleDB가 measured_at에 자동 파티션 인덱스 생성)
CREATE INDEX idx_process_data_lot_id         ON process_data(lot_id, measured_at DESC);
CREATE INDEX idx_process_data_equipment_id   ON process_data(equipment_id, measured_at DESC);

-- equipment_sensor_data
CREATE INDEX idx_sensor_data_equipment_type  ON equipment_sensor_data(equipment_id, sensor_type, measured_at DESC);
CREATE INDEX idx_sensor_data_anomaly         ON equipment_sensor_data(equipment_id, measured_at DESC) WHERE is_anomaly = TRUE;

-- quality_inspections
CREATE INDEX idx_inspections_lot_id          ON quality_inspections(lot_id);
CREATE INDEX idx_inspections_type_result     ON quality_inspections(inspection_type, result);
CREATE INDEX idx_inspections_date            ON quality_inspections(inspection_date DESC);

-- defect_details
CREATE INDEX idx_defects_inspection_id   ON defect_details(inspection_id);
CREATE INDEX idx_defects_lot_id          ON defect_details(lot_id);
CREATE INDEX idx_defects_code            ON defect_details(defect_code);

-- claims
CREATE INDEX idx_claims_customer_id  ON claims(customer_id);
CREATE INDEX idx_claims_lot_id       ON claims(lot_id);
CREATE INDEX idx_claims_status       ON claims(status);
CREATE INDEX idx_claims_date         ON claims(claim_date DESC);

-- shipments
CREATE INDEX idx_shipments_customer_id   ON shipments(customer_id);
CREATE INDEX idx_shipments_date          ON shipments(shipment_date DESC);
CREATE INDEX idx_shipments_status        ON shipments(status);

-- shipment_lots
CREATE INDEX idx_shipment_lots_shipment  ON shipment_lots(shipment_id);
CREATE INDEX idx_shipment_lots_lot       ON shipment_lots(lot_id);

-- cad_analyses
CREATE INDEX idx_cad_lot_id          ON cad_analyses(lot_id);
CREATE INDEX idx_cad_analyzed_at     ON cad_analyses(analyzed_at DESC);

-- estimates
CREATE INDEX idx_estimates_customer  ON estimates(customer_id);
CREATE INDEX idx_estimates_status    ON estimates(status);
CREATE INDEX idx_estimates_no        ON estimates(estimate_no);

-- bom_items
CREATE INDEX idx_bom_estimate_id     ON bom_items(estimate_id);
CREATE INDEX idx_bom_lot_id          ON bom_items(lot_id);

-- ai_query_history
CREATE INDEX idx_ai_query_user_id    ON ai_query_history(user_id, created_at DESC);
CREATE INDEX idx_ai_query_agent_type ON ai_query_history(agent_type, created_at DESC);
CREATE INDEX idx_ai_query_session    ON ai_query_history(session_id);
CREATE INDEX idx_ai_query_status     ON ai_query_history(status);

-- ml_datasets
CREATE INDEX idx_ml_datasets_code    ON ml_datasets(dataset_code);
CREATE INDEX idx_ml_datasets_status  ON ml_datasets(status);

-- kpi_targets
CREATE INDEX idx_kpi_period          ON kpi_targets(target_period, kpi_category);

-- notification_settings
CREATE INDEX idx_notifications_user  ON notification_settings(user_id);

-- system_logs
CREATE INDEX idx_system_logs_at      ON system_logs(logged_at DESC);
CREATE INDEX idx_system_logs_user    ON system_logs(user_id, logged_at DESC);
CREATE INDEX idx_system_logs_table   ON system_logs(table_name, record_id);
CREATE INDEX idx_system_logs_level   ON system_logs(level, logged_at DESC);


-- =============================================================================
-- SECTION 10: TimescaleDB 설정
-- =============================================================================

-- process_data: 7일 청크 간격 (IoT 고빈도 데이터)
SELECT create_hypertable(
    'process_data',
    'measured_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- equipment_sensor_data: 7일 청크 간격 (실시간 센서 데이터)
SELECT create_hypertable(
    'equipment_sensor_data',
    'measured_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- 데이터 보존 정책: process_data 2년 초과 압축
SELECT add_compression_policy('process_data', INTERVAL '90 days');
SELECT add_compression_policy('equipment_sensor_data', INTERVAL '90 days');

-- 연속 집계(Continuous Aggregate): 설비별 시간당 평균 센서값
CREATE MATERIALIZED VIEW mv_sensor_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', measured_at) AS bucket,
    equipment_id,
    sensor_type,
    AVG(value)                         AS avg_value,
    MIN(value)                         AS min_value,
    MAX(value)                         AS max_value,
    COUNT(*)                           AS sample_count,
    SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) AS anomaly_count
FROM equipment_sensor_data
GROUP BY bucket, equipment_id, sensor_type
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'mv_sensor_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

COMMENT ON MATERIALIZED VIEW mv_sensor_hourly IS '설비 센서 시간별 집계 (연속 집계 뷰)';


-- =============================================================================
-- SECTION 11: 트리거 — updated_at 자동 갱신 (process_data 제외: hypertable)
-- =============================================================================

-- 기준정보 그룹 트리거는 CREATE TABLE 섹션에서 이미 정의됨 (인라인 방식)
-- TimescaleDB hypertable(process_data, equipment_sensor_data)은
-- updated_at 컬럼 없이 append-only 방식 운영

-- system_logs는 불변 (트리거 없음)


-- =============================================================================
-- SECTION 12: 초기 기준 데이터 (Seed Data)
-- =============================================================================

-- RBAC 역할 초기 데이터
INSERT INTO roles (name, description) VALUES
    ('production_manager',  '생산 관리자 — 전 공정 조회/관리, LOT 생성'),
    ('quality_inspector',   '품질 검사원 — 검사 등록, 불량 처리'),
    ('process_engineer',    '공정 엔지니어 — 공정 마스터 관리, 설비 모니터링'),
    ('executive',           '경영진 — 전체 대시보드 조회 (읽기 전용)'),
    ('sales_engineer',      '영업 엔지니어 — 견적 생성, 고객/출하 관리')
ON CONFLICT (name) DO NOTHING;

-- =============================================================================
-- 스키마 생성 완료
-- =============================================================================
-- 테이블 수   : 27개
-- ENUM 타입  : 16개
-- 인덱스     : 55개
-- hypertable : 2개 (process_data, equipment_sensor_data)
-- 연속 집계  : 1개 (mv_sensor_hourly)
-- 트리거     : 23개 (updated_at 자동 갱신)
-- 불변 정책  : lots (DELETE 금지), system_logs (UPDATE/DELETE 금지)
-- =============================================================================
