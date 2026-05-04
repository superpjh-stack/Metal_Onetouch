from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import check_db_connection
from app.core.exceptions import register_exception_handlers
from app.middleware.audit import AuditMiddleware

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------------------
# Trace ID Middleware
# ------------------------------------------------------------------------------

class TraceIDMiddleware(BaseHTTPMiddleware):
    """
    모든 요청에 UUID trace_id를 주입합니다.

    - X-Request-ID 헤더가 있으면 그 값을 사용합니다.
    - 없으면 새 UUID를 생성합니다.
    - request.state.trace_id에 저장되어 예외 핸들러에서 참조됩니다.
    - 응답 헤더 X-Trace-ID에도 반영됩니다.
    """

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """앱 시작/종료 시 실행되는 lifespan 이벤트"""
    # Startup
    logger.info("Onetouch AI+MES API 서버 시작 중...", version="1.0.0")

    # DB 연결 확인
    db_ok = await check_db_connection()
    if db_ok:
        logger.info("PostgreSQL 연결 성공")
    else:
        logger.warning("PostgreSQL 연결 실패 - 서버는 계속 시작됩니다")

    # Redis 연결 확인
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.aclose()
        logger.info("Redis 연결 성공")
    except Exception as e:
        logger.warning("Redis 연결 실패", error=str(e))

    logger.info("서버 준비 완료", host="0.0.0.0", port=8000)

    yield

    # Shutdown
    logger.info("Onetouch AI+MES API 서버 종료 중...")


def create_application() -> FastAPI:
    app = FastAPI(
        title="Onetouch AI+MES API",
        version="1.0.0",
        description=(
            "원터치 AI+MES (Manufacturing Execution System) REST API\n\n"
            "## 기능\n"
            "- LOT 관리 (생성, 상태 변경, 역추적)\n"
            "- 사용자 인증 (JWT, RBAC)\n"
            "- 생산/품질/공정 데이터 관리\n\n"
            "## 역할 (RBAC)\n"
            "- `production_manager`: 생산 관리자\n"
            "- `quality_inspector`: 품질 검사자\n"
            "- `process_engineer`: 공정 엔지니어\n"
            "- `executive`: 임원\n"
            "- `sales_engineer`: 영업 엔지니어\n"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Audit 미들웨어 (변경 작업 감사 로그)
    app.add_middleware(AuditMiddleware)

    # Trace ID 미들웨어 (CORS보다 먼저 등록 — 내부 우선 처리)
    app.add_middleware(TraceIDMiddleware)

    # CORS 미들웨어
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 커스텀 예외 핸들러 등록
    register_exception_handlers(app)

    # API 라우터 등록
    app.include_router(api_v1_router)

    # Health check 엔드포인트
    @app.get("/health", tags=["System"], summary="헬스 체크")
    async def health_check():
        """서버 상태 확인 엔드포인트 (로드밸런서 헬스 체크용)"""
        db_ok = await check_db_connection()

        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await r.ping()
            await r.aclose()
            redis_ok = True
        except Exception:
            redis_ok = False

        overall = "healthy" if db_ok and redis_ok else "degraded"

        return {
            "status": overall,
            "version": "1.0.0",
            "app": settings.APP_NAME,
            "dependencies": {
                "database": "ok" if db_ok else "unavailable",
                "redis": "ok" if redis_ok else "unavailable",
            },
        }

    return app


app = create_application()
