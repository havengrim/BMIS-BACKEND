"""Auth service — all business logic for authentication & TOTP.

The router delegates to this service, keeping handlers thin.
"""
import logging
import secrets

import httpx
import pyotp
from datetime import datetime, timezone
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import Security
from app.modules.auth.schema import (
    LoginRequest,
    RegisterRequest,
    TOTPDisableRequest,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TokenResponse,
)
from app.modules.rbac.model import Role, UserRoleAssignment
from app.modules.users.model import User, UserRole, UserStatus

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


# ─── Registration ─────────────────────────────────────────────────────────────

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
    await _ensure_dynamic_role_assignment(db, user, "resident")
    await db.commit()
    await db.refresh(user)
    logger.info("AUTH_REGISTER user_id=%s email=%s username=%s", user.id, user.email, user.username)

    return _make_tokens(user)


# ─── Login ────────────────────────────────────────────────────────────────────

async def login_user(body: LoginRequest, db: AsyncSession) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user: User | None = result.scalar_one_or_none()

    if not user or not user.hashed_password or not Security.verify_password(body.password, user.hashed_password):
        logger.warning("AUTH_LOGIN_FAILED email=%s reason=invalid_credentials", body.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if user.status != UserStatus.ACTIVE:
        logger.warning("AUTH_LOGIN_BLOCKED user_id=%s email=%s status=%s", user.id, user.email, user.status.value)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status.value}. Contact your administrator.",
        )

    # MFA gate
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
    return _make_tokens(user)


# ─── Token refresh ────────────────────────────────────────────────────────────

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


# ─── Logout ───────────────────────────────────────────────────────────────────

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


# ─── Google OAuth ─────────────────────────────────────────────────────────────

async def get_google_oauth_url(redis: Redis) -> str:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google OAuth is not configured")

    state = secrets.token_urlsafe(32)
    await redis.setex(f"oauth_state:{state}", 600, "1")
    logger.info("AUTH_GOOGLE_OAUTH_URL_GENERATED state=%s", state)

    params = "&".join([
        f"client_id={settings.GOOGLE_CLIENT_ID}",
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}",
        "response_type=code",
        "scope=openid%20email%20profile",
        f"state={state}",
        "access_type=offline",
        "prompt=select_account",
    ])
    return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"


async def handle_google_callback(code: str, state: str, db: AsyncSession, redis: Redis):
    if not await redis.get(f"oauth_state:{state}"):
        logger.warning("AUTH_GOOGLE_CALLBACK_INVALID_STATE state=%s", state)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")
    await redis.delete(f"oauth_state:{state}")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        token_data = token_resp.json()
        if "error" in token_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Google error: {token_data['error']}")

        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        google_user = user_resp.json()

    user = await find_or_create_google_user(db, google_user)
    logger.info("AUTH_GOOGLE_CALLBACK_SUCCESS user_id=%s email=%s", user.id, user.email)
    return _make_tokens(user)


async def login_with_google_id_token(id_token: str, db: AsyncSession) -> TokenResponse:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
        info = resp.json()

    if resp.status_code != 200 or "error_description" in info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google ID token")

    if settings.GOOGLE_CLIENT_ID and info.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token audience mismatch")

    google_user = {
        "id": info.get("sub"),
        "email": info.get("email"),
        "given_name": info.get("given_name", ""),
        "family_name": info.get("family_name", ""),
    }
    user = await find_or_create_google_user(db, google_user)
    logger.info("AUTH_GOOGLE_TOKEN_LOGIN user_id=%s email=%s", user.id, user.email)
    return _make_tokens(user)


# ─── TOTP ─────────────────────────────────────────────────────────────────────

async def totp_setup(current_user: dict, db: AsyncSession) -> TOTPSetupResponse:
    user = await _get_user_or_404(db, current_user["sub"])

    if user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP is already enabled")

    secret = pyotp.random_base32()
    user.totp_secret = secret
    await db.commit()

    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="BMIS Barangay")
    logger.info("TOTP_SETUP_INITIATED user_id=%s", user.id)
    return TOTPSetupResponse(provisioning_uri=uri, secret=secret)


async def totp_confirm(body: TOTPVerifyRequest, current_user: dict, db: AsyncSession) -> None:
    user = await _get_user_or_404(db, current_user["sub"])

    if not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP setup not initiated")
    if user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TOTP is already enabled")
    if not pyotp.TOTP(user.totp_secret).verify(body.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authenticator code")

    user.totp_enabled = True
    await db.commit()
    logger.info("TOTP_ENABLED user_id=%s", user.id)


async def totp_disable(body: TOTPDisableRequest, current_user: dict, db: AsyncSession) -> None:
    user = await _get_user_or_404(db, current_user["sub"])

    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP is not enabled")
    if not pyotp.TOTP(user.totp_secret).verify(body.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authenticator code")

    user.totp_enabled = False
    user.totp_secret = None
    await db.commit()
    logger.info("TOTP_DISABLED user_id=%s", user.id)


async def totp_get_status(current_user: dict, db: AsyncSession) -> dict:
    user = await _get_user_or_404(db, current_user["sub"])
    return {"totp_enabled": user.totp_enabled}


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _make_tokens(user: User) -> TokenResponse:
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=Security.create_access_token(token_data),
        refresh_token=Security.create_refresh_token(token_data),
    )


async def _get_user_or_404(db: AsyncSession, user_id: str) -> User:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def find_or_create_google_user(db: AsyncSession, google_user: dict) -> User:
    google_id = str(google_user.get("id", ""))
    email = google_user.get("email", "")

    if google_id:
        user = (await db.execute(select(User).where(User.oauth_provider_id == google_id))).scalar_one_or_none()
        if user:
            return user

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user:
        if not user.oauth_provider_id:
            user.oauth_provider_id = google_id
            user.oauth_provider = "google"
            user.is_verified = True
            await _ensure_dynamic_role_assignment(db, user, "resident")
            await db.commit()
        return user

    username_base = email.split("@")[0]
    username = username_base
    suffix = 1
    while (await db.execute(select(User).where(User.username == username))).scalar_one_or_none():
        username = f"{username_base}{suffix}"
        suffix += 1

    user = User(
        email=email,
        username=username,
        hashed_password=None,
        first_name=google_user.get("given_name", ""),
        last_name=google_user.get("family_name", ""),
        oauth_provider="google",
        oauth_provider_id=google_id,
        role=UserRole.RESIDENT,
        status=UserStatus.ACTIVE,
        is_verified=True,
    )
    db.add(user)
    await _ensure_dynamic_role_assignment(db, user, "resident")
    await db.commit()
    await db.refresh(user)
    return user


async def _ensure_dynamic_role_assignment(db: AsyncSession, user: User, role_code: str) -> None:
    if user.id is None:
        await db.flush()

    role = (await db.execute(select(Role).where(Role.code == role_code))).scalar_one_or_none()
    if role is None:
        return

    existing = (await db.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.role_id == role.id,
        )
    )).scalar_one_or_none()

    if existing is None:
        db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
