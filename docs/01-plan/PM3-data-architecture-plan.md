# 데이터 아키텍처 계획 (PM3-data-architecture)

> **Summary**: 원터치 AI+MES 시스템의 핵심 데이터 모델, 통합 전략, 실시간 파이프라인, AI 학습 데이터 관리를 포괄하는 데이터 아키텍처 계획
>
> **Project**: Metal-Onetouch AI+MES
> **Author**: PM (Data Architecture)
> **Date**: 2026-04-30
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

원터치 AI+MES 시스템은 금속 가공 제조 현장에서 입고-공정-출하 전 과정을 LOT 단위로 추적하고, ERP/MES/IoT/CAD 시스템의 데이터를 단일 데이터허브로 통합하여 AI 기반 의사결정을 지원한다. 본 계획서는 이 시스템의 데이터 아키텍처 전반을 정의하며, 개발팀이 실행 가능한 구체적 기준으로 활용할 수 있도록 작성한다.

### 1.2 Background

현행 문제:
- ERP, MES, IoT 시스템이 각각 분리 운영되어 LOT 단위 추적이 불가능
- 공정 데이터와 품질 데이터의 단절로 이상 원인 추적에 수작업 의존
- CAD 도면 기반 견적 산출이 수작업으로 이루어져 시간 과다 소요
- AI 모델 학습을 위한 양질의 라벨링 데이터 부재

### 1.3 Related Documents

- 사업계획서 42-46페이지: 기능 구성도, 기능 상세 설명
- `docs/pages42-46.txt`: 사업계획서 원문

---

## 2. Scope

### 2.1 In Scope

- [ ] 핵심 데이터 엔티티 정의 및 관계 모델 (ERD 수준)
- [ ] 3가지 주요 데이터 흐름도 (생산추적 / 견적생성 / 실시간모니터링)
- [ ] ERP / MES / IoT / CAD 연동 통합 전략 (패턴 선택 기준 포함)
- [ ] IoT 실시간 스트리밍 아키텍처 및 기술 스택
- [ ] 데이터 거버넌스 원칙 (LOT 추적 보장, 정합성, 마스터데이터)
- [ ] AI 학습 데이터 파이프라인 (운영→학습 변환, 레이블링, 버전관리)
- [ ] API 설계 원칙 (RESTful 그룹, WebSocket 사용 기준)

### 2.2 Out of Scope

- 프론트엔드 UI/UX 설계
- 인프라 물리 구성 (서버 사양, 네트워크 토폴로지)
- ERP 소프트웨어 내부 커스터마이징
- ML 모델 알고리즘 상세 설계

---

## 3. 핵심 데이터 모델 (ERD 수준)

### 3.1 엔티티 목록 및 정의

#### 3.1.1 LOT (추적 기본 단위)

```
LOT
├── lot_id              PK  VARCHAR(20)  예: 'L20260430-001'
├── raw_material_id     FK  → RAW_MATERIAL
├── received_at         DATETIME
├── lot_status          ENUM  [입고대기, 공정중, 검사중, 출하대기, 출하완료, 반품]
├── quantity            DECIMAL(10,3)   단위: kg
├── created_at          DATETIME
└── updated_at          DATETIME
```

**설계 원칙**: lot_id는 시스템 전체에서 불변(immutable). 상태 변경은 LOT_HISTORY 이력으로 기록.

#### 3.1.2 RAW_MATERIAL (원자재)

```
RAW_MATERIAL
├── material_id         PK  VARCHAR(20)
├── material_name       VARCHAR(100)
├── spec_code           VARCHAR(50)    규격 코드
├── supplier_id         FK  → SUPPLIER
├── unit_weight         DECIMAL(10,3)  단위: kg
├── standard_doc_url    VARCHAR(500)   입고 기준서 파일 경로
└── created_at          DATETIME

RAW_MATERIAL_RECEIPT  (입고 이벤트)
├── receipt_id          PK
├── lot_id              FK  → LOT
├── material_id         FK  → RAW_MATERIAL
├── received_qty        DECIMAL(10,3)
├── received_date       DATE
├── inspector_id        FK  → USER
├── inspection_result   ENUM  [합격, 불합격, 조건부합격]
└── erp_sync_id         VARCHAR(50)    ERP 연동 식별자
```

#### 3.1.3 PROCESS (공정 마스터)

```
PROCESS
├── process_id          PK  VARCHAR(20)
├── process_name        VARCHAR(100)   예: 'Press_01', 'Welding_02'
├── process_type        ENUM  [프레스, 용접, 도장, 조립, 검사]
├── machine_id          FK  → EQUIPMENT
├── standard_conditions JSONB          표준 작업 조건 (속도, 압력, 온도 범위)
└── sequence_no         INTEGER        공정 순서

PROCESS_RESULT  (공정 실적)
├── result_id           PK
├── lot_id              FK  → LOT
├── process_id          FK  → PROCESS
├── worker_id           FK  → USER
├── started_at          DATETIME
├── ended_at            DATETIME
├── input_qty           DECIMAL(10,3)
├── output_qty          DECIMAL(10,3)
├── defect_qty          DECIMAL(10,3)
└── mes_sync_id         VARCHAR(50)
```

#### 3.1.4 PROCESS_DATA (IoT 공정 데이터)

```
PROCESS_DATA  (시계열, 고빈도)
├── data_id             PK  BIGSERIAL
├── lot_id              FK  → LOT
├── process_id          FK  → PROCESS
├── equipment_id        FK  → EQUIPMENT
├── measured_at         TIMESTAMPTZ    인덱스 필수
├── speed               DECIMAL(8,2)   m/min
├── pressure            DECIMAL(8,2)   bar
├── current             DECIMAL(8,2)   A
├── temperature         DECIMAL(8,2)   °C
├── rpm                 DECIMAL(8,2)
└── raw_payload         JSONB          원본 IoT 페이로드 보존
```

**저장소 선택**: TimescaleDB (PostgreSQL 확장) 또는 InfluxDB. 보존 정책: 원본 1년, 집계(1분 평균) 5년.

#### 3.1.5 EQUIPMENT (설비)

```
EQUIPMENT
├── equipment_id        PK  VARCHAR(20)
├── equipment_name      VARCHAR(100)
├── equipment_type      VARCHAR(50)
├── location            VARCHAR(100)
├── install_date        DATE
├── status              ENUM  [정상, 점검중, 고장, 대기]
└── iot_device_id       VARCHAR(50)    IoT 게이트웨이 식별자

EQUIPMENT_SENSOR_DATA  (실시간 설비 상태)
├── sensor_id           PK  BIGSERIAL
├── equipment_id        FK  → EQUIPMENT
├── measured_at         TIMESTAMPTZ
├── current             DECIMAL(8,2)   A
├── temperature         DECIMAL(8,2)   °C
├── vibration           DECIMAL(8,2)   mm/s
├── rpm                 DECIMAL(8,2)
└── anomaly_score       DECIMAL(5,4)   ML 이상 점수 (0.0~1.0)
```

#### 3.1.6 QUALITY (품질 검사)

```
QUALITY_INSPECTION
├── inspection_id       PK
├── lot_id              FK  → LOT
├── process_id          FK  → PROCESS  (null 허용 = 출하 최종검사)
├── inspection_type     ENUM  [공정검사, 최종검사, 입고검사]
├── inspector_id        FK  → USER
├── inspected_at        DATETIME
├── total_qty           INTEGER
├── defect_qty          INTEGER
├── defect_rate         DECIMAL(5,4)    계산 컬럼
├── result              ENUM  [합격, 불합격, 조건부합격]
└── notes               TEXT

DEFECT_DETAIL
├── defect_id           PK
├── inspection_id       FK  → QUALITY_INSPECTION
├── defect_type         VARCHAR(50)    예: '치수불량', '표면불량'
├── defect_count        INTEGER
└── image_url           VARCHAR(500)

CLAIM
├── claim_id            PK
├── lot_id              FK  → LOT
├── customer_id         FK  → CUSTOMER
├── claim_date          DATE
├── claim_type          VARCHAR(50)
├── root_cause_process  FK  → PROCESS  (원인 공정)
├── resolution          TEXT
└── status              ENUM  [접수, 분석중, 조치완료, 종결]
```

#### 3.1.7 ESTIMATE & BOM (견적 및 자재명세)

```
CAD_ANALYSIS
├── analysis_id         PK
├── file_name           VARCHAR(200)
├── file_url            VARCHAR(500)
├── file_type           ENUM  [PDF, DWG]
├── analyzed_at         DATETIME
├── vision_model_ver    VARCHAR(20)    사용된 AI 모델 버전
├── objects             JSONB          인식된 객체 목록
├── dimensions          JSONB          추출 치수 데이터
└── confidence_score    DECIMAL(5,4)

ESTIMATE
├── estimate_id         PK
├── customer_id         FK  → CUSTOMER
├── cad_analysis_id     FK  → CAD_ANALYSIS
├── estimate_date       DATE
├── valid_until         DATE
├── total_cost          DECIMAL(15,2)
├── cost_breakdown      JSONB          공정별 원가 상세
├── status              ENUM  [초안, 제출, 수주, 실패]
└── created_by          FK  → USER

BOM  (자재명세서)
├── bom_id              PK
├── estimate_id         FK  → ESTIMATE
├── item_seq            INTEGER
├── material_id         FK  → RAW_MATERIAL
├── process_id          FK  → PROCESS
├── quantity            DECIMAL(10,3)
├── unit                VARCHAR(20)
└── notes               TEXT
```

#### 3.1.8 SHIPMENT (출하)

```
SHIPMENT
├── shipment_id         PK
├── customer_id         FK  → CUSTOMER
├── estimate_id         FK  → ESTIMATE  (수주 연결)
├── planned_date        DATE
├── actual_date         DATE
├── status              ENUM  [출하예정, 출하완료, 지연, 취소]
└── erp_sync_id         VARCHAR(50)

SHIPMENT_LOT  (출하-LOT 매핑, N:M)
├── shipment_id         FK  → SHIPMENT
├── lot_id              FK  → LOT
├── quantity            DECIMAL(10,3)
└── inspection_id       FK  → QUALITY_INSPECTION  (출하 검사 결과)
```

#### 3.1.9 AI_QUERY_HISTORY (AI 질의 이력)

```
AI_QUERY_HISTORY
├── query_id            PK
├── user_id             FK  → USER
├── queried_at          DATETIME
├── query_text          TEXT
├── response_text       TEXT
├── context_lot_id      FK  → LOT  (질의 대상 LOT, nullable)
├── agent_type          ENUM  [입고Agent, 출하Agent, 통합AI]
├── model_version       VARCHAR(20)
└── feedback_score      SMALLINT  (1~5, nullable, 사용자 평가)
```

### 3.2 엔티티 관계 요약

```
SUPPLIER ──< RAW_MATERIAL ──< RAW_MATERIAL_RECEIPT
                                        │
                                       LOT ─────────────────────────────┐
                                        │                                │
                  ┌─────────────────────┤                                │
                  ↓                     ↓                                ↓
           PROCESS_RESULT         QUALITY_INSPECTION             SHIPMENT_LOT
                  │                     │                                │
                  ↓                     ↓                                ↓
           PROCESS_DATA           DEFECT_DETAIL                    SHIPMENT
                  │                                                      │
                  ↓                                                      ↓
            EQUIPMENT                                               CUSTOMER
                  │
                  ↓
        EQUIPMENT_SENSOR_DATA

CAD_ANALYSIS → ESTIMATE → BOM → RAW_MATERIAL
                   │
                   ↓
                SHIPMENT
```

---

## 4. 데이터 흐름도

### 4.1 흐름 1: 생산 추적 (입고→공정→출하)

```
[입고 이벤트]
  ERP 입고 데이터 수신
        │
        ▼
  LOT 자동 부여 (lot_id 생성)
  RAW_MATERIAL_RECEIPT 등록
        │
        ▼
  [공정 투입 지시]
  MES → PROCESS_RESULT 생성
  IoT 수집 시작 (PROCESS_DATA 스트리밍)
        │
        ▼
  [공정별 품질 검사]
  QUALITY_INSPECTION 등록
  불합격 시 → DEFECT_DETAIL 등록 + 알림
        │
        ▼
  [출하 전 최종 검사]
  QUALITY_INSPECTION (최종검사) 등록
  합격 LOT만 SHIPMENT_LOT 연결 허용
        │
        ▼
  [출하 완료]
  SHIPMENT 상태 → 출하완료
  ERP 재고 차감 동기화
  LOT 상태 → 출하완료
        │
        ▼
  [클레임 발생 시]
  CLAIM 등록 → lot_id 기준 공정 이력 즉시 조회
```

### 4.2 흐름 2: 견적 생성 (CAD→견적→BOM→생산지시)

```
[CAD 파일 업로드]
  PDF / DWG 수신
        │
        ▼
  [Vision AI 분석]
  CAD_ANALYSIS 생성
  객체(홀, 슬롯, 형상) + 치수 추출
  confidence_score 산출
        │
        ▼ (신뢰도 < 0.85 → 수동 검토 플래그)
  [객체 인식 결과 검증]
  작업자 검토 인터페이스
  수정 시 이력 보존 (원본 vs 수정 JSONB 보존)
        │
        ▼
  [견적 자동 산출]
  Feature × 공정별 단가 → ESTIMATE.cost_breakdown
  과거 유사 견적 비교 (ML 기반)
        │
        ▼
  [BOM 자동 생성]
  객체 구조 → BOM 항목 매핑
  RAW_MATERIAL 마스터 참조
        │
        ▼
  [수주 확정]
  ESTIMATE.status → 수주
  생산지시 → MES 연동
  SHIPMENT 예약 생성
```

### 4.3 흐름 3: 실시간 모니터링 (IoT→이상감지→알림)

```
[IoT 센서]
  장비별 전류, 온도, 진동, RPM
  수집 주기: 1~5초
        │
        ▼
  [메시지 브로커]
  MQTT → Apache Kafka
  토픽: equipment.{equipment_id}.sensor
        │
        ▼
  [스트림 처리]
  Apache Flink (또는 Kafka Streams)
  ① 시계열 저장: EQUIPMENT_SENSOR_DATA
  ② 실시간 이상 감지:
     - 임계값 기반 룰 (즉각 알림)
     - ML 이상 점수 갱신 (anomaly_score)
        │
        ▼ (이상 감지 시)
  [알림 발송]
  알림 유형:
    - Level 1 (임계값 초과): 즉시 SMS/앱 푸시
    - Level 2 (이상 패턴): 대시보드 경고
    - Level 3 (예방정비 예측): 일일 리포트
        │
        ▼
  [대시보드 갱신]
  WebSocket → 프론트엔드 실시간 업데이트
  EQUIPMENT.status 갱신
```

---

## 5. 데이터 통합 전략

### 5.1 통합 패턴 선택 기준

| 패턴 | 사용 조건 | 적용 시스템 |
|------|-----------|-------------|
| **API (REST/Webhook)** | 실시간성 요구, 트랜잭션 보장 필요, 이벤트 기반 | ERP 입고/출하, MES 공정지시 |
| **CDC (Change Data Capture)** | ERP/MES DB에 직접 접근 가능, 변경 데이터 연속 동기화 필요 | ERP 재고 잔량, MES 실적 동기화 |
| **파일 배치 (ETL)** | 레거시 시스템, 실시간성 불필요, 대용량 과거 데이터 | CAD 파일 처리, 일일 실적 보고 |
| **메시지 스트리밍** | 고빈도 데이터, 손실 허용 불가 | IoT 센서 데이터 |

### 5.2 ERP 연동 상세

**패턴: API + 배치 혼용**

```
[이벤트성 데이터] API 방향: ERP → 데이터허브
  - 입고 확정 이벤트 → RAW_MATERIAL_RECEIPT 등록 트리거
  - 출하 지시 이벤트 → SHIPMENT 생성
  - 재고 차감 이벤트 → SHIPMENT_LOT 상태 갱신

[배치 동기화] 주기: 1시간
  - 재고 잔량 스냅샷 동기화
  - 공급처 마스터 동기화 (SUPPLIER)
  - 품목 마스터 동기화 (RAW_MATERIAL)

오류 처리:
  - API 실패 시 재시도 큐 (최대 3회, 지수 백오프)
  - 배치 실패 시 알림 + 수동 재처리 인터페이스
  - erp_sync_id 기반 중복 처리 방지 (멱등성 보장)
```

### 5.3 MES 연동 상세

**패턴: CDC + API 혼용**

```
[CDC] Debezium → Kafka
  - PROCESS_RESULT 테이블 변경 감지 → 데이터허브 동기화
  - 변경 스트림: INSERT(생성), UPDATE(완료/수정)

[API] 방향: 데이터허브 → MES
  - 생산지시 (BOM 기반 작업지시서 전달)
  - 작업 조건 기준값 조회 (PROCESS.standard_conditions)

LOT 연결 보장:
  - MES 작업 시작 시 lot_id 필수 파라미터
  - MES 측 lot_id 미입력 시 공정 시작 불가 (API 레벨 검증)
```

### 5.4 IoT 연동 상세

**패턴: 메시지 스트리밍 (MQTT → Kafka)**

```
장비 → IoT 게이트웨이 → MQTT Broker → Kafka → 처리 레이어

Kafka 토픽 구조:
  raw.sensor.process      # 공정 데이터 (속도, 압력, 전류, 온도, RPM)
  raw.sensor.equipment    # 설비 상태 (전류, 온도, 진동, RPM)
  processed.anomaly       # 이상 감지 결과
  alert.equipment         # 알림 이벤트

데이터 보존:
  - Kafka: 7일 원본 보존 (재처리 가능)
  - TimescaleDB: 원본 1년, 1분 집계 5년, 1시간 집계 영구 보존
```

### 5.5 CAD 시스템 연동 상세

**패턴: 파일 배치 + 비동기 처리**

```
[업로드] 사용자 → 파일 스토리지 (S3 호환)
[트리거] 파일 업로드 이벤트 → 분석 큐 등록
[처리] Vision AI 워커 → CAD_ANALYSIS 결과 저장
[알림] 분석 완료 → WebSocket 알림 → 사용자 검토 인터페이스

파일 처리 순서:
  1. PDF → 이미지 변환 (pdf2image)
  2. DWG → DXF 변환 (ezdxf 라이브러리)
  3. Vision AI 객체 인식
  4. 치수 파싱 및 정규화
  5. CAD_ANALYSIS 저장 (원본 JSONB 포함)
```

---

## 6. 실시간 스트리밍 아키텍처

### 6.1 기술 스택 선택

| 레이어 | 선택 기술 | 선택 이유 |
|--------|-----------|-----------|
| 수집 프로토콜 | MQTT v5 | 경량, IoT 표준, QoS 레벨 지원 |
| 메시지 브로커 | Apache Kafka | 고가용성, 재처리 가능, 생태계 풍부 |
| 스트림 처리 | Apache Flink | 정확한 이벤트 타임 처리, 상태 관리 |
| 시계열 DB | TimescaleDB | PostgreSQL 호환, 집계 자동화 |
| 알림 발송 | Redis Pub/Sub → WebSocket | 저지연 브로드캐스트 |
| 대시보드 | WebSocket (Socket.IO) | 브라우저 실시간 갱신 |

### 6.2 파이프라인 상세

```
[수집 레이어]
IoT 게이트웨이 (장비당 1개)
  ├── 프로토콜 변환: OPC-UA / Modbus → MQTT
  ├── 로컬 버퍼링: 네트워크 단절 시 최대 1시간 로컬 저장
  └── 데이터 압축: Avro 스키마 직렬화

[브로커 레이어]
Apache Kafka Cluster (3 브로커 권장)
  ├── 파티션 수: equipment_id 기반 파티션
  ├── 복제 인수: 2 (데이터 유실 방지)
  └── 압축: LZ4

[처리 레이어]
Apache Flink Job 1: 저장 파이프라인
  INPUT  → Kafka raw.sensor.*
  TRANSFORM → 단위 변환, 유효성 검증, lot_id 조인
  OUTPUT → TimescaleDB PROCESS_DATA / EQUIPMENT_SENSOR_DATA

Apache Flink Job 2: 이상 감지
  INPUT  → Kafka raw.sensor.equipment
  PROCESS → 슬라이딩 윈도우 (5분), 통계 기반 이상 감지
  ML     → 사전 학습된 Isolation Forest 모델 적용
  OUTPUT → Kafka processed.anomaly + anomaly_score 갱신

Apache Flink Job 3: 알림 라우팅
  INPUT  → Kafka processed.anomaly
  RULE   → 임계값 룰 엔진 (YAML 설정 기반)
  OUTPUT → Kafka alert.equipment → Redis → WebSocket

[저장 레이어]
TimescaleDB
  ├── hypertable: PROCESS_DATA (measured_at 기준 자동 파티션)
  ├── hypertable: EQUIPMENT_SENSOR_DATA
  ├── 연속 집계: 1분 평균, 1시간 평균 자동 생성
  └── 보존 정책: 원본 365일, 1분집계 5년
```

### 6.3 이상 감지 임계값 기준 (초기값, 운영 중 튜닝)

| 파라미터 | 경고 임계값 | 위험 임계값 | 알림 레벨 |
|----------|-------------|-------------|-----------|
| 전류 | 정격 90% 초과 | 정격 110% 초과 | L2 / L1 |
| 온도 | 설정값 +20°C | 설정값 +40°C | L2 / L1 |
| 진동 | 4.5 mm/s | 7.1 mm/s (ISO 10816) | L2 / L1 |
| anomaly_score | 0.7 초과 | 0.9 초과 | L3 / L2 |

---

## 7. 데이터 거버넌스

### 7.1 LOT 추적 보장 원칙

**원칙 1: LOT 연속성 규칙**
- LOT는 생성 후 삭제 불가. 상태(lot_status)와 이력(LOT_HISTORY)으로만 관리
- 공정 분리 발생 시 (예: 절반만 불량) → 신규 LOT 파생 생성, 원본 LOT와 parent-child 관계 기록
- lot_id는 시스템 자동 부여, 수동 입력 금지

**원칙 2: 전과정 이력 의무화**
- 입고 → 공정 투입 → 공정 완료 → 품질검사 → 출하 각 단계에서 lot_id 기재 필수
- MES API에서 lot_id 누락 시 400 오류 반환 (공정 시작 차단)
- 이력 공백 발생 시 (단계 누락) 자동 알림 → 데이터 담당자 수동 보완

**원칙 3: 클레임 역추적 보장**
- 클레임 접수 시 lot_id 기반으로 5분 내 전 공정 이력 조회 가능
- 분기별 역추적 시나리오 테스트 수행 (테스트 LOT 활용)

### 7.2 데이터 정합성 검증

**검증 레이어 구조:**

```
레이어 1: 입력 검증 (API 레벨)
  - 필수 필드 존재 여부
  - 데이터 타입 및 범위 검증
  - 참조 무결성 (lot_id, process_id 존재 확인)

레이어 2: 비즈니스 규칙 검증 (서비스 레벨)
  - 출하 LOT는 최종 품질검사 합격 여부 확인
  - 공정 투입 수량 ≤ 입고 수량 검증
  - 불량률 = 불량수량 / 총수량 자동 계산 후 일치 확인

레이어 3: 배치 정합성 검사 (일일 실행)
  - LOT별 입고수량 vs 공정 투입수량 합계 비교
  - ERP 재고 vs 데이터허브 재고 대사
  - 미완료 LOT 이력 확인 (상태 = 공정중이나 7일 경과)
  결과 → 정합성 대시보드 + 이상 건 알림
```

### 7.3 마스터데이터 관리 (MDM)

| 마스터 데이터 | 원천 시스템 | 갱신 주기 | 갱신 방식 |
|---------------|-------------|-----------|-----------|
| RAW_MATERIAL (품목 코드) | ERP | 실시간 | API Webhook |
| PROCESS (공정 코드) | MES + 수동 | 변경 시 | 관리자 화면 |
| EQUIPMENT (설비 코드) | 수동 등록 | 변경 시 | 관리자 화면 |
| SUPPLIER (공급처) | ERP | 1시간 배치 | CDC |
| CUSTOMER (고객사) | ERP | 1시간 배치 | CDC |

**MDM 원칙:**
- 코드 변경 시 과거 이력 영향 없음 (코드 이력 테이블 별도 관리)
- 코드 폐기 시 soft delete (deleted_at 기록), 물리 삭제 금지
- 마스터 변경 시 관련 캐시 자동 무효화

---

## 8. AI 학습 데이터 파이프라인

### 8.1 운영 데이터 → 학습 데이터 변환

```
[운영 데이터 원천]
  PROCESS_DATA          → 이상 감지 모델 학습
  EQUIPMENT_SENSOR_DATA → 예방 정비 모델 학습
  QUALITY_INSPECTION    → 불량 예측 모델 학습
  CAD_ANALYSIS          → Vision AI 모델 재학습
  AI_QUERY_HISTORY      → AI Agent 응답 품질 향상

[변환 파이프라인]
  ① 데이터 추출: 야간 배치 (00:00~04:00)
     - 기준: 전일 신규/변경 데이터
     - 형식: Parquet 파일 (컬럼형 저장, 압축 효율)

  ② 전처리 (Feature Engineering)
     - 결측값 처리: 시계열 선형 보간 (최대 5포인트)
     - 이상치 처리: IQR 기반 클리핑 (필드별 정책 설정)
     - 정규화: Min-Max 스케일링 (스케일러 파라미터 버전 관리)
     - 윈도우 피처 생성: 이동평균(5분, 30분), 변화율

  ③ 레이블링
     이상 감지: anomaly_score > 0.9 → label=1 (자동)
     불량 예측: QUALITY_INSPECTION.result = '불합격' → label=1 (자동)
     Vision AI: 작업자 수동 검토 결과 → 능동 학습 (Active Learning)
     AI Agent: AI_QUERY_HISTORY.feedback_score 활용

  ④ 데이터셋 등록
     ML_DATASET 테이블에 메타데이터 등록
     실제 파일: S3 호환 스토리지 (/ml-datasets/{model_type}/{version}/)
```

### 8.2 ML 데이터셋 관리 스키마

```
ML_DATASET
├── dataset_id          PK
├── model_type          ENUM  [anomaly_detection, quality_prediction, vision_cad, ai_agent]
├── version             VARCHAR(20)   예: 'v2026.04.30'
├── created_at          DATETIME
├── data_from           DATE          데이터 수집 시작일
├── data_to             DATE          데이터 수집 종료일
├── total_records       INTEGER
├── positive_count      INTEGER       label=1 건수
├── negative_count      INTEGER       label=0 건수
├── file_path           VARCHAR(500)  S3 경로
├── preprocessing_config JSONB        전처리 파라미터 (재현성 보장)
├── is_active           BOOLEAN       현재 학습에 사용 중인 버전
└── notes               TEXT

ML_TRAINING_RUN  (학습 실행 이력)
├── run_id              PK
├── dataset_id          FK  → ML_DATASET
├── model_type          VARCHAR(50)
├── started_at          DATETIME
├── completed_at        DATETIME
├── metrics             JSONB         {accuracy, precision, recall, f1, auc}
├── model_artifact_path VARCHAR(500)  학습된 모델 파일 경로
└── deployed_at         DATETIME      (null = 미배포)
```

### 8.3 데이터셋 버전 관리 원칙

- 모든 데이터셋은 불변(immutable). 동일 버전 덮어쓰기 금지
- 모델 재학습 시 신규 버전 생성 후 평가 → 성능 개선 시에만 배포
- 이전 버전 데이터셋 최소 3개 버전 보존 (롤백 대비)
- 학습 재현성 보장: preprocessing_config JSONB에 모든 파라미터 기록

### 8.4 능동 학습 (Active Learning) 프로세스 - Vision AI

```
[자동화 루프]
  모델 예측 → confidence_score < 0.75 인 샘플 → 검토 큐 등록
  작업자 검토 → 수정/승인 → CAD_ANALYSIS 이력 업데이트
  주 1회 → 누적 검토 건수 ≥ 200건 → 자동 재학습 트리거
  재학습 완료 → A/B 테스트 (기존 모델 vs 신규 모델)
  → 정확도 +2% 이상 시 자동 배포
```

---

## 9. API 설계 원칙

### 9.1 RESTful 엔드포인트 그룹

#### 그룹 1: LOT 추적 API

```
GET    /api/v1/lots/{lotId}                      # LOT 상세 + 현재 상태
GET    /api/v1/lots/{lotId}/history              # 전 공정 이력 타임라인
GET    /api/v1/lots/{lotId}/process-data         # IoT 공정 데이터 (기간 파라미터)
GET    /api/v1/lots/{lotId}/quality              # 품질 검사 이력
GET    /api/v1/lots/{lotId}/traceability         # 완전 역추적 리포트
POST   /api/v1/lots                              # LOT 생성 (입고 시)
PATCH  /api/v1/lots/{lotId}/status              # 상태 변경 (이력 자동 생성)
```

#### 그룹 2: 공정 관리 API

```
GET    /api/v1/processes                         # 공정 목록
POST   /api/v1/process-results                   # 공정 실적 등록 (MES 연동)
GET    /api/v1/process-results?lotId=&processId= # 실적 조회
GET    /api/v1/process-results/{id}/process-data # 해당 실적의 IoT 데이터
```

#### 그룹 3: 품질 API

```
POST   /api/v1/quality/inspections               # 검사 결과 등록
GET    /api/v1/quality/inspections?lotId=        # LOT 검사 이력
POST   /api/v1/quality/claims                    # 클레임 접수
GET    /api/v1/quality/supplier-analysis         # 공급처별 품질 분석
```

#### 그룹 4: 견적/BOM API

```
POST   /api/v1/cad/upload                        # CAD 파일 업로드 → 비동기 분석 시작
GET    /api/v1/cad/analyses/{analysisId}         # 분석 결과 조회
PATCH  /api/v1/cad/analyses/{analysisId}/objects # 인식 결과 수정
POST   /api/v1/estimates                         # 견적 생성
GET    /api/v1/estimates/{estimateId}/bom        # BOM 조회
POST   /api/v1/estimates/{estimateId}/bom/generate # BOM 자동 생성
```

#### 그룹 5: 설비 모니터링 API

```
GET    /api/v1/equipment                         # 설비 목록 + 현재 상태
GET    /api/v1/equipment/{equipmentId}/status    # 실시간 상태 (폴링용)
GET    /api/v1/equipment/{equipmentId}/history   # 센서 이력 (기간 파라미터)
GET    /api/v1/equipment/anomalies               # 이상 감지 목록
PATCH  /api/v1/equipment/{equipmentId}/status    # 상태 수동 변경
```

#### 그룹 6: 데이터허브 API

```
GET    /api/v1/hub/search?query=&filters=        # 통합 데이터 검색
GET    /api/v1/hub/export?type=&format=xlsx      # 데이터 다운로드
POST   /api/v1/hub/ai-query                      # AI 자연어 질의
GET    /api/v1/hub/ai-query/history              # AI 질의 이력
```

### 9.2 WebSocket 사용 시점 및 채널

**WebSocket 사용 판단 기준:**
- 업데이트 주기 < 5초: WebSocket
- 업데이트 주기 ≥ 5초: HTTP 폴링 또는 Server-Sent Events
- 양방향 통신 필요: WebSocket
- 단방향 서버→클라이언트: Server-Sent Events 우선 검토

**WebSocket 채널 목록:**

```
ws://host/ws/equipment/{equipmentId}
  → 설비 실시간 센서값 (1초 주기)
  → 이상 감지 알림 즉시 수신

ws://host/ws/dashboard/production
  → 생산 현황 실시간 갱신 (5초 주기)
  → 설비 가동 상태 변경 즉시 반영

ws://host/ws/alerts
  → 전체 알림 수신 (Level 1 즉시, Level 2/3 5분 집계)

ws://host/ws/cad/analysis/{analysisId}
  → CAD 분석 진행 상태 실시간 수신
```

### 9.3 공통 API 설계 원칙

```
버전 관리: URL 버전 (/api/v1/)
인증: JWT Bearer Token + Refresh Token
페이지네이션: cursor 기반 (시계열 데이터), offset 기반 (일반 목록)
필터: query parameter (?lotId=, ?from=, ?to=, ?status=)
오류 응답 형식:
  {
    "error": {
      "code": "LOT_NOT_FOUND",
      "message": "LOT ID L20260430-001 를 찾을 수 없습니다.",
      "traceId": "abc-123"
    }
  }
Rate Limiting: 일반 API 100req/min, 데이터 다운로드 10req/min
멱등성: POST 요청에 Idempotency-Key 헤더 지원 (입고/출하 이벤트)
```

---

## 10. Success Criteria

### 10.1 Definition of Done

- [ ] 8개 핵심 엔티티 테이블 생성 및 인덱스 설계 완료
- [ ] ERP/MES/IoT 3개 연동 패턴 구현 및 동작 확인
- [ ] Kafka → Flink → TimescaleDB 스트리밍 파이프라인 동작
- [ ] LOT 역추적 API 응답 시간 5분 이내 (전 공정 이력 기준)
- [ ] ML_DATASET 버전 관리 스키마 구현
- [ ] 주요 API 엔드포인트 6개 그룹 구현

### 10.2 Quality Criteria

| 지표 | 목표값 | 측정 방법 |
|------|--------|-----------|
| IoT 데이터 수집 지연 | < 2초 (센서 → DB 저장) | Kafka Consumer Lag 모니터링 |
| LOT 역추적 조회 | < 3초 (전 이력) | API 응답 시간 측정 |
| ERP 동기화 지연 | < 5분 (배치 기준) | 배치 실행 로그 |
| 데이터 정합성 오류율 | < 0.1% | 일일 정합성 검사 결과 |
| 시스템 가용성 | 99.5% | 월간 Uptime 측정 |

---

## 11. Risks and Mitigation

| 위험 | 영향 | 발생가능성 | 대응 방안 |
|------|------|------------|-----------|
| ERP API 미제공 (레거시 시스템) | 높음 | 중간 | 파일 배치(FTP/Excel) 대안 준비, CDC 어댑터 개발 |
| IoT 게이트웨이 미표준화 | 높음 | 높음 | 프로토콜 변환 레이어 선행 개발, 주요 PLC 프로토콜 지원 목록 사전 확인 |
| TimescaleDB 데이터 폭증 | 중간 | 중간 | 보존 정책 및 연속 집계 선제적 설정, 파티션 전략 수립 |
| ML 모델 학습 데이터 불균형 | 중간 | 높음 | 초기 3개월 운영 데이터 수집 후 모델 학습 시작, SMOTE 오버샘플링 적용 |
| CAD 파일 포맷 다양성 | 중간 | 중간 | PDF 우선 지원, DWG 2단계 지원, 고객사 사전 포맷 조사 |

---

## 12. Architecture Considerations

### 12.1 Project Level

**Enterprise** 수준 선택 — 고빈도 IoT 데이터, 다중 외부 시스템 연동, AI 파이프라인을 포함하는 복잡한 아키텍처이므로 레이어 분리 엄격히 적용.

### 12.2 Key Architectural Decisions

| 결정 항목 | 선택 | 이유 |
|-----------|------|------|
| 시계열 DB | TimescaleDB | PostgreSQL 호환으로 기존 RDB 운영 역량 활용 가능 |
| 메시지 브로커 | Apache Kafka | 재처리 가능, 높은 처리량, 생태계 성숙 |
| 스트림 처리 | Apache Flink | 이벤트 타임 처리 정확성, 상태 관리 기능 |
| API 아키텍처 | REST + WebSocket | REST로 대부분 처리, 실시간 데이터만 WebSocket |
| ML 모델 서빙 | REST API (FastAPI) | Python ML 생태계 호환, 모델 교체 용이 |

---

## 13. Next Steps

1. [ ] ERP/MES 담당자와 API 인터페이스 협의 (현행 시스템 파악)
2. [ ] IoT 장비 현황 조사 (프로토콜 종류, 게이트웨이 유무)
3. [ ] 데이터 아키텍처 설계 문서 작성 (`PM3-data-architecture.design.md`)
4. [ ] 팀 리뷰 및 CTO 승인
5. [ ] PoC: Kafka→TimescaleDB 파이프라인 단일 장비 연결 테스트

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-30 | Initial draft — 데이터 모델, 통합 전략, AI 파이프라인 초안 | PM (Data Architecture) |
