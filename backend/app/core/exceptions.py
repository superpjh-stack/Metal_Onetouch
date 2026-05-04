"""
커스텀 예외 클래스 및 FastAPI 예외 핸들러

에러 응답 봉투 (설계 표준, docs/02-design/api/api-spec.md):
    {
        "error": {
            "code": "...",
            "message": "...",
            "traceId": "..."
        }
    }

trace_id는 TraceIDMiddleware가 request.state.trace_id에 주입합니다.
"""
import uuid
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ------------------------------------------------------------------------------
# Custom Exceptions
# ------------------------------------------------------------------------------

class OnetouchBaseException(Exception):
    """Onetouch MES 기본 예외 클래스"""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "내부 서버 오류가 발생했습니다"

    def __init__(self, message: Optional[str] = None, detail: Optional[str] = None):
        self.message = message or self.__class__.message
        self.detail = detail
        super().__init__(self.message)


class LotNotFoundException(OnetouchBaseException):
    status_code = 404
    error_code = "LOT_NOT_FOUND"
    message = "LOT을 찾을 수 없습니다"


class InsufficientPermissionException(OnetouchBaseException):
    status_code = 403
    error_code = "INSUFFICIENT_PERMISSION"
    message = "권한이 없습니다"


class LotDeleteForbiddenException(OnetouchBaseException):
    """LOT 삭제 금지 예외 — DB 레벨 no_delete_lots 룰과 동일한 정책을 앱 레벨에서 강제"""
    status_code = 403
    error_code = "LOT_DELETE_FORBIDDEN"
    message = "LOT은 삭제할 수 없습니다. 상태를 cancelled로 변경하세요."


class LotStatusTransitionException(OnetouchBaseException):
    status_code = 422
    error_code = "INVALID_STATUS_TRANSITION"
    message = "허용되지 않은 상태 전환입니다"


class ValidationException(OnetouchBaseException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "입력 데이터가 유효하지 않습니다"


class ExternalServiceException(OnetouchBaseException):
    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"
    message = "외부 서비스 연결에 실패했습니다"


class DuplicateResourceException(OnetouchBaseException):
    status_code = 409
    error_code = "DUPLICATE_RESOURCE"
    message = "이미 존재하는 리소스입니다"


class RawMaterialNotFoundException(OnetouchBaseException):
    status_code = 404
    error_code = "RAW_MATERIAL_NOT_FOUND"
    message = "원자재를 찾을 수 없습니다"


# ------------------------------------------------------------------------------
# Helper: build error envelope
# ------------------------------------------------------------------------------

def _error_body(error_code: str, message: str, trace_id: str) -> dict:
    """설계 표준 에러 봉투를 생성합니다."""
    return {
        "error": {
            "code": error_code,
            "message": message,
            "traceId": trace_id,
        }
    }


def _get_trace_id(request: Request) -> str:
    """request.state에서 trace_id를 가져옵니다. 없으면 새 UUID를 생성합니다."""
    return getattr(request.state, "trace_id", None) or str(uuid.uuid4())


# ------------------------------------------------------------------------------
# Exception Handler Registration
# ------------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """FastAPI 앱에 커스텀 예외 핸들러를 등록합니다."""

    @app.exception_handler(OnetouchBaseException)
    async def onetouch_exception_handler(
        request: Request, exc: OnetouchBaseException
    ) -> JSONResponse:
        trace_id = _get_trace_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_code, exc.message, trace_id),
        )

    # Specific subclass handlers (registered after base — FastAPI uses the most
    # specific matching handler, so order matters for subclasses that need
    # custom logic beyond the base handler)

    @app.exception_handler(LotNotFoundException)
    async def lot_not_found_handler(
        request: Request, exc: LotNotFoundException
    ) -> JSONResponse:
        trace_id = _get_trace_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_code, exc.message, trace_id),
        )

    @app.exception_handler(InsufficientPermissionException)
    async def permission_handler(
        request: Request, exc: InsufficientPermissionException
    ) -> JSONResponse:
        trace_id = _get_trace_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_code, exc.message, trace_id),
        )

    @app.exception_handler(LotDeleteForbiddenException)
    async def lot_delete_forbidden_handler(
        request: Request, exc: LotDeleteForbiddenException
    ) -> JSONResponse:
        trace_id = _get_trace_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_code, exc.message, trace_id),
        )

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(
        request: Request, exc: ValidationException
    ) -> JSONResponse:
        trace_id = _get_trace_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_code, exc.message, trace_id),
        )

    @app.exception_handler(ExternalServiceException)
    async def external_service_handler(
        request: Request, exc: ExternalServiceException
    ) -> JSONResponse:
        trace_id = _get_trace_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error_code, exc.message, trace_id),
        )
