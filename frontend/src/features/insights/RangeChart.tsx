// Диапазоны зарплат на общей шкале: полоса — середина распределения (25–75%), риска — медиана,
// пунктир — сравниваемое значение (ожидания кандидата, вилка вакансии). Один цвет, подписи —
// цветом текста; подсказка по наведению и фокусу, таблица — для чтения без графика.
import { useState } from "react";
import type { SalaryBand } from "../../api/types";
import { cn } from "../../lib/cn";
import { formatSalaryRange } from "../../lib/format";
import { bandValues, compactMoney, domainOf, labeledTicks, percentOf, ticks, type Domain } from "./scale";

export type RangeRow = {
  key: string;
  label: string;
  band: SalaryBand | null;
  /** что считали: «вакансий», «офферов», «кандидатов» */
  unit: string;
  /** выделенная строка (текущий грейд); остальные приглушены */
  emphasis?: boolean;
};

export type Marker = { value: number; label: string };

type Props = { rows: RangeRow[]; marker?: Marker | null; caption: string; minGroup: number };

const LABEL_COLUMN = "grid-cols-[7.5rem_minmax(0,1fr)] sm:grid-cols-[10rem_minmax(0,1fr)]";

export function RangeChart({ rows, marker, caption, minGroup }: Props) {
  const domain = domainOf([...bandValues(rows.map((r) => r.band)), ...(marker ? [marker.value] : [])]);
  if (!domain) return <p className="text-sm text-muted">{emptyText(minGroup)}</p>;
  return (
    <figure className="flex flex-col gap-3">
      <div className="relative">
        <Overlay domain={domain} marker={marker} />
        <ul className="relative flex flex-col">
          {rows.map((row) => (
            <Row key={row.key} row={row} domain={domain} minGroup={minGroup} />
          ))}
        </ul>
        <Axis domain={domain} />
      </div>
      <figcaption className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span aria-hidden className="h-1.5 w-5 rounded-full bg-accent" />
          половина значений (25–75%)
        </span>
        <span className="flex items-center gap-1.5">
          <span aria-hidden className="h-3 w-0.5 rounded-full bg-fg" />
          медиана
        </span>
        {marker && (
          <span className="flex items-center gap-1.5">
            <span aria-hidden className="h-3 border-l-2 border-dashed border-info" />
            {marker.label}
          </span>
        )}
      </figcaption>
      <DataTable rows={rows} caption={caption} marker={marker} />
    </figure>
  );
}

function emptyText(minGroup: number): string {
  return `Пока мало данных: показываем распределение, когда наберётся не меньше ${minGroup} значений от разных компаний.`;
}

function Row({ row, domain, minGroup }: { row: RangeRow; domain: Domain; minGroup: number }) {
  const [active, setActive] = useState(false);
  const { band } = row;
  const summary = band
    ? `${row.label}: медиана ${compactMoney(band.median)} ₽, обычно ${formatSalaryRange(band.p25, band.p75)}, ${band.count} ${row.unit}`
    : `${row.label}: мало данных (меньше ${minGroup})`;
  return (
    <li className={cn("grid items-center gap-3", LABEL_COLUMN)}>
      <div className="min-w-0 py-1.5">
        <p className={cn("truncate text-sm", row.emphasis ? "font-semibold" : "text-muted")}>{row.label}</p>
        <p className="text-xs tabular text-muted">{band ? `медиана ${compactMoney(band.median)}` : "мало данных"}</p>
      </div>
      {/* role="img": у обычного div нет роли, и скринридер не озвучил бы подпись */}
      <div
        role="img"
        tabIndex={band ? 0 : undefined}
        aria-label={summary}
        onMouseEnter={() => setActive(true)}
        onMouseLeave={() => setActive(false)}
        onFocus={() => setActive(true)}
        onBlur={() => setActive(false)}
        className="relative h-10 rounded-md outline-offset-2"
      >
        {band && <Band band={band} domain={domain} muted={row.emphasis === false} />}
        {band && active && <Tooltip band={band} unit={row.unit} domain={domain} />}
      </div>
    </li>
  );
}

function Band({ band, domain, muted }: { band: SalaryBand; domain: Domain; muted: boolean }) {
  const left = percentOf(band.p25, domain);
  const width = Math.max(percentOf(band.p75, domain) - left, 0);
  return (
    <>
      <span
        aria-hidden
        className={cn("absolute top-1/2 h-2 min-w-2 -translate-y-1/2 rounded-full bg-accent", muted && "opacity-45")}
        style={{ left: `${left}%`, width: `${width}%` }}
      />
      <span
        aria-hidden
        className="absolute top-1/2 h-4 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-fg ring-2 ring-surface"
        style={{ left: `${percentOf(band.median, domain)}%` }}
      />
    </>
  );
}

function Tooltip({ band, unit, domain }: { band: SalaryBand; unit: string; domain: Domain }) {
  const center = percentOf(band.median, domain);
  // у краёв подсказка прижимается к краю графика, а не выходит за него
  const anchor = center < 25 ? "left-0" : center > 75 ? "right-0" : "-translate-x-1/2";
  return (
    <div
      aria-hidden
      data-testid="range-tooltip"
      className={cn(
        "pointer-events-none absolute bottom-full z-10 mb-1 w-max max-w-64 rounded-lg border border-line bg-surface-2 px-3 py-2 text-xs shadow-lg",
        anchor,
      )}
      style={anchor === "-translate-x-1/2" ? { left: `${center}%` } : undefined}
    >
      <p className="text-sm font-semibold tabular">{compactMoney(band.median)} ₽</p>
      <p className="tabular text-muted">обычно {formatSalaryRange(band.p25, band.p75)}</p>
      <p className="text-muted">
        {band.count} {unit}
      </p>
    </div>
  );
}

function Overlay({ domain, marker }: { domain: Domain; marker?: Marker | null }) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-x-0 top-0 bottom-5 grid gap-3", LABEL_COLUMN)}>
      <span />
      <div className="relative">
        {ticks(domain).map((value) => (
          <span key={value} className="absolute inset-y-0 border-l border-line/60" style={{ left: `${percentOf(value, domain)}%` }} />
        ))}
        {marker && (
          <span
            className="absolute inset-y-0 border-l-2 border-dashed border-info"
            style={{ left: `${percentOf(marker.value, domain)}%` }}
          />
        )}
      </div>
    </div>
  );
}

function Axis({ domain }: { domain: Domain }) {
  const values = labeledTicks(ticks(domain));
  return (
    <div aria-hidden className={cn("grid gap-3 pt-1", LABEL_COLUMN)}>
      <span />
      <div className="relative h-4 text-[11px] tabular text-muted">
        {values.map((value) => (
          <span
            key={value}
            className={cn(
              "absolute top-0 whitespace-nowrap",
              // на телефоне шкала узкая: подписаны только края
              value === domain.min ? "" : value === domain.max ? "-translate-x-full" : "hidden -translate-x-1/2 sm:block",
            )}
            style={{ left: `${percentOf(value, domain)}%` }}
          >
            {compactMoney(value)}
          </span>
        ))}
      </div>
    </div>
  );
}

function DataTable({ rows, caption, marker }: { rows: RangeRow[]; caption: string; marker?: Marker | null }) {
  return (
    <details className="text-sm">
      <summary className="w-fit cursor-pointer text-xs text-muted hover:text-fg">Показать таблицей</summary>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-left text-xs tabular">
          <caption className="sr-only">{caption}</caption>
          <thead className="text-muted">
            <tr>
              <th className="py-1 pr-3 font-medium">Источник</th>
              <th className="py-1 pr-3 font-medium">25%</th>
              <th className="py-1 pr-3 font-medium">Медиана</th>
              <th className="py-1 pr-3 font-medium">75%</th>
              <th className="py-1 font-medium">Значений</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ key, label, band }) => (
              <tr key={key} className="border-t border-line">
                <td className="py-1 pr-3">{label}</td>
                <td className="py-1 pr-3">{band ? compactMoney(band.p25) : "—"}</td>
                <td className="py-1 pr-3">{band ? compactMoney(band.median) : "—"}</td>
                <td className="py-1 pr-3">{band ? compactMoney(band.p75) : "—"}</td>
                <td className="py-1">{band?.count ?? "мало"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {marker && <p className="mt-2 text-xs text-muted">Сравнение: {marker.label}</p>}
      </div>
    </details>
  );
}
