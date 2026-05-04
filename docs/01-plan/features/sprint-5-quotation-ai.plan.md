# Sprint 5 — 수주견적AI 기반 구축 Plan

> **Feature**: sprint-5-quotation-ai  
> **Phase**: Plan  
> **Date**: 2026-05-04  
> **Status**: Draft  
> **Depends on**: sprint-4-inbound-kpi (완료, Match Rate 95%)

---

## 1. 목적 및 배경

### 1.1 목적

Sprint 5는 Metal-Onetouch AI+MES의 **Phase 3 진입 스프린트**입니다.  
Phase 1~2에서 구축된 LOT 추적 + KPI + 수주 기반 위에  
**수주견적 AI 핵심 파이프라인**을 구현합니다:

1. **CAD 도면 업로드 인프라** — MinIO 파일 스토리지, presigned URL 업로드/다운로드
2. **GPT-4o Vision 도면 분석** — CAD 이미지 → 구조화된 객체 JSON (홀/슬롯/절곡/치수)
3. **규칙 기반 자동견적** — 공정별 단가표 × 분석 결과 → 견적금액 자동 산출
4. **견적서 관리** — 견적 저장, 수정, 고객사 제출, 수주 연결
5. **Quotation 페이지 완성** — 현재 "개발 예정" 스텁 → 실동작

### 1.2 배경

**사업계획서 목표 (42-46페이지)**:
- 견적 산출 시간: 2시간/건 → 10분/건 (CAD 자동 분석)
- Phase 3 핵심: 수주견적AI관리 모듈 (10주 계획)

**Sprint 4 완료 현황 (Match Rate 95%)**:
- 수주 기초 관리 완성 (orders + order_items)
- LOT 기반 전 공정 추적 체인 완성 (입고→공정→품질→출하)
- `quotation/page.tsx` 현재 완전 스텁 ("개발 예정")

**기술 전략 — Phase 3 단계적 접근**:
| 단계 | 범위 | 시기 |
|------|------|------|
| Sprint 5 (이번) | GPT-4o Vision + 규칙 기반 견적 | Phase 3 초기 |
| Sprint 6 | YOLOv8 fine-tuning 파이프라인 + Active Learning UI | Phase 3 중기 |
| Sprint 7 | XGBoost 보정 모델 + SHAP 영향요인 분석 | Phase 3 후기 |

YOLOv8 fine-tuning은 최소 500장 어노테이션 데이터가 필요하므로 Sprint 5에서는 GPT-4o Vision으로 즉시 시작하고, 학습 데이터 축적 후 Sprint 6에서 교체한다.

### 1.3 관련 문서

- Master Plan: `docs/01-plan/MASTER-PLAN.md` Section 4 (Phase 3)
- AI Features Plan: `docs/01-plan/features/PM2-ai-features-plan.md` Section 3.3~3.6
- Sprint 4 Report: `docs/04-report/features/sprint-4-inbound-kpi.report.md`

---

## 2. 범위 및 기능 목록

### 2.1 In Scope — 5개 도메인

#### 도메인 1: 파일 스토리지 인프라 (MinIO)
- MinIO 클라이언트 설정 (`backend/app/core/storage.py`)
- Presigned URL 업로드 엔드포인트 (`POST /api/v1/files/presigned-upload`)
- Presigned URL 다운로드 엔드포인트 (`GET /api/v1/files/presigned-download/{key}`)
- 파일 메타데이터 DB 저장 (bucket, key, mime_type, size, created_by)
- CAD 파일 허용 형식: PDF, PNG, JPG (DWG/DXF는 Sprint 6에서 ezdxf 파싱 추가)

#### 도메인 2: CAD 도면 분석 (GPT-4o Vision)
- `cad_drawings` 테이블: 업로드 파일 메타 + 분석 결과 JSON
- `CadAnalysisService`: GPT-4o Vision API 호출, 구조화된 JSON 추출
- 분석 결과 구조:
  ```json
  {
    "objects": [{"type": "hole", "diameter": 12.5, "count": 4, "tolerance": "H7"}, ...],
    "dimensions": {"length": 200.0, "width": 150.0, "thickness": 3.2},
    "material_hint": "SUS304",
    "confidence": 0.91
  }
  ```
- Celery 비동기 처리 (분석 시간 10~30초 소요)
- 분석 상태: `pending` → `analyzing` → `completed` / `failed`
- 분석 결과 수동 수정 API (Active Learning 데이터 수집 기초)

#### 도메인 3: 단가표 기준정보 (공정별 단가 마스터)
- `process_price_master` 테이블: 공정유형 × 재질등급 × 단가
- 관리자 CRUD API (`/api/v1/master/price-master`)
- 기본 공정 단가 시드: 절단, 홀가공, 절곡, 용접, 도장
- 재질 단가 테이블: `material_price_master` (SUS304/SUS316/SS400/AL6061 등)

#### 도메인 4: 자동견적 산출 엔진
- `quotations` 테이블: 견적번호, 고객사, 상태, 총금액, order_id FK (nullable)
- `quotation_items` 테이블: 공정별 금액 breakdown (재료비, 공정별 가공비)
- `QuotationService.calculate()`: 규칙 기반 원가 계산
  ```
  총견적 = 재료비 + Σ공정비
  재료비 = 면적(㎡) × 두께(mm) × 밀도(kg/㎥) × 재질단가(원/kg)
  공정비[절단] = 절단길이(mm) × 절단단가(원/mm)
  공정비[홀가공] = 홀수 × 직경보정계수 × 홀단가(원/개)
  공정비[절곡] = 절곡횟수 × 각도보정계수 × 절곡단가(원/회)
  공정비[용접] = 용접길이(mm) × 용접단가(원/mm)
  ```
- 유사 견적 레퍼런스 검색 (Qdrant 벡터 유사도, 피처 임베딩)
- 견적 확정 → 수주 연결 (`quotation_id` → `order_id`)
- 견적 이력 관리 (버전 관리, 수정 이력)

#### 도메인 5: 견적 UI (quotation/page.tsx 완성)
- 파일 업로드 컴포넌트 (드래그앤드롭, 진행률 표시)
- 분석 결과 시각화 (객체 목록, 치수 요약, 신뢰도)
- 견적 항목 편집 테이블 (단가 수동 조정 가능)
- 견적서 미리보기 및 저장
- 견적 목록 DataTable (상태 필터, 고객사 필터)
- 수주 연결 버튼 (기존 order 선택 또는 신규 생성)

### 2.2 Out of Scope (Sprint 6+)
- YOLOv8 fine-tuning 파이프라인 → Sprint 6
- DWG/DXF 파싱 (ezdxf) → Sprint 6
- Active Learning 어노테이션 UI → Sprint 6
- XGBoost 보정 모델 → Sprint 7
- SHAP 영향요인 분석 → Sprint 7
- BOM 자동생성 → Sprint 6 (견적 확정 후 연동)
- ERP 완전 연동 → Phase 3 후반

---

## 3. 사용자 스토리

| # | 역할 | As a... | I want to... | So that... |
|---|------|---------|--------------|------------|
| US-01 | 영업담당자 | 영업담당자로서 | CAD 도면을 업로드하면 자동으로 견적이 산출되길 원한다 | 2시간 걸리던 견적을 10분 안에 고객에게 제시할 수 있다 |
| US-02 | 영업담당자 | 영업담당자로서 | AI가 분석한 견적 항목을 수동으로 조정하고 싶다 | AI 실수를 보정하여 정확한 견적을 낼 수 있다 |
| US-03 | 원가담당자 | 원가담당자로서 | 공정별 단가표를 시스템에서 관리하고 싶다 | 단가 변경 시 모든 견적에 즉시 반영할 수 있다 |
| US-04 | 경영진 | 경영진으로서 | 유사한 과거 견적과 현재 견적을 비교하고 싶다 | 견적 일관성을 확보하고 레퍼런스를 활용할 수 있다 |
| US-05 | 영업담당자 | 영업담당자로서 | 확정된 견적을 수주로 바로 연결하고 싶다 | 견적 → 수주 프로세스를 한 화면에서 완결할 수 있다 |
| US-06 | 관리자 | 관리자로서 | 파일 업로드 스토리지를 중앙화하여 관리하고 싶다 | 도면 파일이 안전하게 보관되고 검색 가능하게 된다 |

---

## 4. 기술 요구사항

### 4.1 신규 DB 모델 (마이그레이션 0008)

```sql
-- 파일 메타데이터
uploaded_files
  id              UUID PK
  bucket          VARCHAR(100) NOT NULL
  object_key      VARCHAR(500) NOT NULL UNIQUE
  original_name   VARCHAR(500)
  mime_type       VARCHAR(100)
  file_size       BIGINT
  uploaded_by     UUID FK → users
  created_at      TIMESTAMPTZ DEFAULT NOW()

-- CAD 도면 분석
cad_drawings
  id              UUID PK
  file_id         UUID FK → uploaded_files
  drawing_number  VARCHAR(30) UNIQUE   -- DRW-YYYYMMDD-NNNN
  customer_id     UUID FK → customers (nullable)
  analysis_status VARCHAR(20)          -- pending/analyzing/completed/failed
  raw_result      JSONB                -- GPT-4o Vision 원본 응답
  parsed_objects  JSONB                -- 정제된 객체 목록
  dimensions      JSONB                -- {length, width, thickness}
  material_hint   VARCHAR(100)
  confidence      DECIMAL(4,3)
  analyzed_at     TIMESTAMPTZ
  error_message   TEXT
  created_by      UUID FK → users
  created_at      TIMESTAMPTZ DEFAULT NOW()

-- 공정 단가 마스터
process_price_master
  id              UUID PK
  process_type    VARCHAR(50) NOT NULL  -- cutting/drilling/bending/welding/painting
  material_grade  VARCHAR(50)           -- SUS304/SS400/AL6061/etc (NULL = 공통)
  unit_price      DECIMAL(12,4) NOT NULL
  price_unit      VARCHAR(20)           -- per_mm/per_piece/per_count
  effective_from  DATE DEFAULT CURRENT_DATE
  notes           TEXT
  updated_by      UUID FK → users
  updated_at      TIMESTAMPTZ DEFAULT NOW()

-- 재질 단가 마스터
material_price_master
  id              UUID PK
  material_code   VARCHAR(50) UNIQUE    -- SUS304_2T, SS400_3T, ...
  material_name   VARCHAR(200)
  price_per_kg    DECIMAL(12,4) NOT NULL
  density         DECIMAL(8,4)          -- kg/㎥ (default by material)
  updated_by      UUID FK → users
  updated_at      TIMESTAMPTZ DEFAULT NOW()

-- 견적서
quotations
  id              UUID PK
  quotation_number VARCHAR(30) UNIQUE   -- QUO-YYYYMMDD-NNNN
  customer_id     UUID FK → customers
  drawing_id      UUID FK → cad_drawings (nullable)
  order_id        UUID FK → orders (nullable, 수주 연결 후)
  status          quotation_status_enum -- draft/submitted/accepted/rejected/expired
  material_cost   DECIMAL(14,2)
  process_cost    DECIMAL(14,2)
  total_amount    DECIMAL(14,2)
  margin_rate     DECIMAL(5,3)          -- 이윤율
  final_amount    DECIMAL(14,2)         -- total_amount × (1 + margin_rate)
  valid_until     DATE
  notes           TEXT
  version         INTEGER DEFAULT 1
  created_by      UUID FK → users
  created_at      TIMESTAMPTZ DEFAULT NOW()
  updated_at      TIMESTAMPTZ DEFAULT NOW()

-- 견적 항목 (공정별 금액 breakdown)
quotation_items
  id              UUID PK
  quotation_id    UUID FK → quotations CASCADE
  item_type       VARCHAR(50)    -- material/cutting/drilling/bending/welding/etc
  description     VARCHAR(500)
  quantity        DECIMAL(12,4)
  unit            VARCHAR(20)
  unit_price      DECIMAL(12,4)
  amount          DECIMAL(14,2)
  sort_order      INTEGER DEFAULT 0
```

### 4.2 MinIO 연동 설계

```python
# backend/app/core/storage.py
class StorageClient:
    def __init__(self): ...  # MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
    def get_presigned_upload_url(self, bucket: str, key: str, expires: int = 3600) -> str
    def get_presigned_download_url(self, bucket: str, key: str, expires: int = 3600) -> str
    def delete_object(self, bucket: str, key: str) -> None
    def object_exists(self, bucket: str, key: str) -> bool
```

Bucket 구조:
```
metal-onetouch/
├── cad-drawings/     {YYYY}/{MM}/{uuid}.{ext}
├── reports/          {YYYY}/{MM}/{quotation_number}.pdf
└── temp/             {uuid}  (presigned 업로드 임시 경로)
```

### 4.3 GPT-4o Vision 분석 설계

```python
# backend/app/services/cad_analysis_service.py
class CadAnalysisService:
    async def analyze_drawing(self, drawing_id: UUID) -> CadDrawing:
        # 1. MinIO presigned URL 생성
        # 2. GPT-4o Vision API 호출 (image_url 또는 base64)
        # 3. 구조화된 JSON 파싱
        # 4. DB 업데이트 (parsed_objects, confidence)
        ...

    @staticmethod
    def _build_prompt() -> str:
        # 금속 가공 도면 분석 시스템 프롬프트
        # 출력 스키마: objects[], dimensions, material_hint, confidence
        ...
```

Celery 태스크:
```python
# backend/app/tasks/cad_tasks.py
@celery_app.task(name="analyze_cad_drawing")
def analyze_cad_drawing_task(drawing_id: str): ...
```

### 4.4 견적 산출 엔진

```python
# backend/app/services/quotation_service.py
class QuotationService:
    async def calculate_from_drawing(self, drawing_id, customer_id, margin_rate) -> QuotationRead:
        # 1. cad_drawings.parsed_objects 조회
        # 2. material_price_master에서 재질 단가 조회
        # 3. process_price_master에서 공정 단가 조회
        # 4. 규칙 기반 원가 계산
        # 5. quotation + quotation_items INSERT
        ...

    async def calculate_material_cost(self, dimensions, material_code) -> Decimal: ...
    async def calculate_process_cost(self, objects, material_grade) -> list[QuotationItemCreate]: ...
    async def link_to_order(self, quotation_id, order_id) -> QuotationRead: ...
    async def find_similar_quotations(self, quotation_id, top_k=5) -> list[QuotationSummary]: ...
```

Qdrant 벡터 유사도 (유사 견적 검색):
```
피처 벡터: [object_counts, total_length, total_holes, material_type_code, thickness]
인덱스: quotation_features (collection: "quotations")
검색: cosine similarity top-5
```

### 4.5 API 엔드포인트 (신규 ~16개)

**파일 스토리지 (`/api/v1/files`)**:
- `POST /presigned-upload` — 업로드 presigned URL 발급 + DB 레코드 생성
- `POST /confirm-upload` — 업로드 완료 확인 (size, mime_type 기록)
- `GET /presigned-download/{file_id}` — 다운로드 URL 발급

**CAD 분석 (`/api/v1/cad`)**:
- `POST /` — 도면 등록 + 비동기 분석 시작 (Celery 태스크 enqueue)
- `GET /` — 도면 목록 (분석 상태 필터)
- `GET /{id}` — 상세 (분석 결과 포함)
- `PATCH /{id}/objects` — 분석 결과 수동 수정 (Active Learning 데이터)
- `GET /{id}/status` — 분석 진행 상태 폴링

**견적 (`/api/v1/quotations`)**:
- `POST /` — 견적 생성 (drawing_id로 자동 산출 또는 수동 입력)
- `GET /` — 목록 (상태/고객사 필터)
- `GET /{id}` — 상세 (items + drawing 포함)
- `PATCH /{id}` — 견적 수정 (항목 단가 조정)
- `POST /{id}/submit` — 고객 제출 상태 변경
- `POST /{id}/link-order` — 수주 연결
- `GET /{id}/similar` — 유사 견적 검색

**단가 마스터 (`/api/v1/master/price-master`)**:
- `GET /process` — 공정 단가 목록
- `PUT /process` — 공정 단가 일괄 업데이트 (admin)
- `GET /material` — 재질 단가 목록
- `PUT /material` — 재질 단가 업데이트 (admin)

### 4.6 프론트엔드 컴포넌트

| 컴포넌트 | 경로 | 역할 |
|---------|------|------|
| `QuotationPage` | `quotation/page.tsx` | 메인 페이지 (탭: 견적목록 / 도면분석 / 단가설정) |
| `CadUploader` | `components/quotation/cad-uploader.tsx` | 드래그앤드롭 + presigned URL 업로드 |
| `DrawingAnalysisCard` | `components/quotation/drawing-analysis.tsx` | 분석 상태 + 결과 시각화 |
| `QuotationItemsTable` | `components/quotation/quotation-items.tsx` | 항목별 금액 편집 테이블 |
| `QuotationPreview` | `components/quotation/quotation-preview.tsx` | 견적서 미리보기 |
| `SimilarQuotations` | `components/quotation/similar-quotations.tsx` | 유사 견적 레퍼런스 카드 |

React Query 훅:
- `use-cad.ts`: `useCadDrawings`, `useCreateDrawing`, `usePollAnalysisStatus`, `useUpdateDrawingObjects`
- `use-quotations.ts`: `useQuotations`, `useCreateQuotation`, `useUpdateQuotation`, `useLinkOrder`, `useSimilarQuotations`
- `use-price-master.ts`: `useProcessPrices`, `useMaterialPrices`, `useUpdateProcessPrices`

### 4.7 환경 변수 추가

```bash
# .env
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=metal-onetouch
MINIO_USE_SSL=false

OPENAI_API_KEY=sk-...        # GPT-4o Vision 분석
OPENAI_MODEL=gpt-4o

QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_QUOTATIONS=quotations
```

---

## 5. 완료 기준 (Definition of Done)

- [ ] MinIO presigned URL 업로드/다운로드 E2E 동작
- [ ] CAD PDF/이미지 업로드 → GPT-4o Vision 분석 → parsed_objects JSON 저장
- [ ] Celery 비동기 분석 태스크 (`analyze_cad_drawing`) 동작
- [ ] 규칙 기반 자동견적 산출 (`quotation_items` 공정별 breakdown 포함)
- [ ] 견적서 수동 수정 → 저장 → 제출 상태 변경 흐름 동작
- [ ] 견적 → 수주 연결 (`quotation.order_id` 업데이트)
- [ ] `quotation/page.tsx` 실동작 (업로드 + 분석결과 + 견적편집)
- [ ] 유사 견적 검색 (Qdrant 필요, 없으면 DB 기반 폴백 허용)
- [ ] 공정 단가 마스터 CRUD 동작
- [ ] Gap Analysis Match Rate ≥ 90%

---

## 6. 일정 및 우선순위

| 우선순위 | 도메인 | 예상 작업량 | 이유 |
|---------|--------|------------|------|
| P0 | MinIO 인프라 + presigned URL | 1일 | 파일 업로드 없이 이후 모든 기능 불가 |
| P0 | CAD 분석 (GPT-4o Vision) + Celery | 2일 | Phase 3 핵심 AI 기능 시작점 |
| P1 | 단가 마스터 + 자동견적 엔진 | 1.5일 | 견적 산출 로직 — 비즈니스 가치 직결 |
| P1 | 견적 관리 API + 수주 연결 | 1일 | 견적 → 수주 전환 프로세스 완성 |
| P2 | 견적 UI (quotation/page.tsx) | 2일 | 사용자 스토리 US-01~05 달성 |
| P2 | 유사 견적 Qdrant 검색 | 0.5일 | Qdrant 미설치 시 DB 폴백으로 대체 |

**총 예상 기간**: 8일

---

## 7. 리스크 및 대응

| 리스크 | 영향 | 가능성 | 대응 |
|--------|------|--------|------|
| GPT-4o Vision 분석 정확도 낮음 | 견적 오차 | 중 | 분석 결과 수동 수정 UI 필수 제공; 신뢰도(confidence) 낮을 때 사용자 경고 |
| MinIO 미설치 환경 | 업로드 불가 | 중 | docker-compose에 MinIO 서비스 추가; 폴백으로 로컬 파일 저장 임시 허용 |
| GPT-4o API 비용 | 운영 비용 | 중 | 분석 결과 캐싱; 동일 도면 재분석 방지 (file hash 체크) |
| Qdrant 미설치 | 유사 견적 검색 불가 | 중 | DB 기반 간단 유사도(금액 범위 + 공정 유형)로 폴백 허용 |
| Celery 태스크 큐 지연 | 분석 응답 지연 | 저 | UI 폴링 방식 (5초 간격, 최대 2분); 완료 시 알림 토스트 |
| 단가표 미입력 시 견적 불가 | 기능 차단 | 저 | 시드 데이터로 기본 단가 제공; 단가 미설정 항목은 견적에 "단가 미설정" 표시 |

---

## 8. 의존성 및 사전 조건

### 8.1 외부 서비스 (신규)
- **MinIO**: `docker-compose.yml`에 추가 필요 (port 9000/9001)
- **Qdrant**: `docker-compose.yml`에 추가 필요 (port 6333) — 유사 견적 검색
- **Redis**: 이미 설치됨 (Celery 브로커 재사용)

### 8.2 환경 변수 (신규)
- `OPENAI_API_KEY` — GPT-4o Vision 분석
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- `QDRANT_HOST`, `QDRANT_PORT`

### 8.3 Python 패키지 (신규)
```
minio>=7.2.0           # MinIO Python SDK
openai>=1.0.0          # GPT-4o Vision API
qdrant-client>=1.7.0   # 벡터 유사도 검색
pdf2image>=1.17.0      # PDF → 이미지 변환 (분석 전처리)
pillow>=10.0.0         # 이미지 처리
```

### 8.4 선행 작업
- Migration 0008 실행 (기존 0007 완료 확인됨)
- MinIO docker 서비스 시작 및 버킷 생성
- `OPENAI_API_KEY` 환경 변수 설정

---

## 9. 다음 단계

Sprint 5 완료 후 Phase 3 중기 진입:
- **Sprint 6**: YOLOv8 fine-tuning 파이프라인 구축 + Active Learning UI + DWG/DXF 파싱 (ezdxf)
- **Sprint 7**: XGBoost 보정 모델 (견적 정확도 향상) + SHAP 영향요인 분석 대시보드
- **Phase 3 완료 기준**: 도면 업로드 → 10분 내 확정 견적, 수주 자동 연결, BOM 초안 생성
