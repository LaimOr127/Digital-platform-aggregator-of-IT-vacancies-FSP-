import { afterEach, describe, expect, it, vi } from "vitest";
import { randomKey } from "./ids";

describe("randomKey", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("is unique", () => {
    expect(randomKey()).not.toBe(randomKey());
  });

  it("falls back to getRandomValues outside a secure context", () => {
    // вне https/localhost браузер не даёт randomUUID
    vi.stubGlobal("crypto", { getRandomValues: crypto.getRandomValues.bind(crypto) });
    expect(randomKey()).toMatch(/^[0-9a-f]{32}$/);
  });
});
