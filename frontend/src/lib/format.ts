// Подписи перечислений и форматирование значений для интерфейса.
import type {
  CompanyStatus,
  Grade,
  InterviewFormat,
  InterviewResult,
  InterviewStatus,
  OfferStatus,
  SearchStatus,
  Specialization,
  UserRole,
  VacancyStatus,
  VerificationTier,
  WorkFormat,
} from "../api/types";

const money = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
const date = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short", year: "numeric" });
const dateTime = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});
const DAY_MS = 86_400_000;

export function formatSalaryRange(min?: number | null, max?: number | null): string {
  if (min && max) return `${money.format(min)} – ${money.format(max)} ₽`;
  if (min) return `от ${money.format(min)} ₽`;
  if (max) return `до ${money.format(max)} ₽`;
  return "Не указана";
}

export function formatDate(iso: string): string {
  return date.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return dateTime.format(new Date(iso));
}

export function daysLeft(iso: string | null | undefined, now: Date = new Date()): number | null {
  if (!iso) return null;
  return Math.max(0, Math.ceil((new Date(iso).getTime() - now.getTime()) / DAY_MS));
}

export const labels = {
  specialization: {
    backend: "Бэкенд-разработка",
    frontend: "Фронтенд-разработка",
    mobile: "Мобильная разработка",
    data: "Данные и машинное обучение",
    devops: "DevOps и инфраструктура",
    qa: "Тестирование",
    security: "Информационная безопасность",
  } satisfies Record<Specialization, string>,
  grade: {
    intern: "Стажёр",
    junior: "Junior",
    middle: "Middle",
    senior: "Senior",
    lead: "Lead",
  } satisfies Record<Grade, string>,
  workFormat: {
    office: "Офис",
    hybrid: "Гибрид",
    remote: "Удалённо",
  } satisfies Record<WorkFormat, string>,
  vacancyStatus: {
    draft: "Черновик",
    active: "Опубликована",
    closed: "Закрыта",
    blocked: "Заблокирована",
  } satisfies Record<VacancyStatus, string>,
  companyStatus: {
    pending: "На модерации",
    approved: "Одобрена",
    blocked: "Заблокирована",
  } satisfies Record<CompanyStatus, string>,
  offerStatus: {
    sent: "Ждёт ответа",
    accepted: "Принят",
    declined: "Отклонён",
    withdrawn: "Отозван",
    expired: "Истёк",
  } satisfies Record<OfferStatus, string>,
  searchStatus: {
    active: "Активно ищу работу",
    open: "Рассматриваю предложения",
    closed: "Не ищу работу",
  } satisfies Record<SearchStatus, string>,
  interviewStatus: {
    invited: "Ждёт выбора времени",
    scheduled: "Назначено",
    declined: "Кандидат отказался",
    cancelled: "Отменено",
    completed: "Состоялось",
    expired: "Истекло",
  } satisfies Record<InterviewStatus, string>,
  interviewResult: {
    passed: "Успешно",
    failed: "Не подошёл",
  } satisfies Record<InterviewResult, string>,
  interviewFormat: {
    online: "Онлайн",
    office: "В офисе",
  } satisfies Record<InterviewFormat, string>,
  role: {
    candidate: "Кандидат",
    employer: "Работодатель",
    admin: "Администратор",
  } satisfies Record<UserRole, string>,
  tier: {
    self_declared: "Заявлено кандидатом",
    resume_parsed: "Подтверждено резюме",
    verified_fsp: "Подтверждено ФСП",
  } satisfies Record<VerificationTier, string>,
};

export const tierLabels: Record<string, string> = {
  elite: "Высший уровень",
  advanced: "Продвинутый уровень",
  base: "Базовый уровень",
};

export const levelLabels: Record<string, string> = {
  regional: "Региональный",
  national: "Всероссийский",
  international: "Международный",
};

/** Итог участия: место, финал или участие. */
export function outcomeLabel(place: number | null | undefined, stage: string): string {
  if (place) return `${place} место`;
  return stage === "final" ? "Финалист" : "Участник";
}

export function options<K extends string>(map: Record<K, string>): { value: K; label: string }[] {
  return (Object.keys(map) as K[]).map((value) => ({ value, label: map[value] }));
}
