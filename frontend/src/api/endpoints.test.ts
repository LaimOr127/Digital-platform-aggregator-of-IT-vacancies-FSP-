import { beforeEach, describe, expect, it, vi } from "vitest";
import { adminApi, authApi, candidateApi, employerApi, fspApi, passportApi, publicApi } from "./endpoints";
import { session } from "./session";

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  session.clear();
  fetchMock = vi.fn(async () => new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
});

const lastCall = () => {
  const [url, init] = fetchMock.mock.calls.at(-1)!;
  return { url, method: init.method, body: init.body ? JSON.parse(init.body) : undefined };
};

describe("endpoints map to the backend API", () => {
  it.each([
    ["login", () => authApi.login({ email: "a@b.ru", password: "x" }), "POST", "/api/v1/auth/login"],
    ["me", () => authApi.me(), "GET", "/api/v1/auth/me"],
    ["register candidate", () => authApi.registerCandidate({ email: "a@b.ru", password: "x", full_name: "Анна" }), "POST", "/api/v1/auth/register/candidate"],
    ["register employer", () => authApi.registerEmployer({ email: "a@b.ru", password: "x", company_name: "ООО" }), "POST", "/api/v1/auth/register/employer"],
    ["skills", () => publicApi.skills(), "GET", "/api/v1/public/skills"],
    ["profile", () => candidateApi.profile(), "GET", "/api/v1/candidate/profile"],
    ["update profile", () => candidateApi.updateProfile({ city: "Казань" }), "PATCH", "/api/v1/candidate/profile"],
    ["company", () => employerApi.company(), "GET", "/api/v1/employer/company"],
    ["vacancies", () => employerApi.vacancies("draft", "c1"), "GET", "/api/v1/employer/vacancies?status=draft&cursor=c1&limit=20"],
    ["create vacancy", () => employerApi.createVacancy({ title: "T", grade: "middle", work_format: "remote", salary_min: 1, salary_max: 2 }), "POST", "/api/v1/employer/vacancies"],
    ["update vacancy", () => employerApi.updateVacancy("v/1", { title: "T" }), "PATCH", "/api/v1/employer/vacancies/v%2F1"],
    ["publish", () => employerApi.publishVacancy("v1"), "POST", "/api/v1/employer/vacancies/v1/publish"],
    ["close", () => employerApi.closeVacancy("v1"), "POST", "/api/v1/employer/vacancies/v1/close"],
    ["delete", () => employerApi.deleteVacancy("v1"), "DELETE", "/api/v1/employer/vacancies/v1"],
    ["companies", () => adminApi.companies("pending", undefined), "GET", "/api/v1/admin/companies?status=pending&limit=20"],
    ["set status", () => adminApi.setCompanyStatus("c1", "blocked", "фейк"), "POST", "/api/v1/admin/companies/c1/status"],
    ["fsp status", () => fspApi.status(), "GET", "/api/v1/candidate/fsp"],
    ["fsp link", () => fspApi.link("FSP-1"), "POST", "/api/v1/candidate/fsp/link"],
    ["fsp confirm", () => fspApi.confirm("123456"), "POST", "/api/v1/candidate/fsp/confirm"],
    ["fsp sync", () => fspApi.sync(), "POST", "/api/v1/candidate/fsp/sync"],
    ["fsp unlink", () => fspApi.unlink(), "DELETE", "/api/v1/candidate/fsp"],
    ["passport", () => passportApi.active(), "GET", "/api/v1/candidate/passport"],
    ["issue passport", () => passportApi.issue(true), "POST", "/api/v1/candidate/passport"],
    ["revoke passport", () => passportApi.revoke(), "DELETE", "/api/v1/candidate/passport"],
    ["public passport", () => publicApi.passport("p/1"), "GET", "/api/v1/public/passport/p%2F1"],
  ])("%s", async (_name, call, method, url) => {
    await call();
    expect(lastCall()).toMatchObject({ method, url });
  });

  it("sends moderation reason in body", async () => {
    await adminApi.setCompanyStatus("c1", "blocked", "фейк");
    expect(lastCall().body).toEqual({ status: "blocked", reason: "фейк" });
  });
});
