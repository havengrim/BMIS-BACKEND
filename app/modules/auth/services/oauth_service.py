"""Google OAuth service — URL generation, callback handling, ID token login."""
import logging
import secrets

import httpx
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.auth.schema import TokenResponse
from app.modules.auth.services.helpers import ensure_dynamic_role_assignment, make_tokens
from app.modules.users.model import User, UserRole, UserStatus

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


async def get_oauth_url(redis: Redis) -> str:
    """Generate a Google OAuth consent URL with a CSRF state token."""
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
    return f"{GOOGLE_AUTH_URL}?{params}"


async def handle_callback(code: str, state: str, db: AsyncSession, redis: Redis) -> TokenResponse:
    """Exchange an auth code for user info and return BMIS JWT tokens."""
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

    user = await find_or_create_user(db, google_user)
    logger.info("AUTH_GOOGLE_CALLBACK_SUCCESS user_id=%s email=%s", user.id, user.email)
    return make_tokens(user)


async def login_with_id_token(id_token: str, db: AsyncSession) -> TokenResponse:
    """Verify a Google ID token (SPA/mobile flow) and return BMIS JWT tokens."""
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
    user = await find_or_create_user(db, google_user)
    logger.info("AUTH_GOOGLE_TOKEN_LOGIN user_id=%s email=%s", user.id, user.email)
    return make_tokens(user)


async def find_or_create_user(db: AsyncSession, google_user: dict) -> User:
    """Find an existing user by Google ID or email, or create a new one."""
    google_id = str(google_user.get("id", ""))
    email = google_user.get("email", "")

    # 1. Lookup by Google provider ID
    if google_id:
        user = (await db.execute(select(User).where(User.oauth_provider_id == google_id))).scalar_one_or_none()
        if user:
            return user

    # 2. Link existing account by email
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user:
        if not user.oauth_provider_id:
            user.oauth_provider_id = google_id
            user.oauth_provider = "google"
            user.is_verified = True
            await ensure_dynamic_role_assignment(db, user, "resident")
            await db.commit()
        return user

    # 3. Create new user with unique username
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
    await ensure_dynamic_role_assignment(db, user, "resident")
    await db.commit()
    await db.refresh(user)
    return user
