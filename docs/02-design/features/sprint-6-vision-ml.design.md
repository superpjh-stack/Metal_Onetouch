# Sprint 6 — Vision ML 파이프라인 Design

> **Feature**: sprint-6-vision-ml  
> **Phase**: Design  
> **Date**: 2026-05-04  
> **Status**: Draft  
> **Depends on**: sprint-5-quotation-ai (완료, Match Rate 100%)

---

## 1. 개요

Sprint 6은 Phase 3 중기 스프린트로 4개 도메인을 구현합니다:

1. **DWG/DXF 파싱 (ezdxf)** — 벡터 CAD 파일에서 직접 객체 추출, 파일 형식별 분석 라우팅
2. **Active Learning 어노테이션 파이프라인** — AI 결과 보정 UI → 학습 데이터셋 자동 빌드
3. **YOLOv8 Fine-tuning 파이프라인** — MLflow 실험 추적, Celery GPU 태스크, 모델 버전 관리
4. **BOM 자동생성** — 확정 견적 → 재질소요량 계산 → Excel 내보내기

---

## 2. DB 스키마 (Migration 0009)

### 2.1 annotation_tasks (어노테이션 태스크)

```sql
CREATE TYPE annotation_status_enum AS ENUM (
    'pending',       -- AI 분석 완료, 검토 대기
    'in_progress',   -- 어노테이터 작업 중
    'completed',     -- 수정 완료, 학습 데이터 포함 대상
    'skipped'        -- 신뢰도 높음, 스킵 처리
);

CREATE TABLE annotation_tasks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drawing_id       UUID NOT NULL REFERENCES cad_drawings(id) ON DELETE CASCADE,
    status           annotation_status_enum NOT NULL DEFAULT 'pending',
    original_parsed  JSONB NOT NULL,             -- AI 원본 결과 (수정 전 스냅샷)
    corrected_parsed JSONB,                      -- 어노테이터 수정 결과 (NULL = 미수정)
    annotator_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    assigned_at      TIMESTAMPTZ,
    completed_at     TIMESTAMPTZ,
    skip_reason      VARCHAR(200),               -- skipped 상태 시 사유
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_annot_drawing  ON annotation_tasks(drawing_id);
CREATE INDEX ix_annot_status   ON annotation_tasks(status);
CREATE INDEX ix_annot_annotator ON annotation_tasks(annotator_id);
```

**태스크 생성 트리거**: `CadAnalysisService.run_analysis()` 완료 시 `confidence < 0.95`인 경우 자동 생성. `confidence >= 0.95`인 경우 `skipped` 상태로 생성.

### 2.2 annotation_datasets (어노테이션 데이터셋)

```sql
CREATE TABLE annotation_datasets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version      VARCHAR(20) NOT NULL UNIQUE,   -- v1.0, v1.1, v1.2, ...
    image_count  INTEGER NOT NULL DEFAULT 0,
    label_counts JSONB NOT NULL DEFAULT '{}',   -- {"hole": 1240, "bend": 890, "cut": 320}
    s3_path      VARCHAR(500),                  -- MinIO: datasets/yolo/v1.0/
    built_at     TIMESTAMPTZ,
    status       VARCHAR(20) NOT NULL DEFAULT 'building',  -- building/ready/failed
    notes        TEXT,
    created_by   UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**데이터셋 버전 채번**: `v{major}.{minor}` — 최초 빌드 `v1.0`, 이후 어노테이션 추가 시 마이너 증가.

### 2.3 training_jobs (YOLOv8 학습 잡)

```sql
CREATE TYPE training_status_enum AS ENUM (
    'pending',     -- 큐 대기
    'running',     -- GPU 워커 실행 중
    'completed',   -- 학습 완료 (val_map50 달성)
    'failed'       -- 학습 실패 또는 mAP 미달
);

CREATE TABLE training_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id      UUID NOT NULL REFERENCES annotation_datasets(id) ON DELETE RESTRICT,
    model_version   VARCHAR(20) NOT NULL DEFAULT 'yolov8s',  -- yolov8n/yolov8s/yolov8m
    epochs          INTEGER NOT NULL DEFAULT 100,
    batch_size      INTEGER NOT NULL DEFAULT 16,
    img_size        INTEGER NOT NULL DEFAULT 640,
    status          training_status_enum NOT NULL DEFAULT 'pending',
    train_map50     NUMERIC(6,4),              -- mAP@0.5 on train set
    val_map50       NUMERIC(6,4),              -- mAP@0.5 on val set
    model_s3_path   VARCHAR(500),              -- MinIO: models/yolo/{id}/best.pt
    mlflow_run_id   VARCHAR(100),
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,  -- 현재 추론에 사용 중인 모델
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    hyperparams     JSONB NOT NULL DEFAULT '{}',     -- 기타 하이퍼파라미터
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_train_dataset  ON training_jobs(dataset_id);
CREATE INDEX ix_train_status   ON training_jobs(status);
CREATE INDEX ix_train_active   ON training_jobs(is_active) WHERE is_active = TRUE;
```

**활성 모델 제약**: `is_active = TRUE`인 레코드는 최대 1개. 새 모델 활성화 시 기존 활성 모델 `is_active = FALSE`로 전환.

### 2.4 dxf_layer_mappings (DXF 레이어 매핑)

```sql
CREATE TABLE dxf_layer_mappings (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    layer_pattern VARCHAR(100) NOT NULL,   -- "HOLE*", "BEND_*", "*CUT*", "WELD*"
    process_type  VARCHAR(50)  NOT NULL,   -- cutting/drilling/bending/welding
    priority      SMALLINT     NOT NULL DEFAULT 0,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX ix_dxf_pattern ON dxf_layer_mappings(layer_pattern) WHERE is_active = TRUE;
```

**시드 데이터**:
| layer_pattern | process_type | priority |
|---|---|---|
| HOLE* | drilling | 10 |
| DRILL* | drilling | 9 |
| BEND* | bending | 10 |
| FOLD* | bending | 9 |
| CUT* | cutting | 10 |
| *SLOT* | cutting | 8 |
| WELD* | welding | 10 |

### 2.5 bom_headers (BOM 헤더)

```sql
CREATE TABLE bom_headers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quotation_id    UUID NOT NULL REFERENCES quotations(id) ON DELETE RESTRICT UNIQUE,
    order_id        UUID REFERENCES orders(id) ON DELETE SET NULL,
    revision        SMALLINT NOT NULL DEFAULT 1,
    total_weight_kg NUMERIC(12,3) NOT NULL DEFAULT 0,
    notes           TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_bom_quotation ON bom_headers(quotation_id);
CREATE INDEX ix_bom_order     ON bom_headers(order_id);
```

### 2.6 bom_items (BOM 항목)

```sql
CREATE TABLE bom_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bom_id          UUID NOT NULL REFERENCES bom_headers(id) ON DELETE CASCADE,
    material_code   VARCHAR(50) NOT NULL,
    specification   VARCHAR(200) NOT NULL,    -- "SUS304 3.2t × 200 × 150" 또는 "SUS304 Ø12.5"
    quantity        NUMERIC(12,4) NOT NULL DEFAULT 1,
    unit            VARCHAR(20) NOT NULL DEFAULT 'kg',  -- kg/m/ea/sheet
    unit_weight_kg  NUMERIC(10,4),            -- ea당 무게 (unit='ea'인 경우)
    total_weight_kg NUMERIC(12,3) NOT NULL DEFAULT 0,
    sort_order      SMALLINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_bom_items_bom ON bom_items(bom_id);
```

---

## 3. 백엔드 서비스 설계

### 3.1 DxfParserService

**파일**: `backend/app/services/dxf_parser_service.py`

```python
class DxfParserService:
    def parse(self, file_bytes: bytes, filename: str) -> dict:
        """DXF/DWG 파일 → parsed_objects 표준 JSON 구조 반환"""
    
    def _load_layer_mappings(self) -> list[dict]:
        """dxf_layer_mappings 테이블에서 활성 매핑 로드 (캐시 60s)"""
    
    def _match_layer(self, layer_name: str, mappings: list) -> str | None:
        """레이어명 → process_type 매핑 (fnmatch 패턴 매칭, priority 순)"""
    
    def _extract_circles(self, msp) -> list[dict]:
        """CIRCLE 엔티티 → {"type": "hole", "diameter": d, "count": 1, "x": x, "y": y}"""
    
    def _extract_lines(self, msp) -> list[dict]:
        """LINE/POLYLINE → {"type": "cut", "length": l} 또는 {"type": "weld", "length": l}"""
    
    def _extract_arcs(self, msp) -> list[dict]:
        """ARC 엔티티 → {"type": "bend", "angle": a, "radius": r, "count": 1}"""
    
    def _infer_dimensions(self, msp) -> dict:
        """MTEXT/TEXT DIMENSION 엔티티에서 치수 추출, 없으면 경계상자 계산"""
```

**출력 표준 형식**:
```json
{
  "objects": [
    {"type": "hole", "diameter": 12.5, "count": 4, "x": 50.0, "y": 30.0, "layer": "HOLE_6MM"},
    {"type": "bend", "angle": 90.0, "radius": 3.0, "count": 1, "layer": "BEND_R3"},
    {"type": "cut",  "length": 800.0, "layer": "CUT_OUTER"}
  ],
  "dimensions": {"length": 200.0, "width": 150.0, "thickness": 3.2},
  "layers": ["HOLE_6MM", "BEND_R3", "CUT_OUTER", "DIM"],
  "material_hint": null,
  "confidence": 1.0,
  "source": "dxf"
}
```

**형식 감지 로직** (`CadAnalysisService.detect_format()`):
```
.dxf  → DxfParserService
.dwg  → HTTP 400 "DXF 형식으로 변환 후 업로드 요청" (Sprint 7에서 자동화)
.pdf / .png / .jpg → 활성 YOLOv8 모델 또는 GPT-4o Vision (폴백)
```

### 3.2 YoloService

**파일**: `backend/app/services/yolo_service.py`

```python
class YoloService:
    _model_cache: dict[str, "YOLO"] = {}   # job_id → YOLO 인스턴스 캐시
    
    async def get_active_model(self, db: AsyncSession) -> "YOLO | None":
        """training_jobs WHERE is_active=TRUE → MinIO에서 .pt 다운로드 → 캐시"""
    
    def predict(self, model: "YOLO", image_bytes: bytes) -> dict:
        """이미지 → YOLO 추론 → parsed_objects 표준 형식 변환"""
    
    def _boxes_to_objects(self, results) -> list[dict]:
        """YOLO BoundingBox → type/diameter/angle/length 추정 변환"""
    
    def _calc_confidence(self, results) -> float:
        """박스별 conf 평균 (없으면 0.0)"""
```

**추론 라우팅** (`CadAnalysisService.analyze_image()`):
```python
active_model = await YoloService().get_active_model(db)
if active_model:
    result = YoloService().predict(active_model, image_bytes)
else:
    result = await self._analyze_with_gpt4o_vision(image_bytes)  # 폴백
```

### 3.3 TrainingService

**파일**: `backend/app/services/training_service.py`

```python
class TrainingService:
    def __init__(self, db: AsyncSession) -> None: ...
    
    async def build_dataset(self, created_by: uuid.UUID) -> AnnotationDatasetRead:
        """
        1. annotation_tasks WHERE status='completed' 수집
        2. corrected_parsed → YOLO label format (.txt) 변환
        3. 이미지 + 라벨을 MinIO datasets/yolo/{version}/ 에 업로드
        4. annotation_datasets 레코드 생성
        """
    
    async def start_training(
        self, dataset_id: uuid.UUID, params: TrainingJobCreate, created_by: uuid.UUID
    ) -> TrainingJobRead:
        """training_jobs INSERT → train_yolo_model_task.delay()"""
    
    async def activate_model(self, job_id: uuid.UUID) -> TrainingJobRead:
        """기존 is_active=TRUE 레코드를 FALSE로 → 지정 job is_active=TRUE"""
    
    async def get_job_status(self, job_id: uuid.UUID) -> TrainingJobRead: ...
```

**YOLO label format 변환**:
```
# corrected_parsed["objects"] 각 항목 → {class_id} {cx} {cy} {w} {h} (0~1 정규화)
# class 매핑: hole=0, bend=1, cut=2, weld=3, slot=4
```

### 3.4 AnnotationTaskService

**파일**: `backend/app/services/annotation_task_service.py`

```python
class AnnotationTaskService:
    def __init__(self, db: AsyncSession) -> None: ...
    
    async def create_for_drawing(self, drawing_id: uuid.UUID) -> AnnotationTask | None:
        """cad_drawings.confidence 기반 자동 생성 (0.95 미만 → pending, 이상 → skipped)"""
    
    async def list_pending(
        self, annotator_id: uuid.UUID | None = None, page: int = 1, limit: int = 20
    ) -> tuple[list[AnnotationTaskRead], int]: ...
    
    async def submit_correction(
        self, task_id: uuid.UUID, corrected: dict, annotator_id: uuid.UUID
    ) -> AnnotationTaskRead:
        """
        1. corrected_parsed 저장
        2. cad_drawings.parsed_objects 업데이트 (최신 보정 결과 반영)
        3. status = 'completed', completed_at = now()
        """
    
    async def skip(self, task_id: uuid.UUID, reason: str) -> AnnotationTaskRead: ...
```

### 3.5 BomService

**파일**: `backend/app/services/bom_service.py`

```python
class BomService:
    def __init__(self, db: AsyncSession) -> None: ...
    
    async def generate_from_quotation(
        self, quotation_id: uuid.UUID, created_by: uuid.UUID
    ) -> BomRead:
        """
        quotation_items → BOM 라인 변환:
        - item_type='material' → bom_items (재질/규격/무게)
        - item_type='cutting'  → bom_items (절단 가공 자재)
        - 중복 material_code 집계 (같은 재질 합산)
        total_weight_kg = Σ bom_items.total_weight_kg
        """
    
    async def get_bom(self, quotation_id: uuid.UUID) -> BomRead | None: ...
    
    async def export_xlsx(self, bom_id: uuid.UUID) -> bytes:
        """openpyxl로 BOM Excel 생성 → bytes 반환"""
```

**Excel 시트 구조**:
```
Sheet: BOM
행 1: 견적번호 | 작성일 | 리비전
행 2: [헤더] 재질코드 | 규격 | 수량 | 단위 | 단위중량(kg) | 총중량(kg)
행 3~: bom_items 데이터
마지막 행: 합계 | - | - | - | - | total_weight_kg
```

---

## 4. Celery 태스크 설계

### 4.1 parse_dxf_task

**파일**: `backend/app/tasks/dxf_tasks.py`

```python
@celery_app.task(
    bind=True,
    name="app.tasks.dxf_tasks.parse_dxf_task",
    queue="cad_queue",
    max_retries=1,
    default_retry_delay=5,
    soft_time_limit=30,
    time_limit=60,
)
def parse_dxf_task(self, drawing_id: str) -> None:
    """
    동기 태스크 (DXF 파싱은 CPU 바운드, I/O 없음)
    1. drawing_id로 cad_drawings 조회 (동기 세션)
    2. MinIO에서 파일 다운로드
    3. DxfParserService.parse() 호출
    4. parsed_objects, dimensions, confidence, analyzed_at 업데이트
    5. status → 'completed' 또는 'failed'
    6. AnnotationTaskService.create_for_drawing() 호출
    """
```

### 4.2 train_yolo_model_task

**파일**: `backend/app/tasks/training_tasks.py`

```python
@celery_app.task(
    bind=True,
    name="app.tasks.training_tasks.train_yolo_model_task",
    queue="train_queue",
    max_retries=0,
    soft_time_limit=82800,   # 23h
    time_limit=86400,        # 24h
)
def train_yolo_model_task(self, job_id: str) -> None:
    """
    1. training_jobs.status → 'running', started_at = now()
    2. MinIO에서 데이터셋 다운로드 → /tmp/yolo_dataset_{job_id}/
    3. mlflow.set_experiment("cad-yolo") + mlflow.start_run()
    4. YOLO(model_version).train(data=..., epochs=..., batch=..., imgsz=...)
    5. mlflow.log_metrics({"train_map50": ..., "val_map50": ...})
    6. best.pt → MinIO models/yolo/{job_id}/best.pt 업로드
    7. training_jobs UPDATE: status='completed', val_map50, model_s3_path, mlflow_run_id
    8. /tmp 임시 파일 삭제
    """
```

**Celery 라우팅 업데이트** (`backend/app/core/celery_app.py`):
```python
task_routes = {
    "app.tasks.ai_agent.*":      {"queue": "ai_agent_queue"},
    "app.tasks.cad_tasks.*":     {"queue": "cad_queue"},
    "app.tasks.dxf_tasks.*":     {"queue": "cad_queue"},
    "app.tasks.training_tasks.*": {"queue": "train_queue"},
}
```

---

## 5. API 엔드포인트 설계

### 5.1 어노테이션 API (`/api/v1/cad`)

기존 `backend/app/api/v1/cad.py` 확장:

```
GET    /api/v1/cad/{id}/annotation-task
       → AnnotationTaskRead | null
       → 200 (존재), 404 (없음)

PUT    /api/v1/cad/{id}/annotation
       Body: { "corrected_parsed": {...} }
       → AnnotationTaskRead
       → 200

GET    /api/v1/cad/annotation-tasks
       Query: status=pending|in_progress|completed|skipped, page, limit
       → { items: AnnotationTaskRead[], total: int }
       → 200
       권한: annotator, admin, production_manager
```

### 5.2 ML 관리 API (`/api/v1/ml`)

신규 라우터: `backend/app/api/v1/ml.py`

```
POST   /api/v1/ml/datasets/build
       Body: { "notes": "..." }
       → AnnotationDatasetRead
       → 202 (Accepted, 빌드 비동기)
       권한: admin, ai_engineer

GET    /api/v1/ml/datasets
       Query: page, limit
       → { items: AnnotationDatasetRead[], total: int }
       → 200

POST   /api/v1/ml/training-jobs
       Body: TrainingJobCreate
       → TrainingJobRead
       → 201
       권한: admin, ai_engineer

GET    /api/v1/ml/training-jobs/{id}
       → TrainingJobRead
       → 200

GET    /api/v1/ml/training-jobs
       Query: status, page, limit
       → { items: TrainingJobRead[], total: int }

PATCH  /api/v1/ml/training-jobs/{id}/activate
       → TrainingJobRead (is_active=true)
       → 200
       권한: admin, ai_engineer
       조건: status='completed' AND val_map50 IS NOT NULL
```

### 5.3 BOM API (`/api/v1/quotations`, `/api/v1/bom`)

기존 `backend/app/api/v1/quotations.py` 확장:

```
POST   /api/v1/quotations/{id}/bom
       → BomRead
       → 201
       조건: quotation.status IN ('accepted')
       효과: bom_headers + bom_items 생성

GET    /api/v1/quotations/{id}/bom
       → BomRead | null
       → 200

GET    /api/v1/bom/{id}/export
       Query: format=xlsx (기본값)
       → Response(content=xlsx_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
       → 200
```

### 5.4 Files API 확장

기존 `backend/app/api/v1/files.py` 수정:

```python
# 허용 MIME 타입 추가
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    # Sprint 6 추가:
    "application/dxf",
    "image/vnd.dxf",
    "application/acad",           # .dwg (업로드는 허용, 분석 시 오류 반환)
    "application/x-autocad",
}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".dxf", ".dwg"}
```

---

## 6. Pydantic 스키마 설계

**파일**: `backend/app/schemas/ml.py` (신규), `backend/app/schemas/bom.py` (신규)

```python
# ml.py
class AnnotationTaskRead(BaseModel):
    id: uuid.UUID
    drawing_id: uuid.UUID
    status: str
    original_parsed: dict
    corrected_parsed: dict | None
    annotator_id: uuid.UUID | None
    assigned_at: datetime | None
    completed_at: datetime | None

class AnnotationDatasetRead(BaseModel):
    id: uuid.UUID
    version: str
    image_count: int
    label_counts: dict
    s3_path: str | None
    status: str
    built_at: datetime | None

class TrainingJobCreate(BaseModel):
    dataset_id: uuid.UUID
    model_version: str = "yolov8s"
    epochs: int = Field(default=100, ge=10, le=500)
    batch_size: int = Field(default=16, ge=4, le=64)
    img_size: int = Field(default=640, ge=320, le=1280)
    hyperparams: dict = {}

class TrainingJobRead(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    model_version: str
    epochs: int
    status: str
    train_map50: float | None
    val_map50: float | None
    model_s3_path: str | None
    mlflow_run_id: str | None
    is_active: bool
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime

# bom.py
class BomItemRead(BaseModel):
    id: uuid.UUID
    material_code: str
    specification: str
    quantity: float
    unit: str
    unit_weight_kg: float | None
    total_weight_kg: float
    sort_order: int

class BomRead(BaseModel):
    id: uuid.UUID
    quotation_id: uuid.UUID
    order_id: uuid.UUID | None
    revision: int
    total_weight_kg: float
    items: list[BomItemRead]
    created_at: datetime
```

---

## 7. SQLAlchemy 모델 설계

**파일**: `backend/app/models/annotation.py` (신규)

```python
class AnnotationTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "annotation_tasks"

    drawing_id:       Mapped[uuid.UUID]        = mapped_column(ForeignKey("cad_drawings.id", ondelete="CASCADE"))
    status:           Mapped[str]              = mapped_column(String(20), default="pending")
    original_parsed:  Mapped[dict]             = mapped_column(JSONB, nullable=False)
    corrected_parsed: Mapped[dict | None]      = mapped_column(JSONB)
    annotator_id:     Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    assigned_at:      Mapped[datetime | None]  = mapped_column(TIMESTAMPTZ)
    completed_at:     Mapped[datetime | None]  = mapped_column(TIMESTAMPTZ)
    skip_reason:      Mapped[str | None]       = mapped_column(String(200))

    drawing: Mapped["CadDrawing"] = relationship(back_populates="annotation_task")

class AnnotationDataset(Base, UUIDMixin):
    __tablename__ = "annotation_datasets"

    version:      Mapped[str]  = mapped_column(String(20), unique=True)
    image_count:  Mapped[int]  = mapped_column(Integer, default=0)
    label_counts: Mapped[dict] = mapped_column(JSONB, default={})
    s3_path:      Mapped[str | None] = mapped_column(String(500))
    status:       Mapped[str]  = mapped_column(String(20), default="building")
    built_at:     Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    notes:        Mapped[str | None] = mapped_column(Text)
    created_by:   Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at:   Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())

    jobs: Mapped[list["TrainingJob"]] = relationship(back_populates="dataset")

class TrainingJob(Base, UUIDMixin):
    __tablename__ = "training_jobs"

    dataset_id:     Mapped[uuid.UUID] = mapped_column(ForeignKey("annotation_datasets.id", ondelete="RESTRICT"))
    model_version:  Mapped[str]       = mapped_column(String(20), default="yolov8s")
    epochs:         Mapped[int]       = mapped_column(Integer, default=100)
    batch_size:     Mapped[int]       = mapped_column(Integer, default=16)
    img_size:       Mapped[int]       = mapped_column(Integer, default=640)
    status:         Mapped[str]       = mapped_column(String(20), default="pending")
    train_map50:    Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    val_map50:      Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    model_s3_path:  Mapped[str | None]    = mapped_column(String(500))
    mlflow_run_id:  Mapped[str | None]    = mapped_column(String(100))
    is_active:      Mapped[bool]          = mapped_column(Boolean, default=False)
    started_at:     Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    completed_at:   Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    error_message:  Mapped[str | None]    = mapped_column(Text)
    hyperparams:    Mapped[dict]          = mapped_column(JSONB, default={})
    created_by:     Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at:     Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())

    dataset: Mapped["AnnotationDataset"] = relationship(back_populates="jobs")
```

**파일**: `backend/app/models/bom.py` (신규)

```python
class BomHeader(Base, UUIDMixin):
    __tablename__ = "bom_headers"

    quotation_id:    Mapped[uuid.UUID]        = mapped_column(ForeignKey("quotations.id", ondelete="RESTRICT"), unique=True)
    order_id:        Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    revision:        Mapped[int]              = mapped_column(SmallInteger, default=1)
    total_weight_kg: Mapped[Decimal]          = mapped_column(Numeric(12, 3), default=0)
    notes:           Mapped[str | None]       = mapped_column(Text)
    created_by:      Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at:      Mapped[datetime]         = mapped_column(TIMESTAMPTZ, server_default=func.now())
    updated_at:      Mapped[datetime]         = mapped_column(TIMESTAMPTZ, server_default=func.now(), onupdate=func.now())

    items: Mapped[list["BomItem"]] = relationship(back_populates="bom", cascade="all, delete-orphan", order_by="BomItem.sort_order")

class BomItem(Base, UUIDMixin):
    __tablename__ = "bom_items"

    bom_id:          Mapped[uuid.UUID] = mapped_column(ForeignKey("bom_headers.id", ondelete="CASCADE"))
    material_code:   Mapped[str]       = mapped_column(String(50))
    specification:   Mapped[str]       = mapped_column(String(200))
    quantity:        Mapped[Decimal]   = mapped_column(Numeric(12, 4), default=1)
    unit:            Mapped[str]       = mapped_column(String(20), default="kg")
    unit_weight_kg:  Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    total_weight_kg: Mapped[Decimal]   = mapped_column(Numeric(12, 3), default=0)
    sort_order:      Mapped[int]       = mapped_column(SmallInteger, default=0)
    created_at:      Mapped[datetime]  = mapped_column(TIMESTAMPTZ, server_default=func.now())

    bom: Mapped["BomHeader"] = relationship(back_populates="items")
```

**`backend/app/models/__init__.py` 추가**:
```python
from app.models.annotation import AnnotationTask, AnnotationDataset, TrainingJob
from app.models.bom import BomHeader, BomItem

__all__ = [
    ...,
    "AnnotationTask", "AnnotationDataset", "TrainingJob",
    "BomHeader", "BomItem",
]
```

---

## 8. 프론트엔드 설계

### 8.1 React Query Hooks

**`frontend/src/lib/hooks/use-annotation.ts`** (신규):

```typescript
// 도면의 어노테이션 태스크 조회
export function useAnnotationTask(drawingId: string | undefined) {
  return useQuery({
    queryKey: ['annotation-task', drawingId],
    queryFn: () => api.get(`/cad/${drawingId}/annotation-task`).then(r => r.data),
    enabled: !!drawingId,
  })
}

// 미완료 태스크 목록
export function usePendingAnnotationTasks(params?: { page?: number; limit?: number }) {
  return useQuery({
    queryKey: ['annotation-tasks', 'pending', params],
    queryFn: () => api.get('/cad/annotation-tasks', { params: { status: 'pending', ...params } }).then(r => r.data),
  })
}

// 어노테이션 제출
export function useSubmitAnnotation(drawingId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (corrected_parsed: object) =>
      api.put(`/cad/${drawingId}/annotation`, { corrected_parsed }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['annotation-task', drawingId] })
      qc.invalidateQueries({ queryKey: ['annotation-tasks'] })
    },
  })
}
```

**`frontend/src/lib/hooks/use-ml.ts`** (신규):

```typescript
export function useTrainingJobs(params?: { status?: string }) {
  return useQuery({ queryKey: ['training-jobs', params], queryFn: ... })
}

export function useStartTraining() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TrainingJobCreate) => api.post('/ml/training-jobs', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['training-jobs'] }),
  })
}

export function useBuildDataset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (notes?: string) => api.post('/ml/datasets/build', { notes }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['annotation-datasets'] }),
  })
}

export function useActivateModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => api.patch(`/ml/training-jobs/${jobId}/activate`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['training-jobs'] }),
  })
}

// 학습 잡 실시간 폴링 (running 상태인 경우만)
export function useTrainingJobStatus(jobId: string | undefined) {
  return useQuery({
    queryKey: ['training-job', jobId],
    queryFn: () => api.get(`/ml/training-jobs/${jobId}`).then(r => r.data),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'running' || status === 'pending' ? 10000 : false
    },
  })
}
```

**`frontend/src/lib/hooks/use-bom.ts`** (신규):

```typescript
export function useBom(quotationId: string | undefined) {
  return useQuery({
    queryKey: ['bom', quotationId],
    queryFn: () => api.get(`/quotations/${quotationId}/bom`).then(r => r.data),
    enabled: !!quotationId,
  })
}

export function useGenerateBom(quotationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post(`/quotations/${quotationId}/bom`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bom', quotationId] }),
  })
}

export function useExportBom(bomId: string | undefined) {
  return useMutation({
    mutationFn: () =>
      api.get(`/bom/${bomId}/export`, { responseType: 'blob' }).then(r => {
        const url = URL.createObjectURL(r.data)
        const a = document.createElement('a')
        a.href = url
        a.download = `bom-${bomId}.xlsx`
        a.click()
        URL.revokeObjectURL(url)
      }),
  })
}
```

### 8.2 UI 컴포넌트

**`frontend/src/components/ml/annotation-editor.tsx`** (신규):

```typescript
interface AnnotationEditorProps {
  drawingId: string
  originalParsed: ParsedObjects
  onSubmit?: () => void
}

export function AnnotationEditor({ drawingId, originalParsed, onSubmit }: AnnotationEditorProps) {
  // 객체 목록 편집: 타입/직경/각도/길이/개수 수정
  // 치수(length/width/thickness) 수정
  // 항목 추가/삭제
  // "보정 완료" 버튼 → useSubmitAnnotation
}
```

**`frontend/src/components/ml/training-job-card.tsx`** (신규):

```typescript
interface TrainingJobCardProps {
  job: TrainingJobRead
  onActivate?: (jobId: string) => void
}

export function TrainingJobCard({ job, onActivate }: TrainingJobCardProps) {
  // 상태 배지: pending/running(Progress)/completed(mAP)/failed
  // running 시: 경과 시간 표시, 폴링 via useTrainingJobStatus
  // completed 시: val_map50 표시, "모델 활성화" 버튼 (admin/ai_engineer 권한)
  // MLflow 링크 (mlflow_run_id 있는 경우)
}
```

**`frontend/src/components/quotation/bom-table.tsx`** (신규):

```typescript
interface BomTableProps {
  quotationId: string
  quotationStatus: string
}

export function BomTable({ quotationId, quotationStatus }: BomTableProps) {
  const { data: bom } = useBom(quotationId)
  const generateBom = useGenerateBom(quotationId)
  const exportBom = useExportBom(bom?.id)
  
  // 견적 accepted 상태이고 BOM 없으면 "BOM 자동생성" 버튼
  // BOM 존재 시 항목 테이블 + "Excel 내보내기" 버튼
  // 총 중량 합계 표시
}
```

### 8.3 페이지

**`frontend/src/app/(dashboard)/ml/annotation/page.tsx`** (신규):

```
레이아웃:
- 페이지 헤더: "어노테이션 관리" + 완료/대기 통계
- 필터 탭: 전체 / 대기중 / 진행중 / 완료
- 태스크 카드 목록 (DrawingNumber, 신뢰도, 업로드일)
- 카드 클릭 → Sheet(or Modal)로 AnnotationEditor 열기
```

**`frontend/src/app/(dashboard)/ml/training/page.tsx`** (신규):

```
레이아웃:
- 페이지 헤더: "YOLOv8 학습 관리"
- 상단: 현재 활성 모델 카드 (모델버전, val_mAP, 활성화일)
- 중단: 데이터셋 목록 (버전, 이미지수, 빌드일) + "새 데이터셋 빌드" 버튼
- 하단: 학습 잡 목록 (TrainingJobCard × N) + "새 학습 시작" 버튼
```

**`frontend/src/app/(dashboard)/quotation/page.tsx`** 수정:

```
견적상세 탭 내부에 BomTable 컴포넌트 추가 (accepted 상태 견적 선택 시 표시)
```

---

## 9. 인프라 변경

### 9.1 docker-compose.yml 추가 서비스

```yaml
services:
  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.13.0
    ports:
      - "5000:5000"
    command: >
      mlflow server
      --backend-store-uri postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}_mlflow
      --default-artifact-root s3://mlflow/
      --host 0.0.0.0
    environment:
      MLFLOW_S3_ENDPOINT_URL: http://minio:9000
      AWS_ACCESS_KEY_ID: ${MINIO_ROOT_USER}
      AWS_SECRET_ACCESS_KEY: ${MINIO_ROOT_PASSWORD}
    depends_on:
      - db
      - minio

  celery-gpu-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.core.celery_app worker -Q train_queue --concurrency 1 --loglevel=info
    environment:
      - CELERY_BROKER_URL=${REDIS_URL}
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - MLFLOW_S3_ENDPOINT_URL=http://minio:9000
    volumes:
      - /tmp:/tmp
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    depends_on:
      - redis
      - mlflow
      - minio
```

**환경변수 추가** (`backend/.env`, `docker-compose.yml`):
```
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_S3_ENDPOINT_URL=http://minio:9000
YOLO_CONFIDENCE_THRESHOLD=0.95    # 어노테이션 태스크 자동 생성 임계값
DATASET_MIN_IMAGES=50             # 최소 학습 이미지 수 (미달 시 build 거부)
```

### 9.2 requirements.txt 추가

```
ultralytics==8.2.0
ezdxf==1.3.4
mlflow==2.13.0
openpyxl==3.1.3
```

### 9.3 config.py 추가

```python
class Settings(BaseSettings):
    ...
    # Sprint 6
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.95
    DATASET_MIN_IMAGES: int = 50
    YOLO_ACTIVATION_MAP50_THRESHOLD: float = 0.85
```

---

## 10. router.py 업데이트

**`backend/app/api/v1/router.py`** 수정:

```python
from app.api.v1 import files, cad, quotations, ml, bom  # ml, bom 추가

api_v1_router.include_router(ml.router,  prefix="/ml",  tags=["ML"])
api_v1_router.include_router(bom.router, prefix="/bom", tags=["BOM"])
```

---

## 11. 구현 순서

```
Phase A: DB + 모델 (2일)
  1. Migration 0009 생성 (6개 테이블 + 시드 데이터)
  2. annotation.py, bom.py 모델 파일 생성
  3. ml.py, bom.py 스키마 파일 생성
  4. models/__init__.py 업데이트

Phase B: DXF 파싱 (2일)
  5. dxf_parser_service.py 구현 (ezdxf)
  6. dxf_tasks.py Celery 태스크 구현
  7. CadAnalysisService 라우팅 로직 업데이트
  8. cad.py API — DXF 분기 + 어노테이션 엔드포인트 추가
  9. files.py — DXF/DWG 허용 확장

Phase C: 어노테이션 + 학습 (3일)
  10. annotation_task_service.py 구현
  11. training_service.py 구현 (데이터셋 빌드, 모델 활성화)
  12. yolo_service.py 구현 (추론, 캐시)
  13. training_tasks.py Celery 태스크 구현
  14. ml.py API 라우터 구현 (7개 엔드포인트)

Phase D: BOM (1일)
  15. bom_service.py 구현 (생성, Excel 내보내기)
  16. quotations.py + bom.py API 엔드포인트 추가

Phase E: 프론트엔드 (2일)
  17. use-annotation.ts, use-ml.ts, use-bom.ts hooks
  18. annotation-editor.tsx, training-job-card.tsx, bom-table.tsx 컴포넌트
  19. ml/annotation/page.tsx, ml/training/page.tsx 페이지
  20. quotation/page.tsx 견적상세 탭에 BomTable 추가

Phase F: 인프라 + 통합 (1일)
  21. docker-compose.yml MLflow 서비스 추가
  22. celery_app.py train_queue 라우팅 추가
  23. config.py 환경변수 추가
  24. router.py 신규 라우터 등록
```
