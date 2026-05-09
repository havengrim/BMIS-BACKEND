import logging
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.redis import get_redis_dep
from app.core.security import Security
from app.db.session import get_db
from app.modules.auth.schema import (
    GoogleTokenRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.rbac.model import Role, UserRoleAssignment
from app.modules.users.model import User, UserRole, UserStatus

router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


# ─── Email / Password Auth ────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new resident account."""
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

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=Security.create_access_token(token_data),
        refresh_token=Security.create_refresh_token(token_data),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email + password."""
    result = await db.execute(select(User).where(User.email == body.email))
    user: User | None = result.scalar_one_or_none()

    if not user or not user.hashed_password or not Security.verify_password(body.password, user.hashed_password):
        logger.warning("AUTH_LOGIN_FAILED email=%s reason=invalid_credentials", body.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if user.status != UserStatus.ACTIVE:
        logger.warning(
            "AUTH_LOGIN_BLOCKED user_id=%s email=%s status=%s",
            user.id, user.email, user.status.value,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status.value}. Contact your administrator.",
        )

    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    logger.info("AUTH_LOGIN_SUCCESS user_id=%s email=%s role=%s", user.id, user.email, user.role.value)

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=Security.create_access_token(token_data),
        refresh_token=Security.create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, redis: Redis = Depends(get_redis_dep)):
    """Obtain a new access token using a valid refresh token."""
    payload = Security.decode_token(body.refresh_token)
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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis_dep),
):
    """Revoke both the current access token and the provided refresh token."""
    # Blacklist access token
    access_jti = current_user.get("jti")
    if access_jti:
        await redis.setex(f"blacklist:{access_jti}", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")

    # Blacklist refresh token
    payload = Security.decode_token(body.refresh_token)
    if payload:
        refresh_jti = payload.get("jti")
        if refresh_jti:
            await redis.setex(f"blacklist:{refresh_jti}", settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, "1")

    logger.info("AUTH_LOGOUT user_id=%s", current_user.get("sub"))


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Returns the decoded payload of the current access token."""
    return current_user


# ─── Google OAuth ─────────────────────────────────────────────────────────────


@router.get("/google/url")
async def google_oauth_url(redis: Redis = Depends(get_redis_dep)):
    """Returns the Google consent page URL. Frontend should redirect the user there."""
    if not settings.GOOGLE_CLIENT_ID:
        logger.warning("AUTH_GOOGLE_URL_REQUESTED but GOOGLE_CLIENT_ID not configured")
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google OAuth is not configured")

    state = secrets.token_urlsafe(32)
    await redis.setex(f"oauth_state:{state}", 600, "1")  # 10-minute window
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
    return {"url": f"{GOOGLE_AUTH_URL}?{params}"}


@router.get("/google/callback")
async def google_oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_dep),
):
    """
    Server-side OAuth callback. Google redirects here after consent.
    Exchanges the code for user info, creates/finds the user, then
    redirects the frontend to FRONTEND_URL/auth/callback with tokens.
    """
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
            logger.warning("AUTH_GOOGLE_TOKEN_EXCHANGE_FAILED error=%s", token_data.get("error"))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Google error: {token_data['error']}")

        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        google_user = user_resp.json()

    user = await _find_or_create_google_user(db, google_user)
    jwt_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    access_token = Security.create_access_token(jwt_data)
    refresh_token = Security.create_refresh_token(jwt_data)
    logger.info("AUTH_GOOGLE_CALLBACK_SUCCESS user_id=%s email=%s", user.id, user.email)

    # Redirect frontend with tokens in query string (use HTTPS in production)
    return RedirectResponse(
        f"{settings.FRONTEND_URL}/auth/callback?access_token={access_token}&refresh_token={refresh_token}"
    )


@router.post("/google/token", response_model=TokenResponse)
async def google_login_with_id_token(
    body: GoogleTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    SPA / mobile flow: the frontend obtains a Google id_token via Google's JS SDK
    and sends it here. Backend verifies it and returns BMIS JWT tokens.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={body.id_token}")
        info = resp.json()

    if resp.status_code != 200 or "error_description" in info:
        logger.warning("AUTH_GOOGLE_TOKEN_INVALID error=%s", info.get("error_description"))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google ID token")

    if settings.GOOGLE_CLIENT_ID and info.get("aud") != settings.GOOGLE_CLIENT_ID:
        logger.warning("AUTH_GOOGLE_AUDIENCE_MISMATCH aud=%s expected=%s", info.get("aud"), settings.GOOGLE_CLIENT_ID)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token audience mismatch")

    google_user = {
        "id": info.get("sub"),
        "email": info.get("email"),
        "given_name": info.get("given_name", ""),
        "family_name": info.get("family_name", ""),
    }
    user = await _find_or_create_google_user(db, google_user)
    logger.info("AUTH_GOOGLE_TOKEN_LOGIN user_id=%s email=%s", user.id, user.email)
    jwt_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=Security.create_access_token(jwt_data),
        refresh_token=Security.create_refresh_token(jwt_data),
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _find_or_create_google_user(db: AsyncSession, google_user: dict) -> User:
    """Find user by Google ID → email → create new."""
    google_id = str(google_user.get("id", ""))
    email = google_user.get("email", "")

    # 1. Lookup by Google provider ID
    if google_id:
        result = await db.execute(select(User).where(User.oauth_provider_id == google_id))
        user = result.scalar_one_or_none()
        if user:
            return user

    # 2. Lookup by email (link existing account)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        if not user.oauth_provider_id:
            user.oauth_provider_id = google_id
            user.oauth_provider = "google"
            user.is_verified = True
            await _ensure_dynamic_role_assignment(db, user, "resident")
            await db.commit()
        return user

    # 3. Create new user — auto-generate unique username from email prefix
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

    existing = (
        await db.execute(
            select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user.id,
                UserRoleAssignment.role_id == role.id,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
