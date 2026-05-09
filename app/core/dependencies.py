import uuid

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import current_user_id_var
from app.core.redis import get_redis_dep
from app.core.security import Security
from app.db.session import get_db
from app.modules.rbac.model import Permission, RolePermission, UserRoleAssignment

bearer_scheme = HTTPBearer()


# --------------------------------------------------------------------------- #
# Pagination dependency — inject into any list endpoint                         #
# --------------------------------------------------------------------------- #


class Pagination:
    """Reusable query-parameter dependency for cursor-less offset pagination."""

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip (offset)"),
        limit: int = Query(50, ge=1, le=200, description="Max records to return (max 200)"),
    ) -> None:
        self.skip = skip
        self.limit = limit


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    redis: Redis = Depends(get_redis_dep),
) -> dict:
    token = credentials.credentials
    payload = Security.decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not Security.is_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check Redis blacklist (set on logout)
    jti = payload.get("jti")
    if jti and await redis.get(f"blacklist:{jti}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Propagate user_id into ContextVar so every log record in this request carries it
    current_user_id_var.set(payload.get("sub", ""))

    return payload


def require_roles(*roles: str):
    """RBAC dependency factory. Usage: Depends(require_roles('super_admin', 'barangay_admin'))"""
    async def dependency(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user
    return dependency


async def invalidate_user_permissions_cache(user_id: uuid.UUID | str, redis: Redis) -> None:
    await redis.delete(f"user_permissions:{user_id}")


async def _load_user_permission_codes(
    user_id: str,
    db: AsyncSession,
    redis: Redis,
) -> set[str]:
    cache_key = f"user_permissions:{user_id}"

    cached = await redis.smembers(cache_key)
    if cached:
        return set(cached)

    query = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == RolePermission.role_id)
        .where(UserRoleAssignment.user_id == uuid.UUID(user_id))
    )
    result = await db.execute(query)
    codes = {row[0] for row in result.all()}

    if codes:
        await redis.sadd(cache_key, *list(codes))
        await redis.expire(cache_key, 300)

    return codes


def require_permissions(*permission_codes: str):
    """Dynamic RBAC dependency. Example: Depends(require_permissions('complaints.manage'))."""

    async def dependency(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis_dep),
    ) -> dict:
        # Super admin bypass for bootstrapping and emergency access
        if current_user.get("role") == "super_admin":
            return current_user

        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )

        dynamic_codes = await _load_user_permission_codes(user_id, db, redis)

        if not dynamic_codes and current_user.get("role") == "barangay_admin":
            # Transitional fallback for existing enum roles if not yet assigned in dynamic RBAC
            return current_user

        missing = [p for p in permission_codes if p not in dynamic_codes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )

        return current_user

    return dependency
