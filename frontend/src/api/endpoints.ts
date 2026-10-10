// Эндпоинты API в одном месте: компоненты не собирают URL сами.
import { api } from "./client";
import type {
  Accepted,
  AdminUser,
  AdminVacancy,
  AiProvider,
  AiProviderInput,
  AiProviderUpdate,
  AiReview,
  AiStatus,
  AiTest,
  Application,
  ApplicationDirection,
  ApplicationStatus,
  AssessmentState,
  Attempt,
  AttemptResult,
  AuditEntry,
  BoardFilters,
  BoardVacancy,
  CandidateCard,
  CandidateRegisterIn,
  CandidateSection,
  CandidateUpdates,
  CatalogCategory,
  CatalogFilters,
  Company,
  CompanyStatus,
  CompanyUpdate,
  ComplaintInput,
  CurrentTask,
  Dictionaries,
  EmployerApplication,
  EmployerInterview,
  EmployerOffer,
  EmployerRegisterIn,
  EmployerSection,
  EmployerTask,
  EmployerUpdates,
  FspCategory,
  FspLinkStart,
  FspStatus,
  Grade,
  Growth,
  ImportCapabilities,
  Interview,
  InterviewInvite,
  InterviewResult,
  InterviewStatus,
  InvitationInput,
  LoginIn,
  LoginResult,
  Me,
  MfaSetup,
  ModerationAction,
  MyTaskAnswer,
  Offer,
  OfferContacts,
  OfferCreate,
  OfferStatus,
  Page,
  Passport,
  PassportVerify,
  PreviewQuestion,
  Profile,
  ProfileDraft,
  ProfileUpdate,
  SalaryRadar,
  Skill,
  Suggestion,
  SurveyInput,
  TaskAnswer,
  TaskInput,
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
  dictionaries: () => api<Dictionaries>("GET", "/public/dictionaries"),
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
  /** удаление аккаунта и всех данных (152-ФЗ); сервер завершает сессию */
  deleteAccount: (password: string) => api<void>("POST", "/candidate/account/delete", { body: { password } }),
  /** время последнего события по разделам — для индикаторов нового */
  updates: () => api<CandidateUpdates>("GET", "/candidate/updates"),
  /** раздел открыт — отметка общая для всех устройств аккаунта */
  markSeen: (section: CandidateSection) => api<void>("POST", "/candidate/updates/seen", { body: { section } }),
};

export const insightsApi = {
  salary: () => api<SalaryRadar>("GET", "/candidate/insights/salary"),
  growth: () => api<Growth>("GET", "/candidate/insights/growth"),
  /** рынок для вакансии: та же аналитика по грейду и навыкам из формы */
  market: (grade: Grade, skills: readonly string[]) =>
    api<SalaryRadar>("GET", "/employer/insights/salary", { query: { grade, skills } }),
};

const vacancyUrl = (id: string, action = "") => `/employer/vacancies/${encodeURIComponent(id)}${action}`;

export const employerApi = {
  company: () => api<Company>("GET", "/employer/company"),
  updates: () => api<EmployerUpdates>("GET", "/employer/updates"),
  markSeen: (section: EmployerSection) => api<void>("POST", "/employer/updates/seen", { body: { section } }),
  updateCompany: (body: CompanyUpdate) => api<Company>("PATCH", "/employer/company", { body }),
  vacancies: (status: VacancyStatus | undefined, cursor: string | undefined) =>
    api<Page<Vacancy>>("GET", "/employer/vacancies", { query: { status, cursor, limit: 20 } }),
  createVacancy: (body: VacancyCreate) => api<Vacancy>("POST", "/employer/vacancies", { body }),
  updateVacancy: (id: string, body: VacancyUpdate) => api<Vacancy>("PATCH", vacancyUrl(id), { body }),
  publishVacancy: (id: string) => api<Vacancy>("POST", vacancyUrl(id, "/publish")),
  closeVacancy: (id: string) => api<Vacancy>("POST", vacancyUrl(id, "/close")),
  deleteVacancy: (id: string) => api<void>("DELETE", vacancyUrl(id)),
  /** пример теста, который система соберёт под вакансию (с ответами) */
  assessmentPreview: (id: string) => api<PreviewQuestion[]>("GET", vacancyUrl(id, "/assessment-preview")),
};

export const assessmentApi = {
  state: () => api<AssessmentState>("GET", "/candidate/assessment"),
  saveSurvey: (body: SurveyInput) => api<AssessmentState>("PUT", "/candidate/assessment/survey", { body }),
  /** подсказка специализации и грейда: языковая модель или правила по стеку и стажу */
  suggest: () => api<Suggestion>("POST", "/candidate/assessment/suggestion"),
  start: (grade: Grade) => api<Attempt>("POST", "/candidate/assessment/attempts", { body: { grade } }),
  /** ответы по порядку: номер варианта или число; null — без ответа */
  /** focusLosses — уходы со вкладки: сигнал в результате, на оценку не влияют */
  submit: (id: string, responses: (string | null)[], focusLosses = 0) =>
    api<AttemptResult>("POST", `/candidate/assessment/attempts/${encodeURIComponent(id)}/submit`, {
      body: { responses, focus_losses: focusLosses },
    }),
  /** PrintScreen во время теста: попытка не засчитывается */
  violation: (id: string) =>
    api<AttemptResult>("POST", `/candidate/assessment/attempts/${encodeURIComponent(id)}/violation`, {
      body: { reason: "screenshot" },
    }),
};

export const catalogApi = {
  categories: () => api<CatalogCategory[]>("GET", "/employer/catalog/categories"),
  fspCategories: () => api<FspCategory[]>("GET", "/employer/catalog/fsp-categories"),
  candidates: (filters: CatalogFilters, cursor: string | undefined) =>
    api<Page<CandidateCard>>("GET", "/employer/catalog/candidates", { query: { ...filters, cursor, limit: 20 } }),
  aiStatus: () => api<AiStatus>("GET", "/employer/catalog/ai-status"),
  /** второе мнение языковой модели о кандидатах под вакансию (до 10, по анонимным карточкам) */
  aiReview: (vacancyId: string, anonIds: string[]) =>
    api<AiReview[]>("POST", "/employer/catalog/ai-review", { body: { vacancy_id: vacancyId, anon_ids: anonIds } }),
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
  vacancies: (status: VacancyStatus | undefined, withComplaints: boolean, cursor: string | undefined) =>
    api<Page<AdminVacancy>>("GET", "/admin/vacancies", {
      query: { status, with_complaints: withComplaints || undefined, cursor, limit: 20 },
    }),
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

type ApplicationQuery = { direction?: ApplicationDirection; status?: ApplicationStatus };

/** Выход на контакт: приглашения компании и отклики кандидатов. */
export const applicationsApi = {
  invite: (body: InvitationInput) => api<EmployerApplication>("POST", "/employer/applications", { body }),
  list: (query: ApplicationQuery, cursor: string | undefined) =>
    api<Page<EmployerApplication>>("GET", "/employer/applications", { query: { ...query, cursor, limit: 20 } }),
  accept: (id: string, contactMethod: string) =>
    api<EmployerApplication>("POST", interviewUrl("/employer/applications", id, "/accept"), {
      body: { contact_method: contactMethod },
    }),
  decline: (id: string, reason: string) =>
    api<EmployerApplication>("POST", interviewUrl("/employer/applications", id, "/decline"), { body: { reason } }),
  withdraw: (id: string) => api<EmployerApplication>("POST", interviewUrl("/employer/applications", id, "/withdraw")),
  contacts: (id: string) => api<OfferContacts>("GET", interviewUrl("/employer/applications", id, "/contacts")),
};

export const myApplicationsApi = {
  list: (query: ApplicationQuery, cursor: string | undefined) =>
    api<Page<Application>>("GET", "/candidate/applications", { query: { ...query, cursor, limit: 20 } }),
  accept: (id: string) => api<Application>("POST", interviewUrl("/candidate/applications", id, "/accept")),
  decline: (id: string, reason: string) =>
    api<Application>("POST", interviewUrl("/candidate/applications", id, "/decline"), { body: { reason } }),
  withdraw: (id: string) => api<Application>("POST", interviewUrl("/candidate/applications", id, "/withdraw")),
  vacancies: (filters: BoardFilters, cursor: string | undefined) =>
    api<Page<BoardVacancy>>("GET", "/candidate/vacancies", { query: { ...filters, cursor, limit: 20 } }),
  respond: (vacancyId: string, message: string) =>
    api<Application>("POST", interviewUrl("/candidate/vacancies", vacancyId, "/respond"), { body: { message } }),
  /** жалоба на вакансию — её увидит модератор */
  complain: (vacancyId: string, body: ComplaintInput) =>
    api<void>("POST", interviewUrl("/candidate/vacancies", vacancyId, "/complaint"), { body }),
};

export const tasksApi = {
  create: (body: TaskInput) => api<EmployerTask>("POST", "/employer/tasks", { body }),
  list: (cursor: string | undefined) => api<Page<EmployerTask>>("GET", "/employer/tasks", { query: { cursor, limit: 20 } }),
  close: (id: string) => api<EmployerTask>("POST", interviewUrl("/employer/tasks", id, "/close")),
  answers: (id: string, cursor: string | undefined) =>
    api<Page<TaskAnswer>>("GET", interviewUrl("/employer/tasks", id, "/answers"), { query: { cursor, limit: 20 } }),
  rate: (taskId: string, answerId: string, rating: number) =>
    api<TaskAnswer>("POST", interviewUrl("/employer/tasks", taskId, `/answers/${encodeURIComponent(answerId)}/rate`), {
      body: { rating },
    }),
};

export const myTasksApi = {
  current: () => api<CurrentTask>("GET", "/candidate/tasks/current"),
  answer: (taskId: string, answer: string) =>
    api<MyTaskAnswer>("POST", interviewUrl("/candidate/tasks", taskId, "/answers"), { body: { answer } }),
  answers: (cursor: string | undefined) =>
    api<Page<MyTaskAnswer>>("GET", "/candidate/tasks/answers", { query: { cursor, limit: 20 } }),
  /** снимок экрана во время решения: задача закрывается */
  violation: (taskId: string) => api<void>("POST", interviewUrl("/candidate/tasks", taskId, "/violation")),
};

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
