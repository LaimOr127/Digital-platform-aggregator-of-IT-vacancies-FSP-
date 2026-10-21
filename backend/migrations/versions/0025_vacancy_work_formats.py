"""Allow a vacancy to offer multiple work formats.

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("vacancies", sa.Column("work_formats", sa.JSON(), nullable=True))
    if op.get_bind().dialect.name == "postgresql":
        op.execute("UPDATE vacancies SET work_formats = json_build_array(work_format)")
    else:
        op.execute("UPDATE vacancies SET work_formats = json_array(work_format)")


def downgrade() -> None:
    op.drop_column("vacancies", "work_formats")
