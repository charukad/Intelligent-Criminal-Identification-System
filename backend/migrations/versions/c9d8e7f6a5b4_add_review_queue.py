"""Add duplicate identity review queue

Revision ID: c9d8e7f6a5b4
Revises: f1a2b3c4d5e6
Create Date: 2026-03-03 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "review_cases",
        sa.Column(
            "case_type",
            sa.Enum("DUPLICATE_IDENTITY", name="reviewcasetype"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "CONFIRMED_DUPLICATE",
                "FALSE_POSITIVE",
                "DISMISSED",
                name="reviewcasestatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "risk_level",
            sa.Enum(
                "PROBABLE_DUPLICATE",
                "NEEDS_REVIEW",
                name="duplicaterisklevel",
            ),
            nullable=False,
        ),
        sa.Column("source_criminal_id", sa.Uuid(), nullable=False),
        sa.Column("matched_criminal_id", sa.Uuid(), nullable=False),
        sa.Column("source_face_id", sa.Uuid(), nullable=True),
        sa.Column("matched_face_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_by_id", sa.Uuid(), nullable=True),
        sa.Column("distance", sa.Float(), nullable=False),
        sa.Column("embedding_version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("template_version", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("submitted_filename", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["source_criminal_id"], ["criminals.id"]),
        sa.ForeignKeyConstraint(["matched_criminal_id"], ["criminals.id"]),
        sa.ForeignKeyConstraint(["source_face_id"], ["face_embeddings.id"]),
        sa.ForeignKeyConstraint(["matched_face_id"], ["face_embeddings.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_cases_source_criminal_id"), "review_cases", ["source_criminal_id"], unique=False)
    op.create_index(op.f("ix_review_cases_matched_criminal_id"), "review_cases", ["matched_criminal_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_review_cases_matched_criminal_id"), table_name="review_cases")
    op.drop_index(op.f("ix_review_cases_source_criminal_id"), table_name="review_cases")
    op.drop_table("review_cases")
    op.execute("DROP TYPE IF EXISTS duplicaterisklevel")
    op.execute("DROP TYPE IF EXISTS reviewcasestatus")
    op.execute("DROP TYPE IF EXISTS reviewcasetype")
