// Эндпоинты API в одном месте: компоненты не собирают URL сами.
import { api } from "./client";
import type {
  AdminUser,
  AdminVacancy,
  AuditEntry,
  CandidateCard,
  CandidateRegisterIn,
  CatalogCategory,
  CatalogFilters,
  Company,
  CompanyStatus,
  EmployerRegisterIn,
  FspLinkStart,
  FspStatus,
  LoginIn,
  LoginResult,
  Me,
  MfaSetup,
  ModerationAction,
  Offer,
  OfferContacts,
  OfferCreate,
  OfferStatus,
  EmployerOffer,
  Page,
  Passport,
  PassportVerify,
  Profile,
  ProfileUpdate,
  Skill,
  TokenOut,
  UserRole,
  Vacancy,
  VacancyCreate,
  VacancyStatus,
  VacancyUpdate,
} from "./types";

export const authApi = {
  /** администратору вместо токенов приходит шаг 2FA (mfa_required) */
  login: (body: LoginIn) => api<LoginResult>("POST", "/auth/login", { body }),
  /** первый вход: код подключения выдаёт CLI (make create-admin / make reset-admin-2fa) */
  mfaSetup: (mfaToken: string, enrollmentCode: string) =>
    api<MfaSetup>("POST", "/auth/2fa/setup", { body: { mfa_token: mfaToken, enrollment_code: enrollmentCode } }),
  mfaVerify: (mfaToken: string, code: string) =>
    api<TokenOut>("POST", "/auth/2fa/verify", { body: { mfa_token: mfaToken, code } }),
  registerCandidate: (body: CandidateRegisterIn) =>
    api<TokenOut>("POST", "/auth/register/candidate", { body }),
  registerEmployer: (body: EmployerRegisterIn) =>
    api<TokenOut>("POST", "/auth/register/employer", { body }),
  me: () => api<Me>("GET", "/auth/me"),
};

export const publicApi = {
  skills: () => api<Skill[]>("GET", "/public/skills"),
  passport: (id: string) => api<PassportVerify>("GET", `/public/passport/${encodeURIComponent(id)}`),
};

export const fspApi = {
  status: () => api<FspStatus>("GET", "/candidate/fsp"),
  link: (athleteId: string) => api<FspLinkStart>("POST", "/candidate/fsp/link", { body: { athlete_id: athleteId } }),
  confirm: (code: string) => api<FspStatus>("POST", "/candidate/fsp/confirm", { body: { code } }),
  sync: () => api<FspStatus>("POST", "/candidate/fsp/sync"),
  unlink: () => api<void>("DELETE", "/candidate/fsp"),
};

export const passportApi = {
  active: () => api<Passport | null>("GET", "/candidate/passport"),
  issue: (showName: boolean) => api<Passport>("POST", "/candidate/passport", { body: { show_name: showName } }),
  revoke: () => api<void>("DELETE", "/candidate/passport"),
};

export const candidateApi = {
  profile: () => api<Profile>("GET", "/candidate/profile"),
  updateProfile: (body: ProfileUpdate) => api<Profile>("PATCH", "/candidate/profile", { body }),
};

const vacancyUrl = (id: string, action = "") => `/employer/vacancies/${encodeURIComponent(id)}${action}`;

export const employerApi = {
  company: () => api<Company>("GET", "/employer/company"),
  vacancies: (status: VacancyStatus | undefined, cursor: string | undefined) =>
    api<Page<Vacancy>>("GET", "/employer/vacancies", { query: { status, cursor, limit: 20 } }),
  createVacancy: (body: VacancyCreate) => api<Vacancy>("POST", "/employer/vacancies", { body }),
  updateVacancy: (id: string, body: VacancyUpdate) => api<Vacancy>("PATCH", vacancyUrl(id), { body }),
  publishVacancy: (id: string) => api<Vacancy>("POST", vacancyUrl(id, "/publish")),
  closeVacancy: (id: string) => api<Vacancy>("POST", vacancyUrl(id, "/close")),
  deleteVacancy: (id: string) => api<void>("DELETE", vacancyUrl(id)),
};

export const catalogApi = {
  categories: () => api<CatalogCategory[]>("GET", "/employer/catalog/categories"),
  candidates: (filters: CatalogFilters, cursor: string | undefined) =>
    api<Page<CandidateCard>>("GET", "/employer/catalog/candidates", { query: { ...filters, cursor, limit: 20 } }),
};

const offerUrl = (id: string, action = "") => `/employer/offers/${encodeURIComponent(id)}${action}`;

export const employerOffersApi = {
  /** idempotencyKey: повтор запроса (двойной клик, сбой сети) не создаёт второй оффер */
  send: (body: OfferCreate, idempotencyKey: string) =>
    api<EmployerOffer>("POST", "/employer/offers", { body, headers: { "Idempotency-Key": idempotencyKey } }),
  list: (status: OfferStatus | undefined, cursor: string | undefined) =>
    api<Page<EmployerOffer>>("GET", "/employer/offers", { query: { status, cursor, limit: 20 } }),
  withdraw: (id: string) => api<EmployerOffer>("POST", offerUrl(id, "/withdraw")),
  contacts: (id: string) => api<OfferContacts>("GET", offerUrl(id, "/contacts")),
};

const inboxUrl = (id: string, action: string) => `/candidate/offers/${encodeURIComponent(id)}${action}`;

export const candidateOffersApi = {
  list: (status: OfferStatus | undefined, cursor: string | undefined) =>
    api<Page<Offer>>("GET", "/candidate/offers", { query: { status, cursor, limit: 20 } }),
  accept: (id: string) => api<Offer>("POST", inboxUrl(id, "/accept")),
  decline: (id: string, reason: string) => api<Offer>("POST", inboxUrl(id, "/decline"), { body: { reason } }),
};

export const adminApi = {
  companies: (status: CompanyStatus | undefined, cursor: string | undefined) =>
    api<Page<Company>>("GET", "/admin/companies", { query: { status, cursor, limit: 20 } }),
  setCompanyStatus: (id: string, status: CompanyStatus, reason: string) =>
    api<Company>("POST", `/admin/companies/${encodeURIComponent(id)}/status`, { body: { status, reason } }),
  vacancies: (status: VacancyStatus | undefined, cursor: string | undefined) =>
    api<Page<AdminVacancy>>("GET", "/admin/vacancies", { query: { status, cursor, limit: 20 } }),
  moderateVacancy: (id: string, action: ModerationAction, reason: string) =>
    api<AdminVacancy>("POST", `/admin/vacancies/${encodeURIComponent(id)}/moderation`, { body: { action, reason } }),
  users: (filters: { role?: UserRole; q?: string }, cursor: string | undefined) =>
    api<Page<AdminUser>>("GET", "/admin/users", { query: { ...filters, cursor, limit: 20 } }),
  moderateUser: (id: string, action: ModerationAction, reason: string) =>
    api<AdminUser>("POST", `/admin/users/${encodeURIComponent(id)}/moderation`, { body: { action, reason } }),
  audit: (action: string | undefined, cursor: string | undefined) =>
    api<Page<AuditEntry>>("GET", "/admin/audit", { query: { action, cursor, limit: 50 } }),
};
