// Радар зарплат кандидата: рынок для его грейда и стека и лестница зарплат по грейдам.
import type { Grade, SalaryRadar } from "../../../api/types";
import { formatSalaryRange, labels } from "../../../lib/format";
import { Badge } from "../../../ui/Badge";
import { Card, CardTitle } from "../../../ui/Card";
import { positionLabel, positionTone, type Position } from "../../insights/position";
import { marketRows } from "../../insights/marketRows";
import { RangeChart, type Marker, type RangeRow } from "../../insights/RangeChart";
import { compactMoney } from "../../insights/scale";

const ADVICE: Record<Position, string> = {
  below: "Ваши ожидания ниже типичной вилки — можно смело просить больше.",
  within: "Ожидания в пределах типичной вилки для вашего уровня и стека.",
  above: "Ожидания выше типичной вилки: подкрепите их результатами ФСП или будьте готовы к торгу.",
};

export function SalaryCard({ radar }: { radar: SalaryRadar }) {
  const verdict = verdictText(radar);
  const marker: Marker | null = radar.expectation
    ? { value: radar.expectation, label: `ваши ожидания: от ${compactMoney(radar.expectation)} ₽` }
    : null;
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>Радар зарплат</CardTitle>
          <p className="mt-1 text-sm text-muted">{scopeText(radar)}</p>
        </div>
        {radar.position && <Badge tone={positionTone[radar.position]}>{positionLabel[radar.position]}</Badge>}
      </div>
      {verdict && <p className="mt-4 text-sm">{verdict}</p>}
      <div className="mt-6">
        <RangeChart rows={marketRows(radar, true)} marker={marker} caption="Зарплаты для вашего грейда и стека" minGroup={radar.min_group} />
      </div>
    </Card>
  );
}

export function LadderCard({ radar }: { radar: SalaryRadar }) {
  const rows: RangeRow[] = radar.ladder.map(({ grade, band }) => ({
    key: grade,
    label: labels.grade[grade],
    band,
    unit: "вакансий",
    emphasis: grade === radar.grade,
  }));
  return (
    <Card>
      <CardTitle>Зарплаты по грейдам</CardTitle>
      <p className="mt-1 text-sm text-muted">Вилки вакансий с вашим стеком — сколько платят на каждом уровне.</p>
      <div className="mt-6">
        <RangeChart rows={rows} caption="Вилки вакансий по грейдам" minGroup={radar.min_group} />
      </div>
    </Card>
  );
}

function scopeText(radar: SalaryRadar): string {
  const grade = labels.grade[radar.grade as Grade];
  if (radar.skills.length === 0) return `${grade}, все навыки`;
  const shown = radar.skills.slice(0, 4).join(", ");
  const more = radar.skills.length > 4 ? ` и ещё ${radar.skills.length - 4}` : "";
  return `${grade} · ${shown}${more}`;
}

function verdictText(radar: SalaryRadar): string {
  if (radar.position) return ADVICE[radar.position];
  const reference = radar.vacancies ?? radar.offers;
  if (!radar.expectation && reference) {
    return `Обычно платят ${formatSalaryRange(reference.p25, reference.p75)}. Укажите ожидания в профиле — покажем, где вы относительно рынка.`;
  }
  if (!reference) return "Вакансий с вашим стеком пока мало для сравнения — ориентируйтесь на ожидания коллег.";
  return "";
}
