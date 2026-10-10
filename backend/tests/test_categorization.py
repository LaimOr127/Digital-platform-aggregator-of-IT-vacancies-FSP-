"""Категоризация: чистые детерминированные правила (без БД)."""

import pytest

from app.services.categorization import Evidence, categorize, discipline_tier, result_tier


def ev(
    level: str, place: int | None, stage: str = "final", discipline: str = "product"
) -> Evidence:
    return Evidence(discipline, level, place, stage, "Соревнование", "2025-10-01")


@pytest.mark.parametrize(
    ("evidence", "tier"),
    [
        ([ev("national", 2)], "advanced"),  # один приз — уровень выше участия
        ([ev("regional", 1), ev("national", 3)], "elite"),  # два приза — при любом уровне
        ([ev("regional", 2), ev("regional", 1)], "elite"),  # региональные не хуже всероссийских
        ([ev("international", None), ev("regional", None)], "advanced"),  # два финала
        ([ev("national", None)], "base"),  # один финал без приза
        ([ev("regional", 5, stage="qualification")] * 6, "base"),  # явками уровень не набить
    ],
)
def test_tier_counts_prizes_and_finals_not_competition_status(evidence, tier):
    assert discipline_tier(evidence) == tier
    assert categorize(evidence, rank=None)[0].tier == tier


def test_result_strength_ignores_competition_status():
    assert result_tier(ev("regional", 1)) == result_tier(ev("international", 1)) == "elite"
    assert result_tier(ev("national", None)) == "advanced"
    assert result_tier(ev("national", None, stage="qualification")) == "base"


def test_reasons_list_the_results_that_counted():
    matches = categorize([ev("regional", 5, stage="qualification"), ev("national", 1)], rank=None)
    assert [(m.discipline, m.tier) for m in matches] == [("product", "advanced")]
    assert matches[0].slug == "product-advanced"
    assert any("1 место" in r for r in matches[0].reasons)
    assert not any("участие" in r for r in matches[0].reasons)


def test_one_category_per_discipline_sorted():
    matches = categorize(
        [
            ev("regional", None, discipline="security"),
            ev("national", 2, discipline="algorithmic"),
            ev("regional", 3, discipline="algorithmic"),
        ],
        rank=None,
    )
    assert [m.slug for m in matches] == ["algorithmic-elite", "security-base"]


@pytest.mark.parametrize(("rank", "tier"), [("МС", "elite"), ("КМС", "advanced"), ("2", "base")])
def test_rank_raises_tier_only_where_there_are_results(rank, tier):
    matches = categorize([ev("regional", None, stage="qualification")], rank=rank)
    assert matches[0].tier == tier
    if tier != "base":
        assert any(rank in r for r in matches[0].reasons)


def test_no_results_no_categories():
    assert categorize([], rank="МС") == []


def test_titles_are_human_readable():
    (match,) = categorize([ev("national", 1, discipline="drones")], rank=None)
    assert match.title.startswith("Программирование беспилотных авиационных систем")


def test_deterministic():
    data = [ev("national", 2), ev("regional", 1, discipline="security")]
    assert categorize(data, "1") == categorize(list(reversed(data)), "1")
