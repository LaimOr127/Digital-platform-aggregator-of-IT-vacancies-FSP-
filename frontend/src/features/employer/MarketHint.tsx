// Подсказка в форме вакансии: сколько платят на рынке за этот грейд и стек и где ваша вилка.
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useWatch, type Control } from "react-hook-form";
import { insightsApi } from "../../api/endpoints";
import type { Grade } from "../../api/types";
import { formatSalaryRange, labels } from "../../lib/format";
import { useDebounced } from "../../lib/useDebounced";
import { Badge } from "../../ui/Badge";
import { positionLabel, positionOf, positionTone, type Position } from "../insights/position";
import { marketRows } from "../insights/marketRows";
import { RangeChart } from "../insights/RangeChart";
import { compactMoney } from "../insights/scale";
import type { VacancyFormInput } from "./schemas";

const ADVICE: Record<Position, string> = {
  below: "Вилка ниже рынка — откликов и согласий на оффер может быть меньше.",
  within: "Вилка в рынке для этого уровня и стека.",
  above: "Вилка выше рынка — вакансия заметнее для сильных кандидатов.",
};

function useMarket(grade: Grade | undefined, skills: string[]) {
  // строка, а не объект: у объекта новая ссылка на каждый рендер — debounce не успокоится
  const key = useDebounced([grade ?? "", ...[...skills].sort()].join(","), 400);
  const [debouncedGrade, ...rest] = key.split(",");
  const debouncedSkills = rest.filter(Boolean);
  return useQuery({
    queryKey: ["market", key],
    queryFn: () => insightsApi.market(debouncedGrade as Grade, debouncedSkills),
    enabled: Boolean(grade && debouncedGrade),
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
}

/** Потолок зарплаты, как у бэкенда: всё больше — опечатка, сравнивать не с чем. */
const MAX_SALARY = 10_000_000;

/** Середина вилки из полей формы (пока поле пустое или не число — сравнивать не с чем). */
export function midpoint(min: unknown, max: unknown): number | null {
  const low = Number(min);
  const high = Number(max);
  if (!low || !high || high < low || high > MAX_SALARY) return null;
  return Math.round((low + high) / 2);
}

export function MarketHint({ control }: { control: Control<VacancyFormInput> }) {
  const [grade, skills, salaryMin, salaryMax] = useWatch({
    control,
    name: ["grade", "skills", "salary_min", "salary_max"],
  });
  const market = useMarket(grade as Grade | undefined, skills ?? []);
  const radar = market.data;
  // без грейда запрос выключен, а прежний ответ — про другой грейд
  if (!radar || !grade) return null;

  const reference = radar.vacancies ?? radar.offers;
  const scope = `${labels.grade[radar.grade as Grade]}${radar.skills.length ? " с этим стеком" : ""}`;
  if (!reference) {
    return (
      <p className="rounded-xl border border-dashed border-line p-4 text-sm text-muted sm:col-span-2">
        По рынку для {scope} пока мало данных — подсказка появится, когда наберётся {radar.min_group} вакансий от
        трёх компаний.
      </p>
    );
  }

  const middle = midpoint(salaryMin, salaryMax);
  const position = middle ? positionOf(middle, reference) : null;
  return (
    <section aria-label="Рынок зарплат" className="rounded-xl border border-line bg-surface-2/40 p-4 sm:col-span-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm">
          Рынок для {scope}: обычно {formatSalaryRange(reference.p25, reference.p75)}, медиана{" "}
          {compactMoney(reference.median)} ₽
        </p>
        {position && <Badge tone={positionTone[position]}>{positionLabel[position]}</Badge>}
      </div>
      {position && <p className="mt-1 text-sm text-muted">{ADVICE[position]}</p>}
      <div className="mt-4">
        <RangeChart
          rows={marketRows(radar, false)}
          marker={middle ? { value: middle, label: `середина вашей вилки: ${compactMoney(middle)} ₽` } : null}
          caption="Рынок зарплат для вакансии"
          minGroup={radar.min_group}
        />
      </div>
    </section>
  );
}
