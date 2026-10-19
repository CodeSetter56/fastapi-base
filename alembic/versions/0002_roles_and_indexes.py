"""add user roles and pagination indexes

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN role text NOT NULL DEFAULT 'user'")
    # Existing databases predate roles. Promote the oldest account so there is
    # at least one admin; fresh databases instead promote the first registered
    # user in the registration service.
    op.execute(
        """
        UPDATE users
        SET role = 'admin'
        WHERE id = (SELECT id FROM users ORDER BY created_at LIMIT 1)
        """
    )
    op.execute("CREATE INDEX ix_users_created_at ON users (created_at)")
    op.execute("DROP INDEX IF EXISTS ix_items_owner_id")
    op.execute(
        "CREATE INDEX ix_items_owner_id_created_at "
        "ON items (owner_id, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_items_owner_id_created_at")
    op.execute("CREATE INDEX ix_items_owner_id ON items (owner_id)")
    op.execute("DROP INDEX IF EXISTS ix_users_created_at")
    op.execute("ALTER TABLE users DROP COLUMN role")
