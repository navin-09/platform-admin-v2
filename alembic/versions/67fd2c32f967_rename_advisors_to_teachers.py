"""rename advisors to teachers

Revision ID: 67fd2c32f967
Revises: f3e16adb471b
Create Date: 2026-09-02 00:05:28.011049

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "67fd2c32f967"
down_revision: str | Sequence[str] | None = "f3e16adb471b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename advisors -> teachers (table + columns), preserving data."""
    op.rename_table("advisors", "teachers")
    op.alter_column("teachers", "advisor_name", new_column_name="teacher_name")
    op.alter_column("students", "advisor_id", new_column_name="teacher_id")


def downgrade() -> None:
    """Revert teachers -> advisors."""
    op.alter_column("students", "teacher_id", new_column_name="advisor_id")
    op.alter_column("teachers", "teacher_name", new_column_name="advisor_name")
    op.rename_table("teachers", "advisors")
