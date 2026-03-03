"""Add face quality columns

Revision ID: e8b7d4c2f1a0
Revises: d4f1b0f1e2c3
Create Date: 2026-02-28 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8b7d4c2f1a0'
down_revision: Union[str, Sequence[str], None] = 'd4f1b0f1e2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'face_embeddings',
        sa.Column('quality_status', sa.String(length=64), nullable=False, server_default='accepted'),
    )
    op.add_column(
        'face_embeddings',
        sa.Column('quality_score', sa.Float(), nullable=True),
    )
    op.add_column(
        'face_embeddings',
        sa.Column('blur_score', sa.Float(), nullable=True),
    )
    op.add_column(
        'face_embeddings',
        sa.Column('brightness_score', sa.Float(), nullable=True),
    )
    op.add_column(
        'face_embeddings',
        sa.Column('face_area_ratio', sa.Float(), nullable=True),
    )
    op.add_column(
        'face_embeddings',
        sa.Column('quality_warnings', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('face_embeddings', 'quality_warnings')
    op.drop_column('face_embeddings', 'face_area_ratio')
    op.drop_column('face_embeddings', 'brightness_score')
    op.drop_column('face_embeddings', 'blur_score')
    op.drop_column('face_embeddings', 'quality_score')
    op.drop_column('face_embeddings', 'quality_status')
