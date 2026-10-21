import { screen } from "@testing-library/react";
import { useForm } from "react-hook-form";
import { afterEach, describe, expect, it, vi } from "vitest";
import { json, renderWithApp, serveRoutes } from "../../test/render";
import { MarketHint, midpoint } from "./MarketHint";
import { emptyVacancy, type VacancyFormInput } from "./schemas";

const market = {
  grade: "senior",
  skills: ["Python"],
  vacancies: { count: 14, p25: 300_000, median: 350_000, p75: 400_000 },
  offers: null,
  peers: null,
  ladder: [],
  position: null,
  min_group: 5,
};

function Form({ values }: { values: Partial<VacancyFormInput> }) {
  const form = useForm<VacancyFormInput>({ defaultValues: { ...emptyVacancy, ...values } });
  return <MarketHint control={form.control} />;
}

afterEach(() => vi.unstubAllGlobals());

describe("MarketHint", () => {
  it("compares the vacancy range with the market", async () => {
    const fetchMock = serveRoutes({ "/employer/insights/salary": () => json(market) });
    renderWithApp(<Form values={{ grade: "senior", skills: ["python", "go"], salary_min: 200_000, salary_max: 260_000 }} />);
    expect(await screen.findByText("Ниже рынка")).toBeInTheDocument();
    expect(screen.getByText(/Рынок для Senior с этим стеком: обычно 300/)).toBeInTheDocument();
    expect(screen.getByText("середина вашей вилки: 230 тыс ₽")).toBeInTheDocument();
    // навыки — в порядке, не зависящем от порядка выбора (один ключ кэша)
    expect(String(fetchMock.mock.calls[0][0])).toBe("/api/v1/employer/insights/salary?grade=senior&skills=go&skills=python");
  });

  it("does not compare an impossible range (typo)", async () => {
    serveRoutes({ "/employer/insights/salary": () => json(market) });
    renderWithApp(<Form values={{ grade: "senior", salary_min: 200_000, salary_max: 1_000_000_000_000 }} />);
    expect(await screen.findByText(/Рынок для Senior/)).toBeInTheDocument();
    expect(screen.queryByText(/середина вашей вилки/)).not.toBeInTheDocument();
    expect(screen.queryByText("Выше рынка")).not.toBeInTheDocument();
  });

  it("explains when there is not enough market data", async () => {
    serveRoutes({ "/employer/insights/salary": () => json({ ...market, vacancies: null, skills: [] }) });
    renderWithApp(<Form values={{ grade: "senior" }} />);
    expect(await screen.findByText(/пока мало данных/)).toHaveTextContent("5 вакансий от трёх компаний");
  });
});

describe("midpoint", () => {
  it("needs both ends of a valid range", () => {
    expect(midpoint(200_000, 300_000)).toBe(250_000);
    expect(midpoint("", 300_000)).toBeNull();
    expect(midpoint(300_000, 200_000)).toBeNull();
  });
});
