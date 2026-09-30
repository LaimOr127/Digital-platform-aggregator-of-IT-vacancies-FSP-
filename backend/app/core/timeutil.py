from datetime import UTC, datetime


def as_aware(value: datetime) -> datetime:
    """SQLite возвращает naive datetime, PostgreSQL — aware. Приводим к UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)
