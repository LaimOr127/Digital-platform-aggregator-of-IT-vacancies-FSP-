"""Города в профилях и вакансиях — к написанию справочника

До справочника город вводился вручную («Санкт Петербург», «мск»). Новая проверка принимает только
города из списка, и без нормализации любое сохранение такого профиля или вакансии получало бы 422.
Известные написания приводятся к справочнику, неизвестные очищаются (выбрать город заново).

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.services.cities import canonical_city

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("candidate_profiles", "vacancies")


def upgrade() -> None:
    bind = op.get_bind()
    for table in _TABLES:
        cities = bind.execute(sa.text(f"SELECT DISTINCT city FROM {table} WHERE city IS NOT NULL"))
        for (city,) in list(cities):
            fixed = canonical_city(city)
            if fixed != city:
                bind.execute(
                    sa.text(f"UPDATE {table} SET city = :fixed WHERE city = :city"),
                    {"fixed": fixed, "city": city},
                )


def downgrade() -> None:
    """Исходные написания не сохраняются: откатывать нечего."""
