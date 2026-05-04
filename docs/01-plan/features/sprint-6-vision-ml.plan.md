# Sprint 6 — Vision ML 파이프라인 Plan

> **Feature**: sprint-6-vision-ml  
> **Phase**: Plan  
> **Date**: 2026-05-04  
> **Status**: Draft  
> **Depends on**: sprint-5-quotation-ai (완료, Match Rate 100%)

---

## 1. 목적 및 배경

### 1.1 목적

Sprint 6은 Metal-Onetouch AI+MES의 **Phase 3 중기 스프린트**입니다.  
Sprint 5에서 GPT-4o Vision으로 축적한 CAD 분석 데이터를 기반으로  
**자체 Vision ML 파이프라인**을 구축합니다:

1. **YOLOv8 Fine-tuning 파이프라인** — Sprint 5에서 축적된 어노테이션 데이터로 커스텀 모델 학습
2. **DWG/DXF 파싱** — ezdxf 라이브러리 연동, 벡터 CAD 파일에서 직접 객체 추출
3. **Active Learning 어노테이션 UI** — 분석 결과 보정 → 학습 데이터로 피드백
4. **BOM 자동생성** — 확정 견적에서 자재소요량(BOM) 자동 추출

### 1.2 배경

**Sprint 5 완료 현황 (Match Rate 100%)**:
- GPT-4o Vision으로 CAD PDF/이미지 분석 파이프라인 완성
- `cad_drawings.parsed_objects` JSONB에 구조화된 분석 결과 누적 중
- 영업담당자 수동 수정(Active Learning 데이터 수집 기초) API 구현 완료
- MinIO 파일 스토리지 + Celery 비동기 처리 기반 안정화

**YOLOv8 전환 시점**:
- 최소 500장 어노테이션 데이터 필요 → Sprint 5 운영 2~4주 후 달성 예상
- 자체 모델 전환 시 GPT-4o Vision 비용(~$0.01/이미지) 제거 + 응답속도 개선 (30s → 3s)

**기술 전략 — Phase 3 단계적 접근**:
| 단계 | 범위 | 시기 |
|------|------|------|
| Sprint 5 (완료) | GPT-4o Vision + 규칙 기반 견적 | Phase 3 초기 |
| Sprint 6 (이번) | YOLOv8 fine-tuning + DWG/DXF + Active Learning | Phase 3 중기 |
| Sprint 7 | XGBoost 보정 모델 + SHAP 영향요인 분석 | Phase 3 후기 |

### 1.3 관련 문서

- Master Plan: `docs/01-plan/MASTER-PLAN.md` Section 4 (Phase 3)
- Sprint 5 Plan: `docs/01-plan/features/sprint-5-quotation-ai.plan.md`
- Sprint 5 Report: `docs/04-report/features/sprint-5-quotation-ai.report.md`
- AI Features Plan: `docs/01-plan/features/PM2-ai-features-plan.md`

---

## 2. 범위 및 기능 목록

### 2.1 In Scope — 4개 도메인

#### 도메인 1: YOLOv8 Fine-tuning 파이프라인

- **데이터셋 관리** — `annotation_datasets` 테이블: 버전, 이미지 수, 레이블 분포
- **학습 잡 관리** — `training_jobs` 테이블: 모델 버전, 에포크, 학습/검증 mAP, 상태
- **MLflow 실험 추적** — `mlflow.set_experiment("cad-yolo")`, 하이퍼파라미터 + 메트릭 로깅
- **Celery 학습 태스크** — `train_yolo_model_task`: GPU 워커, `train_queue`, max 24h timeout
- **모델 레지스트리** — MinIO에 `.pt` 파일 저장, `training_jobs.model_s3_path`로 참조
- **모델 버전 전환 API** — `PATCH /api/v1/ml/models/{id}/activate`: 활성 모델 교체
- **추론 라우팅** — `CadAnalysisService` 내부에서 활성 YOLOv8 모델 우선, 폴백으로 GPT-4o Vision

#### 도메인 2: DWG/DXF 파싱 (ezdxf)

- **ezdxf 파서 서비스** — `DxfParserService`: DWG/DXF → 동일 `parsed_objects` JSON 구조 출력
  ```json
  {
    "objects": [{"type": "hole", "diameter": 12.5, "count": 4, "x": 50.0, "y": 30.0}],
    "dimensions": {"length": 200.0, "width": 150.0, "thickness": 3.2},
    "layers": ["HOLES", "BENDS", "CUTS"],
    "material_hint": null,
    "confidence": 1.0
  }
  ```
- **레이어 → 공정 매핑** — `DXF_LAYER_MAP` 설정 테이블: 레이어명 패턴 → `process_type`
- **Celery 파싱 태스크** — `parse_dxf_task`: 동기, `cad_queue`, 5s timeout (벡터 파싱이므로 빠름)
- **파일 형식 감지** — `StorageService.detect_format()`: MIME + magic bytes 기반 라우팅
  - `.pdf` / `.png` / `.jpg` → GPT-4o Vision 또는 YOLOv8
  - `.dxf` / `.dwg` → ezdxf 파서
- **CAD 파일 허용 확장 업데이트** — 기존 PDF/PNG/JPG에 DXF/DWG 추가

#### 도메인 3: Active Learning 어노테이션 UI

- **어노테이션 태스크 관리** — `annotation_tasks` 테이블: drawing_id, annotator_id, 상태, 수정 전/후 비교
- **어노테이션 API**
  - `GET /api/v1/cad/{id}/annotation-task` — 도면의 어노테이션 태스크 조회
  - `PUT /api/v1/cad/{id}/annotation` — 분석 결과 수동 수정 + 태스크 완료
  - `GET /api/v1/ml/annotation-tasks` — 미완료 태스크 목록 (어노테이터 할당용)
- **UI 컴포넌트** — `AnnotationEditor`: 객체 목록 편집, 치수 수정, 레이블 추가/삭제
- **데이터셋 빌드** — `POST /api/v1/ml/datasets/build`: 완료된 어노테이션 → 학습 데이터셋 패키징
- **어노테이션 페이지** — `app/(dashboard)/ml/annotation/page.tsx`: 태스크 목록 + 에디터

#### 도메인 4: BOM 자동생성

- **BOM 테이블** — `bom_headers` + `bom_items`: 견적 → 재질/수량/규격 breakdown
- **BOM 생성 서비스** — `BomService.generate_from_quotation()`: `quotation_items` → BOM 라인 변환
  ```
  BOM 라인 = {재질코드, 규격(두께×폭×길이), 수량, 단위중량, 총중량}
  ```
- **BOM API**
  - `POST /api/v1/quotations/{id}/bom` — 확정 견적에서 BOM 생성
  - `GET /api/v1/quotations/{id}/bom` — BOM 조회
  - `GET /api/v1/bom/{id}/export?format=xlsx` — Excel 내보내기
- **BOM 트리거** — `link_order()` 호출 시 자동으로 BOM 생성 (accepted 상태 전환 후)

### 2.2 Out of Scope (Sprint 7+)

- XGBoost 보정 모델 (규칙 기반 견적 오차 보정) → Sprint 7
- SHAP 영향요인 분석 대시보드 → Sprint 7
- ERP 완전 연동 (BOM → 구매발주 자동화) → Phase 3 후반
- 실시간 GPU 모니터링 대시보드 → Sprint 7

---

## 3. 사용자 스토리

| # | 역할 | As a... | I want to... | So that... |
|---|------|---------|--------------|------------|
| US-01 | AI 엔지니어 | AI 엔지니어로서 | 축적된 CAD 분석 데이터로 YOLOv8 모델을 학습시키고 싶다 | GPT-4o 의존도를 줄이고 비용을 절감할 수 있다 |
| US-02 | AI 엔지니어 | AI 엔지니어로서 | MLflow로 학습 실험을 추적하고 싶다 | 최적 모델을 선택하고 성능 변화를 모니터링할 수 있다 |
| US-03 | 영업담당자 | 영업담당자로서 | DWG/DXF 형식의 CAD 파일도 업로드하고 싶다 | 고객이 제공하는 모든 형식의 도면을 처리할 수 있다 |
| US-04 | 어노테이터 | 어노테이터로서 | AI 분석 결과를 UI에서 쉽게 수정하고 싶다 | 오류를 빠르게 보정하여 더 많은 학습 데이터를 만들 수 있다 |
| US-05 | 원가담당자 | 원가담당자로서 | 확정 견적에서 BOM을 자동으로 생성하고 싶다 | 재질소요량 계산과 구매계획 수립을 자동화할 수 있다 |
| US-06 | 구매팀 | 구매팀으로서 | BOM을 Excel로 내보내고 싶다 | 공급업체 견적 요청 시 표준 형식으로 전달할 수 있다 |

---

## 4. 기술 요구사항

### 4.1 신규 DB 모델 (마이그레이션 0009)

```sql
-- YOLOv8 학습 데이터셋
annotation_datasets
  id              UUID PK
  version         VARCHAR(20)          -- v1.0, v1.1, ...
  image_count     INTEGER
  label_counts    JSONB                -- {"hole": 1240, "bend": 890, ...}
  s3_path         VARCHAR(500)         -- MinIO 내 YOLO format 데이터셋 경로
  built_at        TIMESTAMPTZ
  created_by      UUID FK → users
  created_at      TIMESTAMPTZ DEFAULT NOW()

-- 학습 잡
training_jobs
  id              UUID PK
  dataset_id      UUID FK → annotation_datasets
  model_version   VARCHAR(20)          -- yolov8n/yolov8s/yolov8m
  epochs          INTEGER DEFAULT 100
  batch_size      INTEGER DEFAULT 16
  img_size        INTEGER DEFAULT 640
  status          VARCHAR(20)          -- pending/running/completed/failed
  train_map50     DECIMAL(6,4)         -- mAP@0.5 on train set
  val_map50       DECIMAL(6,4)         -- mAP@0.5 on val set
  model_s3_path   VARCHAR(500)         -- MinIO 내 .pt 파일 경로
  mlflow_run_id   VARCHAR(100)
  is_active       BOOLEAN DEFAULT FALSE
  started_at      TIMESTAMPTZ
  completed_at    TIMESTAMPTZ
  error_message   TEXT
  created_by      UUID FK → users
  created_at      TIMESTAMPTZ DEFAULT NOW()

-- 어노테이션 태스크
annotation_tasks
  id              UUID PK
  drawing_id      UUID FK → cad_drawings
  status          VARCHAR(20)          -- pending/in_progress/completed/skipped
  original_parsed JSONB                -- AI 원본 결과 (수정 전)
  corrected_parsed JSONB               -- 어노테이터 수정 결과
  annotator_id    UUID FK → users (nullable)
  assigned_at     TIMESTAMPTZ
  completed_at    TIMESTAMPTZ
  created_at      TIMESTAMPTZ DEFAULT NOW()

-- BOM 헤더
bom_headers
  id              UUID PK
  quotation_id    UUID FK → quotations UNIQUE
  order_id        UUID FK → orders (nullable)
  revision        SMALLINT DEFAULT 1
  total_weight_kg DECIMAL(10,3)
  notes           TEXT
  created_by      UUID FK → users
  created_at      TIMESTAMPTZ DEFAULT NOW()

-- BOM 항목
bom_items
  id              UUID PK
  bom_id          UUID FK → bom_headers ON DELETE CASCADE
  material_code   VARCHAR(50)
  specification   VARCHAR(200)         -- 두께×폭×길이 또는 규격코드
  quantity        DECIMAL(10,3)
  unit            VARCHAR(20)          -- kg/m/ea
  unit_weight_kg  DECIMAL(10,4)
  total_weight_kg DECIMAL(10,3)
  sort_order      SMALLINT DEFAULT 0
  created_at      TIMESTAMPTZ DEFAULT NOW()

-- DXF 레이어 매핑
dxf_layer_mappings
  id              UUID PK
  layer_pattern   VARCHAR(100)         -- e.g., "HOLE*", "BEND_*", "*CUT*"
  process_type    VARCHAR(50)          -- cutting/drilling/bending/welding
  priority        SMALLINT DEFAULT 0   -- 매칭 우선순위
  is_active       BOOLEAN DEFAULT TRUE
  created_at      TIMESTAMPTZ DEFAULT NOW()
```

### 4.2 신규 서비스

```
backend/app/services/
  dxf_parser_service.py    — ezdxf DWG/DXF → parsed_objects JSON
  bom_service.py           — quotation_items → BOM 생성, Excel 내보내기
  yolo_service.py          — YOLOv8 추론, 이미지 전처리, 결과 변환
  training_service.py      — 데이터셋 빌드, Celery 학습 태스크 관리

backend/app/tasks/
  training_tasks.py        — train_yolo_model_task (GPU 워커, train_queue)
  dxf_tasks.py             — parse_dxf_task (cad_queue)
```

### 4.3 신규 API 엔드포인트

```
# YOLOv8 학습 관리
POST   /api/v1/ml/datasets/build          — 어노테이션 → 데이터셋 패키징
GET    /api/v1/ml/datasets                — 데이터셋 목록
POST   /api/v1/ml/training-jobs           — 학습 잡 시작
GET    /api/v1/ml/training-jobs/{id}      — 학습 잡 상태 조회
PATCH  /api/v1/ml/training-jobs/{id}/activate — 모델 활성화

# 어노테이션
GET    /api/v1/cad/{id}/annotation-task   — 어노테이션 태스크 조회
PUT    /api/v1/cad/{id}/annotation        — 분석 결과 수정 + 완료
GET    /api/v1/ml/annotation-tasks        — 미완료 태스크 목록

# BOM
POST   /api/v1/quotations/{id}/bom        — BOM 생성
GET    /api/v1/quotations/{id}/bom        — BOM 조회
GET    /api/v1/bom/{id}/export            — Excel 내보내기 (?format=xlsx)
```

### 4.4 프론트엔드 신규 파일

```
frontend/src/
  lib/hooks/
    use-ml.ts               — useTrainingJobs, useActivateModel, useDatasetBuild
    use-annotation.ts       — useAnnotationTask, useSubmitAnnotation, usePendingTasks
    use-bom.ts              — useBom, useGenerateBom, useExportBom

  components/
    ml/
      annotation-editor.tsx  — 객체 목록 편집 + 치수 수정 인터페이스
      training-job-card.tsx  — 학습 잡 상태 카드 (mAP, 진행률)
      dataset-builder.tsx    — 데이터셋 빌드 버튼 + 통계 표시
    quotation/
      bom-table.tsx          — BOM 항목 테이블 + Excel 내보내기 버튼

  app/(dashboard)/
    ml/
      annotation/page.tsx    — 어노테이션 태스크 목록 + 에디터
      training/page.tsx      — 학습 잡 관리 + 모델 버전 히스토리
```

### 4.5 의존성 추가

```
# backend/requirements.txt
ultralytics==8.2.0          — YOLOv8
ezdxf==1.3.4                — DWG/DXF 파싱
mlflow==2.13.0              — 실험 추적
openpyxl==3.1.3             — BOM Excel 내보내기
```

```yaml
# docker-compose.yml 추가 서비스
mlflow:
  image: ghcr.io/mlflow/mlflow:v2.13.0
  ports: ["5000:5000"]
  environment:
    MLFLOW_BACKEND_STORE_URI: postgresql://...
    MLFLOW_DEFAULT_ARTIFACT_ROOT: s3://mlflow/artifacts

celery-gpu-worker:           — 학습 전용 GPU 워커 (train_queue)
  command: celery worker -A app.core.celery_app -Q train_queue --concurrency 1
```

---

## 5. 아키텍처 다이어그램

```
┌────────────────────────────────────────────────────────────┐
│                    CAD 분석 라우팅 (Sprint 6)              │
│                                                            │
│  업로드된 파일                                              │
│      │                                                     │
│      ├─ .dxf/.dwg ──→ DxfParserService ──→ parsed_objects │
│      │                   (ezdxf)            (즉시, 5s이내)  │
│      │                                                     │
│      └─ .pdf/.png/.jpg → 활성 모델 확인                    │
│                              │                             │
│                    ┌─────────┴─────────┐                   │
│                    ↓                   ↓                   │
│             YOLOv8 모델           GPT-4o Vision            │
│             (is_active=True)       (폴백)                  │
│             3초 추론               30초 API 호출            │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                  Active Learning 사이클                    │
│                                                            │
│  cad_drawings.parsed_objects                               │
│       │                                                    │
│  영업담당자 검토 → 오류 발견                                 │
│       │                                                    │
│  annotation_tasks 생성                                     │
│       │                                                    │
│  AnnotationEditor UI → corrected_parsed 저장              │
│       │                                                    │
│  BuildDataset → annotation_datasets (YOLO format)         │
│       │                                                    │
│  train_yolo_model_task → MLflow 추적                       │
│       │                                                    │
│  val_map50 ≥ 0.85 → activate → 다음 분석부터 YOLOv8 사용  │
└────────────────────────────────────────────────────────────┘
```

---

## 6. 리스크 및 완화 방안

| # | 리스크 | 가능성 | 영향 | 완화 방안 |
|---|--------|--------|------|-----------|
| R-01 | Sprint 5 데이터 500장 미달 | 중 | 중 | GPT-4o 폴백 유지 + 데이터 부족 시 학습 잡 차단 |
| R-02 | DWG 바이너리 포맷 파싱 실패 | 중 | 중 | ezdxf는 DXF만 네이티브 지원, DWG는 변환 레이어(ODA) 필요 |
| R-03 | GPU 워커 인프라 미구성 | 높음 | 높음 | CPU로 학습 가능하지만 시간 증가 (10h vs 1h); Phase 3 인프라 확보 필요 |
| R-04 | YOLOv8 mAP 미달 (<0.85) | 낮음 | 높음 | GPT-4o 폴백 유지로 서비스 연속성 보장 |
| R-05 | BOM 자동생성 정확도 | 중 | 중 | 초기에는 검토 후 승인 프로세스 필수, 자동화 수준 점진적 향상 |

**R-02 DWG 대응 전략**:
- Sprint 6에서는 DXF만 지원 (ezdxf 네이티브)
- DWG → DXF 변환: 고객에게 DXF 제출 요청하거나, LibreCAD CLI 컨버터 통합 (Sprint 7)
- `CadAnalysisService.detect_format()`: `.dwg` 확장자 감지 시 "DXF 형식으로 재업로드 요청" 메시지 반환

---

## 7. 구현 순서 (권장)

```
Phase A: 기반 인프라 (1주)
  1. Migration 0009 — annotation_datasets, training_jobs, annotation_tasks, bom_headers, bom_items, dxf_layer_mappings
  2. 신규 모델 파일 — annotation.py, training.py, bom.py
  3. docker-compose MLflow 서비스 추가
  4. requirements.txt — ultralytics, ezdxf, mlflow, openpyxl

Phase B: DXF 파싱 (3일)
  5. DxfParserService — ezdxf 파싱 + parsed_objects 변환
  6. dxf_tasks.py — parse_dxf_task Celery 태스크
  7. CadAnalysisService 라우팅 로직 업데이트 (DXF 분기)
  8. files.py API — DXF/DWG MIME 타입 허용 추가

Phase C: Active Learning (3일)
  9. AnnotationTaskService — 태스크 생성, 할당, 완료
  10. annotation API 엔드포인트 (3개)
  11. AnnotationEditor 컴포넌트
  12. ml/annotation/page.tsx

Phase D: YOLOv8 파이프라인 (3일)
  13. YoloService — 추론, 이미지 전처리
  14. TrainingService — 데이터셋 빌드, 학습 파라미터
  15. training_tasks.py — train_yolo_model_task
  16. ML API 엔드포인트 (5개)
  17. training/page.tsx, training-job-card.tsx

Phase E: BOM (2일)
  18. BomService — generate_from_quotation, Excel 내보내기
  19. BOM API 엔드포인트 (3개)
  20. bom-table.tsx 컴포넌트

Phase F: 통합 및 정리 (1일)
  21. router.py — 신규 라우터 등록
  22. celery_app.py — train_queue 추가
  23. link_order() → BOM 자동생성 트리거 연결
```

---

## 8. 인수 기준 (Definition of Done)

- [ ] `annotation_tasks`, `training_jobs`, `bom_headers`, `bom_items` 테이블 마이그레이션 완료
- [ ] DXF 파일 업로드 → `parsed_objects` 추출 성공 (ezdxf)
- [ ] 어노테이션 에디터에서 AI 결과 수정 → `corrected_parsed` 저장 가능
- [ ] 데이터셋 빌드 → MLflow 실험 생성 → 학습 잡 시작 가능
- [ ] YOLOv8 활성 모델 설정 시 새 분석 요청에 YOLOv8 라우팅
- [ ] 확정 견적(accepted 상태)에서 BOM 자동생성 → Excel 내보내기
- [ ] Gap Analysis Match Rate ≥ 90%

---

## 9. 다음 단계

**Sprint 7**: XGBoost 보정 모델 + SHAP 영향요인 분석  
- 규칙 기반 견적 오차 분석 (실제 수주금액 vs 견적금액)
- XGBoost 회귀 모델로 오차 보정 계수 학습
- SHAP 값 기반 견적 영향요인 대시보드
- DWG → DXF 변환 자동화 (LibreCAD CLI 통합)
