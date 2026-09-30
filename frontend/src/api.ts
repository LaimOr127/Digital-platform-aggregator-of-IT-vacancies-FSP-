// Единая точка обращения к API. В фазе 1 заменяется клиентом, сгенерированным из OpenAPI.
export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`/api/v1${path}`, { credentials: "same-origin" });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return (await res.json()) as T;
}
