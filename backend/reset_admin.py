import asyncio
from src.infrastructure.database import AsyncSessionLocal
from src.infrastructure.repositories.user import UserRepository
from src.core.security import get_password_hash
from src.domain.models.user import User
from src.domain.models.criminal import Criminal
from src.domain.models.face import FaceEmbedding
from src.domain.models.case import Case
from src.domain.models.station import Station

async def reset_password():
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        user = await repo.get_by_username("admin")
        if user:
            print(f"User found: {user.username}")
            new_hash = get_password_hash("admin123")
            user.hashed_password = new_hash
            db.add(user)
            await db.commit()
            print("Password reset successfully.")
        else:
            print("User 'admin' not found. Creating...")
            # If not found, create it
            user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                is_active=True,
                station_id=None
            )
            db.add(user)
            await db.commit()
            print("User 'admin' created.")

if __name__ == "__main__":
    asyncio.run(reset_password())
