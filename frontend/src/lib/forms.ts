// Ошибки сервера -> поля формы; то, что не относится к полю, возвращается общим текстом.
import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { errorMessage, fieldErrors } from "../api/errors";

export function applyServerErrors<T extends FieldValues>(
  err: unknown,
  setError: UseFormSetError<T>,
  fields: readonly string[],
): string | null {
  const byField = fieldErrors(err);
  let unmatched = false;
  for (const [field, message] of Object.entries(byField)) {
    if (fields.includes(field)) setError(field as Path<T>, { message });
    else unmatched = true;
  }
  return Object.keys(byField).length === 0 || unmatched ? errorMessage(err) : null;
}
