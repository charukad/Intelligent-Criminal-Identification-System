"""Add identity templates and template roles

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-03-03 03:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy.vector
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'face_embeddings',
        sa.Column('template_role', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='archived'),
    )
    op.add_column(
        'face_embeddings',
        sa.Column('template_distance', sa.Float(), nullable=True),
    )

    op.create_table(
        'identity_templates',
        sa.Column('criminal_id', sa.Uuid(), nullable=False),
        sa.Column('template_version', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('embedding_version', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('primary_face_id', sa.Uuid(), nullable=True),
        sa.Column('included_face_ids', sa.Text(), nullable=True),
        sa.Column('support_face_ids', sa.Text(), nullable=True),
        sa.Column('archived_face_ids', sa.Text(), nullable=True),
        sa.Column('outlier_face_ids', sa.Text(), nullable=True),
        sa.Column('active_face_count', sa.Integer(), nullable=False),
        sa.Column('support_face_count', sa.Integer(), nullable=False),
        sa.Column('archived_face_count', sa.Integer(), nullable=False),
        sa.Column('outlier_face_count', sa.Integer(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('template_embedding', pgvector.sqlalchemy.vector.VECTOR(dim=512), nullable=False),
        sa.ForeignKeyConstraint(['criminal_id'], ['criminals.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('criminal_id'),
    )
    op.create_index(op.f('ix_identity_templates_criminal_id'), 'identity_templates', ['criminal_id'], unique=True)
    op.create_index(op.f('ix_identity_templates_primary_face_id'), 'identity_templates', ['primary_face_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_identity_templates_primary_face_id'), table_name='identity_templates')
    op.drop_index(op.f('ix_identity_templates_criminal_id'), table_name='identity_templates')
    op.drop_table('identity_templates')
    op.drop_column('face_embeddings', 'template_distance')
    op.drop_column('face_embeddings', 'template_role')
