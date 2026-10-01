"""Очередь писем: доставка воркером, повторы, адресаты, уведомления о событиях."""

from httpx import AsyncClient
from sqlalchemy import select, update

from app.models import OutboxMessage, User
from app.models.enums import OutboxStatus, RecipientType
from app.services.emails import TEMPLATES, render
from app.services.outbox import MAX_ATTEMPTS, Outbox
from app.worker.jobs import OutboxJob
from tests.fake_notifier import MemoryNotifier
from tests.helpers import (
    PASSWORD,
    approve_company,
    bearer,
    company_id,
    create_admin,
    register_candidate,
    register_employer,
    unique_email,
)

PUBLIC_URL = "https://itmatch.example"


def job(db, app, notifier: MemoryNotifier) -> OutboxJob:
    return OutboxJob(db, app.state.cipher, notifier, PUBLIC_URL)


async def messages(db) -> list[OutboxMessage]:
    async with db.sessionmaker() as session:
        return list((await session.execute(select(OutboxMessage))).scalars())


async def email_of(client: AsyncClient, token: str) -> str:
    return (await client.get("/api/v1/auth/me", headers=bearer(token))).json()["email"]


async def test_delivery_renders_link_and_wipes_payload(client: AsyncClient, db, app):
    email = unique_email("mail")
    await client.post(
        "/api/v1/auth/register/candidate",
        json={"email": email, "password": PASSWORD, "full_name": "Анна"},
    )
    notifier = MemoryNotifier()
    assert await job(db, app, notifier).run() == 1
    [sent] = notifier.sent
    assert sent.to == email and sent.subject == "Подтвердите почту"
    assert f"{PUBLIC_URL}/verify-email#token=" in sent.body
    [message] = await messages(db)
    # токен из письма больше не хранится нигде, кроме ящика получателя
    assert message.status == OutboxStatus.SENT and message.payload_enc is None
    assert await job(db, app, notifier).run() == 0  # отправленное не уходит повторно


async def test_failed_send_is_retried_later_then_given_up(client: AsyncClient, db, app):
    await register_candidate(client)
    failing = MemoryNotifier(fail=True)
    assert await job(db, app, failing).run() == 1
    [message] = await messages(db)
    assert message.status == OutboxStatus.PENDING and message.attempts == 1
    assert await job(db, app, failing).run() == 0  # следующая попытка — после паузы
    async with db.sessionmaker() as session:
        await session.execute(
            update(OutboxMessage).values(
                attempts=MAX_ATTEMPTS - 1, next_attempt_at=message.created_at
            )
        )
        await session.commit()
    await job(db, app, failing).run()
    [message] = await messages(db)
    assert message.status == OutboxStatus.FAILED and message.payload_enc is None


async def test_blocked_recipient_is_dropped(client: AsyncClient, db, app):
    token = await register_candidate(client)
    email = await email_of(client, token)
    async with db.sessionmaker() as session:
        await session.execute(update(OutboxMessage).values(status=OutboxStatus.SENT))
        await session.execute(update(User).where(User.email == email).values(is_active=False))
        await session.commit()
    await client.post("/api/v1/auth/password/forgot", json={"email": email})  # не уйдёт
    async with db.sessionmaker() as session:
        user_id = (await session.execute(select(User.id).where(User.email == email))).scalar_one()
        Outbox(session, app.state.cipher).enqueue("account_exists", RecipientType.USER, user_id)
        await session.commit()
    notifier = MemoryNotifier()
    await job(db, app, notifier).run()
    assert notifier.sent == []
    statuses = {m.status for m in await messages(db)}
    assert OutboxStatus.DROPPED in statuses


async def test_broken_message_does_not_block_queue(client: AsyncClient, db, app):
    await register_candidate(client)  # письмо подтверждения уже доставлено при входе
    async with db.sessionmaker() as session:
        await session.execute(update(OutboxMessage).values(status=OutboxStatus.SENT))
        user_id = (await session.execute(select(User.id))).scalars().first()
        outbox = Outbox(session, app.state.cipher)
        outbox.enqueue("no_such_template", RecipientType.USER, user_id)
        outbox.enqueue("account_exists", RecipientType.USER, user_id)
        await session.commit()
    notifier = MemoryNotifier()
    await job(db, app, notifier).run()
    assert [e.subject for e in notifier.sent] == ["Попытка регистрации"]
    assert {m.kind: m.status for m in await messages(db)}["no_such_template"] == "failed"


async def test_offer_and_answer_notify_both_sides(client: AsyncClient, db, app):
    from tests.test_offers import approved_employer, send, verified_candidate

    employer = await approved_employer(client, db, app)
    candidate = await verified_candidate(client)
    offer = await send(client, candidate, employer)
    await client.post(
        f"/api/v1/candidate/offers/{offer['id']}/accept", headers=bearer(candidate["token"])
    )
    notifier = MemoryNotifier()
    await job(db, app, notifier).run()
    received = {e.to: e for e in notifier.sent if e.subject in ("Новый оффер", "Оффер принят")}
    candidate_mail = received[await email_of(client, candidate["token"])]
    employer_mail = received[await email_of(client, employer["token"])]
    assert candidate_mail.subject == "Новый оффер" and offer["vacancy_title"] in candidate_mail.body
    # компании письмо без данных кандидата: контакты — только в кабинете
    assert employer_mail.subject == "Оффер принят" and "@anna" not in employer_mail.body


async def test_company_gets_moderation_decision(client: AsyncClient, db, app):
    employer = await register_employer(client, company="ООО Почта")
    admin = await create_admin(db, app)
    await approve_company(client, admin, await company_id(client, employer))
    notifier = MemoryNotifier()
    await job(db, app, notifier).run()
    approved = [e for e in notifier.sent if e.subject == "Компания одобрена"]
    assert len(approved) == 1 and "«ООО Почта»" in approved[0].body
    assert approved[0].to == await email_of(client, employer)


def test_every_template_renders_with_signature():
    payloads = {
        "verify_email": {"token": "t"},
        "account_exists": {},
        "password_reset": {"token": "t"},
        "offer_received": {
            "company": "A",
            "vacancy": "B",
            "salary_min": 100000,
            "salary_max": 200000,
        },
        "offer_answered": {"vacancy": "B", "accepted": False},
        "company_status": {"company": "A", "status": "blocked"},
    }
    assert set(payloads) == set(TEMPLATES)
    for kind, payload in payloads.items():
        subject, body = render(kind, payload, PUBLIC_URL + "/")
        assert subject and "\n" not in subject and body.endswith("данными ФСП")
        assert "//" not in body.replace("https://", "")  # без двойного слеша в ссылках
    assert "100 000 – 200 000 ₽" in render("offer_received", payloads["offer_received"], "u")[1]
