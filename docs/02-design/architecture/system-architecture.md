# Onetouch AI+MES System Architecture

> **Summary**: 원터치 AI+MES 시스템의 프로젝트 구조, 개발/운영 인프라, 환경 설정, RBAC, IoT 스트리밍 파이프라인, 핵심 백엔드 코드 패턴을 정의한 시스템 아키텍처 문서
>
> **Project**: Metal-Onetouch AI+MES
> **Version**: 1.0
> **Author**: Enterprise Architect Agent (superpjh@gmail.com)
> **Date**: 2026-04-30
> **Status**: Draft
> **Reference**: `docs/01-plan/PM1-architecture-plan.md`, `docs/01-plan/PM3-data-architecture-plan.md`

---

## 1. 프로젝트 디렉토리 구조

원터치 AI+MES는 모노레포(monorepo) 구조를 채택한다. AI 코드 생성 도구가 전체 컨텍스트를 한번에 파악하고, frontend/backend/infra 간 atomic commit이 가능하도록 한다.

```
metal-onetouch/
├── frontend/                              # Next.js 14 App Router
│   ├── app/                               # 라우팅 (App Router)
│   │   ├── (auth)/                        # 인증 그룹 라우트
│   │   │   ├── login/page.tsx
│   │   │   └── layout.tsx
│   │   ├── (dashboard)/                   # 인증된 사용자 그룹
│   │   │   ├── layout.tsx                 # 사이드바 + 헤더
│   │   │   ├── page.tsx                   # AI 대시보드 (홈)
│   │   │   ├── ai-dashboard/              # 모듈 1: AI 대시보드
│   │   │   │   ├── production/page.tsx
│   │   │   │   ├── quality/page.tsx
│   │   │   │   ├── equipment/page.tsx
│   │   │   │   └── shipment/page.tsx
│   │   │   ├── process/                   # 모듈 2: 공정관리
│   │   │   │   ├── records/page.tsx
│   │   │   │   ├── monitoring/page.tsx
│   │   │   │   ├── conditions/page.tsx
│   │   │   │   └── history/page.tsx
│   │   │   ├── inventory/                 # 모듈 3: 입고재고관리
│   │   │   │   ├── receipts/page.tsx
│   │   │   │   ├── traceability/page.tsx
│   │   │   │   └── supplier-quality/page.tsx
│   │   │   ├── shipment/                  # 모듈 4: 출하물류관리
│   │   │   │   ├── orders/page.tsx
│   │   │   │   ├── lot-tracking/page.tsx
│   │   │   │   ├── inspection/page.tsx
│   │   │   │   └── claims/page.tsx
│   │   │   ├── quotation/                 # 모듈 5: 수주견적AI관리
│   │   │   │   ├── upload/page.tsx        # CAD 업로드
│   │   │   │   ├── analysis/[id]/page.tsx # Vision AI 분석 결과
│   │   │   │   └── shap/[id]/page.tsx     # SHAP 분석
│   │   │   ├── master/                    # 모듈 6: 기준정보관리
│   │   │   ├── kpi/                       # 모듈 7: KPI관리
│   │   │   ├── data-hub/                  # 모듈 8: 데이터허브관리
│   │   │   ├── ai-agent/                  # 모듈 9: AI Agent 통합관리
│   │   │   │   ├── chat/page.tsx
│   │   │   │   └── history/page.tsx
│   │   │   └── system/                    # 모듈 10: 사용자/시스템관리
│   │   │       ├── users/page.tsx
│   │   │       ├── roles/page.tsx
│   │   │       └── settings/page.tsx
│   │   ├── api/                           # Next.js API routes (proxy 용도)
│   │   │   └── auth/[...nextauth]/route.ts
│   │   ├── globals.css                    # Tailwind 글로벌 스타일
│   │   └── layout.tsx                     # 루트 레이아웃
│   ├── components/                        # React 컴포넌트
│   │   ├── ui/                            # shadcn/ui 컴포넌트
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── data-table.tsx             # 공통 테이블
│   │   │   └── ...
│   │   ├── charts/                        # Recharts 래퍼
│   │   │   ├── line-chart.tsx
│   │   │   ├── kpi-card.tsx
│   │   │   ├── shap-plot.tsx              # SHAP 시각화
│   │   │   └── sensor-stream.tsx          # 실시간 센서 차트
│   │   ├── ai/                            # AI 전용 컴포넌트
│   │   │   ├── chat-window.tsx            # 스트리밍 채팅
│   │   │   ├── citation-card.tsx          # RAG 출처 표시
│   │   │   └── cad-viewer.tsx             # CAD 뷰어
│   │   ├── forms/                         # 폼 컴포넌트
│   │   │   ├── lot-input-form.tsx
│   │   │   └── inspection-form.tsx
│   │   └── layout/                        # 레이아웃 컴포넌트
│   │       ├── sidebar.tsx
│   │       ├── header.tsx
│   │       └── breadcrumb.tsx
│   ├── lib/                               # 유틸리티
│   │   ├── api/                           # API 클라이언트
│   │   │   ├── client.ts                  # Axios 인스턴스
│   │   │   ├── lots.ts                    # LOT 관련 API
│   │   │   ├── quotation.ts               # 견적 API
│   │   │   └── ai.ts                      # AI Agent API
│   │   ├── hooks/                         # React 훅
│   │   │   ├── use-auth.ts
│   │   │   ├── use-socket.ts              # Socket.io 훅
│   │   │   └── use-rbac.ts                # 권한 체크 훅
│   │   ├── stores/                        # Zustand 스토어
│   │   │   ├── auth-store.ts
│   │   │   └── ui-store.ts
│   │   ├── utils/
│   │   │   ├── format.ts                  # 날짜/숫자 포매팅
│   │   │   └── validation.ts              # Zod 스키마
│   │   └── constants.ts                   # 상수
│   ├── public/                            # 정적 파일
│   ├── .env.local.example                 # 환경변수 예시
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── backend/                               # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py                        # FastAPI 엔트리포인트
│   │   ├── api/                           # API 라우터
│   │   │   ├── deps.py                    # 공통 Depends (DB, Auth)
│   │   │   └── v1/
│   │   │       ├── router.py              # v1 메인 라우터
│   │   │       ├── auth.py                # 로그인/토큰
│   │   │       ├── users.py               # 사용자 관리
│   │   │       ├── lots.py                # LOT CRUD/추적
│   │   │       ├── processes.py           # 공정관리
│   │   │       ├── inventory.py           # 입고재고
│   │   │       ├── shipment.py            # 출하물류
│   │   │       ├── quotation.py           # 견적
│   │   │       ├── master_data.py         # 기준정보
│   │   │       ├── kpi.py                 # KPI 집계
│   │   │       ├── data_hub.py            # 데이터 허브
│   │   │       ├── ai_agent.py            # 통합 AI Agent
│   │   │       └── ws.py                  # WebSocket 엔드포인트
│   │   ├── core/                          # 코어 설정
│   │   │   ├── config.py                  # Pydantic Settings
│   │   │   ├── security.py                # JWT, RBAC
│   │   │   ├── database.py                # SQLAlchemy 세션
│   │   │   ├── redis.py                   # Redis 연결
│   │   │   ├── kafka.py                   # Kafka 프로듀서
│   │   │   ├── minio.py                   # MinIO 클라이언트
│   │   │   ├── qdrant.py                  # Qdrant 클라이언트
│   │   │   ├── logging.py                 # 구조화 로깅
│   │   │   └── exceptions.py              # 커스텀 예외
│   │   ├── models/                        # SQLAlchemy ORM 모델
│   │   │   ├── base.py                    # 베이스 모델 + 믹스인
│   │   │   ├── user.py
│   │   │   ├── role.py
│   │   │   ├── lot.py
│   │   │   ├── lot_history.py
│   │   │   ├── raw_material.py
│   │   │   ├── process.py
│   │   │   ├── process_record.py
│   │   │   ├── equipment.py
│   │   │   ├── quality_record.py
│   │   │   ├── shipment.py
│   │   │   ├── claim.py
│   │   │   ├── quotation.py
│   │   │   ├── bom.py
│   │   │   └── sensor_data.py             # TimescaleDB hypertable
│   │   ├── schemas/                       # Pydantic v2 스키마
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── lot.py
│   │   │   ├── process.py
│   │   │   ├── inventory.py
│   │   │   ├── shipment.py
│   │   │   ├── quotation.py
│   │   │   ├── kpi.py
│   │   │   └── ai.py
│   │   ├── services/                      # 비즈니스 로직
│   │   │   ├── auth_service.py
│   │   │   ├── lot_service.py
│   │   │   ├── traceability_service.py    # LOT 추적 핵심
│   │   │   ├── process_service.py
│   │   │   ├── inspection_service.py
│   │   │   ├── shipment_service.py
│   │   │   ├── quotation_service.py
│   │   │   ├── kpi_service.py
│   │   │   └── notification_service.py
│   │   ├── workers/                       # Celery 태스크
│   │   │   ├── celery_app.py              # Celery 앱
│   │   │   ├── tasks/
│   │   │   │   ├── cad_parse.py           # 도면 파싱 (비동기)
│   │   │   │   ├── vision_inference.py    # YOLOv8 추론
│   │   │   │   ├── cost_prediction.py     # XGBoost 예측
│   │   │   │   ├── shap_explain.py        # SHAP 분석
│   │   │   │   ├── rag_indexing.py        # RAG 문서 임베딩
│   │   │   │   ├── erp_sync.py            # ERP 동기화
│   │   │   │   └── alert_dispatch.py      # 알림 발송
│   │   │   └── beat_schedule.py           # 정기 작업 스케줄
│   │   ├── ai/                            # AI 모듈
│   │   │   ├── rag/
│   │   │   │   ├── agent.py               # LangChain RAG 에이전트
│   │   │   │   ├── retriever.py           # Qdrant 검색
│   │   │   │   ├── embeddings.py          # BGE-M3 임베딩
│   │   │   │   ├── ingestion.py           # 문서 인덱싱
│   │   │   │   └── prompts/
│   │   │   │       ├── system_prompt.txt
│   │   │   │       └── tool_prompts.txt
│   │   │   ├── vision/
│   │   │   │   ├── cad_parser.py          # ezdxf/pdfplumber
│   │   │   │   ├── yolo_detector.py       # YOLOv8 추론
│   │   │   │   ├── feature_extractor.py   # 형상/치수/공차
│   │   │   │   └── models/                # 학습된 가중치 (.pt)
│   │   │   ├── ml/
│   │   │   │   ├── cost_model.py          # XGBoost 원가 예측
│   │   │   │   ├── anomaly_detector.py    # Isolation Forest
│   │   │   │   ├── shap_explainer.py      # SHAP 분석
│   │   │   │   └── feature_pipeline.py
│   │   │   ├── agents/
│   │   │   │   ├── inbound_agent.py       # 입고 AI Agent
│   │   │   │   ├── outbound_agent.py      # 출하 AI Agent
│   │   │   │   ├── quotation_agent.py     # 견적 AI Agent
│   │   │   │   └── master_agent.py        # 통합 AI Agent
│   │   │   └── tools/                     # LangChain Tool
│   │   │       ├── lot_lookup_tool.py
│   │   │       ├── kpi_query_tool.py
│   │   │       └── sensor_query_tool.py
│   │   └── integrations/                  # 외부 시스템
│   │       ├── erp/
│   │       │   ├── erp_adapter.py         # ERP REST/DB
│   │       │   └── erp_schemas.py
│   │       ├── mqtt/
│   │       │   └── mqtt_consumer.py
│   │       └── kafka/
│   │           ├── producer.py
│   │           └── consumer.py
│   ├── alembic/                           # DB 마이그레이션
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   ├── tests/                             # pytest
│   │   ├── conftest.py
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── scripts/
│   │   ├── init_db.py                     # 초기 데이터 시딩
│   │   ├── seed_master_data.py
│   │   └── create_admin.py
│   ├── pyproject.toml
│   ├── poetry.lock
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── streaming/                             # IoT/스트리밍 처리
│   ├── flink/                             # Apache Flink Jobs
│   │   ├── jobs/
│   │   │   ├── job1_storage.py            # Kafka → TimescaleDB
│   │   │   ├── job2_anomaly.py            # 이상 감지
│   │   │   └── job3_alert.py              # 알림 라우팅
│   │   └── Dockerfile
│   └── mqtt-bridge/                       # MQTT → Kafka 브릿지
│       ├── bridge.py
│       └── Dockerfile
│
├── infra/                                 # 인프라
│   ├── docker/                            # 개발용 Docker Compose
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.override.yml    # 로컬 오버라이드
│   │   ├── postgres/
│   │   │   ├── init.sql                   # TimescaleDB 확장 활성화
│   │   │   └── Dockerfile
│   │   ├── mosquitto/
│   │   │   └── mosquitto.conf
│   │   ├── kafka/
│   │   │   └── server.properties
│   │   └── nginx/
│   │       └── nginx.conf
│   ├── k8s/                               # 운영용 Kubernetes
│   │   ├── base/                          # 공통 manifest
│   │   │   ├── frontend/
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── service.yaml
│   │   │   │   └── ingress.yaml
│   │   │   ├── backend/
│   │   │   ├── celery-worker/
│   │   │   ├── postgres/                  # StatefulSet
│   │   │   ├── redis/
│   │   │   ├── kafka/                     # Strimzi operator
│   │   │   ├── qdrant/
│   │   │   └── monitoring/                # Prometheus + Grafana
│   │   ├── overlays/
│   │   │   ├── staging/
│   │   │   └── production/
│   │   └── kustomization.yaml
│   ├── terraform/                         # AWS IaC
│   │   ├── modules/
│   │   │   ├── eks/
│   │   │   ├── rds/
│   │   │   ├── s3/
│   │   │   └── vpc/
│   │   └── environments/
│   │       ├── staging/
│   │       └── production/
│   └── argocd/                            # GitOps
│       ├── apps/
│       └── projects/
│
├── packages/                              # 모노레포 공유 패키지 (선택적)
│   ├── shared-types/                      # TS/Python 공유 타입 정의
│   └── api-client-ts/                     # 자동 생성 API 클라이언트
│
├── docs/                                  # PDCA 문서
│   ├── 00-requirement/
│   ├── 01-plan/                           # 본 프로젝트 계획서
│   ├── 02-design/
│   │   ├── architecture/                  # 본 문서 위치
│   │   ├── features/
│   │   └── api-spec/
│   ├── 03-refactoring/
│   └── 04-operation/
│
├── scripts/                               # 모노레포 유틸 스크립트
│   ├── dev-up.sh                          # docker compose up
│   ├── dev-down.sh
│   ├── seed.sh                            # 초기 데이터
│   └── test-all.sh
│
├── .github/
│   └── workflows/
│       ├── frontend-ci.yml
│       ├── backend-ci.yml
│       ├── docker-build.yml
│       └── deploy-staging.yml
│
├── .gitignore
├── .editorconfig
├── README.md
├── CLAUDE.md                              # 프로젝트 전체 컨텍스트
├── pnpm-workspace.yaml                    # pnpm 워크스페이스
└── turbo.json                             # Turborepo 설정 (선택적)
```

---

## 2. Docker Compose 구성 (개발 환경)

### 2.1 `infra/docker/docker-compose.yml`

```yaml
version: "3.9"

x-app-env: &app-env
  TZ: Asia/Seoul
  ENV: development

networks:
  onetouch-net:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
  minio-data:
  qdrant-data:
  kafka-data:
  zookeeper-data:
  mlflow-artifacts:

services:
  # ─────────────────────────────────────────
  # 1) Frontend (Next.js 14)
  # ─────────────────────────────────────────
  frontend:
    build:
      context: ../../frontend
      dockerfile: Dockerfile
      target: dev
    container_name: onetouch-frontend
    ports:
      - "3000:3000"
    environment:
      <<: *app-env
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXT_PUBLIC_WS_URL: ws://localhost:8000
      NEXTAUTH_URL: http://localhost:3000
      NEXTAUTH_SECRET: ${NEXTAUTH_SECRET}
    volumes:
      - ../../frontend:/app
      - /app/node_modules
      - /app/.next
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - onetouch-net
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ─────────────────────────────────────────
  # 2) Backend (FastAPI)
  # ─────────────────────────────────────────
  backend:
    build:
      context: ../../backend
      dockerfile: Dockerfile
      target: dev
    container_name: onetouch-backend
    ports:
      - "8000:8000"
    environment:
      <<: *app-env
      DATABASE_URL: postgresql+asyncpg://onetouch:${POSTGRES_PASSWORD}@postgres:5432/onetouch
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      QDRANT_URL: http://qdrant:6333
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      MQTT_BROKER_URL: mqtt://mosquitto:1883
      MLFLOW_TRACKING_URI: http://mlflow:5000
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
    volumes:
      - ../../backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
      qdrant:
        condition: service_started
      kafka:
        condition: service_started
    networks:
      - onetouch-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 5s
      retries: 5
    command: >
      uvicorn app.main:app
      --host 0.0.0.0 --port 8000
      --reload --reload-dir app

  # ─────────────────────────────────────────
  # 3) Celery Worker
  # ─────────────────────────────────────────
  celery-worker:
    build:
      context: ../../backend
      dockerfile: Dockerfile
      target: dev
    container_name: onetouch-celery-worker
    environment:
      <<: *app-env
      DATABASE_URL: postgresql+asyncpg://onetouch:${POSTGRES_PASSWORD}@postgres:5432/onetouch
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      QDRANT_URL: http://qdrant:6333
      MLFLOW_TRACKING_URI: http://mlflow:5000
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    volumes:
      - ../../backend:/app
    depends_on:
      backend:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - onetouch-net
    command: >
      celery -A app.workers.celery_app worker
      -Q default,ai,vision,erp
      --loglevel=info --concurrency=4

  celery-beat:
    build:
      context: ../../backend
      dockerfile: Dockerfile
      target: dev
    container_name: onetouch-celery-beat
    environment:
      <<: *app-env
      CELERY_BROKER_URL: redis://redis:6379/1
    volumes:
      - ../../backend:/app
    depends_on:
      - redis
    networks:
      - onetouch-net
    command: celery -A app.workers.celery_app beat --loglevel=info

  # ─────────────────────────────────────────
  # 4) PostgreSQL 16 + TimescaleDB
  # ─────────────────────────────────────────
  postgres:
    image: timescale/timescaledb:latest-pg16
    container_name: onetouch-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: onetouch
      POSTGRES_USER: onetouch
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      TZ: Asia/Seoul
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - onetouch-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U onetouch -d onetouch"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ─────────────────────────────────────────
  # 5) Redis 7
  # ─────────────────────────────────────────
  redis:
    image: redis:7-alpine
    container_name: onetouch-redis
    ports:
      - "6379:6379"
    command: ["redis-server", "--appendonly", "yes", "--requirepass", "${REDIS_PASSWORD}"]
    volumes:
      - redis-data:/data
    networks:
      - onetouch-net
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # ─────────────────────────────────────────
  # 6) MinIO (S3 호환 오브젝트 스토리지)
  # ─────────────────────────────────────────
  minio:
    image: minio/minio:latest
    container_name: onetouch-minio
    ports:
      - "9000:9000"   # API
      - "9001:9001"   # Console
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio-data:/data
    command: server /data --console-address ":9001"
    networks:
      - onetouch-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 15s
      timeout: 5s
      retries: 5

  # ─────────────────────────────────────────
  # 7) Qdrant (벡터 DB)
  # ─────────────────────────────────────────
  qdrant:
    image: qdrant/qdrant:latest
    container_name: onetouch-qdrant
    ports:
      - "6333:6333"   # REST
      - "6334:6334"   # gRPC
    volumes:
      - qdrant-data:/qdrant/storage
    networks:
      - onetouch-net
    environment:
      QDRANT__SERVICE__API_KEY: ${QDRANT_API_KEY}

  # ─────────────────────────────────────────
  # 8) Kafka + Zookeeper
  # ─────────────────────────────────────────
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    container_name: onetouch-zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    volumes:
      - zookeeper-data:/var/lib/zookeeper/data
    networks:
      - onetouch-net

  kafka:
    image: confluentinc/cp-kafka:7.6.0
    container_name: onetouch-kafka
    ports:
      - "9092:9092"
      - "9094:9094"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT
      KAFKA_LISTENERS: INTERNAL://0.0.0.0:9092,EXTERNAL://0.0.0.0:9094
      KAFKA_ADVERTISED_LISTENERS: INTERNAL://kafka:9092,EXTERNAL://localhost:9094
      KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
    volumes:
      - kafka-data:/var/lib/kafka/data
    depends_on:
      - zookeeper
    networks:
      - onetouch-net

  # ─────────────────────────────────────────
  # 9) MQTT (Eclipse Mosquitto)
  # ─────────────────────────────────────────
  mosquitto:
    image: eclipse-mosquitto:2.0
    container_name: onetouch-mosquitto
    ports:
      - "1883:1883"
      - "9001:9001"   # WebSocket (충돌 시 9081로 변경)
    volumes:
      - ./mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
    networks:
      - onetouch-net

  # ─────────────────────────────────────────
  # 10) MLflow (실험 추적)
  # ─────────────────────────────────────────
  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.13.0
    container_name: onetouch-mlflow
    ports:
      - "5000:5000"
    environment:
      MLFLOW_S3_ENDPOINT_URL: http://minio:9000
      AWS_ACCESS_KEY_ID: ${MINIO_ROOT_USER}
      AWS_SECRET_ACCESS_KEY: ${MINIO_ROOT_PASSWORD}
    volumes:
      - mlflow-artifacts:/mlflow/artifacts
    depends_on:
      - postgres
      - minio
    networks:
      - onetouch-net
    command: >
      mlflow server
      --backend-store-uri postgresql://onetouch:${POSTGRES_PASSWORD}@postgres:5432/mlflow
      --default-artifact-root s3://mlflow/
      --host 0.0.0.0 --port 5000

  # ─────────────────────────────────────────
  # 11) MQTT → Kafka Bridge
  # ─────────────────────────────────────────
  mqtt-bridge:
    build:
      context: ../../streaming/mqtt-bridge
    container_name: onetouch-mqtt-bridge
    environment:
      MQTT_BROKER_URL: mqtt://mosquitto:1883
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
    depends_on:
      - mosquitto
      - kafka
    networks:
      - onetouch-net
```

> Note: `mosquitto`와 `minio` Console이 둘 다 9001을 사용하지 않도록 한 쪽 포트를 변경한다(예: minio console을 9001 대신 9101로). 위 예시에서는 mosquitto 9001 → 9081로 옮기는 것을 권장.

### 2.2 Postgres 초기화 스크립트 (`infra/docker/postgres/init.sql`)

```sql
-- TimescaleDB 확장
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- MLflow 데이터베이스
CREATE DATABASE mlflow;
GRANT ALL PRIVILEGES ON DATABASE mlflow TO onetouch;
```

---

## 3. 환경변수 설계

### 3.1 Backend `.env.example`

```bash
# ─── Application ───────────────────────────
ENV=development
APP_NAME=onetouch-backend
LOG_LEVEL=INFO
TZ=Asia/Seoul

# ─── Database (PostgreSQL + TimescaleDB) ───
DATABASE_URL=postgresql+asyncpg://onetouch:CHANGE_ME@postgres:5432/onetouch
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
POSTGRES_PASSWORD=CHANGE_ME

# ─── Redis ─────────────────────────────────
REDIS_URL=redis://:CHANGE_ME@redis:6379/0
REDIS_PASSWORD=CHANGE_ME
CELERY_BROKER_URL=redis://:CHANGE_ME@redis:6379/1
CELERY_RESULT_BACKEND=redis://:CHANGE_ME@redis:6379/2

# ─── MinIO (S3 호환) ───────────────────────
MINIO_ENDPOINT=minio:9000
MINIO_ROOT_USER=onetouch_admin
MINIO_ROOT_PASSWORD=CHANGE_ME
MINIO_BUCKET_CAD=cad-files
MINIO_BUCKET_INSPECTION=inspection-images
MINIO_BUCKET_REPORTS=reports
MINIO_USE_SSL=false

# ─── Qdrant (Vector DB) ────────────────────
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=CHANGE_ME
QDRANT_COLLECTION_INBOUND=onetouch_inbound
QDRANT_COLLECTION_OUTBOUND=onetouch_outbound
QDRANT_COLLECTION_MASTER=onetouch_master

# ─── Kafka ─────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_RAW_PROCESS=raw.sensor.process
KAFKA_TOPIC_RAW_EQUIPMENT=raw.sensor.equipment
KAFKA_TOPIC_PROCESSED_ANOMALY=processed.anomaly
KAFKA_TOPIC_ALERT_EQUIPMENT=alert.equipment
KAFKA_CONSUMER_GROUP=onetouch-backend

# ─── MQTT ──────────────────────────────────
MQTT_BROKER_URL=mqtt://mosquitto:1883
MQTT_USERNAME=onetouch
MQTT_PASSWORD=CHANGE_ME
MQTT_TOPIC_PREFIX=onetouch/

# ─── LLM API ───────────────────────────────
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LLM_PRIMARY=gpt-4o
LLM_FALLBACK=claude-3-5-sonnet-20241022
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=4096
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIMENSION=1024

# ─── JWT 인증 ──────────────────────────────
JWT_SECRET_KEY=CHANGE_ME_TO_LONG_RANDOM_STRING
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_MINUTES=10080   # 7 days
JWT_ISSUER=onetouch-mes

# ─── MLflow ────────────────────────────────
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_S3_ENDPOINT_URL=http://minio:9000
MLFLOW_REGISTRY_URI=http://mlflow:5000

# ─── ERP 연동 ──────────────────────────────
ERP_BASE_URL=http://erp.internal:8080/api
ERP_API_KEY=CHANGE_ME
ERP_SYNC_INTERVAL_SECONDS=300

# ─── 보안/CORS ─────────────────────────────
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://onetouch.example.com
RATE_LIMIT_PER_MINUTE=120

# ─── 모니터링 ──────────────────────────────
PROMETHEUS_PORT=9090
SENTRY_DSN=
```

### 3.2 Frontend `.env.local.example`

```bash
# ─── 공개 변수 (브라우저 노출) ─────────────
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_PREFIX=/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_APP_NAME=원터치 AI+MES
NEXT_PUBLIC_DEFAULT_LOCALE=ko-KR

# ─── NextAuth ──────────────────────────────
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=CHANGE_ME_TO_LONG_RANDOM_STRING

# ─── 기능 토글 ─────────────────────────────
NEXT_PUBLIC_ENABLE_AI_AGENT=true
NEXT_PUBLIC_ENABLE_CAD_VIEWER=true

# ─── 외부 서비스 (선택) ────────────────────
NEXT_PUBLIC_SENTRY_DSN=
NEXT_PUBLIC_GA_TRACKING_ID=
```

---

## 4. RBAC 보안 설계

### 4.1 역할 정의 및 권한 매트릭스

| 모듈 / 기능 | production_manager | quality_inspector | process_engineer | executive | sales_engineer |
|---|---|---|---|---|---|
| 공정관리 - 공정실적 | RW | R | RW | R | - |
| 공정관리 - 모니터링 | RW | R | RW | R | - |
| 공정관리 - 작업조건 | R | R | RW | R | - |
| 공정관리 - 이력조회 | RW | RW | RW | R | R |
| 입고재고 - 입고관리 | R | RW | - | R | - |
| 입고재고 - 공급처품질 | R | RW | - | R | R |
| 출하물류 - 출하관리 | RW | RW | - | R | R |
| 출하물류 - LOT추적 | RW | RW | R | R | R |
| 출하물류 - 출하검사 | R | RW | - | R | - |
| 출하물류 - 클레임 | R | RW | R | R | R |
| 수주견적AI | - | - | - | R | RW |
| 기준정보관리 | R | RW | RW | R | - |
| AI 대시보드 | RW | R | R | R | R |
| KPI관리 - 조회 | RW | R | R | R | R |
| KPI관리 - 목표설정 | RW | - | - | RW | - |
| 데이터허브 | R | R | R | R | R |
| AI Agent 통합 | RW | RW | RW | RW | RW |
| 사용자/시스템관리 | - | - | - | RW | - |

> Legend: `R`=Read, `W`=Write, `RW`=둘 다, `-`=접근 불가

### 4.2 권한 모델 (DB 스키마)

```python
# backend/app/models/role.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, JSON, ForeignKey
from app.models.base import Base, TimestampMixin

class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)  # production_manager 등
    name: Mapped[str] = mapped_column(String(100))
    permissions: Mapped[dict] = mapped_column(JSON)
    # permissions 예: {"process.records": ["read", "write"], "kpi.targets": ["read"]}

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
```

### 4.3 FastAPI Depends 권한 체크 패턴

```python
# backend/app/core/security.py
from typing import Iterable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.core.config import settings
from app.api.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명을 확인할 수 없습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


def require_permission(resource: str, action: str = "read"):
    """모듈/기능별 권한 체크 Dependency.

    사용 예:
        @router.get("/lots", dependencies=[Depends(require_permission("process.history", "read"))])
    """
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        # 사용자 권한 집합 (역할 → permissions JSON 합친 결과 캐싱)
        user_perms = await _resolve_permissions(current_user)
        allowed_actions = user_perms.get(resource, [])
        if action not in allowed_actions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"권한 없음: {resource} :: {action}",
            )
        return current_user

    return checker


def require_roles(*allowed_roles: str):
    """역할 코드 기반 빠른 체크 (관리자 전용 라우트 등)."""
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        codes = {r.code for r in current_user.roles}
        if not codes.intersection(allowed_roles):
            raise HTTPException(403, detail="해당 역할만 접근 가능합니다")
        return current_user

    return checker
```

### 4.4 라우터 적용 예시

```python
# backend/app/api/v1/lots.py
from fastapi import APIRouter, Depends
from app.core.security import require_permission, get_current_user
from app.schemas.lot import LotCreate, LotRead

router = APIRouter(prefix="/lots", tags=["lots"])

@router.get(
    "/{lot_id}",
    response_model=LotRead,
    dependencies=[Depends(require_permission("process.history", "read"))],
)
async def get_lot(lot_id: str, ...):
    ...

@router.post(
    "/",
    response_model=LotRead,
    dependencies=[Depends(require_permission("process.records", "write"))],
)
async def create_lot(payload: LotCreate, ...):
    ...
```

---

## 5. IoT 스트리밍 파이프라인 상세 설계

### 5.1 토폴로지 개요

```
[Edge / PLC]
    │ OPC-UA / Modbus
    ▼
[IoT Gateway] ── MQTT publish ──> [Mosquitto MQTT Broker]
                                          │
                                          ▼
                                  [MQTT→Kafka Bridge]
                                          │
                                          ▼
            ┌──────────────────────────────────────────────┐
            │             Apache Kafka                      │
            │  raw.sensor.process     raw.sensor.equipment │
            │  processed.anomaly      alert.equipment       │
            └─────────┬───────────┬────────────┬───────────┘
                      │           │            │
                ┌─────▼─────┐ ┌──▼──────┐ ┌──▼─────────┐
                │  Flink    │ │  Flink  │ │  Flink     │
                │  Job 1    │ │  Job 2  │ │  Job 3     │
                │ (저장)    │ │(이상감지)│ │(알림라우팅)│
                └─────┬─────┘ └──┬──────┘ └──┬─────────┘
                      │          │           │
                      ▼          ▼           ▼
               TimescaleDB   processed   Redis Pub/Sub
               (hypertable)  .anomaly    + WebSocket
                              topic       (Socket.io)
                                          │
                                          ▼
                                    [Frontend Dashboard]
```

### 5.2 Kafka 토픽 설계

| Topic | Partitions | Retention | Schema | 설명 |
|---|---|---|---|---|
| `raw.sensor.process` | 12 | 7d | `ProcessSensorEvent` | 공정 데이터 (온도/압력/속도/시간) |
| `raw.sensor.equipment` | 12 | 7d | `EquipmentSensorEvent` | 설비 상태 (전류/진동/RPM) |
| `processed.anomaly` | 6 | 30d | `AnomalyEvent` | 이상 감지 결과 |
| `alert.equipment` | 3 | 90d | `AlertEvent` | 작업자/관리자 알림 이벤트 |

**파티션 키**: `equipment_id` (동일 설비 이벤트가 동일 파티션에 모이도록 → 순서 보장)

**메시지 스키마 (Avro/JSON Schema)**:

```json
// EquipmentSensorEvent
{
  "schema_version": "1.0",
  "site_id": "ON-PYT01",
  "equipment_id": "PRESS-03",
  "sensor_type": "current",
  "value": 12.34,
  "unit": "A",
  "ts": "2026-04-30T10:23:45.123Z",
  "lot_id": "L20260430-001",
  "operator_id": "user_12"
}
```

### 5.3 Flink Job 1: 저장 파이프라인 (TimescaleDB)

목적: 원시 센서 데이터를 TimescaleDB hypertable에 적재. 1초 단위 다운샘플링과 함께 영속화.

```python
# streaming/flink/jobs/job1_storage.py (PyFlink pseudo-code)
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.common.serialization import JsonRowDeserializationSchema
from pyflink.common.time import Time

env = StreamExecutionEnvironment.get_execution_environment()
env.enable_checkpointing(60_000)  # 60s

# 1) Kafka → DataStream
source = (
    KafkaSource.builder()
    .set_bootstrap_servers("kafka:9092")
    .set_topics("raw.sensor.process", "raw.sensor.equipment")
    .set_group_id("flink-storage")
    .set_starting_offsets(KafkaOffsetsInitializer.committed_offsets())
    .set_value_only_deserializer(JsonRowDeserializationSchema...)
    .build()
)

ds = env.from_source(source, ...)

# 2) 1초 텀블링 윈도우 평균 (다운샘플링)
keyed = ds.key_by(lambda e: (e.equipment_id, e.sensor_type))
windowed = (
    keyed.window(TumblingProcessingTimeWindows.of(Time.seconds(1)))
         .reduce(lambda a, b: avg(a, b))
)

# 3) JDBC Sink → TimescaleDB hypertable
windowed.add_sink(JdbcSink(
    sql="""
        INSERT INTO sensor_data
        (ts, equipment_id, sensor_type, value, unit, lot_id, site_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    db_url="jdbc:postgresql://postgres:5432/onetouch",
    ...
))

env.execute("job1-storage")
```

TimescaleDB 테이블:

```sql
CREATE TABLE sensor_data (
    ts          TIMESTAMPTZ NOT NULL,
    equipment_id VARCHAR(50) NOT NULL,
    sensor_type  VARCHAR(30) NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    unit         VARCHAR(10),
    lot_id       VARCHAR(20),
    site_id      VARCHAR(20)
);
SELECT create_hypertable('sensor_data', 'ts');
CREATE INDEX ON sensor_data (equipment_id, ts DESC);
SELECT add_retention_policy('sensor_data', INTERVAL '180 days');
```

### 5.4 Flink Job 2: 이상 감지 (Isolation Forest)

목적: 슬라이딩 윈도우 통계와 사전 학습된 Isolation Forest 모델로 실시간 이상 탐지.

```python
# streaming/flink/jobs/job2_anomaly.py (pseudo-code)
import joblib
from pyflink.datastream.functions import KeyedProcessFunction

class AnomalyDetector(KeyedProcessFunction):
    def open(self, ctx):
        # MLflow에서 운영 모델 다운로드 (Isolation Forest)
        self.model = joblib.load("/models/isolation_forest_v3.pkl")
        self.feature_buffer = ctx.get_state(...)  # 60s 슬라이딩 윈도우 버퍼

    def process_element(self, event, ctx):
        self.feature_buffer.add(event)
        features = self._extract_features(self.feature_buffer.get())
        # features = [mean, std, max, min, slope, fft_peak]

        score = self.model.decision_function([features])[0]
        is_anomaly = score < settings.ANOMALY_THRESHOLD  # ex) -0.15

        if is_anomaly:
            yield {
                "ts": event.ts,
                "equipment_id": event.equipment_id,
                "sensor_type": event.sensor_type,
                "anomaly_score": float(score),
                "current_value": event.value,
                "threshold": settings.ANOMALY_THRESHOLD,
                "severity": self._severity(score),
                "lot_id": event.lot_id,
            }

# Kafka source: raw.sensor.equipment
# Sink: processed.anomaly
ds.key_by(lambda e: e.equipment_id) \
  .process(AnomalyDetector()) \
  .add_sink(KafkaSink(topic="processed.anomaly", ...))
```

### 5.5 Flink Job 3: 알림 라우팅

목적: 이상 이벤트를 비즈니스 룰(임계치 + 시간대 + 설비 등급)에 따라 작업자/관리자/모바일 푸시로 라우팅.

```python
# streaming/flink/jobs/job3_alert.py (pseudo-code)
class AlertRouter(KeyedProcessFunction):
    def process_element(self, anomaly_event, ctx):
        # 1) 비즈니스 룰 매칭 (Equipment Master 조회 + 캐시)
        equip_meta = self._fetch_equipment_meta(anomaly_event.equipment_id)
        rule = self._match_rule(anomaly_event, equip_meta)
        if rule is None:
            return  # 룰 매치 안되면 무시

        # 2) 알림 대상 결정 (역할 기반)
        recipients = self._resolve_recipients(rule, equip_meta)
        # 예: process_engineer (해당 라인) + production_manager

        # 3) 중복 억제 (10분 내 동일 설비/센서 알림은 1회만)
        if self._is_duplicate(anomaly_event, window_seconds=600):
            return

        # 4) AlertEvent 생성
        alert = {
            "alert_id": uuid4(),
            "type": "EQUIPMENT_ANOMALY",
            "severity": anomaly_event.severity,
            "equipment_id": anomaly_event.equipment_id,
            "message": rule.message_template.format(...),
            "current_value": anomaly_event.current_value,
            "threshold": rule.threshold,
            "recipients": recipients,
            "ts": anomaly_event.ts,
            "lot_id": anomaly_event.lot_id,
        }
        yield alert

# Sinks:
#   1) Kafka topic alert.equipment (이력 보존)
#   2) Redis Pub/Sub (WebSocket 즉시 푸시)
#   3) Celery 태스크 (이메일/SMS/Push 발송)
```

### 5.6 WebSocket 이벤트 구조 (Socket.io)

Backend에서 Redis Pub/Sub을 구독하여 Socket.io로 브로드캐스트한다.

```typescript
// frontend/lib/types/socket-events.ts

// 1) 설비 센서 실시간 (1초 다운샘플)
export interface EquipmentSensorEvent {
  type: "equipment.sensor";
  ts: string;                  // ISO 8601
  site_id: string;
  equipment_id: string;
  sensor_type: "current" | "temperature" | "vibration" | "rpm";
  value: number;
  unit: string;
  lot_id?: string;
}

// 2) 알림 이벤트
export interface AlertEvent {
  type: "alert";
  alert_id: string;
  category: "EQUIPMENT_ANOMALY" | "QUALITY_FAIL" | "SHIPMENT_HOLD" | "ERP_SYNC_ERROR";
  severity: "info" | "warning" | "critical";
  equipment_id?: string;
  lot_id?: string;
  message: string;
  current_value?: number;
  threshold?: number;
  ts: string;
  link?: string;               // 클릭 시 이동할 라우트
}

// 3) 생산 실적 업데이트
export interface ProductionUpdateEvent {
  type: "production.update";
  ts: string;
  line_id: string;
  target_qty: number;
  actual_qty: number;
  defect_qty: number;
  defect_rate: number;
  oee: number;
  status: "normal" | "warning" | "critical";
}

// 4) AI Agent 스트리밍 응답
export interface AiStreamEvent {
  type: "ai.stream";
  conversation_id: string;
  delta: string;               // 스트리밍 텍스트 청크
  citations?: Array<{ source: string; chunk_id: string }>;
  done: boolean;
}

export type SocketEvent =
  | EquipmentSensorEvent
  | AlertEvent
  | ProductionUpdateEvent
  | AiStreamEvent;
```

Socket.io 채널 네이밍:

```
/ws/equipment/{site_id}            # 사이트별 센서 스트림 (room)
/ws/production/{line_id}           # 라인별 생산 실적
/ws/alerts/{user_id}               # 사용자 개인 알림
/ws/ai/{conversation_id}           # AI 채팅 스트리밍
```

---

## 6. 핵심 백엔드 코드 패턴

### 6.1 `backend/app/core/config.py`

```python
"""Pydantic Settings 기반 설정 모듈.

환경변수 또는 .env 파일에서 자동 로드.
"""
from typing import List, Literal
from pydantic import Field, PostgresDsn, RedisDsn, AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "onetouch-backend"
    ENV: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    TZ: str = "Asia/Seoul"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: RedisDsn
    CELERY_BROKER_URL: RedisDsn
    CELERY_RESULT_BACKEND: RedisDsn

    # Object Storage (MinIO)
    MINIO_ENDPOINT: str
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_USE_SSL: bool = False
    MINIO_BUCKET_CAD: str = "cad-files"
    MINIO_BUCKET_INSPECTION: str = "inspection-images"
    MINIO_BUCKET_REPORTS: str = "reports"

    # Vector DB
    QDRANT_URL: AnyHttpUrl
    QDRANT_API_KEY: str | None = None
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024

    # Kafka / MQTT
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC_RAW_PROCESS: str = "raw.sensor.process"
    KAFKA_TOPIC_RAW_EQUIPMENT: str = "raw.sensor.equipment"
    KAFKA_TOPIC_PROCESSED_ANOMALY: str = "processed.anomaly"
    KAFKA_TOPIC_ALERT_EQUIPMENT: str = "alert.equipment"
    MQTT_BROKER_URL: str

    # LLM
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str | None = None
    LLM_PRIMARY: str = "gpt-4o"
    LLM_FALLBACK: str = "claude-3-5-sonnet-20241022"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 4096

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    JWT_ISSUER: str = "onetouch-mes"

    # MLflow
    MLFLOW_TRACKING_URI: AnyHttpUrl

    # CORS
    CORS_ALLOWED_ORIGINS: List[str] = Field(default_factory=list)

    # Anomaly detection
    ANOMALY_THRESHOLD: float = -0.15

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


settings = Settings()
```

### 6.2 `backend/app/core/security.py`

```python
"""JWT 발급/검증, RBAC Depends 모음."""
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.api.deps import get_db
from app.models.user import User
from app.models.role import Role

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


# ─── Password ──────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─── JWT ───────────────────────────────────
def create_access_token(subject: int | str, extra_claims: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iss": settings.JWT_ISSUER,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: int | str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES),
        "iss": settings.JWT_ISSUER,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ─── Current User ──────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명이 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise cred_exc
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise cred_exc

    result = await db.execute(
        select(User)
        .where(User.id == user_id, User.is_active.is_(True))
        .options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise cred_exc
    return user


# ─── RBAC ──────────────────────────────────
async def _resolve_permissions(user: User) -> dict[str, set[str]]:
    """역할들의 permissions JSON을 합쳐서 {resource: {actions}} 형태로 반환."""
    merged: dict[str, set[str]] = {}
    for role in user.roles:
        for resource, actions in (role.permissions or {}).items():
            merged.setdefault(resource, set()).update(actions)
    return merged


def require_permission(resource: str, action: str = "read"):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        perms = await _resolve_permissions(current_user)
        if action not in perms.get(resource, set()):
            raise HTTPException(403, detail=f"권한 없음: {resource}:{action}")
        return current_user
    return checker


def require_roles(*allowed_roles: str):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        codes = {r.code for r in current_user.roles}
        if not codes.intersection(allowed_roles):
            raise HTTPException(403, detail="해당 역할이 필요합니다")
        return current_user
    return checker
```

### 6.3 `backend/app/core/database.py`

```python
"""SQLAlchemy 2.0 비동기 세션."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)
from app.core.config import settings

engine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=(settings.ENV == "development"),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends 진입점."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 6.4 `backend/app/api/v1/router.py`

```python
"""v1 라우터 등록 패턴."""
from fastapi import APIRouter
from app.api.v1 import (
    auth, users, lots, processes, inventory, shipment,
    quotation, master_data, kpi, data_hub, ai_agent, ws,
)

api_router = APIRouter()

api_router.include_router(auth.router,        prefix="/auth",        tags=["auth"])
api_router.include_router(users.router,       prefix="/users",       tags=["users"])
api_router.include_router(master_data.router, prefix="/master",      tags=["master-data"])
api_router.include_router(lots.router,        prefix="/lots",        tags=["lots"])
api_router.include_router(processes.router,   prefix="/processes",   tags=["processes"])
api_router.include_router(inventory.router,   prefix="/inventory",   tags=["inventory"])
api_router.include_router(shipment.router,    prefix="/shipment",    tags=["shipment"])
api_router.include_router(quotation.router,   prefix="/quotation",   tags=["quotation"])
api_router.include_router(kpi.router,         prefix="/kpi",         tags=["kpi"])
api_router.include_router(data_hub.router,    prefix="/data-hub",    tags=["data-hub"])
api_router.include_router(ai_agent.router,    prefix="/ai",          tags=["ai-agent"])
api_router.include_router(ws.router,          prefix="/ws",          tags=["websocket"])


# ─── main.py ─────────────────────────────
# from fastapi import FastAPI
# from app.api.v1.router import api_router
# from app.core.config import settings
#
# app = FastAPI(title="Onetouch AI+MES API", version="1.0.0")
# app.include_router(api_router, prefix=settings.API_V1_PREFIX)
```

### 6.5 `backend/app/models/lot.py`

```python
"""LOT 추적 기본 단위 모델."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import String, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class LotStatus(str, Enum):
    PENDING_RECEIPT = "입고대기"
    IN_PROCESS = "공정중"
    UNDER_INSPECTION = "검사중"
    READY_TO_SHIP = "출하대기"
    SHIPPED = "출하완료"
    RETURNED = "반품"


class Lot(Base, TimestampMixin):
    __tablename__ = "lots"

    lot_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    raw_material_id: Mapped[str] = mapped_column(
        ForeignKey("raw_materials.material_id"), nullable=False, index=True
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lot_status: Mapped[LotStatus] = mapped_column(String(20), default=LotStatus.PENDING_RECEIPT)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3))   # kg
    parent_lot_id: Mapped[str | None] = mapped_column(
        ForeignKey("lots.lot_id"), nullable=True, index=True
    )

    # Relationships
    raw_material = relationship("RawMaterial", back_populates="lots")
    history = relationship(
        "LotHistory", back_populates="lot",
        cascade="all, delete-orphan", order_by="LotHistory.event_at",
    )
    process_records = relationship("ProcessRecord", back_populates="lot")
    quality_records = relationship("QualityRecord", back_populates="lot")
    parent = relationship("Lot", remote_side="Lot.lot_id")
    children = relationship("Lot", back_populates="parent")

    __table_args__ = (
        Index("ix_lots_status_received", "lot_status", "received_at"),
    )

    def __repr__(self) -> str:
        return f"<Lot {self.lot_id} status={self.lot_status}>"
```

### 6.6 `backend/app/ai/rag/agent.py`

```python
"""LangChain RAG 에이전트 기본 구조.

도메인별 retriever를 주입받아 답변 생성. Tool Calling 으로 SQL 조회/IoT 조회를 결합.
"""
from typing import AsyncIterator, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain.tools import StructuredTool

from app.core.config import settings
from app.ai.rag.retriever import QdrantRetriever
from app.ai.tools.lot_lookup_tool import lot_lookup_tool
from app.ai.tools.kpi_query_tool import kpi_query_tool
from app.ai.tools.sensor_query_tool import sensor_query_tool


SYSTEM_PROMPT = """당신은 원터치 AI+MES 시스템의 도메인 전문가 에이전트입니다.
역할: {role}

규칙:
1. 답변은 반드시 검색된 컨텍스트(<context>)와 도구 결과에 기반합니다.
2. 출처를 [source:chunk_id] 형식으로 명시합니다.
3. 데이터에 없는 내용은 "확인되지 않음"이라고 답변합니다.
4. 한국어로 답변합니다.

<context>
{context}
</context>
"""


class RagAgent:
    def __init__(
        self,
        domain: str,                          # "inbound" / "outbound" / "master"
        role: str,                            # "입고 품질관리 도우미" 등
        tools: List[StructuredTool] | None = None,
    ):
        self.domain = domain
        self.role = role
        self.retriever = QdrantRetriever(collection=f"onetouch_{domain}")
        self.llm = ChatOpenAI(
            model=settings.LLM_PRIMARY,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            api_key=settings.OPENAI_API_KEY,
            streaming=True,
        )
        self.tools = tools or [lot_lookup_tool, kpi_query_tool, sensor_query_tool]
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    async def aretrieve(self, query: str, k: int = 5) -> tuple[str, list[dict]]:
        docs = await self.retriever.asearch(query, k=k)
        context = "\n\n".join(
            f"[{d.metadata['source']}:{d.metadata['chunk_id']}]\n{d.page_content}"
            for d in docs
        )
        citations = [
            {"source": d.metadata["source"], "chunk_id": d.metadata["chunk_id"]}
            for d in docs
        ]
        return context, citations

    async def astream_answer(
        self,
        query: str,
        history: list[HumanMessage | AIMessage] | None = None,
    ) -> AsyncIterator[dict]:
        context, citations = await self.aretrieve(query)

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=SYSTEM_PROMPT.format(role=self.role, context=context)),
            MessagesPlaceholder("history"),
            ("human", "{query}"),
        ])
        chain = prompt | self.llm_with_tools

        async for chunk in chain.astream(
            {"history": history or [], "query": query},
            config=RunnableConfig(tags=[self.domain, "rag-agent"]),
        ):
            yield {
                "delta": chunk.content or "",
                "tool_calls": chunk.tool_calls,
                "citations": citations,
                "done": False,
            }

        yield {"delta": "", "citations": citations, "done": True}


# Factory
def get_inbound_agent() -> RagAgent:
    return RagAgent(domain="inbound", role="입고 품질관리 전문 도우미")

def get_outbound_agent() -> RagAgent:
    return RagAgent(domain="outbound", role="출하/클레임 분석 전문 도우미")

def get_master_agent() -> RagAgent:
    return RagAgent(domain="master", role="MES 통합 도우미")
```

---

## 7. Version History

| Version | Date | Changes | Author |
|---|---|---|---|
| 1.0 | 2026-04-30 | 초기 시스템 아키텍처 문서 작성 | Enterprise Architect |
