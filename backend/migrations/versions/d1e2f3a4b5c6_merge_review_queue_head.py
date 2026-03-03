"""Merge identity-template and review-queue heads

Revision ID: d1e2f3a4b5c6
Revises: a1b2c3d4e5f6, c9d8e7f6a5b4
Create Date: 2026-03-03 12:55:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = ("a1b2c3d4e5f6", "c9d8e7f6a5b4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
