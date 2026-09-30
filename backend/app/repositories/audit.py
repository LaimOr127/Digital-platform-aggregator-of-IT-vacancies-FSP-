import uuid

from app.models import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def record(
        self,
        action: str,
        actor_id: uuid.UUID | None,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        meta: dict | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                action=action,
                actor_id=actor_id,
                target_type=target_type,
                target_id=target_id,
                meta=meta or {},
            )
        )
