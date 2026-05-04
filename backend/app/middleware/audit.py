"""감사 로그 미들웨어

POST/PATCH/PUT/DELETE 요청 성공 시 system_logs 테이블에 비동기로 기록합니다.
asyncio.create_task()를 사용해 응답 지연 없이 백그라운드에서 처리합니다.
"""
import asyncio
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class AuditMiddleware(BaseHTTPMiddleware):
    """변경 작업을 감사 로그에 기록하는 미들웨어"""

    AUDITABLE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
    SKIP_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/auth/login",
    }

    async def dispatch(self, request: Request, call_next):
        if (
            request.method not in self.AUDITABLE_METHODS
            or request.url.path in self.SKIP_PATHS
        ):
            return await call_next(request)

        response = await call_next(request)

        if 200 <= response.status_code < 300:
            action = self._resolve_action(request.method, request.url.path)
            resource_type, resource_id = self._parse_resource(request.url.path)
            actor_id = getattr(getattr(request.state, "user", None), "id", None)
            actor_name = getattr(getattr(request.state, "user", None), "full_name", None)
            trace_id = getattr(request.state, "trace_id", None)
            ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent")

            asyncio.create_task(
                self._write_log(
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    actor_id=actor_id,
                    actor_name=actor_name,
                    ip=ip,
                    ua=ua,
                    trace_id=trace_id,
                )
            )

        return response

    def _resolve_action(self, method: str, path: str) -> str:
        if method == "POST" and path.endswith("/login"):
            return "LOGIN"
        if method == "POST" and path.endswith("/logout"):
            return "LOGOUT"
        if method == "POST" and "/status" in path:
            return "STATUS_CHANGE"
        if method == "POST":
            return "CREATE"
        if method in ("PATCH", "PUT"):
            return "UPDATE"
        if method == "DELETE":
            return "DELETE"
        return "CREATE"

    def _parse_resource(self, path: str) -> tuple[str, Optional[str]]:
        """
        경로에서 리소스 유형과 ID를 추출합니다.
        예: /api/v1/master/suppliers/uuid-here -> ("suppliers", "uuid-here")
        """
        parts = [p for p in path.split("/") if p and p not in ("api", "v1", "master")]
        resource_type = parts[0] if parts else "unknown"
        resource_id = parts[1] if len(parts) > 1 else None
        return resource_type, resource_id

    async def _write_log(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        actor_id,
        actor_name: Optional[str],
        ip: Optional[str],
        ua: Optional[str],
        trace_id: Optional[str],
    ) -> None:
        """별도 DB 세션으로 감사 로그를 기록합니다."""
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.system_log import SystemLog

            async with AsyncSessionLocal() as db:
                log = SystemLog(
                    actor_id=actor_id,
                    actor_name=actor_name,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=ip,
                    user_agent=ua,
                    trace_id=trace_id,
                )
                db.add(log)
                await db.commit()
        except Exception:
            # 감사 로그 실패는 조용히 무시 (서비스 가용성 우선)
            pass
