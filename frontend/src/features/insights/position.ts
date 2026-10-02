// Где значение относительно типичной вилки рынка (середина распределения, 25–75%).
// Те же границы, что у бэкенда (InsightsService.candidate_radar): квартили входят в «рынок».
import type { SalaryBand, SalaryRadar } from "../../api/types";
import type { Tone } from "../../ui/Badge";

export type Position = NonNullable<SalaryRadar["position"]>;

export function positionOf(value: number, band: SalaryBand): Position {
  if (value < band.p25) return "below";
  if (value > band.p75) return "above";
  return "within";
}

export const positionLabel: Record<Position, string> = {
  below: "Ниже рынка",
  within: "В рынке",
  above: "Выше рынка",
};

export const positionTone: Record<Position, Tone> = {
  below: "info",
  within: "accent",
  above: "warn",
};
