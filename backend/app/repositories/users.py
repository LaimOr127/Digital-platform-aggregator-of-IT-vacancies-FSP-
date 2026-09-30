import uuid
from datetime import UTC, datetime

from sqlalchemy import func, update

from app.models import RefreshToken, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def by_email(self, email: str) -> User | None:
        return await self.first(func.lower(User.email) == email.lower())


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def by_hash(self, token_hash: str) -> RefreshToken | None:
        return await self.first(RefreshToken.token_hash == token_hash)

    async def consume(self, token_id: uuid.UUID) -> bool:
        """Отозвать токен, только если он ещё активен (условный UPDATE — без гонок)."""
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        return result.rowcount == 1  # type: ignore[attr-defined]

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
