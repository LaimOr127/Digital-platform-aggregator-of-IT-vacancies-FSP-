"""Жалобы на вакансии: кандидат жалуется один раз, модератор видит жалобы и фильтрует по ним."""

from httpx import AsyncClient

from tests.flows import approved_employer, verified_candidate
from tests.helpers import bearer, create_admin, register_candidate

ADMIN_VACANCIES = "/api/v1/admin/vacancies"


def complaint_url(vacancy_id: str) -> str:
    return f"/api/v1/candidate/vacancies/{vacancy_id}/complaint"


async def test_candidate_complains_once_and_moderator_sees_it(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    vacancy_id = employer["vacancy"]["id"]
    candidate = await verified_candidate(client)
    body = {"reason": "fake", "comment": "Просят оплатить обучение"}
    url = complaint_url(vacancy_id)
    assert (
        await client.post(url, json=body, headers=bearer(candidate["token"]))
    ).status_code == 204
    again = await client.post(url, json=body, headers=bearer(candidate["token"]))
    assert again.status_code == 409

    admin = await create_admin(db, app)
    listed = await client.get(
        ADMIN_VACANCIES, params={"with_complaints": True}, headers=bearer(admin)
    )
    (item,) = listed.json()["items"]
    assert item["id"] == vacancy_id and item["complaints"] == 1
    assert item["complaint_notes"] == ["Фиктивная вакансия или компания: Просят оплатить обучение"]


async def test_complaint_needs_published_vacancy_and_known_reason(client: AsyncClient, db, app):
    employer = await approved_employer(client, db, app)
    token = await register_candidate(client)
    bad = await client.post(
        complaint_url(employer["vacancy"]["id"]), json={"reason": "boring"}, headers=bearer(token)
    )
    assert bad.status_code == 422
    missing = await client.post(
        complaint_url("00000000-0000-0000-0000-000000000000"),
        json={"reason": "spam"},
        headers=bearer(token),
    )
    assert missing.status_code == 404
