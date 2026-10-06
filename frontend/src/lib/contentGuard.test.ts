import { describe, expect, it } from "vitest";
import { isScreenshotKey } from "./contentGuard";

const key = (k: string, mods: { metaKey?: boolean; shiftKey?: boolean } = {}) => ({
  key: k,
  metaKey: false,
  shiftKey: false,
  ...mods,
});

describe("isScreenshotKey", () => {
  it("recognizes screenshot shortcuts on Windows and macOS", () => {
    expect(isScreenshotKey(key("PrintScreen"))).toBe(true);
    expect(isScreenshotKey(key("S", { metaKey: true, shiftKey: true }))).toBe(true); // Win+Shift+S
    expect(isScreenshotKey(key("4", { metaKey: true, shiftKey: true }))).toBe(true); // Cmd+Shift+4
    expect(isScreenshotKey(key("$", { metaKey: true, shiftKey: true }))).toBe(true); // то же с раскладкой
  });

  it("ignores ordinary typing", () => {
    expect(isScreenshotKey(key("s"))).toBe(false);
    expect(isScreenshotKey(key("4", { shiftKey: true }))).toBe(false);
    expect(isScreenshotKey(key("c", { metaKey: true }))).toBe(false);
  });
});
