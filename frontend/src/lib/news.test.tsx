import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { json, renderWithApp, serveRoutes } from "../test/render";
import { useNews } from "./news";

const PATHS = { vacancies: "/app/vacancies", offers: "/app/offers" };
const fetchUpdates = () => fetch("/candidate/updates").then((r) => r.json());
const markSeen = (section: string) =>
  fetch("/candidate/updates/seen", { method: "POST", body: JSON.stringify({ section }) });

function Probe() {
  const news = useNews("test", fetchUpdates, markSeen, PATHS);
  return (
    <>
      <p>vacancies: {String(news["/app/vacancies"])}</p>
      <p>offers: {String(news["/app/offers"])}</p>
      <Link to="/app/offers">к офферам</Link>
    </>
  );
}

const marked = (mock: ReturnType<typeof vi.fn>) =>
  mock.mock.calls
    .filter(([url]) => String(url).endsWith("/candidate/updates/seen"))
    .map(([, init]) => JSON.parse(String(init?.body)).section);

afterEach(() => vi.unstubAllGlobals());

describe("useNews", () => {
  it("uses seen marks from the server, so every device shows the same dots", async () => {
    // офферы уже открывали на другом устройстве после последнего события
    serveRoutes({
      "/candidate/updates": () =>
        json({
          vacancies: "2026-10-06T10:00:00Z",
          offers: "2026-10-06T11:00:00Z",
          seen: { offers: "2026-10-06T12:00:00Z" },
        }),
      "/candidate/updates/seen": () => new Response(null, { status: 204 }),
    });
    renderWithApp(<Probe />, "/");
    expect(await screen.findByText("vacancies: true")).toBeInTheDocument();
    expect(screen.getByText("offers: false")).toBeInTheDocument();
  });

  it("marks the opened section on the server and clears its dot at once", async () => {
    // сервер помнит отметки, как настоящий
    const seen: Record<string, string> = {};
    const fetchMock = serveRoutes({
      "/candidate/updates": () => json({ vacancies: "2026-10-06T10:00:00Z", offers: "2026-10-06T11:00:00Z", seen }),
      "/candidate/updates/seen": (init) => {
        seen[JSON.parse(String(init?.body)).section] = new Date().toISOString();
        return new Response(null, { status: 204 });
      },
    });
    renderWithApp(<Probe />, "/app/vacancies");
    // данные пришли: в офферах новое, открытые вакансии отмечены на сервере
    expect(await screen.findByText("offers: true")).toBeInTheDocument();
    expect(screen.getByText("vacancies: false")).toBeInTheDocument();
    await waitFor(() => expect(marked(fetchMock)).toContain("vacancies"));
    await userEvent.click(screen.getByText("к офферам"));
    expect(await screen.findByText("offers: false")).toBeInTheDocument();
    await waitFor(() => expect(marked(fetchMock)).toContain("offers"));
  });
});
