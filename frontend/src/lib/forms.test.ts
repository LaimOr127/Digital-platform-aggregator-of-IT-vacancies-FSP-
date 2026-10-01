import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/errors";
import { applyServerErrors } from "./forms";

describe("applyServerErrors", () => {
  it("puts field errors on known fields and returns no general message", () => {
    const setError = vi.fn();
    const err = new ApiError(422, "validation_error", "Некорректные данные", [{ loc: ["body", "email"], msg: "плохой email" }]);
    expect(applyServerErrors(err, setError, ["email"])).toBeNull();
    expect(setError).toHaveBeenCalledWith("email", { message: "плохой email" });
  });

  it("returns API message for non-field errors", () => {
    const err = new ApiError(409, "conflict", "email уже зарегистрирован");
    expect(applyServerErrors(err, vi.fn(), ["email"])).toBe("email уже зарегистрирован");
  });

  it("returns general message when a field is unknown to the form", () => {
    const err = new ApiError(422, "validation_error", "Некорректные данные", [{ loc: ["body", "other"], msg: "x" }]);
    expect(applyServerErrors(err, vi.fn(), ["email"])).toBe("Некорректные данные");
  });

  it("maps API paths to form fields via aliases", () => {
    const setError = vi.fn();
    const err = new ApiError(422, "validation_error", "x", [{ loc: ["body", "contacts", "phone"], msg: "длинный" }]);
    expect(applyServerErrors(err, setError, ["phone"], { "contacts.phone": "phone" })).toBeNull();
    expect(setError).toHaveBeenCalledWith("phone", { message: "длинный" });
  });

  it("handles network errors", () => {
    expect(applyServerErrors(new TypeError("offline"), vi.fn(), [])).toBe("Не удалось связаться с сервером");
  });
});
