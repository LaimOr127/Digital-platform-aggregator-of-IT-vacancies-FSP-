// Шкала зарплатных графиков: «круглые» границы и деления, позиция значения в процентах.
import type { SalaryBand } from "../../api/types";

export type Domain = { min: number; max: number; step: number };

const MULTIPLIERS = [1, 2.5, 5, 10];
const TARGET_TICKS = 4;

/** Шаг делений: «круглый» (1, 2,5 или 5 × 10ⁿ), чтобы на оси было не больше TARGET_TICKS
 * промежутков при любом размахе — число делений не растёт с величиной значений. */
export function niceStep(span: number): number {
  const base = 10 ** Math.floor(Math.log10(Math.max(span, 1) / TARGET_TICKS));
  const multiplier = MULTIPLIERS.find((m) => span / (base * m) <= TARGET_TICKS) ?? 10;
  return base * multiplier;
}

/** Общая шкала для всех строк графика: от минимума до максимума с запасом в полшага. */
export function domainOf(values: number[]): Domain | null {
  const finite = values.filter((v) => Number.isFinite(v) && v > 0);
  if (finite.length === 0) return null;
  const low = Math.min(...finite);
  const high = Math.max(...finite);
  const step = niceStep(Math.max(high - low, 1));
  const min = Math.max(0, Math.floor((low - step / 2) / step) * step);
  const max = Math.ceil((high + step / 2) / step) * step;
  return { min, max, step };
}

/** Подписи оси: при частых делениях — через одно, чтобы не слипались; оба края подписаны всегда. */
export function labeledTicks(values: number[]): number[] {
  if (values.length <= 5) return values;
  const everyOther = values.filter((_, index) => index % 2 === 0);
  const last = values[values.length - 1];
  return everyOther[everyOther.length - 1] === last ? everyOther : [...everyOther.slice(0, -1), last];
}

export function ticks(domain: Domain): number[] {
  const result: number[] = [];
  for (let value = domain.min; value <= domain.max; value += domain.step) result.push(value);
  return result;
}

/** Позиция значения на шкале, 0–100 (за пределами шкалы — прижато к краю). */
export function percentOf(value: number, domain: Domain): number {
  const ratio = (value - domain.min) / (domain.max - domain.min);
  return Math.min(100, Math.max(0, ratio * 100));
}

/** Все значения, которые должны поместиться на шкале. */
export function bandValues(bands: (SalaryBand | null | undefined)[]): number[] {
  return bands.flatMap((band) => (band ? [band.p25, band.median, band.p75] : []));
}

const thousands = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
const millions = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 });

/** Короткая сумма для осей и подписей: «250 тыс», «1,2 млн». */
export function compactMoney(value: number): string {
  const inThousands = Math.round(value / 1000);
  if (inThousands === 0) return "0";
  // порог — после округления: 999 600 — это «1 млн», а не «1 000 тыс»
  if (inThousands >= 1000) return `${millions.format(value / 1_000_000)} млн`;
  return `${thousands.format(inThousands)} тыс`;
}
