"""Core auth service — registration, login, token refresh, logout."""
import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import Security
from app.modules.auth.schema import LoginRequest, RegisterRequest, TokenResponse
from app.modules.auth.services.helpers import ensure_dynamic_role_assignment, make_tokens
from app.modules.users.model import User, UserRole, UserStatus

logger = logging.getLogger(__name__)


async def register_user(body: RegisterRequest, db: AsyncSession) -> TokenResponse:
    if (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    user = User(
        email=body.email,
        username=body.username,
        hashed_password=Security.hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        middle_name=body.middle_name,
        contact_number=body.contact_number,
        oauth_provider="email",
        role=UserRole.RESIDENT,
        status=UserStatus.PENDING,
        is_verified=False,
    )
    db.add(user)
    await ensure_dynamic_role_assignment(db, user, "resident")
    await db.commit()
    await db.refresh(user)
    logger.info("AUTH_REGISTER user_id=%s email=%s username=%s", user.id, user.email, user.username)
    return make_tokens(user)


async def login_user(body: LoginRequest, db: AsyncSession) -> TokenResponse:
    import pyotp

    user: User | None = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()

    if not user or not user.hashed_password or not Security.verify_password(body.password, user.hashed_password):
        logger.warning("AUTH_LOGIN_FAILED email=%s reason=invalid_credentials", body.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if user.status != UserStatus.ACTIVE:
        logger.warning("AUTH_LOGIN_BLOCKED user_id=%s email=%s status=%s", user.id, user.email, user.status.value)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status.value}. Contact your administrator.",
        )

    # MFA gate — delegate to totp_service logic inline to avoid circular imports
    if user.totp_enabled and user.totp_secret:
        if not body.totp_code:
            return TokenResponse(access_token="", refresh_token="", mfa_required=True)
        if not pyotp.TOTP(user.totp_secret).verify(body.totp_code, valid_window=1):
            logger.warning("AUTH_LOGIN_MFA_FAILED user_id=%s email=%s", user.id, user.email)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authenticator code")
        logger.info("AUTH_LOGIN_MFA_OK user_id=%s email=%s", user.id, user.email)

    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    logger.info("AUTH_LOGIN_SUCCESS user_id=%s email=%s role=%s", user.id, user.email, user.role.value)
    return make_tokens(user)


async def refresh_user_token(refresh_token: str, redis: Redis) -> TokenResponse:
    payload = Security.decode_token(refresh_token)
    if payload is None or not Security.is_token_type(payload, "refresh"):
        logger.warning("AUTH_REFRESH_FAILED reason=invalid_token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    jti = payload.get("jti")
    if jti and await redis.get(f"blacklist:{jti}"):
        logger.warning("AUTH_REFRESH_REVOKED sub=%s jti=%s", payload.get("sub"), jti)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")

    logger.info("AUTH_REFRESH_SUCCESS sub=%s", payload.get("sub"))
    token_data = {"sub": payload["sub"], "email": payload["email"], "role": payload["role"]}
    return TokenResponse(
        access_token=Security.create_access_token(token_data),
        refresh_token=Security.create_refresh_token(token_data),
    )


async def logout_user(refresh_token: str, current_user: dict, redis: Redis) -> None:
    access_jti = current_user.get("jti")
    if access_jti:
        await redis.setex(f"blacklist:{access_jti}", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")

    payload = Security.decode_token(refresh_token)
    if payload:
        refresh_jti = payload.get("jti")
        if refresh_jti:
            await redis.setex(f"blacklist:{refresh_jti}", settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, "1")

    logger.info("AUTH_LOGOUT user_id=%s", current_user.get("sub"))
