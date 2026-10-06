import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  adminApi,
  aiAdminApi,
  authApi,
  candidateApi,
  candidateOffersApi,
  catalogApi,
  employerApi,
  employerOffersApi,
  fspApi,
  insightsApi,
  interviewsApi,
  myInterviewsApi,
  passportApi,
  publicApi,
} from "./endpoints";
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
    ["register candidate", () => authApi.registerCandidate({ email: "a@b.ru", password: "x", full_name: "Анна", consent: true }), "POST", "/api/v1/auth/register/candidate"],
    ["register employer", () => authApi.registerEmployer({ email: "a@b.ru", password: "x", company_name: "ООО", consent: true }), "POST", "/api/v1/auth/register/employer"],
    ["verify email", () => authApi.verifyEmail("tok"), "POST", "/api/v1/auth/verify-email"],
    ["resend verification", () => authApi.resendVerification("a@b.ru"), "POST", "/api/v1/auth/verify-email/resend"],
    ["forgot password", () => authApi.forgotPassword("a@b.ru"), "POST", "/api/v1/auth/password/forgot"],
    ["reset password", () => authApi.resetPassword("tok", "Str0ng-pass"), "POST", "/api/v1/auth/password/reset"],
    ["skills", () => publicApi.skills(), "GET", "/api/v1/public/skills"],
    ["profile", () => candidateApi.profile(), "GET", "/api/v1/candidate/profile"],
    ["update profile", () => candidateApi.updateProfile({ city: "Казань" }), "PATCH", "/api/v1/candidate/profile"],
    ["company", () => employerApi.company(), "GET", "/api/v1/employer/company"],
    ["vacancies", () => employerApi.vacancies("draft", "c1"), "GET", "/api/v1/employer/vacancies?status=draft&cursor=c1&limit=20"],
    ["create vacancy", () => employerApi.createVacancy({ title: "T", grade: "middle", specialization: "backend", work_format: "remote", salary_min: 1, salary_max: 2 }), "POST", "/api/v1/employer/vacancies"],
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
    ["mfa setup", () => authApi.mfaSetup("t", "enroll-code"), "POST", "/api/v1/auth/2fa/setup"],
    ["mfa verify", () => authApi.mfaVerify("t", "123456"), "POST", "/api/v1/auth/2fa/verify"],
    ["admin vacancies", () => adminApi.vacancies("active", undefined), "GET", "/api/v1/admin/vacancies?status=active&limit=20"],
    ["moderate vacancy", () => adminApi.moderateVacancy("v1", "block", "x"), "POST", "/api/v1/admin/vacancies/v1/moderation"],
    ["admin users", () => adminApi.users({ role: "candidate", q: "anna" }, undefined), "GET", "/api/v1/admin/users?role=candidate&q=anna&limit=20"],
    ["moderate user", () => adminApi.moderateUser("u1", "unblock", ""), "POST", "/api/v1/admin/users/u1/moderation"],
    ["audit", () => adminApi.audit("admin.", undefined), "GET", "/api/v1/admin/audit?action=admin.&limit=50"],
    ["invite", () => interviewsApi.invite({} as never), "POST", "/api/v1/employer/interviews"],
    ["interviews", () => interviewsApi.list("scheduled", undefined), "GET", "/api/v1/employer/interviews?status=scheduled&limit=20"],
    ["cancel interview", () => interviewsApi.cancel("i1", ""), "POST", "/api/v1/employer/interviews/i1/cancel"],
    ["complete interview", () => interviewsApi.complete("i1", "passed", ""), "POST", "/api/v1/employer/interviews/i1/complete"],
    ["my interviews", () => myInterviewsApi.list(undefined, undefined), "GET", "/api/v1/candidate/interviews?limit=20"],
    ["accept slot", () => myInterviewsApi.accept("i1", "2026-10-05T09:00:00Z"), "POST", "/api/v1/candidate/interviews/i1/accept"],
    ["decline interview", () => myInterviewsApi.decline("i1", ""), "POST", "/api/v1/candidate/interviews/i1/decline"],
    ["ai providers", () => aiAdminApi.list(), "GET", "/api/v1/admin/ai-providers"],
    ["activate ai", () => aiAdminApi.activate("p1"), "POST", "/api/v1/admin/ai-providers/p1/activate"],
    ["deactivate ai", () => aiAdminApi.deactivate(), "POST", "/api/v1/admin/ai-providers/deactivate"],
    ["test ai", () => aiAdminApi.test("p1"), "POST", "/api/v1/admin/ai-providers/p1/test"],
    ["catalog categories", () => catalogApi.categories(), "GET", "/api/v1/employer/catalog/categories"],
    ["catalog candidates", () => catalogApi.candidates({ category: "product-elite", grade: "middle" }, "c"), "GET", "/api/v1/employer/catalog/candidates?category=product-elite&grade=middle&cursor=c&limit=20"],
    ["employer offers", () => employerOffersApi.list("sent", undefined), "GET", "/api/v1/employer/offers?status=sent&limit=20"],
    ["withdraw offer", () => employerOffersApi.withdraw("o1"), "POST", "/api/v1/employer/offers/o1/withdraw"],
    ["offer contacts", () => employerOffersApi.contacts("o1"), "GET", "/api/v1/employer/offers/o1/contacts"],
    ["inbox", () => candidateOffersApi.list(undefined, undefined), "GET", "/api/v1/candidate/offers?limit=20"],
    ["accept offer", () => candidateOffersApi.accept("o1"), "POST", "/api/v1/candidate/offers/o1/accept"],
    ["decline offer", () => candidateOffersApi.decline("o1", "нет"), "POST", "/api/v1/candidate/offers/o1/decline"],
    ["delete account", () => candidateApi.deleteAccount("x"), "POST", "/api/v1/candidate/account/delete"],
    ["salary radar", () => insightsApi.salary(), "GET", "/api/v1/candidate/insights/salary"],
    ["growth", () => insightsApi.growth(), "GET", "/api/v1/candidate/insights/growth"],
    ["market", () => insightsApi.market("senior", ["python", "go"]), "GET", "/api/v1/employer/insights/salary?grade=senior&skills=python&skills=go"],
    ["market without skills", () => insightsApi.market("junior", []), "GET", "/api/v1/employer/insights/salary?grade=junior"],
  ])("%s", async (_name, call, method, url) => {
    await call();
    expect(lastCall()).toMatchObject({ method, url });
  });

  it("sends offer with idempotency key header", async () => {
    await employerOffersApi.send(
      { interview_id: "i1", salary_min: 1, salary_max: 2, message: "" },
      "key-1",
    );
    const [url, init] = fetchMock.mock.calls.at(-1)!;
    expect(url).toBe("/api/v1/employer/offers");
    expect(init.headers["Idempotency-Key"]).toBe("key-1");
  });

  it("sends moderation reason in body", async () => {
    await adminApi.setCompanyStatus("c1", "blocked", "фейк");
    expect(lastCall().body).toEqual({ status: "blocked", reason: "фейк" });
  });
});
