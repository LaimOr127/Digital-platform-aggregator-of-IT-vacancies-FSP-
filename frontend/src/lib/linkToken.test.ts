import { describe, expect, it } from "vitest";
import { forgetLinkToken, readLinkToken } from "./linkToken";

describe("link token", () => {
  it("reads a well-formed token from the fragment only", () => {
    const token = "a".repeat(43);
    expect(readLinkToken(`#token=${token}`)).toBe(token);
    expect(readLinkToken("#token=short")).toBeNull();
    expect(readLinkToken("#token=bad%20token-with-space-xxxxxxxxxx")).toBeNull();
    expect(readLinkToken("")).toBeNull();
  });

  it("removes the token from the address bar", () => {
    window.history.replaceState(null, "", `/verify-email#token=${"b".repeat(43)}`);
    forgetLinkToken();
    expect(window.location.hash).toBe("");
    expect(window.location.pathname).toBe("/verify-email");
  });
});
