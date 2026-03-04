"""Add embedding model metadata to face embeddings

Revision ID: f7a8b9c0d1e2
Revises: e2f7c9b4a1d0
Create Date: 2026-03-03 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e2f7c9b4a1d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "face_embeddings",
        sa.Column("embedding_model_name", sa.String(length=128), nullable=False, server_default="TraceNet v1"),
    )
    op.add_column(
        "face_embeddings",
        sa.Column("embedding_migrated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("face_embeddings", "embedding_model_name", server_default=None)


def downgrade() -> None:
    op.drop_column("face_embeddings", "embedding_migrated_at")
    op.drop_column("face_embeddings", "embedding_model_name")
