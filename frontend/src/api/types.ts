// Типы домена из OpenAPI-схемы бэка (src/api/schema.d.ts генерируется: npm run gen:api).
import type { components } from "./schema";

type Schemas = components["schemas"];

export type Me = Schemas["MeOut"];
export type UserRole = Schemas["UserRole"];
export type TokenOut = Schemas["TokenOut"];
export type CandidateRegisterIn = Schemas["CandidateRegisterIn"];
export type EmployerRegisterIn = Schemas["EmployerRegisterIn"];
export type LoginIn = Schemas["LoginIn"];
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
