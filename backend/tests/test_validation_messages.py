"""Ошибки валидации показываются у полей по-русски, без технических формулировок Pydantic."""

import pytest

from app.core.validation import humanize


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        ({"type": "missing"}, "Обязательное поле"),
        ({"type": "string_pattern_mismatch"}, "Недопустимое значение"),
        ({"type": "string_too_short", "ctx": {"min_length": 2}}, "Минимум 2 симв."),
        ({"type": "too_long", "ctx": {"max_length": 50}}, "Не больше 50"),
        ({"type": "less_than_equal", "ctx": {"le": 10}}, "Не больше 10"),
        (
            {"type": "value_error", "msg": "Value error, пароль слишком простой"},
            "пароль слишком простой",
        ),
        (
            {"type": "value_error", "msg": "value is not a valid email address: x"},
            "Некорректный email",
        ),
        ({"type": "something_new", "msg": "English text"}, "Некорректное значение"),
    ],
)
def test_humanize(error: dict, expected: str):
    assert humanize(error) == expected


async def test_api_returns_russian_field_errors(client):
    r = await client.post(
        "/api/v1/auth/register/candidate",
        json={"email": "not-an-email", "password": "x", "full_name": "А"},
    )
    messages = {tuple(d["loc"])[-1]: d["msg"] for d in r.json()["error"]["details"]}
    assert messages["email"] == "Некорректный email"
    assert messages["full_name"] == "Минимум 2 симв."
    assert all("should" not in m and "String" not in m for m in messages.values())
