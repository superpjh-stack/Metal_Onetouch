# 원터치 AI+MES 시스템 — 통합 마스터 플랜

> **Project**: Metal-Onetouch AI+MES  
> **Version**: 1.0  
> **Date**: 2026-04-30  
> **Status**: Planning Phase (PDCA Phase 1)  
> **Authors**: PM1 (아키텍처) + PM2 (AI기능) + PM3 (데이터)

---

## 1. 시스템 개요

원터치 금속 가공(판금/용접/절삭) 제조 현장의 **수주→입고→공정→품질→출하** 전 공정에  
AI 기술(RAG Agent, Vision AI, ML/SHAP)을 내재화한 **Enterprise급 AI+MES 통합 시스템**.

### 핵심 목표

| 지표 | As-Is | To-Be |
|------|-------|-------|
| 견적 산출 시간 | 2시간/건 | 10분/건 (CAD 자동 분석) |
| 클레임 원인 추적 | 2일 | 30분 (LOT 역추적) |
| 설비 고장 예측 | 없음 | 70% 이상 정확도 |
| 불량률 | 기준치 | 20% 감소 |
| 납기 준수율 | 기준치 | 5%p 향상 |

---

## 2. 10대 모듈 구성 (사업계획서 42페이지)

```
원터치 AI 시스템
├── AI 대시보드          (생산·품질·설비·출하 실시간 현황)
├── 입고재고관리          (입고 AI Agent + 원자재 LOT 추적)
├── 수주견적AI관리        (CAD Vision AI + 자동견적 + BOM)
├── 출하물류관리          (출하 AI Agent + 클레임분석)
├── 공정관리             (IoT 모니터링 + 공정실적)
├── 사용자/시스템관리     (RBAC + 로그 + 알림)
├── 기준정보관리          (품질기준 + 작업표준 + 코드)
├── 데이터허브관리        (ERP/MES/IoT 통합 + AI학습데이터)
├── AI Agent 통합관리    (통합AI질의 + 의사결정지원)
└── KPI관리              (생산성·품질 KPI 대시보드)
```

---

## 3. 기술 스택 (확정)

| 레이어 | 기술 |
|--------|------|
| **Frontend** | Next.js 14 (App Router) + TypeScript + shadcn/ui + Tailwind CSS + Recharts + Socket.io |
| **Backend** | FastAPI (Python 3.11) + SQLAlchemy 2.0 + Celery + Pydantic v2 |
| **AI/ML** | LangChain + LlamaIndex + YOLOv8 + XGBoost + SHAP + MLflow |
| **RAG** | Qdrant (온프레미스) + BGE-M3 임베딩 + Hybrid Search (Dense+BM25) |
| **LLM** | GPT-4o / Claude 3.5 Sonnet (Function Calling) |
| **DB** | PostgreSQL 16 + TimescaleDB (IoT) + Redis 7 + MinIO (파일) |
| **Streaming** | MQTT → Apache Kafka → Apache Flink → TimescaleDB |
| **Infra** | Docker + Kubernetes + Nginx + GitHub Actions + Grafana |

---

## 4. 개발 Phase 로드맵

### Phase 1 — MES 핵심 기반 (Month 1~4, 16주)
**목표**: 공정 투입, IoT 연동, AI 학습 데이터 확보 기반 구축

| 모듈 | 핵심 기능 | 기간 |
|------|-----------|------|
| 사용자/시스템관리 | RBAC 5역할, 로그, 알림 | 3주 |
| 기준정보관리 | 품질기준, 작업표준, 코드 | 2주 |
| 공정관리 | 공정실적, 작업조건, 이력 | 5주 |
| AI 대시보드 (기초) | 생산현황, 설비상태 | 3주 |
| IoT 연동 기반 | MQTT→Kafka→InfluxDB | 3주 |

**완료 기준**: LOT 기반 공정 실적 등록/조회, IoT 4종 실시간 대시보드, RBAC 적용

### Phase 2 — 물류/품질 + AI 기초 (Month 5~8, 16주)
**목표**: 입출고 추적, RAG Agent 기초, KPI 대시보드

| 모듈 | 핵심 기능 | 기간 |
|------|-----------|------|
| 입고재고관리 | 입고관리, 이력조회, 공급처분석 | 4주 |
| 출하물류관리 | LOT추적, 검사결과, 클레임분석 | 4주 |
| KPI관리 | 생산성·품질 KPI, 목표설정 | 2주 |
| 입고/출하 AI Agent | RAG 기초, 자연어 질의 | 4주 |
| AI 대시보드 완성 | 품질·출하현황 추가 | 2주 |

**완료 기준**: LOT 입고→출하 전 구간 추적, RAG Agent 자연어 응답, KPI 경영진 대시보드

### Phase 3 — AI 고도화 + 통합 (Month 9~14, 24주)
**목표**: Vision AI 견적, 통합 AI Agent, ERP 완전 연동

| 모듈 | 핵심 기능 | 기간 |
|------|-----------|------|
| 수주견적AI관리 | CAD Vision AI, 자동견적, BOM, SHAP | 10주 |
| 데이터허브관리 | 통합, 시각화, AI학습데이터 | 4주 |
| AI Agent 통합관리 | 전도메인 질의, 의사결정지원 | 6주 |
| ERP 완전 통합 | 양방향 동기화, 수주→BOM→공정 | 4주 |

**완료 기준**: 도면 업로드 후 10분 내 견적, 통합 AI Agent 전도메인 응답, ERP 30초 이내 동기화

---

## 5. 핵심 AI 기능 14개

| # | 기능 | 기술 | Phase |
|---|------|------|-------|
| 1 | 입고 AI Agent | RAG + Qdrant + BGE-M3 | 2 |
| 2 | 출하 AI Agent | RAG + 리스크 등급(GREEN/YELLOW/RED) | 2 |
| 3 | CAD도면 분석 | YOLOv8 + PaddleOCR + GPT-4o Vision | 3 |
| 4 | 객체인식 결과 관리 | Active Learning 파이프라인 | 3 |
| 5 | 견적 자동산출 | 규칙기반 + XGBoost 보정 | 3 |
| 6 | BOM 자동생성 | Rule-based 매핑 | 3 |
| 7 | ML 분석 | XGBoost + LightGBM 원가/생산성 예측 | 2~3 |
| 8 | 영향요인 분석 | SHAP (TreeSHAP) | 3 |
| 9 | 공정데이터 분석 | SPC + K-Means 불량패턴 | 2 |
| 10 | 설비 이상감지 | Isolation Forest + LSTM Autoencoder | 1~2 |
| 11 | 통합 AI 질의 | RAG + Tool Calling (DB 직접 조회) | 3 |
| 12 | 생산/품질 분석 | LLM 자동 리포트 생성 | 2~3 |
| 13 | 의사결정 지원 | Rule Engine + LLM 추천 | 3 |
| 14 | AI학습데이터 관리 | MLflow + Active Learning | 1~3 |

---

## 6. 핵심 데이터 모델 (LOT 중심)

```
SUPPLIER → RAW_MATERIAL → RAW_MATERIAL_RECEIPT
                                    ↓
                                  LOT (불변 추적 단위)
                                    ↓
              ┌─────────────────────┼──────────────────────┐
              ↓                     ↓                       ↓
       PROCESS_RESULT        QUALITY_INSPECTION        SHIPMENT_LOT
              ↓                     ↓                       ↓
       PROCESS_DATA           DEFECT_DETAIL             SHIPMENT
              ↓
         EQUIPMENT
              ↓
   EQUIPMENT_SENSOR_DATA

CAD_ANALYSIS → ESTIMATE → BOM → RAW_MATERIAL
                  ↓
               SHIPMENT
```

**LOT 원칙**: 생성 후 삭제 불가, 상태/이력으로만 관리, 전 공정 단계에서 lot_id 필수

---

## 7. 데이터 통합 전략

| 시스템 | 연동 패턴 | 실시간성 |
|--------|-----------|---------|
| **ERP** | REST API (이벤트) + 1시간 배치 (마스터) | 이벤트성 즉시, 마스터 1시간 |
| **MES** | CDC (Debezium→Kafka) + API (생산지시) | 실시간 CDC |
| **IoT** | MQTT→Kafka→Flink→TimescaleDB | 1~5초 |
| **CAD** | 파일 업로드 + 비동기 처리 큐 | 분 단위 |

---

## 8. 실시간 파이프라인

```
IoT 설비 → MQTT → Apache Kafka → Apache Flink
                                      ├── Job1: TimescaleDB 저장
                                      ├── Job2: Isolation Forest 이상감지
                                      └── Job3: 알림 라우팅 → Redis → WebSocket → 브라우저
```

**알림 레벨**:
- Level 1 (전류 110% / 온도 +40°C / 진동 7.1mm/s): 즉시 SMS/앱 푸시
- Level 2 (이상 패턴): 대시보드 경고
- Level 3 (예방정비 예측): 일일 리포트

---

## 9. 사용자 역할 및 주요 스토리

| 역할 | 주요 모듈 | 핵심 니즈 |
|------|-----------|-----------|
| 생산관리자 | 공정관리, AI대시보드, KPI | 실시간 생산현황, LOT 5분 내 추적 |
| 품질담당자 | 입고관리, 출하관리, 기준정보 | 클레임 원인 즉시 추적, 공급처 분석 |
| 공정기사 | 공정관리, IoT대시보드 | 설비 이상 알림, 최적 작업조건 |
| 경영진 | AI대시보드, KPI, 통합AI | 자연어로 즉시 경영현황 파악 |
| 영업담당자 | 수주견적AI | CAD 업로드 → 10분 내 견적 |

---

## 10. AI 성능 목표

| AI 기능 | KPI | 목표값 |
|---------|-----|--------|
| CAD 도면 분석 | mAP@0.5 | ≥ 85% |
| 견적 오차율 | MAPE | ≤ 8% |
| 설비 이상감지 | Recall | ≥ 90% |
| 오경보율 | False Positive | ≤ 5% |
| RAG 환각 방지 | RAGAS Faithfulness | ≥ 0.85 |
| 통합 AI 응답 시간 | 복합 질의 | ≤ 30초 |

---

## 11. 시스템 비기능 요건

| 항목 | 기준 |
|------|------|
| 동시 사용자 | 50명 |
| API 응답시간 | 평균 500ms 이내 |
| 시스템 가용성 | 99.5% (월 기준) |
| IoT 수집 지연 | < 2초 (센서 → DB) |
| LOT 역추적 조회 | < 3초 (전 이력) |
| 벡터DB 검색 | ≤ 100ms (top-5) |

---

## 12. 다음 Action Items

### 즉시 착수 (이번 주)
- [ ] **ERP/MES 담당자 인터뷰** — 현행 API 제공 여부, 데이터 형식 확인
- [ ] **IoT 장비 현황 조사** — 프로토콜 종류, 게이트웨이 유무
- [ ] **CAD 도면 샘플 500장 수집 계획** — 어노테이션 가이드라인 작성
- [ ] **기존 MES 데이터 인벤토리** — 견적 1,000건, 공정 실적 2,000 LOT 확보 가능 여부

### 설계 단계 진입 (다음 단계)
- [ ] `/pdca design mes-architecture` — DB 스키마 상세 설계
- [ ] Phase 1 스프린트 계획 수립 (2주 스프린트 × 8회)
- [ ] Docker Compose 개발환경 구성
- [ ] Qdrant 온프레미스 PoC 환경 구성

---

## 참조 문서

| 문서 | 경로 |
|------|------|
| PM1 아키텍처 플랜 | `docs/01-plan/PM1-architecture-plan.md` |
| PM2 AI기능 플랜 | `docs/01-plan/features/PM2-ai-features-plan.md` |
| PM3 데이터 아키텍처 | `docs/01-plan/PM3-data-architecture-plan.md` |
| 사업계획서 42-46페이지 | `docs/pages42-46.txt` |
