"""Add stored face bounding box columns

Revision ID: c3d9f0c8a1b2
Revises: b77ca1765eb8
Create Date: 2026-02-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d9f0c8a1b2'
down_revision: Union[str, Sequence[str], None] = 'b77ca1765eb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('face_embeddings', sa.Column('box_x', sa.Integer(), nullable=True))
    op.add_column('face_embeddings', sa.Column('box_y', sa.Integer(), nullable=True))
    op.add_column('face_embeddings', sa.Column('box_w', sa.Integer(), nullable=True))
    op.add_column('face_embeddings', sa.Column('box_h', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('face_embeddings', 'box_h')
    op.drop_column('face_embeddings', 'box_w')
    op.drop_column('face_embeddings', 'box_y')
    op.drop_column('face_embeddings', 'box_x')
