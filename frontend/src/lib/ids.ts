/** Случайный ключ (Idempotency-Key). crypto.randomUUID есть только в защищённом контексте
 * (https, localhost); вне его — 128 бит из crypto.getRandomValues. */
export function randomKey(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
