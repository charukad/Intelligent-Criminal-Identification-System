import asyncio

from src.infrastructure.database import AsyncSessionLocal
from src.infrastructure.repositories.user import UserRepository
from src.core.security import get_password_hash
from src.domain.models.user import User, UserRole


SEED_USERS = [
    {
        "username": "admin",
        "email": "admin@traceiq.com",
        "password": "admin123",
        "role": UserRole.ADMIN,
        "badge_number": "ADMIN001",
    },
    {
        "username": "senior1",
        "email": "senior1@traceiq.com",
        "password": "senior123",
        "role": UserRole.SENIOR_OFFICER,
        "badge_number": "SEN001",
    },
    {
        "username": "officer1",
        "email": "officer1@traceiq.com",
        "password": "officer123",
        "role": UserRole.FIELD_OFFICER,
        "badge_number": "OFF001",
    },
]


async def seed_users():
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        created = []
        skipped = []

        for u in SEED_USERS:
            existing = await repo.get_by_username(u["username"])
            if existing:
                skipped.append(u["username"])
                continue

            user = User(
                username=u["username"],
                email=u["email"],
                hashed_password=get_password_hash(u["password"]),
                role=u["role"],
                is_active=True,
                badge_number=u["badge_number"],
                station_id=None,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            created.append(u["username"])

        print(f"Created users: {created}")
        print(f"Skipped existing: {skipped}")


if __name__ == "__main__":
    asyncio.run(seed_users())
