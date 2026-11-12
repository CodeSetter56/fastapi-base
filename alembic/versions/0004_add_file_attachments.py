"""add file_attachments table

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-11 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'file_attachments',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('owner_type', sa.Text(), nullable=False),
        sa.Column('owner_id', sa.Uuid(), nullable=False),
        sa.Column('label', sa.Text(), nullable=True),
        sa.Column('file_key', sa.Text(), nullable=False),
        sa.Column('thumb_key', sa.Text(), nullable=True),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('content_type', sa.Text(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_file_attachments_owner', 'file_attachments', ['owner_type', 'owner_id'])


def downgrade() -> None:
    op.drop_index('ix_file_attachments_owner', table_name='file_attachments')
    op.drop_table('file_attachments')
