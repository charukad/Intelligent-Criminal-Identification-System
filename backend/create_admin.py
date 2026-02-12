import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.domain.models.user import User, UserRole
from src.core.security import get_password_hash
from src.core.config import settings

async def create_admin():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        admin = User(
            username='admin',
            email='admin@traceiq.local',
            hashed_password=get_password_hash('admin123'),
            role=UserRole.ADMIN,
            is_active=True,
            badge_number='ADMIN001'
        )
        session.add(admin)
        await session.commit()
        print('✅ Admin user created: admin / admin123')

if __name__ == '__main__':
    asyncio.run(create_admin())
