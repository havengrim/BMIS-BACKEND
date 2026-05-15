import time
import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.context import current_ip_address_var, request_id_var

logger = logging.getLogger(__name__)


def _extract_client_ip(request: Request) -> str:
    """Best-effort client IP extraction (proxy-aware)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first_hop = forwarded_for.split(",")[0].strip()
        if first_hop:
            return first_hop

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


class AuthLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        client_ip = _extract_client_ip(request)
        request.state.request_id = request_id
        request.state.client_ip = client_ip
        # Propagate into ContextVar so log records carry it automatically
        req_token = request_id_var.set(request_id)
        ip_token = current_ip_address_var.set(client_ip)
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
            request_id_var.reset(req_token)
            current_ip_address_var.reset(ip_token)
