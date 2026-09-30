// Единый формат ошибок API: {"error": {"code", "message", "details"?}}.
export type ErrorDetail = { loc: (string | number)[]; msg: string };

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: ErrorDetail[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    const { code, message, details } = body.error ?? {};
    if (typeof code === "string") return new ApiError(res.status, code, message ?? code, details ?? []);
  } catch {
    // не JSON (например, ошибка прокси) — ниже общий ответ
  }
  return new ApiError(res.status, `http_${res.status}`, "Сервис временно недоступен");
}

/** Ошибки валидации тела запроса -> {поле: сообщение} для формы. */
export function fieldErrors(err: unknown): Record<string, string> {
  if (!(err instanceof ApiError)) return {};
  const result: Record<string, string> = {};
  for (const detail of err.details) {
    const [where, field] = detail.loc;
    if (where === "body" && typeof field === "string" && !(field in result)) result[field] = detail.msg;
  }
  return result;
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "Не удалось связаться с сервером";
}
