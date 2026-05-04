# Sprint 3 AI Agent — Design Document

> **Feature**: sprint-3-ai-agent
> **Phase**: Design
> **Version**: 1.0
> **Date**: 2026-05-04
> **Depends on**: `docs/01-plan/features/sprint-3-ai-agent.plan.md`, `docs/02-design/features/sprint-2-core.design.md`

---

## 1. 개요

Sprint 2 완료(91% Match Rate) 기반 위에 **품질·출하·AI Agent** 3개 도메인을 추가하고, Sprint 2 잔여 갭인 Service Layer를 추출합니다.

| 영역 | Sprint 2 완료 | Sprint 3 (이번) |
|------|---------------|-----------------|
| DB | 11개 테이블 (0001~0004) | +6개 (0005: 품질/출하 4개, 0006: AI 대화 2개) |
| API | 37개 엔드포인트 | +16개 (품질 6 + 출하 6 + AI Agent 4) |
| Service Layer | ❌ 라우터 인라인 | ✅ 5개 service 추출 |
| Frontend | 4개 기능 페이지 (더미 2항목) | +2개 페이지 + 대시보드 실집계 완성 |
| AI/RAG | 없음 | LangChain + Qdrant + Celery |

---

## 2. DB 스키마 설계

### 2.1 Migration 0005 — 품질검사 + 출하물류

#### `quality_inspections` — 품질 검사

```sql
CREATE TYPE inspection_type_enum AS ENUM (
    'incoming',     -- 입고 검사
    'in_process',   -- 공정 중 검사
    'final',        -- 최종 검사
    'shipment'      -- 출하 전 검사
);

CREATE TYPE inspection_result_enum AS ENUM ('pass', 'fail', 'conditional');

CREATE TABLE quality_inspections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lot_id          UUID NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    inspector_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    inspection_type inspection_type_enum NOT NULL,
    result          inspection_result_enum NOT NULL,
    defect_rate     NUMERIC(5,2) NOT NULL DEFAULT 0,  -- 불량률 (%)
    inspection_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    -- NOTE: 품질 검사 이력은 수정 불가 (불변 이력) — updated_at 없음
);
CREATE INDEX ix_qi_lot         ON quality_inspections(lot_id);
CREATE INDEX ix_qi_inspector   ON quality_inspections(inspector_id);
CREATE INDEX ix_qi_result      ON quality_inspections(result);
CREATE INDEX ix_qi_date        ON quality_inspections(inspection_date);
CREATE INDEX ix_qi_type        ON quality_inspections(inspection_type);
```

#### `defect_details` — 불량 상세

```sql
CREATE TYPE defect_type_enum AS ENUM (
    'dimensional',  -- 치수 불량
    'surface',      -- 표면 불량
    'weld',         -- 용접 불량
    'material',     -- 재질 불량
    'assembly',     -- 조립 불량
    'other'
);

CREATE TABLE defect_details (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id   UUID NOT NULL REFERENCES quality_inspections(id) ON DELETE RESTRICT,
    defect_code     VARCHAR(30) NOT NULL,          -- 예) DEF-DIM-001
    defect_type     defect_type_enum NOT NULL,
    qty             NUMERIC(12,3) NOT NULL DEFAULT 1,
    description     TEXT,
    root_cause      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_dd_inspection  ON defect_details(inspection_id);
CREATE INDEX ix_dd_type        ON defect_details(defect_type);
CREATE INDEX ix_dd_code        ON defect_details(defect_code);
```

#### `shipments` — 출하

```sql
CREATE TYPE shipment_status_enum AS ENUM (
    'pending',      -- 출하 대기
    'shipped',      -- 배송 중
    'delivered',    -- 인수 완료
    'cancelled'     -- 취소
);

CREATE TABLE shipments (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_number  VARCHAR(30) NOT NULL UNIQUE,    -- 예) SH-20260504-0001
    customer_id      UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    status           shipment_status_enum NOT NULL DEFAULT 'pending',
    planned_date     DATE,
    shipped_date     TIMESTAMPTZ,
    delivered_date   TIMESTAMPTZ,
    notes            TEXT,
    created_by       UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_sh_number      ON shipments(shipment_number);
CREATE INDEX ix_sh_customer    ON shipments(customer_id);
CREATE INDEX ix_sh_status      ON shipments(status);
CREATE INDEX ix_sh_planned     ON shipments(planned_date);
```

#### `shipment_lots` — 출하 LOT 묶음

```sql
CREATE TABLE shipment_lots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id     UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    lot_id          UUID NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    qty             NUMERIC(12,3) NOT NULL,
    unit_price      NUMERIC(15,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(shipment_id, lot_id)
);
CREATE INDEX ix_sl_shipment    ON shipment_lots(shipment_id);
CREATE INDEX ix_sl_lot         ON shipment_lots(lot_id);
```

---

### 2.2 Migration 0006 — AI Agent 대화 이력

#### `ai_conversations` — AI 대화 세션

```sql
CREATE TYPE agent_type_enum AS ENUM ('inbound', 'outbound', 'integrated');

CREATE TABLE ai_conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type      agent_type_enum NOT NULL,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(200),    -- 첫 메시지 앞 50자 자동 생성
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_conv_user       ON ai_conversations(user_id);
CREATE INDEX ix_conv_type       ON ai_conversations(agent_type);
CREATE INDEX ix_conv_updated    ON ai_conversations(updated_at DESC);
```

#### `ai_messages` — AI 메시지 (불변)

```sql
CREATE TYPE message_role_enum AS ENUM ('user', 'assistant', 'system');

CREATE TABLE ai_messages (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role             message_role_enum NOT NULL,
    content          TEXT NOT NULL,
    metadata         JSONB,          -- RAG 소스, tool_calls, risk_level 등
    tokens_used      INTEGER,
    latency_ms       INTEGER,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
    -- NOTE: 메시지는 수정 불가
);
CREATE INDEX ix_msg_conversation ON ai_messages(conversation_id);
CREATE INDEX ix_msg_created      ON ai_messages(created_at);
```

---

### 2.3 LOT 상태 전환 규칙 확장

기존 `lot_status_enum`에 `rejected`, `shipped`, `delivered` 3개 값 추가 (0005 마이그레이션에서 `ALTER TYPE`):

```sql
ALTER TYPE lot_status_enum ADD VALUE 'rejected' AFTER 'in_process';
ALTER TYPE lot_status_enum ADD VALUE 'shipped' AFTER 'completed';
ALTER TYPE lot_status_enum ADD VALUE 'delivered' AFTER 'shipped';
```

전환 규칙:

```
기존:  created → in_receipt → received → in_process → completed
추가:
  in_process  → rejected   (fail 검사 결과 등록 시 자동)
  completed   → shipped    (shipment_lots 등록 시 자동)
  shipped     → delivered  (출하 상태 delivered 전환 시 자동)

불변 원칙:
  - rejected 이후 전환 없음 (종료 상태)
  - LOT 직접 삭제 불가
```

---

## 3. Pydantic 스키마

### 3.1 품질 검사 스키마 (`schemas/quality.py`)

```python
class DefectDetailCreate(BaseModel):
    defect_code: str
    defect_type: Literal['dimensional','surface','weld','material','assembly','other']
    qty: Decimal = Decimal('1')
    description: str | None = None
    root_cause: str | None = None

class DefectDetailRead(DefectDetailCreate):
    id: UUID
    inspection_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class QualityInspectionCreate(BaseModel):
    lot_id: UUID
    inspection_type: Literal['incoming','in_process','final','shipment']
    result: Literal['pass','fail','conditional']
    defect_rate: Decimal = Decimal('0')
    inspection_date: datetime | None = None
    notes: str | None = None
    defects: list[DefectDetailCreate] = []

class QualityInspectionRead(BaseModel):
    id: UUID
    lot_id: UUID
    inspector_id: UUID | None
    inspection_type: str
    result: str
    defect_rate: Decimal
    inspection_date: datetime
    notes: str | None
    defects: list[DefectDetailRead] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DefectStatsItem(BaseModel):
    group_key: str        # lot_id / supplier_id / process_type 값
    group_label: str
    total_inspections: int
    fail_count: int
    avg_defect_rate: float

class DefectStatsResponse(BaseModel):
    group_by: str
    period_days: int
    items: list[DefectStatsItem]
```

### 3.2 출하 스키마 (`schemas/shipment.py`)

```python
class ShipmentLotItem(BaseModel):
    lot_id: UUID
    qty: Decimal
    unit_price: Decimal | None = None

class ShipmentCreate(BaseModel):
    customer_id: UUID
    planned_date: date | None = None
    notes: str | None = None
    lots: list[ShipmentLotItem] = []    # 최초 등록 시 LOT 함께 묶기

class ShipmentUpdate(BaseModel):
    planned_date: date | None = None
    notes: str | None = None

class ShipmentStatusUpdate(BaseModel):
    status: Literal['shipped','delivered','cancelled']
    notes: str | None = None

class ShipmentLotRead(BaseModel):
    id: UUID
    lot_id: UUID
    qty: Decimal
    unit_price: Decimal | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ShipmentRead(BaseModel):
    id: UUID
    shipment_number: str
    customer_id: UUID
    customer_name: str | None = None    # JOIN 비정규화
    status: str
    planned_date: date | None
    shipped_date: datetime | None
    delivered_date: datetime | None
    notes: str | None
    lots: list[ShipmentLotRead] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

### 3.3 AI Agent 스키마 (`schemas/ai_agent.py`)

```python
class AgentQueryRequest(BaseModel):
    query: str                              # 자연어 질의
    conversation_id: UUID | None = None     # 기존 대화 이어가기 (None이면 신규)

class AgentQueryResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    content: str
    risk_level: Literal['GREEN','YELLOW','RED'] | None = None
    sources: list[dict] = []                # RAG 참조 소스
    latency_ms: int
    tokens_used: int

class ConversationRead(BaseModel):
    id: UUID
    agent_type: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MessageRead(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    metadata: dict | None
    tokens_used: int | None
    latency_ms: int | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

---

## 4. Service Layer 설계

### 4.1 디렉토리 구조

```
backend/app/services/
├── __init__.py
├── work_order_service.py     ← Sprint 2 인라인 추출
├── dashboard_service.py      ← Sprint 2 인라인 추출
├── quality_service.py        ← NEW
├── shipment_service.py       ← NEW
└── ai_agent_service.py       ← NEW
```

### 4.2 `work_order_service.py`

```python
class WorkOrderService:
    def __init__(self, db: AsyncSession): ...

    async def generate_wo_number(self) -> str:
        """WO-{YYYYMMDD}-{4자리 SEQ}"""

    async def validate_status_transition(
        self, wo: WorkOrder, new_status: str
    ) -> None:
        """WO_STATUS_TRANSITIONS 검증, 실패 시 HTTPException 422"""

    async def apply_status_transition(
        self, wo: WorkOrder, new_status: str, notes: str | None
    ) -> WorkOrder:
        """상태 전환 + actual_start/actual_end 자동 기록"""
```

### 4.3 `dashboard_service.py`

```python
class DashboardService:
    def __init__(self, db: AsyncSession): ...

    async def get_today_production(self) -> dict:
        """오늘 완료 WO 합산 output_qty"""

    async def get_defect_rate(self, days: int = 7) -> float:
        """최근 N일 quality_inspections 기반 defect_rate 실집계"""

    async def get_equipment_utilization(self) -> float:
        """가동 중 equipment 비율"""

    async def get_pending_shipments(self) -> int:
        """shipments WHERE status='pending' 건수"""

    async def get_production_trend(self, days: int = 7) -> list[dict]:
        """일별 생산량 트렌드"""

    async def get_lot_status_summary(self, limit: int = 5) -> list[dict]:
        """LOT 상태별 집계"""
```

### 4.4 `quality_service.py`

```python
class QualityService:
    def __init__(self, db: AsyncSession): ...

    async def create_inspection(
        self, data: QualityInspectionCreate, inspector_id: UUID
    ) -> QualityInspection:
        """검사 등록 + 불량 시 LOT 상태 자동 전환 (in_process → rejected)"""

    async def get_defect_stats(
        self, group_by: str, period_days: int
    ) -> DefectStatsResponse:
        """불량률 집계 (lot / supplier / process_type)"""

    async def get_lot_inspections(self, lot_id: UUID) -> list[QualityInspection]:
        """LOT별 전체 검사 이력"""
```

**LOT 자동 전환 로직**:
```python
if data.result == 'fail':
    lot = await db.get(Lot, data.lot_id)
    if lot.status == 'in_process':
        lot.status = 'rejected'
        lot.updated_at = now_utc
```

### 4.5 `shipment_service.py`

```python
class ShipmentService:
    def __init__(self, db: AsyncSession): ...

    async def generate_shipment_number(self) -> str:
        """SH-{YYYYMMDD}-{4자리 SEQ}"""

    async def create_shipment(
        self, data: ShipmentCreate, created_by: UUID
    ) -> Shipment:
        """출하 등록 + LOT 묶음 생성 + LOT 상태 completed → shipped"""

    async def update_status(
        self, shipment: Shipment, new_status: str, notes: str | None
    ) -> Shipment:
        """상태 전환 + shipped_date/delivered_date 자동 기록
           delivered 시 shipment_lots의 lot 상태 shipped → delivered"""

    async def add_lots(
        self, shipment_id: UUID, lots: list[ShipmentLotItem]
    ) -> list[ShipmentLot]:
        """출하에 LOT 추가 (status=pending 일 때만)"""
```

### 4.6 `ai_agent_service.py`

```python
class AIAgentService:
    def __init__(self, db: AsyncSession): ...

    async def query(
        self,
        agent_type: str,
        query_text: str,
        conversation_id: UUID | None,
        user_id: UUID,
    ) -> AgentQueryResponse:
        """LangChain Agent 실행 → 응답 저장 → 반환"""

    async def _get_or_create_conversation(
        self, agent_type: str, user_id: UUID, conversation_id: UUID | None
    ) -> AIConversation: ...

    async def _save_messages(
        self,
        conversation_id: UUID,
        user_query: str,
        assistant_response: str,
        metadata: dict,
    ) -> AIMessage: ...
```

---

## 5. AI Agent 아키텍처

### 5.1 시스템 구성

```
사용자 자연어 질의
      ↓
FastAPI POST /api/v1/ai-agent/{inbound|outbound}
      ↓ (Celery task enqueue)
Redis Queue: ai_agent_queue
      ↓ (Celery worker consume)
ai_agent_service.AIAgentService.query()
      ↓
LangChain AgentExecutor
  ├── LLM: ChatOpenAI(model="gpt-4o") [primary]
  │         ChatAnthropic(model="claude-3-5-sonnet") [fallback]
  ├── Tools:
  │   ├── rag_search_tool     → QdrantClient.search() (BGE-M3 임베딩)
  │   ├── lot_lookup_tool     → PostgreSQL SELECT (lot_id / status / supplier)
  │   └── quality_stats_tool  → quality_service.get_defect_stats()
  └── Memory: ConversationBufferWindowMemory(k=10)
      ↓
응답 저장 (ai_messages)
      ↓
HTTP 응답 반환 (AgentQueryResponse)
```

### 5.2 LangChain Tool 명세

#### `rag_search_tool`

```python
@tool
def rag_search_tool(query: str, collection: str = "inbound_history") -> str:
    """과거 입고/출하 이력에서 유사 케이스를 검색합니다.
    collection: 'inbound_history' | 'outbound_history'
    """
    # fastembed BGE-M3 로컬 임베딩
    embedding = embedder.embed(query)
    results = qdrant_client.search(
        collection_name=collection,
        query_vector=embedding,
        limit=5,
        score_threshold=0.75
    )
    return format_rag_results(results)
```

#### `lot_lookup_tool`

```python
@tool
def lot_lookup_tool(filters: str) -> str:
    """LOT 정보를 조회합니다. filters: JSON string
    예) {"supplier_name": "현대철강", "status": "received"}
    """
```

#### `quality_stats_tool`

```python
@tool
def quality_stats_tool(group_by: str = "supplier", period_days: int = 30) -> str:
    """불량률 통계를 조회합니다.
    group_by: 'supplier' | 'process_type' | 'lot'
    """
```

### 5.3 Qdrant 컬렉션 설계

| 컬렉션 | 벡터 차원 | 임베딩 모델 | 주요 페이로드 |
|--------|-----------|-------------|---------------|
| `inbound_history` | 1024 | BGE-M3 | lot_id, supplier_name, material_name, quality_result, date |
| `outbound_history` | 1024 | BGE-M3 | shipment_number, customer_name, lot_ids, risk_level, claim_notes |

초기화 스크립트: `backend/app/core/qdrant_init.py`

```python
async def initialize_collections(client: QdrantClient) -> None:
    for name in ["inbound_history", "outbound_history"]:
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
            )
```

### 5.4 리스크 등급 산출 (출하 Agent)

출하 Agent 응답에 `risk_level` 포함:

```
GREEN:  defect_rate < 2% AND 클레임 이력 없음
YELLOW: defect_rate 2~5% OR 클레임 이력 1건
RED:    defect_rate > 5% OR 클레임 이력 2건 이상
```

System prompt에 규칙 명시, LLM이 `risk_level` JSON 필드로 반환하도록 강제:

```
응답은 반드시 다음 JSON 형식을 포함해야 합니다:
{"risk_level": "GREEN|YELLOW|RED", "answer": "..."}
```

### 5.5 Celery 설정

`backend/app/core/celery_app.py`:

```python
from celery import Celery

celery_app = Celery(
    "metal_onetouch",
    broker="redis://redis:6379/1",
    backend="redis://redis:6379/2",
)
celery_app.conf.task_routes = {
    "app.tasks.ai_agent.*": {"queue": "ai_agent_queue"},
}
```

`docker-compose.yml` 추가:

```yaml
celery-worker:
  build: ./backend
  command: celery -A app.core.celery_app worker -Q ai_agent_queue -c 2 --loglevel=info
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - REDIS_URL=redis://redis:6379
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
  depends_on:
    - db
    - redis
    - qdrant
```

---

## 6. API 엔드포인트 명세

### 6.1 품질 검사 (`/api/v1/quality/`)

| Method | Path | Auth | 설명 |
|--------|------|------|------|
| GET | `/` | 로그인 | 검사 목록 (lot_id, result, inspection_type, date_from, date_to 필터, 페이지네이션) |
| POST | `/` | quality_inspector+ | 검사 등록 + 불량 상세 포함 + LOT 상태 자동 전환 |
| GET | `/{id}` | 로그인 | 검사 상세 + 불량 상세 목록 포함 |
| GET | `/stats` | 로그인 | 불량률 집계 (group_by, period_days 파라미터) |
| POST | `/{id}/defects` | quality_inspector+ | 불량 상세 추가 |
| GET | `/lot/{lot_id}` | 로그인 | LOT별 검사 이력 전체 |

**POST `/` 요청/응답**:

```
Request:
  {
    "lot_id": "uuid",
    "inspection_type": "final",
    "result": "fail",
    "defect_rate": 3.5,
    "notes": "용접부 균열 발견",
    "defects": [
      {"defect_code": "DEF-WLD-001", "defect_type": "weld", "qty": 2, "root_cause": "용접 온도 과다"}
    ]
  }

Response 201:
  QualityInspectionRead (defects 포함)
  + 사이드 이펙트: lot.status → rejected (result=fail, lot.status=in_process일 때)
```

**GET `/stats` 파라미터**:

```
group_by: "supplier" | "process_type" | "lot"  (기본: supplier)
period_days: int  (기본: 30, 최대: 365)
Response: DefectStatsResponse
```

### 6.2 출하/물류 (`/api/v1/shipments/`)

| Method | Path | Auth | 설명 |
|--------|------|------|------|
| GET | `/` | 로그인 | 출하 목록 (status, customer_id, date_from, date_to 필터, 페이지네이션) |
| POST | `/` | production_manager+ | 출하 등록 + LOT 묶음 + shipment_number 자동 생성 |
| GET | `/{id}` | 로그인 | 출하 상세 + 포함 LOT 목록 |
| PATCH | `/{id}/status` | production_manager+ | 상태 전환 (shipped/delivered/cancelled) |
| POST | `/{id}/lots` | production_manager+ | 출하에 LOT 추가 (status=pending일 때만) |
| GET | `/pending` | 로그인 | 출하 대기 목록 (대시보드 연동용, 페이지네이션 없음) |

**POST `/` 요청/응답**:

```
Request:
  {
    "customer_id": "uuid",
    "planned_date": "2026-05-10",
    "notes": "긴급 출하",
    "lots": [
      {"lot_id": "uuid", "qty": 100, "unit_price": 50000}
    ]
  }

Response 201:
  ShipmentRead (lots 포함)
  + 사이드 이펙트: lot.status → shipped (lot.status=completed일 때)
```

**PATCH `/{id}/status` 요청/응답**:

```
Request: {"status": "delivered", "notes": "인수 확인"}
Response 200: ShipmentRead
+ 사이드 이펙트(delivered): 포함 lot.status → delivered
```

### 6.3 AI Agent (`/api/v1/ai-agent/`)

| Method | Path | Auth | 설명 |
|--------|------|------|------|
| POST | `/inbound` | 로그인 | 입고 AI Agent 질의 (동기 응답, Celery 내부 처리) |
| POST | `/outbound` | 로그인 | 출하 AI Agent 질의 + risk_level 반환 |
| GET | `/conversations` | 로그인 | 현재 사용자 대화 목록 (agent_type 필터, 최근 20개) |
| GET | `/conversations/{id}/messages` | 로그인 | 특정 대화의 메시지 목록 |

**POST `/inbound` 요청/응답**:

```
Request:
  {
    "query": "현대철강 SUS304 2T 100장 입고 예정인데 품질 이슈 있을까?",
    "conversation_id": null
  }

Response 200:
  {
    "conversation_id": "uuid",
    "message_id": "uuid",
    "content": "현대철강 SUS304 2T 최근 6개월 불량률은 1.2%로 GREEN 등급입니다...",
    "risk_level": null,
    "sources": [{"lot_id": "...", "date": "...", "similarity": 0.92}],
    "latency_ms": 4500,
    "tokens_used": 856
  }
```

**POST `/outbound` 요청/응답**:

```
Request:
  {
    "query": "삼성전자 100EA 출하 예정, LOT-2026-0012 포함, 품질 확인 필요",
    "conversation_id": null
  }

Response 200:
  {
    "conversation_id": "uuid",
    "message_id": "uuid",
    "content": "LOT-2026-0012 최종 검사 통과(불량률 0.5%). 출하 권장합니다.",
    "risk_level": "GREEN",
    "sources": [...],
    "latency_ms": 7200,
    "tokens_used": 1024
  }
```

---

## 7. 라우터 구현 패턴

모든 신규 라우터는 Sprint 2에서 확립된 패턴 준수:

```python
# backend/app/api/v1/quality.py

from app.api.deps import CurrentUser, DBSession, require_roles
from app.services.quality_service import QualityService

router = APIRouter(tags=["Quality"])
_require_inspector = require_roles("admin", "quality_inspector", "production_manager")

@router.post("/", response_model=QualityInspectionRead, status_code=201,
             dependencies=[_require_inspector])
async def create_inspection(
    body: QualityInspectionCreate,
    db: DBSession,                  # Annotated Depends — default 없음
    current_user: CurrentUser,
):
    svc = QualityService(db)
    return await svc.create_inspection(data=body, inspector_id=current_user.id)
```

**필수 체크리스트** (Sprint 2 Depends() 버그 재발 방지):
- [ ] `db: DBSession` — `= None`, `= Depends()` default 절대 금지
- [ ] `current_user: CurrentUser` — 동일 원칙
- [ ] Service 로직은 라우터 내부에 직접 작성 금지 → Service 클래스에 위임

---

## 8. Frontend 설계

### 8.1 신규/수정 페이지

#### `(dashboard)/ai-agent/page.tsx` (stub → 전체 구현)

```
레이아웃:
  ┌──────────────────────────────────────┐
  │ [입고 Agent] [출하 Agent]  탭 전환    │
  ├──────────────────────────────────────┤
  │                                      │
  │  ChatBubble (assistant, ...sources)  │
  │  ChatBubble (user)                   │
  │  ChatBubble (assistant, risk=GREEN)  │
  │                                      │
  ├──────────────────────────────────────┤
  │ [질의 입력창]             [전송]      │
  └──────────────────────────────────────┘

상태:
  - messages: MessageRead[]
  - conversationId: string | null
  - agentType: 'inbound' | 'outbound'
  - isLoading: boolean

API 호출:
  POST /api/v1/ai-agent/{agentType}
  GET  /api/v1/ai-agent/conversations/{id}/messages (초기 로드)
```

#### `(dashboard)/logistics/page.tsx` (stub → 구현)

```
레이아웃:
  PageHeader + [출하 등록] 버튼
  필터: status select + 고객사 검색
  DataTable<ShipmentRead>
    columns: 출하번호, 고객사, 상태, 계획일, LOT수, 액션
  CreateShipmentDialog (inline form)

CreateShipmentDialog:
  - 고객사 Select (useCustomers hook)
  - 계획 출하일 date picker
  - LOT 추가 섹션 (동적 row: LOT select + qty input)
  - 등록 → POST /api/v1/shipments/
```

#### `(dashboard)/inventory/page.tsx` — 품질 탭 추가

기존 입고 현황 페이지에 탭 추가:

```
[입고 현황] [품질 검사]

품질 검사 탭:
  - 상단: 불량률 통계 카드 (공급업체별)
  - DataTable<QualityInspectionRead>
    columns: LOT, 검사유형, 결과, 불량률, 검사일, 담당자
  - [품질 검사 등록] 버튼 → CreateInspectionDialog
```

#### `(dashboard)/page.tsx` — 실집계 2항목 교체

```typescript
// 기존 더미 → 실집계 연동
defect_rate:       useDashboardSummary().data.defect_rate   // quality_inspections 기반
pending_shipments: useDashboardSummary().data.pending_shipments  // shipments 기반
```

`dashboard_service.py`의 `get_defect_rate()`, `get_pending_shipments()` 호출로 교체.

### 8.2 신규 UI 컴포넌트

#### `components/ui/chat-bubble.tsx`

```typescript
interface ChatBubbleProps {
  role: 'user' | 'assistant'
  content: string
  riskLevel?: 'GREEN' | 'YELLOW' | 'RED' | null
  sources?: Array<{ lot_id: string; similarity: number; date: string }>
  isLoading?: boolean   // 스켈레톤 애니메이션
  createdAt?: string
}
```

레이아웃: user(오른쪽 정렬, 파란 배경), assistant(왼쪽 정렬, 회색 배경 + RiskBadge)

#### `components/ui/risk-badge.tsx`

```typescript
interface RiskBadgeProps {
  level: 'GREEN' | 'YELLOW' | 'RED'
  showLabel?: boolean
}
// GREEN → bg-green-100 text-green-800
// YELLOW → bg-yellow-100 text-yellow-800
// RED → bg-red-100 text-red-800
```

### 8.3 신규 React Query Hooks

```
lib/hooks/use-quality.ts
  useQualityInspections(filters?)  → GET /api/v1/quality/
  useCreateInspection()            → POST /api/v1/quality/
  useDefectStats(params)           → GET /api/v1/quality/stats
  useLotInspections(lotId)         → GET /api/v1/quality/lot/{lot_id}

lib/hooks/use-shipments.ts
  useShipments(filters?)           → GET /api/v1/shipments/
  useCreateShipment()              → POST /api/v1/shipments/
  useUpdateShipmentStatus()        → PATCH /api/v1/shipments/{id}/status
  usePendingShipments()            → GET /api/v1/shipments/pending

lib/hooks/use-ai-agent.ts
  useQueryAgent(agentType)         → POST /api/v1/ai-agent/{type}
  useConversations()               → GET /api/v1/ai-agent/conversations
  useConversationMessages(id)      → GET /api/v1/ai-agent/conversations/{id}/messages
```

---

## 9. 라우터 등록 (`router.py`)

```python
# backend/app/api/v1/router.py — 추가 항목

from app.api.v1 import quality, shipments, ai_agent

router.include_router(quality.router,    prefix="/quality",    tags=["Quality"])
router.include_router(shipments.router,  prefix="/shipments",  tags=["Shipments"])
router.include_router(ai_agent.router,   prefix="/ai-agent",   tags=["AI Agent"])
```

---

## 10. SQLAlchemy 모델 설계

### 10.1 `models/quality.py`

```python
class QualityInspection(Base):
    __tablename__ = "quality_inspections"
    id              = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    lot_id          = mapped_column(UUID(as_uuid=True), ForeignKey("lots.id"), nullable=False)
    inspector_id    = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    inspection_type = mapped_column(String(20), nullable=False)
    result          = mapped_column(String(20), nullable=False)
    defect_rate     = mapped_column(Numeric(5,2), nullable=False, default=0)
    inspection_date = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())
    notes           = mapped_column(Text, nullable=True)
    created_at      = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())

    lot             = relationship("Lot", back_populates="quality_inspections")
    inspector       = relationship("User")
    defects         = relationship("DefectDetail", back_populates="inspection", cascade="all, delete-orphan")

class DefectDetail(Base):
    __tablename__ = "defect_details"
    id              = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    inspection_id   = mapped_column(UUID(as_uuid=True), ForeignKey("quality_inspections.id"), nullable=False)
    defect_code     = mapped_column(String(30), nullable=False)
    defect_type     = mapped_column(String(20), nullable=False)
    qty             = mapped_column(Numeric(12,3), nullable=False, default=1)
    description     = mapped_column(Text, nullable=True)
    root_cause      = mapped_column(Text, nullable=True)
    created_at      = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())

    inspection      = relationship("QualityInspection", back_populates="defects")
```

### 10.2 `models/shipment.py`

```python
class Shipment(Base):
    __tablename__ = "shipments"
    id               = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    shipment_number  = mapped_column(String(30), nullable=False, unique=True)
    customer_id      = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    status           = mapped_column(String(20), nullable=False, default="pending")
    planned_date     = mapped_column(Date, nullable=True)
    shipped_date     = mapped_column(TIMESTAMPTZ, nullable=True)
    delivered_date   = mapped_column(TIMESTAMPTZ, nullable=True)
    notes            = mapped_column(Text, nullable=True)
    created_by       = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at       = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())
    updated_at       = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now(), onupdate=func.now())

    customer         = relationship("Customer")
    lots             = relationship("ShipmentLot", back_populates="shipment", cascade="all, delete-orphan")

class ShipmentLot(Base):
    __tablename__ = "shipment_lots"
    id              = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    shipment_id     = mapped_column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False)
    lot_id          = mapped_column(UUID(as_uuid=True), ForeignKey("lots.id"), nullable=False)
    qty             = mapped_column(Numeric(12,3), nullable=False)
    unit_price      = mapped_column(Numeric(15,2), nullable=True)
    created_at      = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())

    shipment        = relationship("Shipment", back_populates="lots")
    lot             = relationship("Lot")
```

### 10.3 `models/ai_agent.py`

```python
class AIConversation(Base):
    __tablename__ = "ai_conversations"
    id           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_type   = mapped_column(String(20), nullable=False)
    user_id      = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title        = mapped_column(String(200), nullable=True)
    created_at   = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())
    updated_at   = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now(), onupdate=func.now())

    user         = relationship("User")
    messages     = relationship("AIMessage", back_populates="conversation", order_by="AIMessage.created_at")

class AIMessage(Base):
    __tablename__ = "ai_messages"
    id               = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id  = mapped_column(UUID(as_uuid=True), ForeignKey("ai_conversations.id"), nullable=False)
    role             = mapped_column(String(20), nullable=False)
    content          = mapped_column(Text, nullable=False)
    metadata         = mapped_column(JSONB, nullable=True)
    tokens_used      = mapped_column(Integer, nullable=True)
    latency_ms       = mapped_column(Integer, nullable=True)
    created_at       = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())

    conversation     = relationship("AIConversation", back_populates="messages")
```

---

## 11. Lot 모델 확장

`models/lot.py`의 `lot_status_enum` 및 전환 규칙 업데이트:

```python
# 기존 상태 + 신규 3개
LOT_STATUS_ENUM = (
    'created', 'in_receipt', 'received',
    'in_process', 'rejected',          # NEW: rejected
    'completed',
    'shipped', 'delivered'             # NEW: shipped, delivered
)

LOT_STATUS_TRANSITIONS: dict[str, list[str]] = {
    'created':    ['in_receipt'],
    'in_receipt': ['received'],
    'received':   ['in_process'],
    'in_process': ['completed', 'rejected'],    # rejected 추가
    'rejected':   [],                           # 종료 상태
    'completed':  ['shipped'],                  # shipped 추가
    'shipped':    ['delivered'],                # NEW
    'delivered':  [],                           # 종료 상태
}
```

---

## 12. 구현 순서 (Implementation Order)

```
Day 1 — Service Layer 추출
  1. backend/app/services/__init__.py
  2. work_order_service.py (work_orders.py 인라인 로직 이동)
  3. dashboard_service.py (dashboard.py 인라인 로직 이동)
  4. work_orders.py, dashboard.py → service 위임으로 교체

Day 2 — DB 모델 + 마이그레이션
  5. models/quality.py, models/shipment.py, models/ai_agent.py
  6. models/__init__.py 업데이트
  7. models/lot.py 상태 확장 (rejected, shipped, delivered)
  8. alembic/versions/0005_quality_shipment.py
  9. alembic/versions/0006_ai_agent.py

Day 3 — 품질 검사 백엔드
  10. schemas/quality.py
  11. services/quality_service.py
  12. api/v1/quality.py (6 endpoints)
  13. api/v1/router.py — quality 등록

Day 4 — 출하/물류 백엔드
  14. schemas/shipment.py
  15. services/shipment_service.py
  16. api/v1/shipments.py (6 endpoints)
  17. api/v1/router.py — shipments 등록

Day 5 — AI Agent 인프라
  18. core/qdrant_init.py
  19. core/celery_app.py
  20. docker-compose.yml — celery-worker 추가
  21. requirements.txt — langchain, qdrant-client, fastembed, celery 추가

Day 6 — 입고 AI Agent
  22. schemas/ai_agent.py
  23. services/ai_agent_service.py (inbound agent + tools)
  24. api/v1/ai_agent.py (POST /inbound + GET /conversations)
  25. api/v1/router.py — ai-agent 등록

Day 7 — 출하 AI Agent
  26. services/ai_agent_service.py (outbound agent + risk 산출)
  27. api/v1/ai_agent.py (POST /outbound + GET messages)

Day 8 — AI 채팅 UI
  28. components/ui/chat-bubble.tsx
  29. components/ui/risk-badge.tsx
  30. lib/hooks/use-ai-agent.ts
  31. app/(dashboard)/ai-agent/page.tsx

Day 9 — 출하/품질 프론트엔드
  32. lib/hooks/use-quality.ts
  33. lib/hooks/use-shipments.ts
  34. app/(dashboard)/logistics/page.tsx
  35. app/(dashboard)/inventory/page.tsx — 품질 탭 추가

Day 10 — 대시보드 실집계 완성
  36. app/(dashboard)/page.tsx — defect_rate, pending_shipments 실집계 교체
  37. 전체 E2E 확인: LOT 입고 → 공정 → 품질검사 → 출하 시나리오
```

---

## 13. 완료 기준 (Gap Detector 체크리스트)

| 항목 | 기준 | 파일 |
|------|------|------|
| Service Layer 5개 파일 | 존재 + 클래스 구현 | `backend/app/services/*.py` |
| Alembic 0005 마이그레이션 | 4개 테이블 upgrade/downgrade | `alembic/versions/0005_*.py` |
| Alembic 0006 마이그레이션 | 2개 테이블 + enum | `alembic/versions/0006_*.py` |
| 품질 API 6개 | router 등록 + 엔드포인트 존재 | `api/v1/quality.py` |
| 출하 API 6개 | router 등록 + 엔드포인트 존재 | `api/v1/shipments.py` |
| AI Agent API 4개 | router 등록 + 엔드포인트 존재 | `api/v1/ai_agent.py` |
| LOT 상태 확장 (rejected/shipped/delivered) | `LOT_STATUS_TRANSITIONS` 업데이트 | `models/lot.py` |
| quality_service LOT 자동 전환 | fail → lot.status=rejected 로직 | `services/quality_service.py` |
| shipment_service LOT 자동 전환 | create → shipped, delivered → delivered | `services/shipment_service.py` |
| ai_agent_service | LangChain Agent + 3개 tools | `services/ai_agent_service.py` |
| Qdrant 초기화 | 2개 컬렉션 생성 | `core/qdrant_init.py` |
| Celery 설정 | celery_app.py + docker-compose worker | `core/celery_app.py` |
| chat-bubble.tsx | role/riskLevel/sources props | `components/ui/chat-bubble.tsx` |
| risk-badge.tsx | GREEN/YELLOW/RED 3색 | `components/ui/risk-badge.tsx` |
| ai-agent/page.tsx | 채팅 UI + Agent 탭 | `app/(dashboard)/ai-agent/page.tsx` |
| logistics/page.tsx | 출하 목록 + 등록 | `app/(dashboard)/logistics/page.tsx` |
| inventory/page.tsx 품질 탭 | 검사 목록 + 등록 다이얼로그 | `app/(dashboard)/inventory/page.tsx` |
| 대시보드 실집계 | defect_rate + pending_shipments 더미 0% | `app/(dashboard)/page.tsx` |
| React Query Hooks (3파일) | use-quality, use-shipments, use-ai-agent | `lib/hooks/` |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-04 | Initial design (Sprint 3 AI Agent) | Enterprise Expert Agent |
