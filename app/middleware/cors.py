from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )
