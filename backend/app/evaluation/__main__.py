"""Отчёт процедуры оценки в Markdown: python -m app.evaluation [--seed N] [--candidates N]."""

import argparse
import sys

from app.evaluation import assessment_eval, matching_eval
from app.services.specializations import GRADE_ORDER, GRADE_TITLES


def main() -> None:
    parser = argparse.ArgumentParser(description="Оценка тестирования и подбора на синтетике")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--candidates", type=int, default=1000)
    parser.add_argument("--vacancies", type=int, default=40)
    args = parser.parse_args()
    assessment = assessment_eval.run(args.seed, args.candidates)
    familiar = assessment_eval.run(args.seed, args.candidates, stack_gap=0.0)
    matching = matching_eval.run(args.seed, args.vacancies, args.candidates)
    sys.stdout.write(report(args.seed, assessment, familiar, matching))


def pct(value: float) -> str:
    return f"{value * 100:.1f} %"


def report(
    seed: int,
    a: assessment_eval.AssessmentReport,
    familiar: assessment_eval.AssessmentReport,
    m: matching_eval.MatchingReport,
) -> str:
    lines = [
        f"# Результаты оценки (seed {seed}, кандидатов {a.candidates}, вакансий {m.vacancies})",
        "",
        "## Тестирование",
        "",
        "| Метрика | Значение | Без штрафа за чужой стек |",
        "|---|---|---|",
        f"| Подтверждённый грейд совпал с настоящим | {pct(a.grade_exact)} | {pct(familiar.grade_exact)} |",
        f"| Ошибка не больше одного грейда | {pct(a.grade_within_one)} | {pct(familiar.grade_within_one)} |",
        f"| Грейд занижен | {pct(a.grade_under)} | {pct(familiar.grade_under)} |",
        f"| Грейд завышен | {pct(a.grade_over)} | {pct(familiar.grade_over)} |",
        f"| Завысил грейд в опросе — не подтверждён | {pct(a.overclaim_caught)} | {pct(familiar.overclaim_caught)} |",
        f"| Повтор: то же решение «сдал / не сдал» | {pct(a.retest_decision)} | {pct(familiar.retest_decision)} |",
        f"| Повтор: корреляция оценок уровня | {a.retest_theta_r:.2f} | {familiar.retest_theta_r:.2f} |",
        f"| Повтор: тот же итоговый грейд | {pct(a.retest_grade)} | {pct(familiar.retest_grade)} |",
        "",
        "Дискриминативность и утечка заданий:",
        "",
        "| Метрика | Значение |",
        "|---|---|",
        f"| Медиана корреляции «задание — остальной тест» | {a.item_r_median:.2f} |",
        f"| Доля шаблонов с корреляцией ≥ 0.2 | {pct(a.item_r_share)} |",
        f"| Различных вариантов шаблона на 200 генераций (медиана) | {a.variants_median} |",
        f"| Одинаковых заданий в двух тестах одной категории | {pct(a.overlap)} |",
        f"| Слабый кандидат сдал Middle честно: банк / единый тест | {pct(a.honest_pass_bank)} / {pct(a.honest_pass_static)} |",
        f"| Он же с ответами {assessment_eval.LEAKED_TESTS} утёкших тестов: банк / единый тест | {pct(a.leak_pass_bank)} / {pct(a.leak_pass_static)} |",
        "",
        "Доля верных ответов в тесте Middle по настоящему грейду: "
        + ", ".join(
            f"{GRADE_TITLES[g]} {pct(a.score_by_grade[g.value])}"
            for g in GRADE_ORDER
            if g.value in a.score_by_grade
        ),
        "",
        "Матрица: настоящий грейд (строки) → подтверждённый тестом (столбцы):",
        "",
        "| | " + " | ".join(GRADE_TITLES[g] for g in GRADE_ORDER) + " | нет |",
        "|---" * (len(GRADE_ORDER) + 2) + "|",
    ]
    for g in GRADE_ORDER:
        row = a.confusion.get(g.value, {})
        cells = [str(row.get(c.value, 0)) for c in GRADE_ORDER] + [str(row.get("none", 0))]
        lines.append(f"| {GRADE_TITLES[g]} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Подбор",
        "",
        f"Релевантных («точно подходит») кандидатов на вакансию в среднем: {m.relevant_per_vacancy:.1f}",
        "",
        "| Выдача | Precision@5 | Precision@10 | nDCG@10 | Переоценённых в топ-10 |",
        "|---|---|---|---|---|",
    ]
    for name, s in m.systems.items():
        lines.append(
            f"| {name} | {pct(s.precision_at_5)} | {pct(s.precision_at_10)} "
            f"| {s.ndcg_at_10:.2f} | {pct(s.overrated_in_top)} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
