import uuid
from datetime import UTC, datetime

from sqlalchemy import update

from app.models import Passport
from app.repositories.base import BaseRepository


class PassportRepository(BaseRepository[Passport]):
    model = Passport

    async def active_for(self, profile_id: uuid.UUID) -> Passport | None:
        stmt = (
            self._select()
            .where(Passport.profile_id == profile_id, Passport.revoked_at.is_(None))
            .order_by(Passport.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def revoke_all(self, profile_id: uuid.UUID) -> None:
        await self.session.execute(
            update(Passport)
            .where(Passport.profile_id == profile_id, Passport.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
