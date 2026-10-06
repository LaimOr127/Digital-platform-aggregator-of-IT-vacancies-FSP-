import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { json, renderWithApp, serveRoutes } from "../../../test/render";
import { CatalogPage } from "./CatalogPage";

const company = { id: "c1", name: "ООО", inn: null, website: null, status: "approved", created_at: "2026-10-01T00:00:00Z" };
const categories = ["backend", "qa"].flatMap((specialization) =>
  ["intern", "junior", "middle", "senior", "lead"].map((grade) => ({
    slug: `${specialization}:${grade}`,
    title: `${specialization} ${grade}`,
    specialization,
    grade,
    candidates: specialization === "backend" && grade === "middle" ? 4 : 0,
  })),
);
const card = {
  anon_id: "abcdef12-0000-0000-0000-000000000000",
  title: "Backend",
  specialization: "backend",
  category: { slug: "backend:middle", title: "Бэкенд-разработчики · Middle" },
  grade: "middle",
  confirmed_grade: "middle",
  assessment_score: 72,
  experience_years: 3,
  work_format: "remote",
  city: null,
  salary_min: null,
  salary_max: null,
  verification_tier: "verified_fsp",
  search_status: "active",
  skills: ["Python", "Go"],
  confirmed_skills: ["Python"],
  fsp_categories: [],
  achievements: [],
  about: null,
  last_activity_at: null,
  match: null,
  strength: { score: 70, factors: [{ key: "assessment", label: "Результат теста", weight: 60, share: 0.72, detail: "72 из 100" }] },
};

function serve() {
  return serveRoutes({
    "/employer/vacancies": () => json({ items: [], next_cursor: null }),
    "/employer/catalog/categories": () => json(categories),
    "/employer/catalog/fsp-categories": () => json([]),
    "/employer/catalog/candidates": () => json({ items: [card], next_cursor: null }),
    "/public/skills": () => json([{ slug: "python", name: "Python" }]),
  });
}

const lastQuery = (mock: ReturnType<typeof vi.fn>) =>
  new URL(String(mock.mock.calls.filter(([u]) => String(u).includes("/catalog/candidates")).at(-1)![0]), "http://x")
    .searchParams;

afterEach(() => vi.unstubAllGlobals());

describe("CatalogPage", () => {
  it("shows only confirmed categories by default and explains the rank", async () => {
    const fetchMock = serve();
    renderWithApp(<CatalogPage company={company as never} />);
    expect(await screen.findByText("Бэкенд-разработчики · Middle")).toBeInTheDocument();
    expect(lastQuery(fetchMock).get("confirmed_only")).toBe("true");
    expect(screen.getByText("72 из 100", { exact: false })).toBeInTheDocument();
    expect(screen.getByLabelText("подтверждён тестом")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Почему" }));
    expect(screen.getByText("Результат теста")).toBeInTheDocument();
  });

  it("filters by category cell, skills and FSP", async () => {
    const fetchMock = serve();
    renderWithApp(<CatalogPage company={company as never} />);
    await userEvent.click(await screen.findByRole("button", { name: "Бэкенд-разработка, Middle: кандидатов 4" }));
    expect(lastQuery(fetchMock).get("category")).toBe("backend:middle");
    expect(screen.getByRole("button", { name: "Тестирование, Middle: кандидатов 0" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Python" }));
    await userEvent.click(screen.getByLabelText(/С достижениями ФСП/));
    const query = lastQuery(fetchMock);
    expect(query.getAll("skill")).toEqual(["python"]);
    expect(query.get("fsp_only")).toBe("true");
  });
});
