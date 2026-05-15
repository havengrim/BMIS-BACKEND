"""Auth router — HTTP boundary only. Business logic lives in auth/services/."""
import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.redis import get_redis_dep
from app.db.session import get_db
from app.modules.auth.schema import (
    GoogleTokenRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TOTPDisableRequest,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TokenResponse,
)
from app.modules.auth.services import auth_service, oauth_service, totp_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Email / Password ─────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.register_user(body, db)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login_user(body, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, redis: Redis = Depends(get_redis_dep)):
    return await auth_service.refresh_user_token(body.refresh_token, redis)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis_dep),
):
    await auth_service.logout_user(body.refresh_token, current_user, redis)


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user


# ─── Google OAuth ─────────────────────────────────────────────────────────────

@router.get("/google/url")
async def google_oauth_url(redis: Redis = Depends(get_redis_dep)):
    url = await oauth_service.get_oauth_url(redis)
    return {"url": url}


@router.get("/google/callback")
async def google_oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_dep),
):
    tokens = await oauth_service.handle_callback(code, state, db, redis)
    return RedirectResponse(
        f"{settings.FRONTEND_URL}/auth/callback"
        f"?access_token={tokens.access_token}&refresh_token={tokens.refresh_token}"
    )


@router.post("/google/token", response_model=TokenResponse)
async def google_login_with_id_token(body: GoogleTokenRequest, db: AsyncSession = Depends(get_db)):
    return await oauth_service.login_with_id_token(body.id_token, db)


# ─── TOTP / MFA ──────────────────────────────────────────────────────────────

@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def totp_setup(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await totp_service.setup(current_user, db)


@router.post("/totp/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def totp_confirm(
    body: TOTPVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await totp_service.confirm(body, current_user, db)


@router.post("/totp/disable", status_code=status.HTTP_204_NO_CONTENT)
async def totp_disable(
    body: TOTPDisableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await totp_service.disable(body, current_user, db)


@router.get("/totp/status")
async def totp_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await totp_service.get_status(current_user, db)
