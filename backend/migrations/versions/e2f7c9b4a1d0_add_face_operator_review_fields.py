"""Add operator review fields for face embeddings

Revision ID: e2f7c9b4a1d0
Revises: d1e2f3a4b5c6
Create Date: 2026-03-03 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2f7c9b4a1d0"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "face_embeddings",
        sa.Column("exclude_from_template", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "face_embeddings",
        sa.Column("operator_review_status", sa.String(), nullable=False, server_default="normal"),
    )
    op.add_column(
        "face_embeddings",
        sa.Column("operator_review_notes", sa.Text(), nullable=True),
    )
    op.alter_column("face_embeddings", "exclude_from_template", server_default=None)
    op.alter_column("face_embeddings", "operator_review_status", server_default=None)


def downgrade() -> None:
    op.drop_column("face_embeddings", "operator_review_notes")
    op.drop_column("face_embeddings", "operator_review_status")
    op.drop_column("face_embeddings", "exclude_from_template")
