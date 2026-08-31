"""Create or reset Platform Admins (dev team: 5 default + 5 named accounts, all super_admin)."""

import argparse
import asyncio
import os

from sqlalchemy import delete, select
from sqlmodel import col

from app.core.security import hash_password
from app.database.database import async_session_factory
from app.database.scripts.seed_rbac import assign_super_admin, ensure_catalog
from app.models.password_history import PasswordHistory
from app.models.platform_admin import PlatformAdmin
from app.models.platform_admin_role import PlatformAdminRole

# (username, email) pairs for the dev team: the first five are generic,
# the rest are named team members.
DEFAULT_DEV_ADMINS: list[tuple[str, str]] = [
    ("admin1", "admin1@example.com"),
    ("admin2", "admin2@example.com"),
    ("admin3", "admin3@example.com"),
    ("admin4", "admin4@example.com"),
    ("admin5", "admin5@example.com"),
    ("shiva", "shiva@gmail.com"),
    ("kishore", "kishore@gmail.com"),
    ("shaktish", "shaktish@gmail.com"),
    ("satish", "satish@gmail.com"),
    ("naveen", "naveen@gmail.com"),
]
DEFAULT_DEV_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Admin@1234")  # noqa: S105


async def seed(username: str, email: str, password: str) -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(PlatformAdmin).where(col(PlatformAdmin.email) == email))
        admin = result.scalar_one_or_none()
        if admin is not None:
            admin.username = username
            admin.hashed_password = hash_password(password)
        else:
            admin = PlatformAdmin(
                username=username, email=email, hashed_password=hash_password(password)
            )
            db.add(admin)
        await ensure_catalog(db)
        await assign_super_admin(db, admin.id)
        await db.commit()
    print(f"PlatformAdmin '{email}' is ready.")


async def reset() -> None:
    """Clear all Platform Admins plus their role links and password history (clean reseed)."""
    async with async_session_factory() as db:
        # Children first, so the FK from these tables to ``platform_admins`` is satisfied.
        await db.execute(delete(PasswordHistory))
        await db.execute(delete(PlatformAdminRole))
        await db.execute(delete(PlatformAdmin))
        await db.commit()
    print("Cleared all Platform Admins (and their role links + password history).")


async def seed_dev_team() -> None:
    for username, email in DEFAULT_DEV_ADMINS:
        await seed(username=username, email=email, password=DEFAULT_DEV_PASSWORD)


async def _run(args: argparse.Namespace) -> None:
    """Run the whole flow in one event loop (asyncpg connections are loop-bound)."""
    if args.reset:
        await reset()
    if args.email:
        await seed(args.username, args.email, args.password)
    else:
        await seed_dev_team()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear all admins first, then seed (clean reseed)",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Seed a single admin (production provisioning); default seeds the 10 dev admins",
    )
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default=DEFAULT_DEV_PASSWORD)
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
