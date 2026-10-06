"""Процедура оценки на малой выборке: свойства, которые должны держаться при любом seed."""

from app.evaluation import assessment_eval, matching_eval
from app.evaluation.__main__ import report
from app.evaluation.matching_eval import _ndcg


def test_assessment_properties():
    result = assessment_eval.run(seed=11, candidates=80)
    assert result.grade_within_one >= 0.9
    assert result.grade_over <= 0.1  # тест не завышает грейд
    assert result.overlap < 0.05  # тесты одной категории почти не пересекаются
    assert result.retest_theta_r > 0.6
    assert result.item_r_median > 0.2
    # утечка ответов ломает единый тест, но почти не помогает против банка шаблонов
    assert result.leak_pass_static >= 0.9 and result.leak_pass_bank < 0.5


def test_matching_beats_random_and_keeps_overrated_out():
    result = matching_eval.run(seed=11, vacancies=8, candidates=250)
    ours, resume, random_order = result.systems.values()
    assert ours.ndcg_at_10 > random_order.ndcg_at_10 + 0.3
    assert ours.overrated_in_top < resume.overrated_in_top


def test_ndcg_of_ideal_and_empty_ranking():
    assert _ndcg([2, 2, 1, 0]) == 1.0
    assert _ndcg([0, 0]) == 0.0


def test_report_is_markdown():
    assessment = assessment_eval.run(seed=3, candidates=30)
    matching = matching_eval.run(seed=3, vacancies=3, candidates=60)
    text = report(3, assessment, assessment, matching)
    assert text.startswith("# Результаты оценки") and "| IT Match |" in text
