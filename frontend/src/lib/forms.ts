// Ошибки сервера -> поля формы; то, что не относится к полю, возвращается общим текстом.
// aliases: путь ошибки API -> имя поля формы (например, "contacts.phone" -> "phone").
import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { errorMessage, fieldErrors } from "../api/errors";

export function applyServerErrors<T extends FieldValues>(
  err: unknown,
  setError: UseFormSetError<T>,
  fields: readonly string[],
  aliases: Record<string, string> = {},
): string | null {
  const byField = fieldErrors(err);
  let unmatched = false;
  for (const [path, message] of Object.entries(byField)) {
    const field = aliases[path] ?? path;
    if (fields.includes(field)) setError(field as Path<T>, { message });
    else unmatched = true;
  }
  return Object.keys(byField).length === 0 || unmatched ? errorMessage(err) : null;
}
