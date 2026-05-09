import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.log_handler import install_db_handler, start_db_log_worker, stop_db_log_worker
from app.core.redis import init_redis, close_redis
from app.db.session import engine
from app.middleware.cors import setup_cors
from app.middleware.auth_middleware import AuthLoggerMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.profiles.router import router as profiles_router
from app.modules.announcements.router import router as announcements_router
from app.modules.blotter.router import router as blotter_router
from app.modules.certificates.router import router as certificates_router
from app.modules.business_permits.router import router as business_permits_router
from app.modules.complaints.router import router as complaints_router
from app.modules.emergency.router import router as emergency_router
from app.modules.chat.router import router as chat_router
from app.modules.rbac.router import router as rbac_router
from app.modules.system_logs.router import router as system_logs_router

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting %s [%s]", settings.APP_NAME, settings.APP_ENV)
    try:
        await init_redis()
        logger.info("Redis connected")
    except Exception as exc:
        logger.warning("Redis initialization failed. App running in degraded mode. %s", exc)

    # Install async DB log handler (non-blocking — uses in-process queue)
    if settings.LOG_TO_DB:
        install_db_handler()
        await start_db_log_worker()
        logger.info("DB log handler active (level=%s)", settings.LOG_LEVEL_DB)

    yield

    # Shutdown — flush remaining log buffer before closing DB pool
    if settings.LOG_TO_DB:
        await stop_db_log_worker()
    try:
        await close_redis()
    except Exception as exc:
        logger.warning("⚠️ Redis shutdown warning: %s", exc)
    await engine.dispose()
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Barangay Management Information System API",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    openapi_url="/openapi.json" if settings.APP_ENV != "production" else None,
    lifespan=lifespan,
)

# --- Middleware (order matters: outermost runs first) ---
setup_cors(app)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        fail_open=settings.RATE_LIMIT_FAIL_OPEN,
        exempt_paths=settings.RATE_LIMIT_EXEMPT_PATHS,
    )
app.add_middleware(AuthLoggerMiddleware)


# --- Global exception handlers ---
def _request_id_from(request: Request) -> str:
    return getattr(request.state, "request_id", request.headers.get("X-Request-ID", "unknown"))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = _request_id_from(request)
    body = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    body["request_id"] = request_id
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        headers={"X-Request-ID": request_id, **(exc.headers or {})},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = _request_id_from(request)
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation failed",
            "errors": exc.errors(),
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    request_id = _request_id_from(request)
    logger.error("Database error: %s | request_id=%s", exc, request_id, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "A database error occurred. Please try again later.",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(RuntimeError)
async def runtime_exception_handler(request: Request, exc: RuntimeError):
    request_id = _request_id_from(request)
    if "Redis connection not initialized" in str(exc):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Service temporarily unavailable. Please retry shortly.",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )
    logger.error("Runtime error: %s | request_id=%s", exc, request_id, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error. Please contact support.",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = _request_id_from(request)
    logger.error("Unhandled exception: %s | request_id=%s", exc, request_id, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error. Please contact support.",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


# --- Routers ---
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(users_router, prefix="/users", tags=["Users"])
app.include_router(profiles_router, prefix="/profiles", tags=["Profiles"])
app.include_router(announcements_router, prefix="/announcements", tags=["Announcements"])
app.include_router(blotter_router, prefix="/blotter", tags=["Blotter"])
app.include_router(certificates_router, prefix="/certificates", tags=["Certificates"])
app.include_router(business_permits_router, prefix="/business-permits", tags=["Business Permits"])
app.include_router(complaints_router, prefix="/complaints", tags=["Complaints"])
app.include_router(emergency_router, prefix="/emergency", tags=["Emergency"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(rbac_router, prefix="/rbac", tags=["RBAC"])
app.include_router(system_logs_router, prefix="/system-logs", tags=["System Logs"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "env": settings.APP_ENV}
