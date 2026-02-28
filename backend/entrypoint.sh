#!/bin/bash
set -e

echo "🔄 Running database migrations..."
alembic upgrade head

echo "🌱 Seeding admin user (if not exists)..."
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from src.domain.models.user import User, UserRole
from src.core.security import get_password_hash
from src.core.config import settings

async def seed_admin():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == 'admin'))
        if result.scalar_one_or_none():
            print('✅ Admin user already exists, skipping.')
            return
        admin = User(
            username='admin',
            email='admin@traceiq.com',
            hashed_password=get_password_hash('admin123'),
            role=UserRole.ADMIN,
            is_active=True,
            badge_number='ADMIN001'
        )
        session.add(admin)
        await session.commit()
        print('✅ Admin user created: admin / admin123')
    await engine.dispose()

asyncio.run(seed_admin())
" || echo "⚠️ Admin seeding skipped (may already exist)"

echo "🚀 Starting TraceIQ Backend..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
