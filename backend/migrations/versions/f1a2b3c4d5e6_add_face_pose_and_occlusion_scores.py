"""Add face pose and occlusion quality columns

Revision ID: f1a2b3c4d5e6
Revises: e8b7d4c2f1a0
Create Date: 2026-03-03 02:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e8b7d4c2f1a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'face_embeddings',
        sa.Column('pose_score', sa.Float(), nullable=True),
    )
    op.add_column(
        'face_embeddings',
        sa.Column('occlusion_score', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('face_embeddings', 'occlusion_score')
    op.drop_column('face_embeddings', 'pose_score')
