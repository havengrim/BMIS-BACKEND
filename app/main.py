import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
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

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting %s [%s]", settings.APP_NAME, settings.APP_ENV)
    yield
    # Shutdown
    await engine.dispose()
    logger.info("🛑 Shutting down %s", settings.APP_NAME)


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
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
app.add_middleware(AuthLoggerMiddleware)


# --- Global exception handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please contact support."},
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


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "env": settings.APP_ENV}
