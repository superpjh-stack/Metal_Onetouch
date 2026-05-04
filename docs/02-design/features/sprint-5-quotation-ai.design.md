# Sprint 5 — 수주견적 AI 기반 구축 Design

> **Feature**: sprint-5-quotation-ai  
> **Phase**: Design  
> **Date**: 2026-05-04  
> **Status**: Draft  
> **Depends on**: sprint-4-inbound-kpi (완료, Match Rate 95%)

---

## 1. 개요

Sprint 5는 Phase 3 진입 스프린트로 5개 도메인을 구현합니다:

1. **MinIO 파일 스토리지 인프라** — presigned URL 업로드/다운로드, 파일 메타 DB
2. **CAD 도면 분석 (GPT-4o Vision)** — PDF/이미지 업로드 → 객체 JSON 추출 (Celery 비동기)
3. **단가 마스터 기준정보** — 공정별·재질별 단가표 관리 CRUD
4. **규칙 기반 자동견적 엔진** — 분석 결과 × 단가표 → 견적서 자동 산출 + 수주 연결
5. **Quotation 페이지 완성** — 현재 "개발 예정" 스텁 → 업로드/분석/견적 실동작

---

## 2. DB 스키마 (Migration 0008)

### 2.1 uploaded_files (파일 메타데이터)

```sql
CREATE TABLE uploaded_files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bucket          VARCHAR(100) NOT NULL DEFAULT 'metal-onetouch',
    object_key      VARCHAR(500) NOT NULL UNIQUE,    -- cad-drawings/2026/05/{uuid}.pdf
    original_name   VARCHAR(500) NOT NULL,
    mime_type       VARCHAR(100),
    file_size       BIGINT,
    file_hash       VARCHAR(64),                     -- SHA-256 (중복 업로드 방지)
    uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_uploaded_files_hash    ON uploaded_files(file_hash);
CREATE INDEX ix_uploaded_files_by      ON uploaded_files(uploaded_by);
```

### 2.2 cad_drawings (CAD 도면 분석)

```sql
CREATE TYPE cad_analysis_status_enum AS ENUM (
    'pending',      -- 업로드 완료, 분석 대기
    'analyzing',    -- Celery 태스크 실행 중
    'completed',    -- 분석 완료
    'failed'        -- 분석 실패
);

CREATE TABLE cad_drawings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drawing_number  VARCHAR(30) NOT NULL UNIQUE,     -- DRW-YYYYMMDD-NNNN
    file_id         UUID NOT NULL REFERENCES uploaded_files(id) ON DELETE RESTRICT,
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    analysis_status cad_analysis_status_enum NOT NULL DEFAULT 'pending',
    raw_result      JSONB,                           -- GPT-4o Vision 원본 응답
    parsed_objects  JSONB,                           -- 정제된 객체 목록
    dimensions      JSONB,                           -- {"length": 200.0, "width": 150.0, "thickness": 3.2}
    material_hint   VARCHAR(100),                    -- "SUS304", "SS400" 등 추정 재질
    confidence      NUMERIC(4,3),                    -- 0.000 ~ 1.000
    analyzed_at     TIMESTAMPTZ,
    error_message   TEXT,
    notes           TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_cad_file          ON cad_drawings(file_id);
CREATE INDEX ix_cad_customer      ON cad_drawings(customer_id);
CREATE INDEX ix_cad_status        ON cad_drawings(analysis_status);
CREATE INDEX ix_cad_number        ON cad_drawings(drawing_number);
```

**채번 규칙**: `DRW-{YYYYMMDD}-{당일 SEQ 4자리}` (기존 패턴 동일)

**parsed_objects JSON 구조**:
```json
{
  "objects": [
    {"type": "hole",  "diameter": 12.5, "count": 4, "tolerance": "H7"},
    {"type": "slot",  "width": 8.0, "length": 50.0, "count": 2},
    {"type": "bend",  "angle": 90, "radius": 3.0, "count": 1},
    {"type": "cut",   "length": 800.0}
  ],
  "dimensions": {"length": 200.0, "width": 150.0, "thickness": 3.2},
  "material_hint": "SUS304",
  "confidence": 0.91
}
```

### 2.3 process_price_master (공정 단가 마스터)

```sql
CREATE TABLE process_price_master (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    process_type    VARCHAR(50)  NOT NULL,   -- cutting/drilling/bending/welding/painting/surface
    material_grade  VARCHAR(50),             -- SUS304/SS400/AL6061/NULL(공통)
    unit_price      NUMERIC(14,4) NOT NULL,
    price_unit      VARCHAR(30)  NOT NULL,   -- per_mm/per_piece/per_count/per_sqm
    effective_from  DATE NOT NULL DEFAULT CURRENT_DATE,
    notes           TEXT,
    updated_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX ix_price_process_material ON process_price_master(process_type, COALESCE(material_grade, ''));
CREATE INDEX ix_price_process_type ON process_price_master(process_type);
```

**시드 데이터** (Migration 0008에 포함):
| process_type | material_grade | unit_price | price_unit |
|---|---|---|---|
| cutting | NULL | 5.0 | per_mm |
| drilling | NULL | 800.0 | per_piece |
| bending | NULL | 1500.0 | per_count |
| welding | NULL | 8.0 | per_mm |
| painting | NULL | 2000.0 | per_sqm |
| surface | SUS304 | 3500.0 | per_sqm |

### 2.4 material_price_master (재질 단가 마스터)

```sql
CREATE TABLE material_price_master (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_code   VARCHAR(50)  NOT NULL UNIQUE,  -- SUS304_2T, SS400_3T, AL6061_1T
    material_name   VARCHAR(200) NOT NULL,
    price_per_kg    NUMERIC(12,4) NOT NULL,         -- 원/kg
    density         NUMERIC(8,4) NOT NULL DEFAULT 7.93,  -- g/cm³ (SUS304 기본)
    notes           TEXT,
    updated_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**시드 데이터**:
| material_code | material_name | price_per_kg | density |
|---|---|---|---|
| SUS304 | SUS304 스테인리스 | 4500 | 7.93 |
| SUS316 | SUS316 스테인리스 | 6000 | 8.00 |
| SS400 | SS400 일반 구조용 강 | 1200 | 7.85 |
| AL6061 | 알루미늄 합금 6061 | 8000 | 2.70 |
| SPCC | SPCC 냉간 압연 강판 | 1500 | 7.85 |

### 2.5 quotations (견적서)

```sql
CREATE TYPE quotation_status_enum AS ENUM (
    'draft',       -- 작성 중
    'submitted',   -- 고객 제출
    'accepted',    -- 수주 확정
    'rejected',    -- 거절됨
    'expired'      -- 유효기간 만료
);

CREATE TABLE quotations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quotation_number  VARCHAR(30)  NOT NULL UNIQUE,   -- QUO-YYYYMMDD-NNNN
    customer_id       UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    drawing_id        UUID REFERENCES cad_drawings(id) ON DELETE SET NULL,
    order_id          UUID REFERENCES orders(id) ON DELETE SET NULL,    -- 수주 연결 후
    status            quotation_status_enum NOT NULL DEFAULT 'draft',
    material_cost     NUMERIC(16,2) NOT NULL DEFAULT 0,
    process_cost      NUMERIC(16,2) NOT NULL DEFAULT 0,
    total_amount      NUMERIC(16,2) NOT NULL DEFAULT 0,
    margin_rate       NUMERIC(5,3) NOT NULL DEFAULT 0.15,               -- 기본 이윤율 15%
    final_amount      NUMERIC(16,2) NOT NULL DEFAULT 0,                 -- total × (1+margin)
    valid_until       DATE,
    notes             TEXT,
    version           INTEGER NOT NULL DEFAULT 1,
    created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_quotation_customer  ON quotations(customer_id);
CREATE INDEX ix_quotation_drawing   ON quotations(drawing_id);
CREATE INDEX ix_quotation_order     ON quotations(order_id);
CREATE INDEX ix_quotation_status    ON quotations(status);
CREATE INDEX ix_quotation_number    ON quotations(quotation_number);
```

### 2.6 quotation_items (견적 항목 breakdown)

```sql
CREATE TABLE quotation_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quotation_id    UUID NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
    item_type       VARCHAR(50) NOT NULL,    -- material/cutting/drilling/bending/welding/painting/etc
    description     VARCHAR(500),
    quantity        NUMERIC(14,4) NOT NULL DEFAULT 1,
    unit            VARCHAR(20),
    unit_price      NUMERIC(14,4) NOT NULL DEFAULT 0,
    amount          NUMERIC(16,2) NOT NULL DEFAULT 0,
    sort_order      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX ix_quotation_items_qid ON quotation_items(quotation_id);
```

---

## 3. 서비스 레이어 설계

### 3.1 StorageService (`backend/app/core/storage.py`)

```python
from minio import Minio
from app.core.config import settings

class StorageService:
    def __init__(self):
        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )

    def get_presigned_upload_url(
        self, bucket: str, object_key: str, expires_seconds: int = 3600
    ) -> str:
        from datetime import timedelta
        return self._client.presigned_put_object(
            bucket, object_key, expires=timedelta(seconds=expires_seconds)
        )

    def get_presigned_download_url(
        self, bucket: str, object_key: str, expires_seconds: int = 3600
    ) -> str:
        from datetime import timedelta
        return self._client.presigned_get_object(
            bucket, object_key, expires=timedelta(seconds=expires_seconds)
        )

    def ensure_bucket(self, bucket: str) -> None:
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    def delete_object(self, bucket: str, object_key: str) -> None:
        self._client.remove_object(bucket, object_key)

storage_service = StorageService()  # 싱글톤
```

### 3.2 FileService (`backend/app/services/file_service.py`)

```python
class FileService:
    def __init__(self, db: AsyncSession): ...

    async def create_presigned_upload(
        self, original_name: str, mime_type: str, folder: str, current_user: User
    ) -> PresignedUploadResponse:
        # 1. object_key = f"{folder}/{datetime.now():%Y/%m}/{uuid4()}.{ext}"
        # 2. presigned_url = storage_service.get_presigned_upload_url(bucket, object_key)
        # 3. uploaded_files INSERT (file_size=None, file_hash=None — confirm 전)
        # 4. return {file_id, presigned_url, object_key, expires_in}

    async def confirm_upload(
        self, file_id: UUID, file_size: int, file_hash: str
    ) -> UploadedFileRead:
        # 1. uploaded_files UPDATE (file_size, file_hash)
        # 2. 중복 hash 검사 — 이미 존재하면 해당 file_id 반환 (중복 방지)

    async def get_download_url(self, file_id: UUID) -> str:
        # 1. uploaded_files 조회 (bucket, object_key)
        # 2. presigned download URL 발급 (1시간)
```

### 3.3 CadAnalysisService (`backend/app/services/cad_analysis_service.py`)

```python
class CadAnalysisService:
    def __init__(self, db: AsyncSession): ...

    async def create_drawing(
        self, file_id: UUID, customer_id: UUID | None, current_user: User
    ) -> CadDrawingRead:
        # 1. DRW-{YYYYMMDD}-{seq:04d} 채번
        # 2. cad_drawings INSERT (status='pending')
        # 3. Celery 태스크 enqueue: analyze_cad_drawing.delay(str(drawing.id))
        # 4. return CadDrawingRead

    async def get_drawing(self, drawing_id: UUID) -> CadDrawingRead: ...

    async def update_objects(
        self, drawing_id: UUID, objects: list[dict], dimensions: dict
    ) -> CadDrawingRead:
        # 수동 수정 (Active Learning 데이터 수집)
        # parsed_objects UPDATE, confidence = 1.0 (사람이 검증)

    @staticmethod
    async def run_analysis(drawing_id: str) -> None:
        """Celery 태스크에서 호출 — DB 세션 별도 생성"""
        # 1. cad_drawings.status = 'analyzing'
        # 2. MinIO presigned URL 생성
        # 3. URL로 이미지 다운로드 (또는 base64 인코딩)
        # 4. OpenAI GPT-4o Vision API 호출
        # 5. 응답 파싱 → parsed_objects, dimensions, material_hint, confidence
        # 6. cad_drawings UPDATE (status='completed', parsed_objects, ...)
        # 실패 시: status='failed', error_message=str(e)
```

**GPT-4o Vision 프롬프트 구조**:
```python
SYSTEM_PROMPT = """
당신은 금속 가공 제조 CAD 도면 분석 전문가입니다.
도면에서 다음 항목을 정확히 추출하여 JSON으로 반환하세요:

응답 형식 (JSON만 반환, 설명 없음):
{
  "objects": [
    {"type": "hole|slot|bend|cut|weld", "diameter"?: float, "width"?: float,
     "length"?: float, "angle"?: float, "radius"?: float, "count": int, "tolerance"?: string}
  ],
  "dimensions": {"length": float, "width": float, "thickness": float},
  "material_hint": "SUS304|SUS316|SS400|AL6061|SPCC|unknown",
  "confidence": float  // 0.0~1.0, 추출 신뢰도
}
"""
```

### 3.4 QuotationService (`backend/app/services/quotation_service.py`)

```python
class QuotationService:
    def __init__(self, db: AsyncSession): ...

    async def calculate_from_drawing(
        self,
        drawing_id: UUID,
        customer_id: UUID,
        material_code: str,
        margin_rate: float,
        current_user: User,
    ) -> QuotationRead:
        # 1. cad_drawings.parsed_objects + dimensions 조회
        # 2. _calc_material_cost(dimensions, material_code)
        # 3. _calc_process_items(objects, material_grade_from_code)
        # 4. QUO-{YYYYMMDD}-{seq} 채번
        # 5. quotations INSERT
        # 6. quotation_items 일괄 INSERT (material + 공정별)
        # 7. 합계 재계산 → quotations.material_cost, process_cost, total_amount, final_amount UPDATE

    async def create_manual(self, data: QuotationCreate, current_user: User) -> QuotationRead:
        # 수동 견적 생성 (도면 없이 직접 항목 입력)

    async def update_items(
        self, quotation_id: UUID, items: list[QuotationItemUpdate]
    ) -> QuotationRead:
        # 항목 단가 수동 조정 → 합계 재계산

    async def submit(self, quotation_id: UUID) -> QuotationRead:
        # status: draft → submitted

    async def link_order(self, quotation_id: UUID, order_id: UUID) -> QuotationRead:
        # quotations.order_id = order_id
        # quotations.status = 'accepted'
        # orders.status → confirmed (optional, 수주 측 상태 변경)

    # ── 원가 계산 내부 메서드 ──────────────────────────────────────────────

    async def _calc_material_cost(
        self, dimensions: dict, material_code: str
    ) -> tuple[Decimal, QuotationItemCreate]:
        # material_price_master 조회 (price_per_kg, density)
        # 체적(cm³) = length × width × thickness / 1000  (mm → cm)
        # 무게(kg) = 체적 × density / 1000  (g/cm³ → kg/cm³)
        # 재료비 = 무게 × price_per_kg

    async def _calc_process_items(
        self, objects: list[dict], material_grade: str
    ) -> list[QuotationItemCreate]:
        # process_price_master 조회 (material_grade 우선, 없으면 NULL 공통)
        items = []
        for obj in objects:
            if obj["type"] == "cut":
                # amount = obj.length × cutting_unit_price × obj.count
            elif obj["type"] == "hole":
                # 직경 보정: diameter_factor = sqrt(diameter / 10.0)
                # amount = obj.count × hole_unit_price × diameter_factor
            elif obj["type"] == "bend":
                # 각도 보정: angle_factor = angle / 90.0
                # amount = obj.count × bending_unit_price × angle_factor
            elif obj["type"] == "weld":
                # amount = obj.length × welding_unit_price × obj.count
        return items
```

### 3.5 Celery 태스크 (`backend/app/tasks/cad_tasks.py`)

```python
from app.core.celery_app import celery_app

@celery_app.task(
    name="analyze_cad_drawing",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def analyze_cad_drawing_task(self, drawing_id: str) -> None:
    """비동기 CAD 분석 태스크 — Celery Worker에서 실행"""
    import asyncio
    from app.services.cad_analysis_service import CadAnalysisService
    try:
        asyncio.run(CadAnalysisService.run_analysis(drawing_id))
    except Exception as exc:
        raise self.retry(exc=exc)
```

---

## 4. API 엔드포인트 설계

### 4.1 파일 스토리지 (`/api/v1/files`)

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `POST` | `/presigned-upload` | presigned 업로드 URL 발급 | 로그인 |
| `POST` | `/confirm-upload` | 업로드 완료 확인 (size, hash) | 로그인 |
| `GET` | `/{file_id}/download-url` | presigned 다운로드 URL 발급 | 로그인 |

**`POST /presigned-upload` 요청/응답**:
```json
// Request
{"original_name": "bracket_v2.pdf", "mime_type": "application/pdf", "folder": "cad-drawings"}

// Response
{
  "file_id": "uuid",
  "presigned_url": "http://minio:9000/metal-onetouch/cad-drawings/...",
  "object_key": "cad-drawings/2026/05/{uuid}.pdf",
  "expires_in": 3600
}
```

### 4.2 CAD 분석 (`/api/v1/cad`)

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `POST` | `/` | 도면 등록 + 분석 시작 | 로그인 |
| `GET` | `/` | 목록 (status/customer 필터, 페이징) | 로그인 |
| `GET` | `/{id}` | 상세 (분석 결과 포함) | 로그인 |
| `GET` | `/{id}/status` | 분석 상태 폴링 | 로그인 |
| `PATCH` | `/{id}/objects` | 수동 수정 (Active Learning) | 로그인 |

### 4.3 견적 (`/api/v1/quotations`)

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `POST` | `/` | 견적 생성 (drawing_id 자동 산출 or 수동) | 로그인 |
| `GET` | `/` | 목록 (status/customer 필터, 페이징) | 로그인 |
| `GET` | `/{id}` | 상세 (items + drawing 포함) | 로그인 |
| `PATCH` | `/{id}/items` | 항목 단가 수동 조정 | 로그인 |
| `POST` | `/{id}/submit` | 고객 제출 (draft→submitted) | 로그인 |
| `POST` | `/{id}/link-order` | 수주 연결 (accepted) | manager |
| `GET` | `/{id}/similar` | 유사 견적 검색 (top-5) | 로그인 |

### 4.4 단가 마스터 (`/api/v1/master/price-master`)

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| `GET` | `/process` | 공정 단가 목록 | 로그인 |
| `PUT` | `/process` | 일괄 업데이트 | admin |
| `GET` | `/material` | 재질 단가 목록 | 로그인 |
| `PUT` | `/material` | 재질 단가 업데이트 | admin |

**Router 등록** (`backend/app/api/v1/router.py`):
```python
from app.api.v1 import files, cad, quotations
from app.api.v1.master import price_master

api_v1_router.include_router(files.router,       prefix="/files",       tags=["Files"])
api_v1_router.include_router(cad.router,          prefix="/cad",         tags=["CAD"])
api_v1_router.include_router(quotations.router,   prefix="/quotations",  tags=["Quotations"])
api_v1_router.include_router(price_master.router, prefix="/master/price-master", tags=["Master"])
```

---

## 5. Pydantic 스키마 설계

### 5.1 파일 스키마 (`backend/app/schemas/file.py`)

```python
class PresignedUploadRequest(BaseModel):
    original_name: str
    mime_type: str
    folder: str = "cad-drawings"

class PresignedUploadResponse(BaseModel):
    file_id: UUID
    presigned_url: str
    object_key: str
    expires_in: int

class ConfirmUploadRequest(BaseModel):
    file_id: UUID
    file_size: int
    file_hash: str  # SHA-256 hex

class UploadedFileRead(BaseModel):
    id: UUID
    original_name: str
    mime_type: str | None
    file_size: int | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

### 5.2 CAD 스키마 (`backend/app/schemas/cad.py`)

```python
class CadDrawingCreate(BaseModel):
    file_id: UUID
    customer_id: UUID | None = None

class CadObjectItem(BaseModel):
    type: str       # hole/slot/bend/cut/weld
    count: int = 1
    diameter: float | None = None
    width: float | None = None
    length: float | None = None
    angle: float | None = None
    radius: float | None = None
    tolerance: str | None = None

class CadDimensions(BaseModel):
    length: float
    width: float
    thickness: float

class CadParsedResult(BaseModel):
    objects: list[CadObjectItem]
    dimensions: CadDimensions
    material_hint: str | None = None
    confidence: float = 0.0

class CadDrawingRead(BaseModel):
    id: UUID
    drawing_number: str
    file_id: UUID
    customer_id: UUID | None
    analysis_status: str
    parsed_objects: CadParsedResult | None
    dimensions: CadDimensions | None
    material_hint: str | None
    confidence: float | None
    analyzed_at: datetime | None
    error_message: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CadUpdateObjects(BaseModel):
    objects: list[CadObjectItem]
    dimensions: CadDimensions
```

### 5.3 견적 스키마 (`backend/app/schemas/quotation.py`)

```python
class QuotationItemRead(BaseModel):
    id: UUID
    item_type: str
    description: str | None
    quantity: Decimal
    unit: str | None
    unit_price: Decimal
    amount: Decimal
    sort_order: int
    model_config = ConfigDict(from_attributes=True)

class QuotationCreate(BaseModel):
    customer_id: UUID
    drawing_id: UUID | None = None       # None이면 수동 견적
    material_code: str | None = None     # 자동 산출 시 필수
    margin_rate: float = 0.15
    notes: str | None = None

class QuotationRead(BaseModel):
    id: UUID
    quotation_number: str
    customer_id: UUID
    customer_name: str | None            # JOIN 역정규화
    drawing_id: UUID | None
    order_id: UUID | None
    status: str
    material_cost: Decimal
    process_cost: Decimal
    total_amount: Decimal
    margin_rate: Decimal
    final_amount: Decimal
    valid_until: date | None
    version: int
    items: list[QuotationItemRead]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class QuotationItemUpdate(BaseModel):
    id: UUID
    unit_price: Decimal
    quantity: Decimal | None = None
    description: str | None = None

class QuotationLinkOrder(BaseModel):
    order_id: UUID
```

### 5.4 단가 마스터 스키마 (`backend/app/schemas/price_master.py`)

```python
class ProcessPriceRead(BaseModel):
    id: UUID
    process_type: str
    material_grade: str | None
    unit_price: Decimal
    price_unit: str
    effective_from: date
    model_config = ConfigDict(from_attributes=True)

class ProcessPriceUpsert(BaseModel):
    process_type: str
    material_grade: str | None = None
    unit_price: Decimal
    price_unit: str

class MaterialPriceRead(BaseModel):
    id: UUID
    material_code: str
    material_name: str
    price_per_kg: Decimal
    density: Decimal
    model_config = ConfigDict(from_attributes=True)

class MaterialPriceUpsert(BaseModel):
    material_code: str
    material_name: str
    price_per_kg: Decimal
    density: Decimal = Decimal("7.93")
```

---

## 6. 프론트엔드 설계

### 6.1 페이지 구조 (`quotation/page.tsx`)

```
QuotationPage
├── PageHeader (수주견적 AI, 버튼: 견적 작성)
├── Tabs
│   ├── TabsTrigger "견적 목록"  → QuotationListTab
│   ├── TabsTrigger "도면 분석"  → DrawingAnalysisTab
│   └── TabsTrigger "단가 설정"  → PriceMasterTab (admin만)
└── CreateQuotationDialog (open/onOpenChange)
```

**QuotationListTab**:
- Select (상태 필터: 전체/draft/submitted/accepted/rejected)
- DataTable columns: 견적번호, 고객사, 상태(StatusBadge), 총금액, 도면번호, 수주번호, 작성일
- 행 클릭 → `QuotationDetailDialog`

**DrawingAnalysisTab**:
- `CadUploader` 드래그앤드롭 컴포넌트
- 업로드 중 진행률 바 (XMLHttpRequest presigned PUT)
- 분석 상태 폴링 카드 (`GET /cad/{id}/status`, 5초 간격, completed 시 중지)
- `DrawingResultCard`: 분석 완료 결과 — 객체 목록 테이블 + 치수 요약
- "견적 산출하기" 버튼 → `CreateQuotationDialog` with drawing_id

**PriceMasterTab** (admin):
- 공정 단가 테이블 (인라인 편집)
- 재질 단가 테이블 (인라인 편집)
- "저장" → `PUT /master/price-master/process`

### 6.2 컴포넌트 설계

#### `CadUploader` (`components/quotation/cad-uploader.tsx`)
```tsx
interface CadUploaderProps {
  onUploadComplete: (fileId: string) => void
}
// 1. POST /files/presigned-upload → presigned_url, file_id
// 2. XMLHttpRequest.put(presigned_url, file) — 진행률 tracking
// 3. POST /files/confirm-upload → { file_id, file_size, file_hash }
// 4. onUploadComplete(file_id)
```

#### `useDrawingStatus` 폴링 훅 (`lib/hooks/use-cad.ts`)
```ts
function useDrawingStatus(drawingId: string | null) {
  return useQuery({
    queryKey: ['cad-status', drawingId],
    queryFn: () => apiClient.get(`/api/v1/cad/${drawingId}/status`).then(r => r.data),
    enabled: !!drawingId,
    refetchInterval: (data) =>
      data?.analysis_status === 'completed' || data?.analysis_status === 'failed'
        ? false   // 완료/실패 시 폴링 중지
        : 5000,   // 5초 간격 폴링
  })
}
```

#### `QuotationItemsTable` (`components/quotation/quotation-items-table.tsx`)
- 항목별 행: item_type(한글 레이블), description, quantity, unit, unit_price(편집가능), amount(자동계산)
- 하단 합계 행: 재료비 소계, 공정비 소계, 합계, 이윤율 입력, 최종금액
- "저장" → `PATCH /quotations/{id}/items`

### 6.3 React Query 훅 목록

**`lib/hooks/use-files.ts`**:
```ts
useCreatePresignedUpload()   // POST /files/presigned-upload
useConfirmUpload()           // POST /files/confirm-upload
useDownloadUrl(fileId)       // GET /files/{id}/download-url
```

**`lib/hooks/use-cad.ts`**:
```ts
useCadDrawings(params?)       // GET /cad
useCadDrawing(id)             // GET /cad/{id}
useDrawingStatus(id)          // GET /cad/{id}/status — 폴링
useCreateDrawing()            // POST /cad
useUpdateDrawingObjects()     // PATCH /cad/{id}/objects
```

**`lib/hooks/use-quotations.ts`**:
```ts
useQuotations(params?)        // GET /quotations
useQuotation(id)              // GET /quotations/{id}
useCreateQuotation()          // POST /quotations
useUpdateQuotationItems()     // PATCH /quotations/{id}/items
useSubmitQuotation()          // POST /quotations/{id}/submit
useLinkOrder()                // POST /quotations/{id}/link-order
useSimilarQuotations(id)      // GET /quotations/{id}/similar
```

**`lib/hooks/use-price-master.ts`**:
```ts
useProcessPrices()            // GET /master/price-master/process
useMaterialPrices()           // GET /master/price-master/material
useUpdateProcessPrices()      // PUT /master/price-master/process
useUpdateMaterialPrices()     // PUT /master/price-master/material
```

---

## 7. 환경 변수 및 설정

### 7.1 신규 환경 변수 (`backend/app/core/config.py`)

```python
class Settings(BaseSettings):
    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "metal-onetouch"
    MINIO_USE_SSL: bool = False

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_QUOTATIONS: str = "quotations"
```

### 7.2 docker-compose 추가 서비스

```yaml
# docker-compose.yml에 추가
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"    # Web Console
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
```

### 7.3 신규 Python 패키지

```
# backend/requirements.txt에 추가
minio>=7.2.0
openai>=1.30.0
qdrant-client>=1.9.0
pdf2image>=1.17.0
pillow>=10.3.0
```

---

## 8. 마이그레이션 (0008) 구조

```python
# backend/alembic/versions/0008_quotation_ai.py
revision = "0008"
down_revision = "0007"

def upgrade():
    # 1. CREATE TYPE cad_analysis_status_enum
    # 2. CREATE TYPE quotation_status_enum
    # 3. CREATE TABLE uploaded_files
    # 4. CREATE TABLE cad_drawings (+ indexes)
    # 5. CREATE TABLE process_price_master (+ unique index)
    # 6. CREATE TABLE material_price_master
    # 7. CREATE TABLE quotations (+ indexes)
    # 8. CREATE TABLE quotation_items (+ index)
    # 9. SEED: process_price_master (6 rows)
    # 10. SEED: material_price_master (5 rows)

def downgrade():
    # 역순 DROP (quotation_items → quotations → material_price_master
    #            → process_price_master → cad_drawings → uploaded_files
    #            → DROP TYPE quotation_status_enum → DROP TYPE cad_analysis_status_enum)
```

---

## 9. 파일 구조 (신규/수정 파일)

```
backend/
├── alembic/versions/
│   └── 0008_quotation_ai.py              [신규]
├── app/
│   ├── core/
│   │   ├── config.py                      [수정] MINIO_*, OPENAI_*, QDRANT_* 추가
│   │   └── storage.py                     [신규] StorageService 싱글톤
│   ├── models/
│   │   ├── file.py                        [신규] UploadedFile
│   │   ├── cad.py                         [신규] CadDrawing
│   │   ├── price_master.py                [신규] ProcessPriceMaster, MaterialPriceMaster
│   │   ├── quotation.py                   [신규] Quotation, QuotationItem
│   │   └── __init__.py                    [수정] 4개 모델 추가
│   ├── schemas/
│   │   ├── file.py                        [신규]
│   │   ├── cad.py                         [신규]
│   │   ├── price_master.py                [신규]
│   │   └── quotation.py                   [신규]
│   ├── services/
│   │   ├── file_service.py                [신규]
│   │   ├── cad_analysis_service.py        [신규]
│   │   ├── quotation_service.py           [신규]
│   │   └── price_master_service.py        [신규]
│   ├── tasks/
│   │   └── cad_tasks.py                   [신규] Celery analyze_cad_drawing 태스크
│   └── api/v1/
│       ├── files.py                       [신규]
│       ├── cad.py                         [신규]
│       ├── quotations.py                  [신규]
│       ├── master/
│       │   └── price_master.py            [신규]
│       └── router.py                      [수정] 4개 라우터 등록

frontend/
├── src/
│   ├── app/(dashboard)/
│   │   └── quotation/
│   │       └── page.tsx                   [수정] 스텁 → 실동작 (3탭)
│   ├── components/
│   │   └── quotation/
│   │       ├── cad-uploader.tsx           [신규]
│   │       ├── drawing-analysis-card.tsx  [신규]
│   │       ├── quotation-items-table.tsx  [신규]
│   │       └── quotation-preview.tsx      [신규]
│   └── lib/hooks/
│       ├── use-files.ts                   [신규]
│       ├── use-cad.ts                     [신규]
│       ├── use-quotations.ts              [신규]
│       └── use-price-master.ts            [신규]

docker-compose.yml                         [수정] minio + qdrant 서비스 추가
```

**총 신규/수정 파일**: ~28개

---

## 10. Gap Detector 체크리스트 (28항목)

### DB / Migration
- [ ] 1. Migration 0008 chain: `down_revision = "0007"`
- [ ] 2. `cad_analysis_status_enum` + `quotation_status_enum` PostgreSQL enum 생성
- [ ] 3. `uploaded_files` 테이블 (file_hash 컬럼, ix_uploaded_files_hash 인덱스 포함)
- [ ] 4. `cad_drawings` 테이블 (parsed_objects JSONB, 4개 인덱스)
- [ ] 5. `process_price_master` — unique index on (process_type, COALESCE(material_grade,''))
- [ ] 6. `material_price_master` — material_code UNIQUE
- [ ] 7. `quotations` 테이블 — drawing_id SET NULL, order_id SET NULL, 5개 인덱스
- [ ] 8. `quotation_items` — quotation_id CASCADE DELETE
- [ ] 9. 시드 데이터: process_price_master 6개 + material_price_master 5개

### Backend Models
- [ ] 10. `UploadedFile` 모델 (file_hash 컬럼)
- [ ] 11. `CadDrawing` 모델 (analysis_status Enum, parsed_objects JSONB)
- [ ] 12. `Quotation` 모델 (margin_rate 기본값 0.15, final_amount 컬럼)
- [ ] 13. `QuotationItem` 모델 (sort_order 컬럼)
- [ ] 14. 4개 모델 `app/models/__init__.py` + `__all__` 등록

### Backend Services
- [ ] 15. `StorageService.get_presigned_upload_url()` MinIO SDK 호출
- [ ] 16. `FileService.confirm_upload()` — file_hash 중복 검사 포함
- [ ] 17. `CadAnalysisService.create_drawing()` — DRW-{YYYYMMDD}-{seq} 채번 + Celery enqueue
- [ ] 18. `analyze_cad_drawing_task` Celery 태스크 — status: pending→analyzing→completed/failed
- [ ] 19. `QuotationService._calc_material_cost()` — 체적×밀도×price_per_kg 계산
- [ ] 20. `QuotationService._calc_process_items()` — 4개 공정 유형(cut/hole/bend/weld) 처리
- [ ] 21. `QuotationService.link_order()` — quotation.order_id + status='accepted'

### Backend APIs
- [ ] 22. `POST /files/presigned-upload` — presigned_url + file_id 반환
- [ ] 23. `GET /cad/{id}/status` — 분석 상태 단순 조회 (폴링용)
- [ ] 24. `GET /quotations/{id}/similar` — Qdrant 또는 DB 폴백 유사 견적 검색
- [ ] 25. 4개 라우터 `router.py` 등록 (files, cad, quotations, master/price-master)

### Frontend
- [ ] 26. `CadUploader` — presigned PUT 업로드 + confirm 2단계 흐름
- [ ] 27. `useDrawingStatus` — `refetchInterval` 조건부 폴링 (completed/failed 시 false)
- [ ] 28. `quotation/page.tsx` — 3탭 구조 (견적목록/도면분석/단가설정) 실동작
