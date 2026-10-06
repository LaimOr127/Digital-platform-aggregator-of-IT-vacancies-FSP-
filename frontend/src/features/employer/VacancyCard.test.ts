import { describe, expect, it } from "vitest";
import type { Vacancy } from "../../api/types";
import { vacancyRank } from "./VacancyCard";

const inDays = (days: number) => new Date(Date.now() + days * 86_400_000).toISOString();
const vacancy = (status: Vacancy["status"], expires: string | null) => ({ status, expires_at: expires }) as Vacancy;

describe("vacancyRank", () => {
  it("puts vacancies to renew first and closed ones last", () => {
    const list = [
      vacancy("closed", null),
      vacancy("active", inDays(10)),
      vacancy("blocked", null),
      vacancy("active", inDays(2)),
      vacancy("draft", null),
    ];
    const ranks = [...list].sort((a, b) => vacancyRank(a) - vacancyRank(b)).map((v) => v.status);
    expect(ranks).toEqual(["active", "active", "draft", "closed", "blocked"]);
    expect(vacancyRank(vacancy("active", inDays(2)))).toBe(0);
  });
});
