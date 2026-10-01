// Нагрузочный тест работающего стека (k6): make load EMP=... CAND=... VAC=...
// EMP / CAND — access-токены работодателя (одобренная компания) и кандидата, VAC — id
// опубликованной вакансии. Каталог наполняется командой make seed-demo N=2000.
// Порог: p95 < 500 мс для пользовательских запросов, ошибок — меньше 1%.
import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE || "http://proxy/api/v1";
const emp = { headers: { Authorization: `Bearer ${__ENV.EMP}` } };
const cand = { headers: { Authorization: `Bearer ${__ENV.CAND}` } };
const step = (name, start, vus) => ({ executor: "constant-vus", vus, duration: "20s", startTime: start, exec: name, tags: { s: name } });

export const options = {
  scenarios: {
    health: step("health", "0s", 50),
    catalog: step("catalog", "22s", 20),
    match: step("match", "44s", 20),
    profile: step("profile", "66s", 20),
  },
  thresholds: Object.fromEntries(
    ["health", "catalog", "match", "profile"].flatMap((n) => [
      [`http_req_duration{s:${n}}`, ["p(95)<500"]],
      [`http_reqs{s:${n}}`, ["count>0"]],
    ]).concat([["http_req_failed", ["rate<0.01"]]]),
  ),
  // общий порог ошибок дополняет пороги по сценариям
  summaryTrendStats: ["avg", "med", "p(95)", "p(99)", "max"],
};

export function health() { check(http.get(`${BASE}/health`), { ok: (r) => r.status === 200 }); }
export function catalog() { check(http.get(`${BASE}/employer/catalog/candidates?limit=20`, emp), { ok: (r) => r.status === 200 }); }
export function match() {
  check(http.get(`${BASE}/employer/catalog/candidates?limit=20&vacancy_id=${__ENV.VAC}`, emp), { ok: (r) => r.status === 200 });
}
export function profile() { check(http.get(`${BASE}/candidate/profile`, cand), { ok: (r) => r.status === 200 }); }
