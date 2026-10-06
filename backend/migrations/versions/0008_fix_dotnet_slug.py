"""Код навыка .NET -> dotnet: код навыка должен начинаться с буквы или цифры

Вакансии и профили с навыком .NET не сохранялись (ошибка проверки кода навыка).
Связи навыков хранятся по id — смена кода не затрагивает профили и вакансии.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE skills SET slug = 'dotnet' WHERE slug = '.net'")


def downgrade() -> None:
    op.execute("UPDATE skills SET slug = '.net' WHERE slug = 'dotnet'")
