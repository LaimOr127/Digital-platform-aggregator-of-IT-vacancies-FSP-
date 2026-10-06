// Цвет бейджа для статусов — в одном месте для всех порталов.
import type { ApplicationStatus, CompanyStatus, InterviewStatus, OfferStatus, SearchStatus, VacancyStatus } from "../api/types";
import type { Tone } from "../ui/Badge";

export const vacancyTone: Record<VacancyStatus, Tone> = {
  draft: "neutral",
  active: "success",
  closed: "info",
  blocked: "danger",
};

export const offerTone: Record<OfferStatus, Tone> = {
  sent: "warn",
  accepted: "success",
  declined: "neutral",
  withdrawn: "neutral",
  expired: "neutral",
};

export const applicationTone: Record<ApplicationStatus, Tone> = {
  sent: "warn",
  viewed: "info",
  accepted: "success",
  declined: "neutral",
  withdrawn: "neutral",
  expired: "neutral",
};

export const tierTone: Record<string, Tone> = {
  elite: "accent",
  advanced: "info",
  base: "neutral",
};

export const companyTone: Record<CompanyStatus, Tone> = {
  pending: "warn",
  approved: "success",
  blocked: "danger",
};

export const searchTone: Record<SearchStatus, Tone> = {
  active: "success",
  open: "info",
  closed: "neutral",
};

export const interviewTone: Record<InterviewStatus, Tone> = {
  invited: "warn",
  scheduled: "info",
  completed: "success",
  declined: "neutral",
  cancelled: "neutral",
  expired: "neutral",
};

/** Цвет процента соответствия: высокий — акцент, средний — инфо, низкий — нейтральный. */
export function matchTone(score: number): Tone {
  if (score >= 70) return "accent";
  if (score >= 45) return "info";
  return "neutral";
}
