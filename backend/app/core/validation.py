"""Ошибки валидации Pydantic -> понятные сообщения на русском (интерфейс показывает их у полей).

Сообщения собственных валидаторов уже на русском: у них убирается служебный префикс.
"""

from typing import Any

_FIXED = {
    "missing": "Обязательное поле",
    "string_pattern_mismatch": "Недопустимое значение",
    "enum": "Выберите значение из списка",
    "literal_error": "Выберите значение из списка",
    "int_parsing": "Нужно целое число",
    "int_type": "Нужно целое число",
    "bool_parsing": "Нужно да или нет",
    "uuid_parsing": "Некорректный идентификатор",
    "json_invalid": "Некорректный JSON",
    "url_parsing": "Некорректная ссылка",
}
_BOUNDS = {
    "string_too_short": "Минимум {min_length} симв.",
    "string_too_long": "Максимум {max_length} симв.",
    "too_short": "Нужно не меньше {min_length}",
    "too_long": "Не больше {max_length}",
    "greater_than_equal": "Не меньше {ge}",
    "greater_than": "Больше {gt}",
    "less_than_equal": "Не больше {le}",
    "less_than": "Меньше {lt}",
}
_VALUE_ERROR_PREFIX = "Value error, "


def humanize(error: dict[str, Any]) -> str:
    kind = error.get("type", "")
    if kind in _FIXED:
        return _FIXED[kind]
    if kind in _BOUNDS:
        return _BOUNDS[kind].format(**error.get("ctx", {}))
    message = str(error.get("msg", ""))
    if kind == "value_error":
        if "email address" in message:
            return "Некорректный email"
        return message.removeprefix(_VALUE_ERROR_PREFIX)
    return "Некорректное значение"
