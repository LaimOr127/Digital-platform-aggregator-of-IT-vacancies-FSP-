import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { isScreenshotKey, useFocusGuard } from "./contentGuard";

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

describe("useFocusGuard", () => {
  it("hides the tasks while the window is inactive and counts each leave once", () => {
    const { result } = renderHook(() => useFocusGuard());
    act(() => {
      window.dispatchEvent(new Event("blur"));
      window.dispatchEvent(new Event("blur")); // один уход — одно событие, даже если пришло дважды
    });
    expect(result.current).toEqual({ hidden: true, leaves: 1 });
    act(() => window.dispatchEvent(new Event("focus")));
    expect(result.current.hidden).toBe(false);
    act(() => window.dispatchEvent(new Event("blur")));
    expect(result.current.leaves).toBe(2);
  });
});
