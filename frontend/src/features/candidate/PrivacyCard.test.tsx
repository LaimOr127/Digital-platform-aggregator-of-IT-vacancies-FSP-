import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithApp } from "../../test/render";
import { PrivacyCard } from "./PrivacyCard";

vi.mock("../../auth/AuthProvider", () => ({ useAuth: () => ({ user: { consent_at: "2026-10-01T09:00:00Z" } }) }));

const profile = { show_salary: true, show_fsp: true, show_about: false };

describe("PrivacyCard", () => {
  it("shows when consent was given and how to withdraw it", () => {
    renderWithApp(<PrivacyCard profile={profile as never} />);
    expect(screen.getByText(/Согласие на обработку и публикацию данных профиля дано 1 окт\.? 2026/)).toBeInTheDocument();
    expect(screen.getByText(/отозвать согласие/)).toBeInTheDocument();
  });
});
