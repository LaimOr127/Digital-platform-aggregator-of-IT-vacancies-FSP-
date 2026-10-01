"""Разбор резюме без внешних сервисов: текст из файлов, правила, справочник навыков."""

import pytest

from app.services.resume import rules
from app.services.resume.extract import UnsupportedResumeError, extract_text
from app.services.skill_matching import SkillDictionary
from tests.resume_files import RESUME_TEXT, docx, pdf


class FakeSkill:
    def __init__(self, slug: str, name: str) -> None:
        self.slug, self.name = slug, name


DICTIONARY = SkillDictionary(
    [
        FakeSkill(s, n)
        for s, n in [
            ("python", "Python"),
            ("go", "Go"),
            ("postgresql", "PostgreSQL"),
            ("c++", "C++"),
            ("c#", "C#"),
            ("dotnet", ".NET"),
            ("docker", "Docker"),
            ("react", "React"),
            ("fastapi", "FastAPI"),
        ]
    ]  # type: ignore[arg-type]
)


def test_rules_extract_profile_fields():
    parsed = rules.parse(RESUME_TEXT)
    assert parsed.full_name == "Анна Смирнова"
    assert parsed.title == "Senior Backend-разработчик"
    assert parsed.grade == "senior" and parsed.experience_years == 6
    assert parsed.city == "Казань" and parsed.work_format == "remote"
    assert parsed.salary_min == 350_000
    assert parsed.email == "anna.dev@example.org"
    assert parsed.phone == "+79001234567" and parsed.telegram == "@anna_backend"
    assert parsed.about.startswith("Строю высоконагруженные") and "Навыки" not in parsed.about


def test_salary_in_thousands():
    assert rules.parse("Иван Петров\nЗарплата: 250к").salary_min == 250_000


def test_contacts_are_masked_before_ai():
    masked = rules.mask_contacts(RESUME_TEXT)
    for secret in ("anna.dev@example.org", "123-45-67", "anna_backend"):
        assert secret not in masked
    assert "Казань" in masked


def test_skills_found_in_text_with_aliases_and_symbols():
    text = "Пишу на C++ и C#, немного .NET; golang и Postgres. Let's go!"
    assert set(DICTIONARY.find_in_text(text)) == {"go", "postgresql", "c++", "c#", "dotnet"}
    # «go» в обычной фразе не считается языком Go
    assert DICTIONARY.find_in_text("we go home") == []


def test_skill_names_matched_with_unknown_reported():
    matched = DICTIONARY.match_names(["python", "Golang", "Rust", "PostgreSQL"])
    assert matched.slugs == ["python", "go", "postgresql"] and matched.unknown == ["Rust"]


def test_docx_and_pdf_text():
    assert "Анна Смирнова" in extract_text(docx())
    assert "Senior Backend Developer" in extract_text(
        pdf(["John Smith", "Senior Backend Developer"])
    )


@pytest.mark.parametrize(
    "data",
    [b"\x89PNG\r\n\x1a\n" + b"0" * 100, b"PK\x03\x04broken", pdf([]), b"%PDF-1.4 garbage"],
)
def test_bad_files_rejected(data: bytes):
    with pytest.raises(UnsupportedResumeError):
        extract_text(data)


def test_docx_zip_bomb_guard(monkeypatch):
    monkeypatch.setattr("app.services.resume.extract._MAX_DOCX_XML", 10)
    with pytest.raises(UnsupportedResumeError, match="слишком большой"):
        extract_text(docx())
