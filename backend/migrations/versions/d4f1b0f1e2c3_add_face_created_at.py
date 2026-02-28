"""Add created_at to face embeddings

Revision ID: d4f1b0f1e2c3
Revises: c3d9f0c8a1b2
Create Date: 2026-02-28 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f1b0f1e2c3'
down_revision: Union[str, Sequence[str], None] = 'c3d9f0c8a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'face_embeddings',
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE face_embeddings SET created_at = NOW() WHERE created_at IS NULL")
    op.alter_column('face_embeddings', 'created_at', nullable=False)


def downgrade() -> None:
    op.drop_column('face_embeddings', 'created_at')
