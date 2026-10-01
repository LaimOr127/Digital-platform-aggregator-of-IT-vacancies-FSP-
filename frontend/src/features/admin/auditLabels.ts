// Подписи событий журнала аудита. Неизвестный код показывается как есть.
import { labels } from "../../lib/format";

const STATUS_LABELS: Record<string, string> = { ...labels.vacancyStatus, ...labels.companyStatus };
const statusLabel = (status: string) => STATUS_LABELS[status] ?? status;
export const AUDIT_ACTIONS: Record<string, string> = {
  "auth.register": "Регистрация",
  "auth.login": "Вход",
  "auth.mfa_challenge": "Запрошен второй фактор",
  "auth.mfa_setup": "Начато подключение 2FA",
  "auth.mfa_enrolled": "Подключена 2FA",
  "auth.mfa_locked": "Вход заблокирован после неверных кодов",
  "auth.mfa_failed": "Неверный код 2FA",
  "auth.mfa_reset": "Сброс 2FA",
  "auth.refresh_reuse": "Повторное использование refresh-токена",
  "admin.created": "Создан администратор",
  "admin.company_status": "Статус компании",
  "admin.vacancy_block": "Вакансия заблокирована",
  "admin.vacancy_unblock": "Вакансия разблокирована",
  "admin.user_block": "Пользователь заблокирован",
  "admin.user_unblock": "Пользователь разблокирован",
  "offer.sent": "Оффер отправлен",
  "offer.withdrawn": "Оффер отозван",
  "offer.accepted": "Оффер принят",
  "offer.declined": "Оффер отклонён",
  "offer.contacts_revealed": "Раскрыты контакты",
  "fsp.linked": "Привязан профиль ФСП",
  "fsp.unlinked": "Отвязан профиль ФСП",
  "fsp.removed_in_fsp": "Профиль удалён в ФСП",
  "passport.issued": "Выпущен паспорт навыков",
};

/** События, которые сигнализируют о возможной атаке — подсвечиваются в журнале. */
export const ALERT_ACTIONS = new Set(["auth.mfa_failed", "auth.mfa_locked", "auth.refresh_reuse"]);

export const auditLabel = (action: string) => AUDIT_ACTIONS[action] ?? action;

/** Краткое описание meta: причина и смена статуса — остальное не показываем. */
export function auditDetails(meta: Record<string, unknown>): string {
  const parts: string[] = [];
  if (typeof meta.from === "string" && typeof meta.to === "string") {
    parts.push(`${statusLabel(meta.from)} → ${statusLabel(meta.to)}`);
  }
  if (typeof meta.reason === "string" && meta.reason) parts.push(`причина: ${meta.reason}`);
  return parts.join(" · ");
}
