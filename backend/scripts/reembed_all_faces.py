import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.database import AsyncSessionLocal  # noqa: E402
from src.infrastructure.repositories.face import FaceRepository  # noqa: E402
from src.infrastructure.repositories.identity_template import IdentityTemplateRepository  # noqa: E402
from src.services.embedding_migration_service import EmbeddingMigrationService  # noqa: E402
from src.services.identity_template_service import IdentityTemplateService  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Re-embed stored face records to a new embedding version with backup and rollback support.",
    )
    parser.add_argument(
        "--target-version",
        help="Target embedding version to write into face embeddings and identity templates.",
    )
    parser.add_argument(
        "--source-version",
        help="Optional source embedding version filter. Only matching face rows will be processed.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        help="Optional custom checkpoint path for custom TraceNet migrations.",
    )
    parser.add_argument(
        "--backup-json",
        type=Path,
        help="Optional path for the pre-migration backup snapshot JSON.",
    )
    parser.add_argument(
        "--rollback-json",
        type=Path,
        help="Restore a previously exported snapshot instead of running a new migration.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional face limit for dry runs or staged migrations.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the plan without mutating stored face records.",
    )
    return parser


def build_default_backup_path(target_version: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return PROJECT_ROOT / "uploads" / "migration-backups" / f"{target_version}-{timestamp}.json"


async def run(args: argparse.Namespace) -> dict:
    async with AsyncSessionLocal() as session:
        face_repo = FaceRepository(session)
        template_repo = IdentityTemplateRepository(session)
        template_service = IdentityTemplateService(template_repo, face_repo)
        migration_service = EmbeddingMigrationService(
            face_repo=face_repo,
            template_repo=template_repo,
            template_service=template_service,
        )

        if args.rollback_json:
            return await migration_service.restore_snapshot(
                args.rollback_json,
                dry_run=args.dry_run,
            )

        if not args.target_version:
            raise SystemExit("--target-version is required unless --rollback-json is provided.")

        backup_path = args.backup_json
        if backup_path is None and not args.dry_run:
            backup_path = build_default_backup_path(args.target_version)

        return await migration_service.reembed_all_faces(
            target_embedding_version=args.target_version,
            source_embedding_version=args.source_version,
            model_path=args.model_path,
            backup_path=backup_path,
            limit=args.limit,
            dry_run=args.dry_run,
        )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = asyncio.run(run(args))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
