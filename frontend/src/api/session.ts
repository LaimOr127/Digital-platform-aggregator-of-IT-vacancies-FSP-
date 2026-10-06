// Access-токен живёт только в памяти (не в localStorage): XSS не может его сохранить надолго,
// а после перезагрузки страницы сессия восстанавливается через refresh-cookie.
type Listener = () => void;

let accessToken: string | null = null;
const listeners = new Set<Listener>();

function notify() {
  listeners.forEach((listener) => listener());
}

export const session = {
  get: () => accessToken,
  set(token: string) {
    accessToken = token;
    notify();
  },
  clear() {
    accessToken = null;
    notify();
  },
  subscribe(listener: Listener) {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
};
