"""
Seed Script — Initial Admin User
Usage: python -m scripts.seed
"""
import asyncio
import selectors
import sys

# Fix for Windows: psycopg async requires SelectorEventLoop
if sys.platform == "win32":
    selector = selectors.SelectSelector()
    loop = asyncio.SelectorEventLoop(selector)
    asyncio.set_event_loop(loop)

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.modules.users.model import User, UserRole, UserStatus
from app.modules.profiles.model import Profile  # noqa: F401
from app.core.security import Security
from app.modules.rbac.model import Permission, Role, RolePermission, UserRoleAssignment


SEEDS = [
    {
        "email": "superadmin@bmis.com",
        "username": "superadmin",
        "password": "Admin1234!",
        "first_name": "System",
        "last_name": "Administrator",
        "role": UserRole.SUPER_ADMIN,
    },
]


DEFAULT_PERMISSIONS = [
    ("users.read", "users", "read", "Read users"),
    ("users.manage", "users", "manage", "Manage users"),
    ("profiles.read", "profiles", "read", "Read profiles"),
    ("profiles.manage", "profiles", "manage", "Manage profiles"),
    ("announcements.manage", "announcements", "manage", "Manage announcements"),
    ("blotter.read", "blotter", "read", "Read blotter reports"),
    ("blotter.manage", "blotter", "manage", "Manage blotter reports"),
    ("certificates.read", "certificates", "read", "Read certificate requests"),
    ("certificates.manage", "certificates", "manage", "Manage certificate requests"),
    ("business_permits.read", "business_permits", "read", "Read business permits"),
    ("business_permits.manage", "business_permits", "manage", "Manage business permits"),
    ("complaints.read", "complaints", "read", "Read complaints"),
    ("complaints.manage", "complaints", "manage", "Manage complaints"),
    ("emergency.read", "emergency", "read", "Read emergency reports"),
    ("emergency.manage", "emergency", "manage", "Manage emergency alerts/reports"),
    ("chat.read", "chat", "read", "Read chat history"),
    ("chat.manage", "chat", "manage", "Use chat"),
    ("rbac.read", "rbac", "read", "Read RBAC entities"),
    ("rbac.manage", "rbac", "manage", "Manage RBAC entities"),
]


DEFAULT_ROLE_PERMISSION_CODES = {
    "super_admin": [code for code, *_ in DEFAULT_PERMISSIONS],
    "barangay_admin": [
        "users.read",
        "users.manage",
        "profiles.read",
        "profiles.manage",
        "announcements.manage",
        "blotter.read",
        "blotter.manage",
        "certificates.read",
        "certificates.manage",
        "business_permits.read",
        "business_permits.manage",
        "complaints.read",
        "complaints.manage",
        "emergency.read",
        "emergency.manage",
        "chat.read",
        "chat.manage",
        "rbac.read",
    ],
    "staff": [
        "profiles.read",
        "profiles.manage",
        "announcements.manage",
        "blotter.read",
        "blotter.manage",
        "certificates.read",
        "certificates.manage",
        "business_permits.read",
        "business_permits.manage",
        "complaints.read",
        "complaints.manage",
        "emergency.read",
        "chat.read",
        "chat.manage",
    ],
    "resident": [
        "profiles.read",
        "profiles.manage",
        "chat.read",
        "chat.manage",
    ],
}


LEGACY_TO_DYNAMIC_ROLE = {
    UserRole.SUPER_ADMIN: "super_admin",
    UserRole.BARANGAY_ADMIN: "barangay_admin",
    UserRole.STAFF: "staff",
    UserRole.RESIDENT: "resident",
}


async def run():
    async with AsyncSessionLocal() as session:
        # 1) Seed permissions
        permission_ids_by_code = {}
        for code, module, action, name in DEFAULT_PERMISSIONS:
            existing = (
                await session.execute(select(Permission).where(Permission.code == code))
            ).scalar_one_or_none()
            if existing is None:
                existing = Permission(code=code, module=module, action=action, name=name)
                session.add(existing)
                await session.flush()
                print(f"  [SEED] Permission: {code}")
            permission_ids_by_code[code] = existing.id

        # 2) Seed dynamic roles
        role_ids_by_code = {}
        for role_code in DEFAULT_ROLE_PERMISSION_CODES.keys():
            existing = (
                await session.execute(select(Role).where(Role.code == role_code))
            ).scalar_one_or_none()
            if existing is None:
                existing = Role(
                    code=role_code,
                    name=role_code.replace("_", " ").title(),
                    description=f"System role: {role_code}",
                    is_system=True,
                )
                session.add(existing)
                await session.flush()
                print(f"  [SEED] Role: {role_code}")
            role_ids_by_code[role_code] = existing.id

        # 3) Seed role-permission mappings
        for role_code, perm_codes in DEFAULT_ROLE_PERMISSION_CODES.items():
            role_id = role_ids_by_code[role_code]
            for perm_code in perm_codes:
                permission_id = permission_ids_by_code[perm_code]
                existing = (
                    await session.execute(
                        select(RolePermission).where(
                            RolePermission.role_id == role_id,
                            RolePermission.permission_id == permission_id,
                        )
                    )
                ).scalar_one_or_none()
                if existing is None:
                    session.add(RolePermission(role_id=role_id, permission_id=permission_id))

        for data in SEEDS:
            # Check for existing username as well
            result_username = await session.execute(
                select(User).where(User.username == data["username"])
            )
            existing_username = result_username.scalar_one_or_none()

            result = await session.execute(
                select(User).where(User.email == data["email"])
            )
            existing = result.scalar_one_or_none()

            if existing or existing_username:
                print(f"  [SKIP] {data['email']} or username '{data['username']}' already exists.")
                continue

            user = User(
                email=data["email"],
                username=data["username"],
                hashed_password=Security.hash_password(data["password"]),
                first_name=data["first_name"],
                last_name=data["last_name"],
                role=data["role"],
                status=UserStatus.ACTIVE,
                is_verified=True,
                oauth_provider="email",
            )
            session.add(user)
            await session.flush()
            print(f"  [SEED] Created: {data['email']} ({data['role']})")

        # 4) Backfill dynamic role assignments for existing users
        all_users = (await session.execute(select(User))).scalars().all()
        for user in all_users:
            mapped_role_code = LEGACY_TO_DYNAMIC_ROLE.get(user.role, "resident")
            role_id = role_ids_by_code[mapped_role_code]
            existing_assignment = (
                await session.execute(
                    select(UserRoleAssignment).where(
                        UserRoleAssignment.user_id == user.id,
                        UserRoleAssignment.role_id == role_id,
                    )
                )
            ).scalar_one_or_none()
            if existing_assignment is None:
                session.add(UserRoleAssignment(user_id=user.id, role_id=role_id))

        await session.commit()
        print("\nSeeding complete.")


if __name__ == "__main__":
    if sys.platform == "win32":
        loop.run_until_complete(run())
    else:
        asyncio.run(run())
