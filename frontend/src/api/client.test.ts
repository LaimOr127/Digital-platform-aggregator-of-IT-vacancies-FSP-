import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, logoutRequest, refreshSession, tokenSubject } from "./client";
import { ApiError, fieldErrors } from "./errors";
import { session } from "./session";

const json = (status: number, body: unknown) =>
  new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const token = (value: string) => json(200, { access_token: value, token_type: "bearer", expires_in: 900 });

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  session.clear();
  document.cookie = "csrf_token=csrf-123; path=/";
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
});

describe("api", () => {
  it("sends JSON body and bearer token", async () => {
    session.set("abc");
    fetchMock.mockResolvedValueOnce(json(200, { ok: true }));
    await api("PATCH", "/candidate/profile", { body: { city: "Казань" } });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/candidate/profile");
    expect(init.method).toBe("PATCH");
    expect(init.headers.Authorization).toBe("Bearer abc");
    expect(JSON.parse(init.body)).toEqual({ city: "Казань" });
  });

  it("builds query string and skips empty values", async () => {
    fetchMock.mockResolvedValueOnce(json(200, []));
    await api("GET", "/employer/vacancies", { query: { status: "draft", cursor: undefined, limit: 20 } });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/employer/vacancies?status=draft&limit=20");
  });

  it("returns undefined for 204", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(api("DELETE", "/employer/vacancies/1")).resolves.toBeUndefined();
  });

  it("throws ApiError with unified error format", async () => {
    fetchMock.mockResolvedValueOnce(json(409, { error: { code: "conflict", message: "email занят" } }));
    const err = await api("POST", "/auth/register/candidate").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 409, code: "conflict", message: "email занят" });
  });

  it("falls back to generic message for non-JSON errors", async () => {
    fetchMock.mockResolvedValueOnce(new Response("Bad gateway", { status: 502 }));
    const err = await api("GET", "/health").catch((e) => e);
    expect(err).toMatchObject({ status: 502, code: "http_502" });
  });

  it("refreshes once on 401 and retries with the new token", async () => {
    session.set("expired");
    fetchMock
      .mockResolvedValueOnce(json(401, { error: { code: "unauthorized", message: "x" } }))
      .mockResolvedValueOnce(token("fresh"))
      .mockResolvedValueOnce(json(200, { id: 1 }));
    await expect(api("GET", "/auth/me")).resolves.toEqual({ id: 1 });
    const [refreshUrl, refreshInit] = fetchMock.mock.calls[1];
    expect(refreshUrl).toBe("/api/v1/auth/refresh");
    expect(refreshInit.headers["X-CSRF-Token"]).toBe("csrf-123");
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe("Bearer fresh");
    expect(session.get()).toBe("fresh");
  });

  it("keeps session and reports transient error when refresh hits a server failure", async () => {
    session.set("expired");
    fetchMock
      .mockResolvedValueOnce(json(401, { error: { code: "unauthorized", message: "x" } }))
      .mockResolvedValueOnce(json(502, { error: { code: "bad_gateway", message: "x" } }));
    const err = (await api("GET", "/auth/me").catch((e) => e)) as ApiError;
    expect(err.code).toBe("session_refresh_failed");
    expect(session.get()).toBe("expired");
  });

  it("retries with a token refreshed by a parallel request without rotating again", async () => {
    session.set("old");
    fetchMock.mockImplementationOnce(async () => {
      session.set("new"); // параллельный запрос успел обновить токен
      return json(401, { error: { code: "unauthorized", message: "x" } });
    });
    fetchMock.mockResolvedValueOnce(json(200, { ok: true }));
    await expect(api("GET", "/auth/me")).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe("Bearer new");
  });

  it("clears session when refresh fails", async () => {
    session.set("expired");
    fetchMock
      .mockResolvedValueOnce(json(401, { error: { code: "unauthorized", message: "x" } }))
      .mockResolvedValueOnce(json(401, { error: { code: "unauthorized", message: "x" } }));
    const err = (await api("GET", "/auth/me").catch((e) => e)) as ApiError;
    expect(err.status).toBe(401);
    expect(session.get()).toBeNull();
  });

  it("does not try to refresh for anonymous requests", async () => {
    fetchMock.mockResolvedValueOnce(json(401, { error: { code: "unauthorized", message: "x" } }));
    await api("POST", "/auth/login", { body: {} }).catch(() => undefined);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("refreshSession", () => {
  it("is single-flight: parallel callers share one request", async () => {
    fetchMock.mockResolvedValueOnce(token("t1"));
    const [a, b] = await Promise.all([refreshSession(), refreshSession()]);
    expect([a, b]).toEqual(["ok", "ok"]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("returns false without csrf cookie and does not call the API", async () => {
    document.cookie = "csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
    await expect(refreshSession()).resolves.toBe("invalid");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("distinguishes transient failures from an invalid session", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("offline"));
    await expect(refreshSession()).resolves.toBe("transient");
    fetchMock.mockResolvedValueOnce(json(403, { error: { code: "forbidden", message: "x" } }));
    await expect(refreshSession()).resolves.toBe("invalid");
  });

  it("uses a cross-tab lock when Web Locks are available", async () => {
    const request = vi.fn((_name: string, fn: () => Promise<unknown>) => fn());
    vi.stubGlobal("navigator", { locks: { request } });
    fetchMock.mockResolvedValueOnce(token("t"));
    await refreshSession();
    expect(request).toHaveBeenCalledWith("itmatch-auth-refresh", expect.any(Function));
  });
});

describe("logoutRequest and tokenSubject", () => {
  it("throws when the server did not log out", async () => {
    fetchMock.mockResolvedValueOnce(json(403, { error: { code: "forbidden", message: "csrf" } }));
    await expect(logoutRequest()).rejects.toMatchObject({ status: 403 });
  });

  it("skips the call without csrf cookie (no server session)", async () => {
    document.cookie = "csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
    await logoutRequest();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("reads sub from a JWT and tolerates garbage", () => {
    const payload = btoa(JSON.stringify({ sub: "u-1" })).replace(/=+$/, "");
    expect(tokenSubject(`h.${payload}.s`)).toBe("u-1");
    expect(tokenSubject("garbage")).toBeNull();
    expect(tokenSubject(null)).toBeNull();
  });
});

describe("fieldErrors", () => {
  it("maps body validation details to form fields", () => {
    const err = new ApiError(422, "validation_error", "Некорректные данные", [
      { loc: ["body", "password"], msg: "слишком короткий" },
      { loc: ["body"], msg: "общая ошибка" },
    ]);
    expect(fieldErrors(err)).toEqual({ password: "слишком короткий" });
  });

  it("keeps nested paths and drops list indexes", () => {
    const err = new ApiError(422, "validation_error", "x", [
      { loc: ["body", "contacts", "email"], msg: "не email" },
      { loc: ["body", "skills", 3], msg: "плохой slug" },
    ]);
    expect(fieldErrors(err)).toEqual({ "contacts.email": "не email", skills: "плохой slug" });
  });

  it("returns empty object for other errors", () => {
    expect(fieldErrors(new Error("x"))).toEqual({});
  });
});

describe("session", () => {
  it("notifies subscribers", () => {
    const listener = vi.fn();
    const unsubscribe = session.subscribe(listener);
    session.set("a");
    session.clear();
    unsubscribe();
    session.set("b");
    expect(listener).toHaveBeenCalledTimes(2);
  });
});
