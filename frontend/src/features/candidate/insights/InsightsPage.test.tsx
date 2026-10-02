import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { json, renderWithApp, serveRoutes } from "../../../test/render";
import { InsightsPage } from "./InsightsPage";

const band = (p25: number, median: number, p75: number, count = 12) => ({ count, p25, median, p75 });

const radar = {
  grade: "middle",
  skills: ["Python", "PostgreSQL"],
  vacancies: band(200_000, 250_000, 300_000),
  offers: null,
  peers: band(180_000, 220_000, 260_000, 7),
  ladder: [
    { grade: "junior", band: band(100_000, 130_000, 150_000) },
    { grade: "middle", band: band(200_000, 250_000, 300_000) },
    { grade: "senior", band: null },
  ],
  expectation: 150_000,
  position: "below",
  min_group: 5,
};

const growth = {
  current_grade: "middle",
  target_grade: "senior",
  vacancies_considered: 9,
  missing_skills: [{ slug: "kubernetes", name: "Kubernetes", share: 0.67 }],
  strengths: [{ slug: "python", name: "Python", share: 0.89 }],
  salary_now: 250_000,
  salary_target: 350_000,
  fsp_next: "Продвинутый уровень ФСП: выйдите в финал",
  min_group: 5,
};

afterEach(() => vi.unstubAllGlobals());

describe("InsightsPage", () => {
  it("shows the salary radar with the candidate's position", async () => {
    serveRoutes({ "/insights/salary": () => json(radar), "/insights/growth": () => json(growth) });
    renderWithApp(<InsightsPage />);
    expect(await screen.findByText("Ниже рынка")).toBeInTheDocument();
    expect(screen.getByText(/можно смело просить больше/)).toBeInTheDocument();
    expect(screen.getByText("Middle · Python, PostgreSQL")).toBeInTheDocument();
    // офферов меньше порога k-анонимности — без распределения
    expect(screen.getByLabelText("Офферы: мало данных (меньше 5)")).toBeInTheDocument();
    expect(screen.getByText("ваши ожидания: от 150 тыс ₽")).toBeInTheDocument();
  });

  it("reveals exact numbers on hover and in the table view", async () => {
    serveRoutes({ "/insights/salary": () => json(radar), "/insights/growth": () => json(growth) });
    renderWithApp(<InsightsPage />);
    const row = await screen.findByLabelText(/^Вилки вакансий: медиана 250 тыс/);
    await userEvent.hover(row);
    expect(within(row).getByTestId("range-tooltip")).toHaveTextContent("12 вакансий");
    const table = screen.getAllByRole("table")[0];
    expect(within(table).getByText("Ожидания коллег").closest("tr")).toHaveTextContent("220 тыс");
  });

  it("highlights the current grade on the ladder", async () => {
    serveRoutes({ "/insights/salary": () => json(radar), "/insights/growth": () => json(growth) });
    renderWithApp(<InsightsPage />);
    const ladder = (await screen.findByText("Зарплаты по грейдам")).closest("div")!;
    expect(within(ladder).getByText("Middle", { selector: "p" })).toHaveClass("font-semibold");
    expect(within(ladder).getByText("Junior", { selector: "p" })).not.toHaveClass("font-semibold");
  });

  it("shows the growth path with missing skills and salary step", async () => {
    serveRoutes({ "/insights/salary": () => json(radar), "/insights/growth": () => json(growth) });
    renderWithApp(<InsightsPage />);
    expect(await screen.findByText("Kubernetes")).toBeInTheDocument();
    expect(screen.getByText("в 67% вакансий")).toBeInTheDocument();
    expect(screen.getByText("+40%")).toBeInTheDocument();
    expect(screen.getByText(/По 9 вакансиям уровня Senior/)).toBeInTheDocument();
    expect(screen.getByText(growth.fsp_next)).toBeInTheDocument();
  });

  it("asks to fill the grade instead of showing an error", async () => {
    serveRoutes({
      "/insights/salary": () => json({ ...radar, grade: null, ladder: [], position: null }),
      "/insights/growth": () => json({ error: { code: "invalid_state", message: "укажите грейд" } }, 409),
    });
    renderWithApp(<InsightsPage />);
    expect(await screen.findByText("Укажите грейд и навыки")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Заполнить профиль" })).toHaveAttribute("href", "/app");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("treats a growth 409 as a missing grade even if the radar still has one", async () => {
    serveRoutes({
      "/insights/salary": () => json(radar),
      "/insights/growth": () => json({ error: { code: "invalid_state", message: "укажите грейд" } }, 409),
    });
    renderWithApp(<InsightsPage />);
    expect(await screen.findByText("Укажите грейд и навыки")).toBeInTheDocument();
  });
});
