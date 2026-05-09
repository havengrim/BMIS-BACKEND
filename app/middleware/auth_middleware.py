import time
import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.context import request_id_var

logger = logging.getLogger(__name__)


class AuthLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        # Propagate into ContextVar so log records carry it automatically
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000

            logger.info(
                "%s %s %s %.2fms request_id=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                request_id,
            )

            # Add request timing/correlation headers
            response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "Unhandled middleware error %s %s %.2fms request_id=%s",
                request.method,
                request.url.path,
                duration_ms,
                request_id,
            )
            raise
        finally:
            request_id_var.reset(token)
