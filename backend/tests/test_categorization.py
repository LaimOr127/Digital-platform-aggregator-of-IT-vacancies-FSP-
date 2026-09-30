"""Категоризация: чистые детерминированные правила (без БД)."""

import pytest

from app.services.categorization import Evidence, categorize, result_tier


def ev(
    level: str, place: int | None, stage: str = "final", discipline: str = "product"
) -> Evidence:
    return Evidence(discipline, level, place, stage, "Соревнование", "2025-10-01")


@pytest.mark.parametrize(
    ("evidence", "tier"),
    [
        (ev("national", 2), "elite"),
        (ev("international", 3), "elite"),
        (ev("international", None), "advanced"),
        (ev("national", None), "advanced"),
        (ev("national", None, stage="qualification"), "base"),
        (ev("regional", 1), "advanced"),
        (ev("regional", 5), "base"),
        (ev("regional", None, stage="qualification"), "base"),
    ],
)
def test_result_tier(evidence, tier):
    assert result_tier(evidence) == tier


def test_best_result_wins_per_discipline():
    matches = categorize([ev("regional", 5), ev("national", 1)], rank=None)
    assert [(m.discipline, m.tier) for m in matches] == [("product", "elite")]
    assert matches[0].slug == "product-elite"
    assert any("1 место" in r for r in matches[0].reasons)


def test_one_category_per_discipline_sorted():
    matches = categorize(
        [ev("regional", None, discipline="security"), ev("national", 2, discipline="algorithmic")],
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
