"""add created_by/updated_by uuid columns and make export reason optional

Revision ID: db1c6b1e7e4f
Revises: f17febf561e3
Create Date: 2026-09-01 14:39:59.107588

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "db1c6b1e7e4f"
down_revision: str | Sequence[str] | None = "f17febf561e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Every table except ``exports`` (handled separately below, since it already
# had a ``created_by`` column of a different type) and ``alembic_version``.
_TABLES = (
    "platform_admins",
    "roles",
    "screens",
    "platform_admin_roles",
    "role_screens",
    "audit_logs",
    "password_history",
    "password_reset_otps",
)


def _fk_name(table: str, column: str) -> str:
    return f"fk_{table}_{column}_platform_admins"


def upgrade() -> None:
    """Upgrade schema."""
    for table in _TABLES:
        # A prior (since-abandoned) migration left these as varchar email
        # columns on some environments; drop them if present so this is safe
        # to run whether or not that leftover exists.
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS created_by")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS updated_by")
        op.add_column(table, sa.Column("created_by", sa.Uuid(), nullable=True))
        op.add_column(table, sa.Column("updated_by", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            _fk_name(table, "created_by"), table, "platform_admins", ["created_by"], ["id"]
        )
        op.create_foreign_key(
            _fk_name(table, "updated_by"), table, "platform_admins", ["updated_by"], ["id"]
        )

    # exports.reason becomes optional.
    op.alter_column("exports", "reason", existing_type=sa.String(length=500), nullable=True)

    # exports.created_by moves from a login-email string to the admin's UUID.
    op.drop_index(op.f("ix_exports_created_by"), table_name="exports")
    op.drop_column("exports", "created_by")
    op.add_column("exports", sa.Column("created_by", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_exports_created_by"), "exports", ["created_by"], unique=False)
    op.create_foreign_key(
        _fk_name("exports", "created_by"), "exports", "platform_admins", ["created_by"], ["id"]
    )
    op.add_column("exports", sa.Column("updated_by", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        _fk_name("exports", "updated_by"), "exports", "platform_admins", ["updated_by"], ["id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(_fk_name("exports", "updated_by"), "exports", type_="foreignkey")
    op.drop_column("exports", "updated_by")
    op.drop_constraint(_fk_name("exports", "created_by"), "exports", type_="foreignkey")
    op.drop_index(op.f("ix_exports_created_by"), table_name="exports")
    op.drop_column("exports", "created_by")
    op.add_column(
        "exports", sa.Column("created_by", sa.String(length=255), nullable=False, server_default="")
    )
    op.alter_column("exports", "created_by", server_default=None)
    op.create_index(op.f("ix_exports_created_by"), "exports", ["created_by"], unique=False)
    op.alter_column("exports", "reason", existing_type=sa.String(length=500), nullable=False)

    for table in reversed(_TABLES):
        op.drop_constraint(_fk_name(table, "updated_by"), table, type_="foreignkey")
        op.drop_constraint(_fk_name(table, "created_by"), table, type_="foreignkey")
        op.drop_column(table, "updated_by")
        op.drop_column(table, "created_by")
