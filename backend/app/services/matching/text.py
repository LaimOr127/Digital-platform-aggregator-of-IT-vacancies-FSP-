"""Смысловая близость текстов без внешних сервисов: общие значимые слова.

Слова приводятся к упрощённой основе (первые 6 букв): «разработка», «разработчик»
и «разрабатывать» совпадают. Служебные и слишком общие слова отбрасываются.
"""

import re

_STEM = 6
_MIN_WORD = 3
_STOP = frozenset(
    [
        "and",
        "the",
        "for",
        "with",
        "you",
        "our",
        "are",
        "from",
        "that",
        "this",
        "will",
        "have",
        "опыт",
        "работы",
        "работа",
        "работать",
        "знание",
        "знания",
        "умение",
        "умения",
        "задачи",
        "задач",
        "команда",
        "команды",
        "компании",
        "компания",
        "проект",
        "проекты",
        "проектов",
        "будет",
        "будем",
        "нужно",
        "надо",
        "можно",
        "также",
        "более",
        "лет",
        "год",
        "года",
        "чем",
        "как",
        "что",
        "это",
        "или",
        "для",
        "при",
        "над",
        "под",
        "без",
        "про",
        "его",
        "ее",
        "наш",
        "наша",
        "ваш",
        "ваша",
        "они",
        "она",
        "оно",
        "все",
        "всех",
        "очень",
        "хорошо",
        "умею",
        "люблю",
        "буду",
        "есть",
        "нас",
        "вас",
        "мне",
        "мой",
        "моя",
        "мои",
        "быть",
        "был",
        "была",
        "были",
    ]
)


def keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zа-яё0-9+#]+", text.lower().replace("ё", "е"))
    return {word[:_STEM] for word in words if len(word) >= _MIN_WORD and word not in _STOP}


def overlap(vacancy_text: str, candidate_text: str) -> tuple[float, list[str]]:
    return overlap_with(frozenset(keywords(vacancy_text)), candidate_text)


def overlap_with(wanted: frozenset[str], candidate_text: str) -> tuple[float, list[str]]:
    """Доля ключевых слов вакансии, встречающихся у кандидата, и примеры общих слов.

    Насыщение на 25%: описания разной длины, полного совпадения слов не бывает.
    Ключевые слова вакансии считаются один раз на весь рейтинг (VacancyContext).
    """
    if not wanted:
        return 0.0, []
    common = wanted & keywords(candidate_text)
    share = len(common) / len(wanted)
    return min(1.0, share / 0.25), sorted(common)[:5]
