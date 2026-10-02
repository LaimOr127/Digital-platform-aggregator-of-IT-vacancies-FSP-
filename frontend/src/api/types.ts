// Типы домена из OpenAPI-схемы бэка (src/api/schema.d.ts генерируется: npm run gen:api).
import type { components } from "./schema";

type Schemas = components["schemas"];

export type Me = Schemas["MeOut"];
export type UserRole = Schemas["UserRole"];
export type TokenOut = Schemas["TokenOut"];
export type CandidateRegisterIn = Schemas["CandidateRegisterIn"];
export type EmployerRegisterIn = Schemas["EmployerRegisterIn"];
export type LoginIn = Schemas["LoginIn"];
export type Accepted = Schemas["AcceptedOut"];
export type Profile = Schemas["ProfileOut"];
export type ProfileUpdate = Schemas["ProfileUpdateIn"];
export type Skill = Schemas["SkillOut"];
export type Grade = Schemas["Grade"];
export type WorkFormat = Schemas["WorkFormat"];
export type VerificationTier = Schemas["VerificationTier"];
export type Company = Schemas["CompanyOut"];
export type CompanyStatus = Schemas["CompanyStatus"];
export type Vacancy = Schemas["VacancyOut"];
export type VacancyStatus = Schemas["VacancyStatus"];
export type VacancyCreate = Schemas["VacancyCreateIn"];
export type VacancyUpdate = Schemas["VacancyUpdateIn"];
export type Page<T> = { items: T[]; next_cursor: string | null };
export type FspStatus = Schemas["FspStatusOut"];
export type FspLinkStart = Schemas["FspLinkStartOut"];
export type Achievement = Schemas["AchievementOut"];
export type Category = Schemas["CategoryOut"];
export type Passport = Schemas["PassportOut"];
export type PassportVerify = Schemas["PassportVerifyOut"];

export type PassportCheck = PassportVerify["status"];
export type MfaChallenge = Schemas["MfaChallengeOut"];
export type MfaSetup = Schemas["MfaSetupOut"];
export type LoginResult = TokenOut | MfaChallenge;
export type AdminVacancy = Schemas["AdminVacancyOut"];
export type AdminUser = Schemas["AdminUserOut"];
export type AuditEntry = Schemas["AuditEntryOut"];
export type ModerationAction = Schemas["ModerationIn"]["action"];
export type CatalogCategory = Schemas["CatalogCategoryOut"];
export type CandidateCard = Schemas["CandidateCardOut"];
export type OfferCreate = Schemas["OfferCreateIn"];
export type Offer = Schemas["OfferOut"];
export type EmployerOffer = Schemas["EmployerOfferOut"];
export type OfferStatus = Schemas["OfferStatus"];
export type OfferContacts = Schemas["OfferContactsOut"];
export type CatalogFilters = {
  category?: string;
  grade?: Grade;
  work_format?: WorkFormat;
  skill?: string;
  search_status?: SearchStatus;
  /** сортировать по соответствию этой вакансии */
  vacancy_id?: string;
};

/** Содержимое паспорта (подписанный JSON, версия 2). */
export type PassportPayload = {
  version: number;
  passport_id: string;
  issuer: string;
  demo?: boolean;
  issued_at: string;
  expires_at?: string;
  /** source: fsp — имя подтверждено ФСП; self — указано кандидатом */
  holder: { name: string | null; source?: "fsp" | "self" | null };
  title: string | null;
  grade: Grade | null;
  skills: string[];
  verification_tier: VerificationTier;
  fsp: { athlete_id: string | null; rank: string | null; achievements: { discipline: string; summary: string }[] };
  categories: string[];
};

export type SearchStatus = Schemas["SearchStatus"];
// поля со значением по умолчанию сервер отдаёт всегда (в схеме OpenAPI они необязательные)
export type ProfileDraft = Required<Schemas["ProfileDraftOut"]>;
export type ImportCapabilities = Schemas["ImportCapabilitiesOut"];

export type Match = Schemas["MatchOut"];
export type MatchFactor = Schemas["MatchFactorOut"];
export type Interview = Schemas["InterviewOut"];
export type EmployerInterview = Schemas["EmployerInterviewOut"];
export type InterviewStatus = Schemas["InterviewStatus"];
export type InterviewResult = Schemas["InterviewResult"];
export type InterviewFormat = Schemas["InterviewFormat"];
export type InterviewInvite = Schemas["InterviewInviteIn"];
export type AiProvider = Schemas["AiProviderOut"];
export type AiProviderInput = Schemas["AiProviderIn"];
export type AiProviderUpdate = Schemas["AiProviderUpdate"];
export type AiProviderKind = Schemas["AiProviderKind"];
export type AiTest = Schemas["AiTestOut"];
export type SalaryBand = Schemas["SalaryBandOut"];
export type SalaryRadar = Schemas["SalaryRadarOut"];
export type GradeSalary = Schemas["GradeSalaryOut"];
export type Growth = Schemas["GrowthOut"];
export type SkillShare = Schemas["SkillShareOut"];
