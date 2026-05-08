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
from app.core.security import Security


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


async def run():
    async with AsyncSessionLocal() as session:
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
            )
            session.add(user)
            print(f"  [SEED] Created: {data['email']} ({data['role']})")

        await session.commit()
        print("\nSeeding complete.")


if __name__ == "__main__":
    if sys.platform == "win32":
        loop.run_until_complete(run())
    else:
        asyncio.run(run())
