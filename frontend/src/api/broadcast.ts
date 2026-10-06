// События входа/выхода между вкладками одного браузера (BroadcastChannel).
export type AuthEvent = "login" | "logout";

const channel = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("itmatch-auth") : null;

export function broadcastAuth(event: AuthEvent): void {
  channel?.postMessage(event);
}

export function onAuthEvent(listener: (event: AuthEvent) => void): () => void {
  if (!channel) return () => undefined;
  const handler = (e: MessageEvent<AuthEvent>) => listener(e.data);
  channel.addEventListener("message", handler);
  return () => channel.removeEventListener("message", handler);
}
