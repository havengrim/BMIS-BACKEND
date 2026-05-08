import time
import logging

from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed sliding window rate limiter.
    Uses a sorted set per IP; safe for multi-instance deployments (AWS ECS/EC2).
    Falls back to allowing the request if Redis is unavailable.
    """

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        fail_open: bool = True,
        exempt_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.fail_open = fail_open
        self.exempt_paths = set(exempt_paths or [])

    def _get_client_ip(self, request: Request) -> str:
        # Respect X-Forwarded-For from AWS ALB / CloudFront
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        try:
            redis = get_redis()
            client_ip = self._get_client_ip(request)
            key = f"rate_limit:{client_ip}"
            now = time.time()
            window_start = now - self.window_seconds
            unique_member = f"{now}:{time.perf_counter_ns()}"

            # Atomic pipeline: clean old entries → add current → count → set TTL
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {unique_member: now})
            pipe.zcard(key)
            pipe.expire(key, self.window_seconds)
            results = await pipe.execute()
            count: int = results[2]

            if count > self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down.", "retry_after": self.window_seconds},
                    headers={
                        "Retry-After": str(self.window_seconds),
                        "X-RateLimit-Limit": str(self.max_requests),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(max(0, self.max_requests - count))
            return response

        except (RedisError, RuntimeError) as exc:
            logger.warning("Rate limiter degraded: %s", exc)
            if self.fail_open:
                # Redis unavailable: fail open — never block legitimate traffic
                return await call_next(request)
            return JSONResponse(
                status_code=503,
                content={"detail": "Rate limiting service unavailable"},
            )
