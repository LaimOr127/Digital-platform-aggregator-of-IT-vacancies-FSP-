import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { json, renderWithApp, serveRoutes } from "../test/render";
import { useNews } from "./news";

vi.mock("../auth/AuthProvider", () => ({ useAuth: () => ({ status: "authenticated", user: { id: "u1" } }) }));

const PATHS = { vacancies: "/app/vacancies", offers: "/app/offers" };
const fetchUpdates = () => fetch("/candidate/updates").then((r) => r.json());

function Probe() {
  const news = useNews("test", fetchUpdates, PATHS);
  return (
    <>
      <p>vacancies: {String(news["/app/vacancies"])}</p>
      <p>offers: {String(news["/app/offers"])}</p>
      <Link to="/app/offers">к офферам</Link>
    </>
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("useNews", () => {
  it("lights sections with events and clears the one the user opens", async () => {
    serveRoutes({ "/candidate/updates": () => json({ vacancies: "2026-10-06T10:00:00Z", offers: "2026-10-06T11:00:00Z" }) });
    renderWithApp(<Probe />, "/app/vacancies");
    // открытый раздел просмотрен, в другом — новое
    expect(await screen.findByText("offers: true")).toBeInTheDocument();
    expect(screen.getByText("vacancies: false")).toBeInTheDocument();
    await userEvent.click(screen.getByText("к офферам"));
    expect(await screen.findByText("offers: false")).toBeInTheDocument();
  });

  it("stays quiet when nothing happened", async () => {
    serveRoutes({ "/candidate/updates": () => json({ vacancies: null, offers: null }) });
    renderWithApp(<Probe />, "/");
    expect(await screen.findByText("offers: false")).toBeInTheDocument();
    expect(screen.getByText("vacancies: false")).toBeInTheDocument();
  });
});
