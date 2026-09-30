// Эндпоинты API в одном месте: компоненты не собирают URL сами.
import { api } from "./client";
import type {
  CandidateRegisterIn,
  Company,
  CompanyStatus,
  EmployerRegisterIn,
  LoginIn,
  Me,
  Page,
  Profile,
  ProfileUpdate,
  Skill,
  TokenOut,
  Vacancy,
  VacancyCreate,
  VacancyStatus,
  VacancyUpdate,
} from "./types";

export const authApi = {
  login: (body: LoginIn) => api<TokenOut>("POST", "/auth/login", { body }),
  registerCandidate: (body: CandidateRegisterIn) =>
    api<TokenOut>("POST", "/auth/register/candidate", { body }),
  registerEmployer: (body: EmployerRegisterIn) =>
    api<TokenOut>("POST", "/auth/register/employer", { body }),
  me: () => api<Me>("GET", "/auth/me"),
};

export const publicApi = {
  skills: () => api<Skill[]>("GET", "/public/skills"),
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

export const adminApi = {
  companies: (status: CompanyStatus | undefined, cursor: string | undefined) =>
    api<Page<Company>>("GET", "/admin/companies", { query: { status, cursor, limit: 20 } }),
  setCompanyStatus: (id: string, status: CompanyStatus, reason: string) =>
    api<Company>("POST", `/admin/companies/${encodeURIComponent(id)}/status`, { body: { status, reason } }),
};
