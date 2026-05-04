# Sprint 3 AI Agent — Plan Document

> **Feature**: sprint-3-ai-agent
> **Phase**: Plan
> **Date**: 2026-05-04
> **Status**: Draft
> **Depends on**: sprint-2-core (완료, Match Rate 91%)

---

## 1. 목적 및 배경

### 1.1 목적

Sprint 3는 Metal-Onetouch AI+MES 시스템의 **Phase 2 핵심**을 구현합니다.  
Sprint 2에서 완성된 MES 기반(기준정보, 작업지시, 대시보드, 사용자 관리) 위에  
**RAG 기반 AI Agent(입고/출하)**, **품질 검사 모듈**, **출하/물류 모듈**, **Service Layer 리팩토링**을 추가하여  
LOT 기반 수주→입고→공정→품질→출하 전 공정의 완전한 추적 사이클을 완성합니다.

### 1.2 배경

**Sprint 2 완료 현황 (2026-05-04, Match Rate 91%)**:
- 8개 DB 모델 + 37개 API 엔드포인트 구현 완료
- 4개 기능 페이지 + 4개 공통 UI 컴포넌트 완성
- 미해결 항목: Service Layer 미추출 (work_order_service, dashboard_service)

**MASTER-PLAN Phase 2 목표 (M5~8)**:
- 입고재고관리: 입고 AI Agent + LOT 자동 생성
- 출하물류관리: 출하 AI Agent + 클레임 분석
- KPI 실집계 연동
- RAG 기반 자연어 질의 응답 (RAGAS Faithfulness ≥ 0.85)

**Sprint 3 진입 조건 (Sprint 2 완료로 모두 충족)**:
- LOT CRUD + 상태머신 동작 확인
- 기준정보 5개 도메인 seed 데이터 입력 완료
- 작업지시 생성 → 공정 실적 등록 E2E 흐름 검증
- 대시보드 실API 연동 완료 (더미 데이터 0%)

### 1.3 관련 문서

| 문서 | 경로 |
|------|------|
| 통합 마스터 플랜 | `docs/01-plan/MASTER-PLAN.md` |
| Sprint 2 계획 | `docs/01-plan/features/sprint-2-core.plan.md` |
| Sprint 2 완료 보고서 | `docs/04-report/sprint-2-core.report.md` |
| MES 아키텍처 설계 | `docs/02-design/features/mes-architecture.design.md` |
| DB 스키마 | `docs/02-design/db/schema.sql` |

---

## 2. 사용자 스토리 (User Stories)

### US-01 입고 AI Agent (품질담당자 / 생산관리자)

> "발주서를 AI Agent에게 자연어로 입력하면, 자동으로 LOT를 생성하고 과거 유사 입고 이력을 참조하여 품질 이상 여부를 사전 경고한다."

**인수 기준**:
- 자연어 질의 입력 → AI가 공급업체/원자재 매칭 → LOT 자동 생성
- Qdrant RAG: 과거 6개월 입고 데이터 기반 품질 이상 패턴 감지
- 응답 시간: 단순 질의 ≤ 10초, 복합 RAG 질의 ≤ 30초
- RAGAS Faithfulness ≥ 0.85 (환각 방지)

### US-02 출하 AI Agent (생산관리자 / 품질담당자)

> "출하 지시를 AI Agent에게 자연어로 입력하면, 출하 LOT 목록과 배송 최적화 제안을 받고, LOT 품질 리스크를 RED/YELLOW/GREEN으로 확인한다."

**인수 기준**:
- 출하 지시 자연어 처리 → 출하 LOT 등록 자동화
- 리스크 등급 산출: GREEN (정상) / YELLOW (주의) / RED (중지)
- 배송 최적화 제안 (납기일, 고객사 우선순위 기반)
- 클레임 이력 RAG 검색 → 유사 불량 패턴 경고

### US-03 품질 검사 모듈 (품질담당자)

> "LOT 단위 품질 검사 결과를 등록하고, 불량 발생 시 LOT 상태가 자동으로 rejected로 전환되며, 불량 원인이 기록된다."

**인수 기준**:
- 품질 검사 등록: LOT 연결, 검사 유형, 합격/불합격, 불량 상세
- 불량 등록 → LOT 상태 자동 전환 (in_process → rejected)
- 불량률 집계 API (LOT별, 공급업체별, 공정유형별)
- 대시보드 defect_rate 실집계 연동 (Sprint 2 더미값 교체)

### US-04 출하/물류 모듈 (생산관리자 / 물류담당자)

> "출하 등록 시 LOT 단위로 출하 묶음을 구성하고, 배송 상태를 단계별로 추적하며, 대시보드 pending_shipments가 실데이터를 표시한다."

**인수 기준**:
- 출하 등록: shipment_number, 고객사, 출하 LOT 목록
- LOT 상태 전환: in_process → shipped → delivered
- 배송 단계 추적: 출하예정 → 배송중 → 인수완료
- 대시보드 `pending_shipments` 실집계 연동

### US-05 Service Layer 리팩토링 (개발팀)

> "Sprint 2에서 라우터 인라인으로 구현된 비즈니스 로직이 Service Layer로 추출되어 단위 테스트가 가능하고, 관심사 분리가 완성된다."

**인수 기준**:
- `backend/app/services/work_order_service.py` 추출 (WO 번호 생성, 상태 전환 검증)
- `backend/app/services/dashboard_service.py` 추출 (집계 쿼리 로직)
- `backend/app/services/ai_agent_service.py` 신규 (Agent 오케스트레이션)
- 단위 테스트 커버리지 Service Layer ≥ 80%

### US-06 AI Agent 채팅 UI (모든 사용자)

> "대시보드의 AI Agent 페이지에서 자연어로 질의하면, 실시간 스트리밍으로 응답을 받고, 대화 이력이 저장된다."

**인수 기준**:
- 채팅 인터페이스: 메시지 입력 → 전송 → 스트리밍 응답 표시
- Socket.io 실시간 스트리밍 (응답 토큰 순차 표시)
- 대화 이력: 세션별 저장, 최근 20개 메시지 조회
- Agent 선택: 입고 Agent / 출하 Agent / 통합 Agent

---

## 3. 기능 범위 (Scope)

### 3.1 In Scope

#### 백엔드

| 우선순위 | 도메인 | 신규 테이블 | API 엔드포인트 수 |
|----------|--------|-------------|-------------------|
| P0 | Service Layer 리팩토링 | 없음 (기존 라우터 리팩토링) | 0 (기존 재구성) |
| P0 | 품질 검사 | `quality_inspections`, `defect_details` | 6개 |
| P0 | 출하/물류 | `shipments`, `shipment_lots` | 6개 |
| P1 | 입고 AI Agent | `ai_conversations`, `ai_messages` | 3개 |
| P1 | 출하 AI Agent | (ai_conversations 공유) | 3개 |
| P2 | Celery 비동기 | Redis 큐 설정, Celery worker | — |

**신규 DB 테이블 (Alembic 마이그레이션 2개)**:

```
0005_quality_shipment.py:
  quality_inspections: id, lot_id(FK), inspector_id(FK users), inspection_type, result(pass/fail),
                       defect_rate, inspection_date, notes, created_at
  defect_details: id, inspection_id(FK), defect_code, defect_type, qty, description,
                  root_cause, created_at
  shipments: id, shipment_number(unique), customer_id(FK), status(pending/shipped/delivered/cancelled),
             planned_date, shipped_date, delivered_date, notes, created_at, updated_at
  shipment_lots: id, shipment_id(FK), lot_id(FK), qty, unit_price, created_at

0006_ai_agent.py:
  ai_conversations: id, agent_type(inbound/outbound/integrated), user_id(FK),
                    title, created_at, updated_at
  ai_messages: id, conversation_id(FK), role(user/assistant), content, metadata(JSONB),
               tokens_used, latency_ms, created_at
```

**신규 API 엔드포인트**:

```
/api/v1/quality/
  GET  /                  — 검사 목록 (lot_id, result, date 필터)
  POST /                  — 검사 등록 (불량 시 LOT 상태 자동 전환)
  GET  /{id}              — 검사 상세 + 불량 상세 포함
  GET  /stats             — 불량률 집계 (기간, 공급업체, 공정유형별)
  POST /{id}/defects       — 불량 상세 추가
  GET  /lot/{lot_id}      — LOT별 검사 이력

/api/v1/shipments/
  GET  /                  — 출하 목록 (status, customer_id, date 필터)
  POST /                  — 출하 등록 + LOT 묶음
  GET  /{id}              — 출하 상세 + 포함 LOT 목록
  PATCH /{id}/status      — 출하 상태 전환 (shipped/delivered/cancelled)
  POST /{id}/lots         — 출하에 LOT 추가
  GET  /pending           — 출하 대기 목록 (대시보드 연동용)

/api/v1/ai-agent/
  POST /inbound           — 입고 AI Agent 질의
  POST /outbound          — 출하 AI Agent 질의
  GET  /conversations     — 대화 이력 목록
  GET  /conversations/{id}/messages — 대화 메시지 조회
```

#### 프론트엔드

| 모듈 | 구현 내용 |
|------|-----------|
| `(dashboard)/ai-agent/page.tsx` | 채팅 인터페이스 (현재 stub → 전체 구현) |
| `(dashboard)/logistics/page.tsx` | 출하 목록 + 등록 폼 (현재 stub → 구현) |
| `(dashboard)/inventory/page.tsx` | 입고 현황 + 품질 검사 탭 추가 |
| `(dashboard)/page.tsx` | pending_shipments 실집계 연동 + defect_rate 교체 |
| `components/ui/chat-bubble.tsx` | AI 채팅 메시지 컴포넌트 |
| `components/ui/risk-badge.tsx` | GREEN/YELLOW/RED 리스크 등급 배지 |

#### 인프라 / AI 스택

| 항목 | 내용 |
|------|------|
| Qdrant 컬렉션 초기화 | `inbound_history`, `outbound_history` 컬렉션 + BGE-M3 임베딩 설정 |
| LangChain Agent 구성 | GPT-4o / Claude 3.5 Sonnet Function Calling + RAG Tool |
| Celery worker | Redis 큐 (`ai_agent_queue`) + 비동기 AI 추론 태스크 |
| Socket.io 서버 이벤트 | `ai_stream_chunk`, `ai_stream_end`, `ai_stream_error` |

### 3.2 Out of Scope (Phase 3로 이관)

| 기능 | 이유 | 예정 Sprint |
|------|------|-------------|
| IoT MQTT→Kafka→Flink 파이프라인 | 전용 인프라 설치 필요, Phase 1 M3 scope | Sprint 4 |
| TimescaleDB 하이퍼테이블 | IoT 파이프라인 의존 | Sprint 4 |
| Vision AI (YOLOv8) CAD 도면 분석 | Phase 3 M9-14 scope | Sprint 9+ |
| 통합 AI Agent (전 도메인 질의) | 입고/출하 Agent 안정화 후 확장 | Sprint 6 |
| ERP 연동 (양방향 동기화) | Phase 3 M9-14 scope | Sprint 9+ |
| ML/XGBoost 원가 예측 | 학습 데이터 충분히 쌓인 후 | Sprint 7+ |
| KPI 전용 페이지 | 대시보드 실집계 먼저 검증 | Sprint 4 |
| 설비 이상감지 (Isolation Forest) | IoT 파이프라인 의존 | Sprint 5+ |

---

## 4. 기술 의존성

### 4.1 신규 패키지 (백엔드)

```
langchain==0.2.x
langchain-openai==0.1.x
langchain-anthropic==0.1.x
qdrant-client==1.9.x
fastembed==0.3.x          # BGE-M3 로컬 임베딩
celery==5.3.x
python-socketio==5.11.x
ragas==0.1.x              # RAG 평가 프레임워크
```

### 4.2 신규 패키지 (프론트엔드)

```
socket.io-client==4.7.x   # 실시간 스트리밍
```

### 4.3 인프라 의존성

| 서비스 | 현재 상태 | Sprint 3 요구사항 |
|--------|-----------|------------------|
| PostgreSQL 16 | Docker Compose 기동 중 | 마이그레이션 0005, 0006 적용 |
| Redis 7 | Docker Compose 기동 중 | Celery 큐 설정 |
| Qdrant | Docker Compose 정의됨 | 컬렉션 초기화 + BGE-M3 인덱스 |
| Celery Worker | 미설정 | docker-compose.yml 추가 |

### 4.4 외부 API

| API | 용도 | 비고 |
|-----|------|------|
| OpenAI GPT-4o | LLM 추론 | OPENAI_API_KEY 환경변수 |
| Anthropic Claude 3.5 Sonnet | LLM 추론 (Fallback) | ANTHROPIC_API_KEY 환경변수 |

---

## 5. 구현 우선순위 (MoSCoW)

### Must (P0 — 이번 Sprint 필수)

| 항목 | 근거 |
|------|------|
| Service Layer 리팩토링 (work_order_service, dashboard_service) | Sprint 2 미해결 갭, 테스트 가능성 확보 |
| 품질 검사 모듈 (DB + API 6개) | LOT → 품질 → 출하 흐름 완성에 필수 |
| 출하/물류 모듈 (DB + API 6개) | pending_shipments 실집계 대시보드 연동에 필수 |
| Alembic 0005 마이그레이션 | 품질/출하 DB 테이블 |
| 대시보드 실집계 2항목 교체 | defect_rate(품질), pending_shipments(출하) |

### Should (P1 — 이번 Sprint 권장)

| 항목 | 근거 |
|------|------|
| 입고 AI Agent (`/api/v1/ai-agent/inbound`) | Phase 2 핵심 기능 |
| 출하 AI Agent (`/api/v1/ai-agent/outbound`) | Phase 2 핵심 기능 |
| Qdrant 컬렉션 초기화 + BGE-M3 임베딩 | AI Agent 전제 조건 |
| AI Agent 채팅 UI (`ai-agent/page.tsx`) | 사용자 가시적 가치 |
| 대화 이력 저장 (ai_conversations, ai_messages) | RAG 품질 평가 기반 |
| Celery 비동기 AI 추론 | API 응답 시간 ≤ 500ms 보장 |

### Could (P2 — 시간 여유 시)

| 항목 | 근거 |
|------|------|
| Socket.io 실시간 스트리밍 | 없어도 폴링으로 대체 가능 |
| ai_agent_service.py 단위 테스트 80% | 기능 동작 우선 |
| risk-badge 컴포넌트 분리 | 인라인으로 대체 가능 |
| RAGAS 평가 파이프라인 자동화 | 수동 평가로 대체 가능 |
| `components/forms/` 추출 (Sprint 2 잔여) | 기능에 영향 없음 |

### Won't (이번 Sprint 제외)

| 항목 | 이유 |
|------|------|
| IoT/Kafka/Flink 파이프라인 | 별도 인프라 설치 필요 |
| Vision AI 견적 | Phase 3 scope |
| 통합 AI Agent | 도메인별 Agent 안정화 후 |
| KPI 전용 페이지 | Sprint 4 |

---

## 6. 완료 기준 (Definition of Done)

### P0 필수

- [ ] `0005_quality_shipment.py` Alembic 마이그레이션 적용 (`alembic upgrade head` 성공)
- [ ] 품질 검사 등록 → 불량 발생 시 LOT 상태 자동 전환 (in_process → rejected) E2E 확인
- [ ] 출하 등록 → LOT 묶음 → 상태 전환 (pending → shipped → delivered) E2E 확인
- [ ] 대시보드 `defect_rate` 실집계 연동 (quality_inspections 테이블 기반)
- [ ] 대시보드 `pending_shipments` 실집계 연동 (shipments 테이블 기반)
- [ ] `work_order_service.py`, `dashboard_service.py` 추출 + 라우터 인라인 로직 제거

### P1 권장

- [ ] 입고 AI Agent — LangChain + GPT-4o Function Calling 동작 확인 (Swagger 검증)
- [ ] 출하 AI Agent — 리스크 등급 산출 (GREEN/YELLOW/RED) 동작 확인
- [ ] Qdrant `inbound_history` 컬렉션 생성 + BGE-M3 임베딩 인덱스 초기화
- [ ] AI Agent 채팅 UI — 메시지 전송 → 응답 수신 흐름 동작 확인
- [ ] Celery worker docker-compose.yml 추가 + AI 추론 비동기 큐 동작 확인
- [ ] AI 응답 시간 측정: 단순 질의 ≤ 10초, 복합 RAG ≤ 30초

### 다음 Sprint (Sprint 4) 진입 조건

- [ ] LOT 입고 → 공정 → 품질검사 → 출하 전체 흐름 E2E 시나리오 1회 이상 성공
- [ ] AI Agent 최소 3개 실제 질의/응답 로그 저장 확인
- [ ] 대시보드 4개 KPI 카드 모두 실집계 연동 (더미값 0%)

---

## 7. 예상 일정 (2주, W5-6)

### Week 5 — 백엔드 핵심 (Day 1-5)

| 일자 | 작업 항목 | 담당 우선순위 |
|------|-----------|---------------|
| D1 | Service Layer 추출: `work_order_service.py`, `dashboard_service.py` | P0 |
| D2 | SQLAlchemy 모델 4개 (quality_inspections, defect_details, shipments, shipment_lots) + 0005 마이그레이션 | P0 |
| D3 | 품질 검사 라우터 (6 엔드포인트) + LOT 상태 전환 로직 | P0 |
| D4 | 출하/물류 라우터 (6 엔드포인트) + LOT 출하 묶음 로직 | P0 |
| D5 | Qdrant 초기화 + LangChain Agent 구성 + Celery worker 설정 | P1 |

### Week 6 — AI Agent + 프론트엔드 (Day 6-10)

| 일자 | 작업 항목 | 담당 우선순위 |
|------|-----------|---------------|
| D6 | 입고 AI Agent 라우터 + RAG 파이프라인 (BGE-M3 임베딩 + Qdrant 검색) | P1 |
| D7 | 출하 AI Agent 라우터 + 리스크 등급 산출 로직 + 대화 이력 저장 | P1 |
| D8 | AI Agent 채팅 UI (ai-agent/page.tsx) + chat-bubble 컴포넌트 | P1 |
| D9 | logistics/page.tsx + inventory 품질 탭 추가 | P1 |
| D10 | 대시보드 실집계 연동 완성 + Socket.io 스트리밍 (가능 시) | P1/P2 |

---

## 8. 리스크

| 리스크 | 영향도 | 발생 확률 | 대응 방안 |
|--------|--------|-----------|-----------|
| OpenAI API 비용/레이트 리밋 | 중 | 중 | 개발 단계 gpt-4o-mini 사용, 프로덕션 전환 시 gpt-4o |
| Qdrant BGE-M3 임베딩 지연 (첫 초기화) | 중 | 높 | fastembed 로컬 다운로드 사전 준비, CI에서 제외 |
| LangChain Agent 환각 (RAGAS Faithfulness < 0.85) | 높 | 중 | System prompt 엄격 제약, 소스 인용 강제, 수동 평가 3회 |
| Celery-Redis 연결 설정 복잡도 | 낮 | 중 | Docker Compose 기존 Redis 재사용, 별도 DB 분리 불필요 |
| Socket.io 스트리밍 구현 시간 초과 | 낮 | 중 | P2로 분류, 폴링 방식으로 대체 가능 (30초 간격) |
| LOT 상태 전환 충돌 (공정 중 불량 등록) | 높 | 낮 | 상태 전환 규칙 명시 (rejected는 in_process에서만 가능) |
| Sprint 2 Depends() 패턴 재발 | 중 | 중 | 라우터 작성 시 get_db Depends 체크리스트 적용 |

---

## 9. 아키텍처 고려사항

### 9.1 AI Agent 아키텍처

```
사용자 질의 (자연어)
     ↓
FastAPI /api/v1/ai-agent/{type}
     ↓
Celery Task Queue (Redis)
     ↓
ai_agent_service.py
  ├── LangChain Agent (GPT-4o / Claude 3.5 Sonnet)
  │     └── Tools:
  │           ├── rag_search_tool     → Qdrant 벡터 검색
  │           ├── lot_lookup_tool     → PostgreSQL LOT 직접 조회
  │           └── quality_stats_tool  → 불량률 집계 API 호출
  └── 응답 저장 (ai_messages)
     ↓
Socket.io emit (ai_stream_chunk) → Frontend
```

### 9.2 Service Layer 구조 (Sprint 2 미완 해결)

```
backend/app/
├── api/v1/
│   ├── quality.py          ← NEW (service 위임)
│   ├── shipments.py        ← NEW (service 위임)
│   ├── ai_agent.py         ← NEW (service 위임)
│   └── work_orders.py      ← 기존 (인라인 로직 → service 위임)
├── services/
│   ├── work_order_service.py   ← NEW (Sprint 2 잔여)
│   ├── dashboard_service.py    ← NEW (Sprint 2 잔여)
│   ├── quality_service.py      ← NEW
│   ├── shipment_service.py     ← NEW
│   └── ai_agent_service.py     ← NEW (Agent 오케스트레이션)
```

### 9.3 LOT 상태 전환 규칙 (확장)

```
기존 (Sprint 1~2):
  created → in_process → completed

Sprint 3 추가:
  in_process → rejected   (불량 검사 등록 시 자동 전환)
  completed  → shipped    (출하 LOT 묶음 등록 시)
  shipped    → delivered  (배송 완료 확인 시)

불변 원칙 유지:
  - LOT 삭제 불가
  - 이력(process_results, quality_inspections) 수정/삭제 불가
```

---

## 10. 성공 지표

| 지표 | 목표값 | 측정 방법 |
|------|--------|-----------|
| PDCA Match Rate | ≥ 90% | Gap Detector 자동 분석 |
| AI Agent 응답 시간 (단순) | ≤ 10초 | ai_messages.latency_ms |
| AI Agent 응답 시간 (RAG) | ≤ 30초 | ai_messages.latency_ms |
| RAGAS Faithfulness | ≥ 0.85 | 수동 10개 샘플 평가 |
| LOT 전공정 추적 시간 | ≤ 3초 | API 응답 시간 측정 |
| 대시보드 더미 데이터 | 0% | 코드 리뷰 |
| Service Layer 테스트 커버리지 | ≥ 80% | pytest --cov |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-04 | Initial draft (Sprint 3 AI Agent Plan) | PM Agent |
