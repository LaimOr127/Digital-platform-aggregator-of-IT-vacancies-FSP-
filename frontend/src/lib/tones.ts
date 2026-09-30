// Цвет бейджа для статусов — в одном месте для всех порталов.
import type { CompanyStatus, VacancyStatus } from "../api/types";
import type { Tone } from "../ui/Badge";

export const vacancyTone: Record<VacancyStatus, Tone> = {
  draft: "neutral",
  active: "accent",
  closed: "info",
  blocked: "danger",
};

export const companyTone: Record<CompanyStatus, Tone> = {
  pending: "warn",
  approved: "accent",
  blocked: "danger",
};
