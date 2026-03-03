import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.core.config import settings
from src.domain.models.face import FaceEmbedding
from src.infrastructure.repositories.face import FaceRepository
from src.infrastructure.repositories.identity_template import IdentityTemplateRepository
from src.services.identity_template_service import IdentityTemplateService


async def rebuild_identity_templates() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(select(FaceEmbedding.criminal_id).distinct())
        criminal_ids = [criminal_id for criminal_id in result.scalars().all() if criminal_id is not None]

        if not criminal_ids:
            print("ℹ️ No enrolled faces found. Identity template rebuild skipped.")
            await engine.dispose()
            return

        face_repo = FaceRepository(session)
        template_repo = IdentityTemplateRepository(session)
        service = IdentityTemplateService(template_repo, face_repo)

        rebuilt_count = 0
        for criminal_id in criminal_ids:
            await service.rebuild_for_criminal(criminal_id)
            rebuilt_count += 1

        print(f"✅ Rebuilt identity templates for {rebuilt_count} criminal(s).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(rebuild_identity_templates())
