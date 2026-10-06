"""Справочник городов: старые и ручные написания приводятся к справочнику (миграция 0021)."""

from app.services.cities import canonical_city


def test_known_spellings_map_to_dictionary():
    assert canonical_city("Санкт Петербург") == "Санкт-Петербург"
    assert canonical_city("  мск ") == "Москва"
    assert canonical_city("Орел") == "Орёл"
    assert canonical_city("Ростов-на-дону") == "Ростов-на-Дону"


def test_unknown_city_is_dropped():
    assert canonical_city("Урюпинск") is None
    assert canonical_city("") is None
