import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    invalidate_user_permissions_cache,
    require_permissions,
)
from app.core.redis import get_redis_dep
from app.db.session import get_db
from app.modules.rbac.model import Permission, Role, RolePermission, UserRoleAssignment
from app.modules.rbac.schema import (
    PermissionCreate,
    PermissionResponse,
    RoleCreate,
    RoleDetailResponse,
    RolePermissionAssignRequest,
    RoleResponse,
    UserRoleAssignRequest,
    UserRoleResponse,
)
from app.modules.users.model import User

router = APIRouter()
logger = logging.getLogger(__name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _guard_system_role(role: Role, action: str = "modify") -> None:
    """Prevent any mutation of system-seeded roles."""
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot {action} a system role.",
        )


async def _invalidate_role_caches(role_id: uuid.UUID, db: AsyncSession, redis: Redis) -> None:
    """Invalidate Redis permission cache for every user assigned to this role."""
    rows = await db.execute(
        select(UserRoleAssignment.user_id).where(UserRoleAssignment.role_id == role_id)
    )
    for user_id in rows.scalars().all():
        await invalidate_user_permissions_cache(user_id, redis)


# ─── Permissions ──────────────────────────────────────────────────────────────


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permissions("rbac.read")),
):
    result = await db.execute(
        select(Permission).order_by(Permission.module.asc(), Permission.action.asc())
    )
    return result.scalars().all()


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    body: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permissions("rbac.manage")),
):
    existing = (await db.execute(select(Permission).where(Permission.code == body.code))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Permission code already exists")

    permission = Permission(**body.model_dump())
    db.add(permission)
    await db.commit()
    await db.refresh(permission)
    logger.info("Permission created: %s by user=%s", permission.code, current_user.get("sub"))
    return permission


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_dep),
    current_user: dict = Depends(require_permissions("rbac.manage")),
):
    perm = (await db.execute(select(Permission).where(Permission.id == permission_id))).scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    # Invalidate caches for all roles that had this permission
    role_ids_rows = await db.execute(
        select(RolePermission.role_id).where(RolePermission.permission_id == permission_id)
    )
    for role_id in role_ids_rows.scalars().all():
        await _invalidate_role_caches(role_id, db, redis)

    await db.delete(perm)
    await db.commit()
    logger.info("Permission deleted: %s by user=%s", perm.code, current_user.get("sub"))


# ─── Roles ────────────────────────────────────────────────────────────────────


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions("rbac.read")),
):
    result = await db.execute(select(Role).order_by(Role.name.asc()))
    return result.scalars().all()


@router.get("/roles/{role_id}", response_model=RoleDetailResponse)
async def get_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions("rbac.read")),
):
    """Returns a role with its full list of assigned permissions."""
    role = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    perm_rows = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.module.asc(), Permission.action.asc())
    )
    permissions = perm_rows.scalars().all()
    return RoleDetailResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        created_at=role.created_at,
        permissions=permissions,
    )


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    body: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permissions("rbac.manage")),
):
    existing = (await db.execute(select(Role).where(Role.code == body.code))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role code already exists")

    role = Role(**body.model_dump(), is_system=False)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    logger.info("Role created: %s by user=%s", role.code, current_user.get("sub"))
    return role


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_dep),
    current_user: dict = Depends(require_permissions("rbac.manage")),
):
    role = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    _guard_system_role(role, "delete")
    await _invalidate_role_caches(role_id, db, redis)
    await db.delete(role)
    await db.commit()
    logger.info("Role deleted: %s by user=%s", role.code, current_user.get("sub"))


# ─── Role ↔ Permission assignment ─────────────────────────────────────────────


@router.post("/roles/{role_id}/permissions", status_code=status.HTTP_204_NO_CONTENT)
async def assign_permission_to_role(
    role_id: uuid.UUID,
    body: RolePermissionAssignRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_dep),
    current_user: dict = Depends(require_permissions("rbac.manage")),
):
    role = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    perm = (await db.execute(select(Permission).where(Permission.id == body.permission_id))).scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    existing = (await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == body.permission_id,
        )
    )).scalar_one_or_none()

    if existing is None:
        db.add(RolePermission(role_id=role_id, permission_id=body.permission_id))
        await db.commit()
        logger.info(
            "Permission %s assigned to role %s by user=%s",
            perm.code, role.code, current_user.get("sub"),
        )

    await _invalidate_role_caches(role_id, db, redis)


@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_permission_from_role(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_dep),
    current_user: dict = Depends(require_permissions("rbac.manage")),
):
    role = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    _guard_system_role(role, "modify")

    rp = (await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
    )).scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await db.delete(rp)
    await db.commit()
    await _invalidate_role_caches(role_id, db, redis)
    logger.info(
        "Permission %s revoked from role %s by user=%s",
        permission_id, role.code, current_user.get("sub"),
    )


# ─── User ↔ Role assignment ───────────────────────────────────────────────────


@router.get("/users/{user_id}/roles", response_model=list[RoleResponse])
async def get_user_roles(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions("rbac.read")),
):
    """Returns all roles currently assigned to a user."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    rows = await db.execute(
        select(Role)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(UserRoleAssignment.user_id == user_id)
        .order_by(Role.name.asc())
    )
    return rows.scalars().all()


@router.post("/users/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
async def assign_role_to_user(
    user_id: uuid.UUID,
    body: UserRoleAssignRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_dep),
    current_user: dict = Depends(require_permissions("rbac.manage")),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = (await db.execute(select(Role).where(Role.id == body.role_id))).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing = (await db.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.role_id == body.role_id,
        )
    )).scalar_one_or_none()

    if existing is None:
        db.add(UserRoleAssignment(user_id=user_id, role_id=body.role_id))
        await db.commit()
        logger.info(
            "Role %s assigned to user %s by user=%s",
            role.code, user_id, current_user.get("sub"),
        )

    await invalidate_user_permissions_cache(user_id, redis)


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_role_from_user(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_dep),
    current_user: dict = Depends(require_permissions("rbac.manage")),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    assignment = (await db.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.role_id == role_id,
        )
    )).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not assigned to user")

    await db.delete(assignment)
    await db.commit()
    await invalidate_user_permissions_cache(user_id, redis)
    logger.info(
        "Role %s revoked from user %s by user=%s",
        role.code, user_id, current_user.get("sub"),
    )
