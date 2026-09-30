"""Модерация компаний и аудит."""

from httpx import AsyncClient
from sqlalchemy import select

from app.models import AuditLog
from tests.helpers import bearer, company_id, create_admin, register_employer


async def test_list_pending_and_approve_with_audit(client: AsyncClient, db, app):
    employer = await register_employer(client, company="ООО Модерация")
    cid = await company_id(client, employer)
    admin = await create_admin(db, app)

    r = await client.get(
        "/api/v1/admin/companies", params={"status": "pending"}, headers=bearer(admin)
    )
    assert r.status_code == 200 and cid in [c["id"] for c in r.json()["items"]]

    r = await client.post(
        f"/api/v1/admin/companies/{cid}/status",
        json={"status": "blocked", "reason": "фейковая компания"},
        headers=bearer(admin),
    )
    assert r.status_code == 200 and r.json()["status"] == "blocked"

    async with db.sessionmaker() as session:
        entry = (
            await session.execute(select(AuditLog).where(AuditLog.action == "admin.company_status"))
        ).scalar_one()
    assert entry.meta == {
        "from": "pending",
        "to": "blocked",
        "reason": "фейковая компания",
        "vacancies": 0,
    }


async def test_unknown_company_404(client: AsyncClient, db, app):
    admin = await create_admin(db, app)
    r = await client.post(
        "/api/v1/admin/companies/00000000-0000-0000-0000-000000000000/status",
        json={"status": "approved"},
        headers=bearer(admin),
    )
    assert r.status_code == 404


async def test_public_skills_dictionary(client: AsyncClient):
    r = await client.get("/api/v1/public/skills")
    assert r.status_code == 200 and "python" in [s["slug"] for s in r.json()]
