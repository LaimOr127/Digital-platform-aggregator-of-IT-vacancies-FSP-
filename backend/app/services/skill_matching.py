"""Сопоставление навыков из внешних источников (анкета ФСП, текст резюме) со справочником.

Названия сравниваются без учёта регистра, с распространёнными синонимами. Короткие названия
(Go, C) в тексте ищутся только с исходным регистром: «go» в обычной фразе — не язык Go.
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Skill

# синоним -> slug навыка из справочника
ALIASES = {
    "golang": "go",
    "postgres": "postgresql",
    "psql": "postgresql",
    "js": "javascript",
    "ts": "typescript",
    "nodejs": "node.js",
    "node": "node.js",
    "k8s": "kubernetes",
    "ml": "machine-learning",
    "машинное обучение": "machine-learning",
    "pytest": "qa-automation",
    "selenium": "qa-automation",
    "ci/cd": "ci-cd",
    "gitlab ci": "ci-cd",
    "github actions": "ci-cd",
    "c sharp": "c#",
    "asp.net": "dotnet",
    "ros": "robotics",
    "компьютерное зрение": "machine-learning",
    "алгоритмы": "algorithms",
    "структуры данных": "algorithms",
    "информационная безопасность": "information-security",
    "иб": "information-security",
    "ctf": "information-security",
    "бпла": "drones",
    "бас": "drones",
}
_SHORT = 2  # названия не длиннее — только с исходным регистром


@dataclass(frozen=True)
class SkillMatch:
    slugs: list[str]
    unknown: list[str]


class SkillDictionary:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = skills
        self.by_key = {s.slug.lower(): s.slug for s in skills} | {
            s.name.lower(): s.slug for s in skills
        }
        known = set(self.by_key.values())
        self.aliases = {alias: slug for alias, slug in ALIASES.items() if slug in known}

    @classmethod
    async def load(cls, session: AsyncSession) -> "SkillDictionary":
        return cls(list((await session.execute(select(Skill))).scalars()))

    def match_names(self, names: list[str]) -> SkillMatch:
        """Список названий (стек из анкеты) -> slug из справочника и нераспознанные."""
        slugs: list[str] = []
        unknown: list[str] = []
        for name in names:
            key = name.strip().lower()
            slug = self.by_key.get(key) or self.aliases.get(key)
            if slug and slug not in slugs:
                slugs.append(slug)
            elif not slug and key:
                unknown.append(name.strip())
        return SkillMatch(slugs, unknown)

    def find_in_text(self, text: str) -> list[str]:
        """Навыки, упомянутые в свободном тексте (резюме), в порядке справочника."""
        found: list[str] = []
        candidates = [(s.name, s.slug) for s in self.skills] + [
            (alias, slug) for alias, slug in self.aliases.items()
        ]
        for name, slug in candidates:
            if slug not in found and _mentioned(name, text):
                found.append(slug)
        return found


def _mentioned(name: str, text: str) -> bool:
    # границы слова с учётом символов в названиях: C++, C#, .NET, Node.js, CI/CD
    pattern = rf"(?<![\w+#.]){re.escape(name)}(?![\w+#])"
    flags = 0 if len(name) <= _SHORT else re.IGNORECASE
    return re.search(pattern, text, flags) is not None
