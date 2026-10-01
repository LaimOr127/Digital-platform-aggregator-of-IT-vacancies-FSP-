// Эндпоинты API в одном месте: компоненты не собирают URL сами.
import { api } from "./client";
import type {
  AiProvider,
  AiProviderInput,
  AiProviderUpdate,
  AiTest,
  EmployerInterview,
  Interview,
  InterviewInvite,
  InterviewResult,
  InterviewStatus,
  ImportCapabilities,
  ProfileDraft,
  Accepted,
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
  /** регистрация не входит в аккаунт: сначала подтверждение почты по ссылке из письма */
  registerCandidate: (body: CandidateRegisterIn) => api<Accepted>("POST", "/auth/register/candidate", { body }),
  registerEmployer: (body: EmployerRegisterIn) => api<Accepted>("POST", "/auth/register/employer", { body }),
  verifyEmail: (token: string) => api<void>("POST", "/auth/verify-email", { body: { token } }),
  resendVerification: (email: string) => api<Accepted>("POST", "/auth/verify-email/resend", { body: { email } }),
  forgotPassword: (email: string) => api<Accepted>("POST", "/auth/password/forgot", { body: { email } }),
  resetPassword: (token: string, password: string) =>
    api<void>("POST", "/auth/password/reset", { body: { token, password } }),
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

export const importApi = {
  capabilities: () => api<ImportCapabilities>("GET", "/candidate/import/capabilities"),
  fromFsp: () => api<ProfileDraft>("GET", "/candidate/import/fsp"),
  /** use_ai — согласие кандидата на разбор ИИ-сервисом (текст без контактов) */
  fromResume: (file: File, useAi: boolean) => {
    const form = new FormData();
    form.append("file", file);
    form.append("use_ai", String(useAi));
    return api<ProfileDraft>("POST", "/candidate/import/resume", { body: form });
  },
};


const interviewUrl = (base: string, id: string, action: string) => `${base}/${encodeURIComponent(id)}${action}`;

export const interviewsApi = {
  invite: (body: InterviewInvite) => api<EmployerInterview>("POST", "/employer/interviews", { body }),
  list: (status: InterviewStatus | undefined, cursor: string | undefined) =>
    api<Page<EmployerInterview>>("GET", "/employer/interviews", { query: { status, cursor, limit: 20 } }),
  cancel: (id: string, reason: string) =>
    api<EmployerInterview>("POST", interviewUrl("/employer/interviews", id, "/cancel"), { body: { reason } }),
  complete: (id: string, result: InterviewResult, feedback: string) =>
    api<EmployerInterview>("POST", interviewUrl("/employer/interviews", id, "/complete"), { body: { result, feedback } }),
};

export const myInterviewsApi = {
  list: (status: InterviewStatus | undefined, cursor: string | undefined) =>
    api<Page<Interview>>("GET", "/candidate/interviews", { query: { status, cursor, limit: 20 } }),
  accept: (id: string, slot: string) =>
    api<Interview>("POST", interviewUrl("/candidate/interviews", id, "/accept"), { body: { slot } }),
  decline: (id: string, reason: string) =>
    api<Interview>("POST", interviewUrl("/candidate/interviews", id, "/decline"), { body: { reason } }),
};

const aiUrl = (id: string, action = "") => `/admin/ai-providers/${encodeURIComponent(id)}${action}`;

export const aiAdminApi = {
  list: () => api<AiProvider[]>("GET", "/admin/ai-providers"),
  create: (body: AiProviderInput) => api<AiProvider>("POST", "/admin/ai-providers", { body }),
  update: (id: string, body: AiProviderUpdate) => api<AiProvider>("PATCH", aiUrl(id), { body }),
  remove: (id: string) => api<void>("DELETE", aiUrl(id)),
  activate: (id: string) => api<AiProvider[]>("POST", aiUrl(id, "/activate")),
  deactivate: () => api<AiProvider[]>("POST", "/admin/ai-providers/deactivate"),
  test: (id: string) => api<AiTest>("POST", aiUrl(id, "/test")),
};
