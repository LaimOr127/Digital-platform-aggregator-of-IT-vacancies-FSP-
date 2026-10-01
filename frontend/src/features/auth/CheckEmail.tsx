import { MailCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { authApi } from "../../api/endpoints";
import { errorMessage } from "../../api/errors";
import { Alert } from "../../ui/Alert";
import { Button } from "../../ui/Button";

const COOLDOWN_SECONDS = 60;

/** Повтор письма подтверждения с паузой: не даёт засыпать ящик письмами. */
function useResendVerification(email: string) {
  const [left, setLeft] = useState(0);
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => {
    if (left <= 0) return;
    const timer = setTimeout(() => setLeft((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [left]);

  const resend = async () => {
    setPending(true);
    try {
      await authApi.resendVerification(email);
      setNotice({ text: "Письмо отправлено ещё раз", ok: true });
      setLeft(COOLDOWN_SECONDS);
    } catch (err) {
      setNotice({ text: errorMessage(err), ok: false });
    } finally {
      setPending(false);
    }
  };
  return { resend, pending, notice, left };
}

export function ResendButton({ email }: { email: string }) {
  const { resend, pending, notice, left } = useResendVerification(email);
  return (
    <div className="flex flex-col gap-3">
      {notice && <Alert tone={notice.ok ? "info" : "danger"}>{notice.text}</Alert>}
      <Button variant="secondary" onClick={resend} loading={pending} disabled={left > 0}>
        {left > 0 ? `Отправить ещё раз через ${left} с` : "Отправить письмо ещё раз"}
      </Button>
    </div>
  );
}

/** Экран после регистрации: вход откроется, когда адрес будет подтверждён. */
export function CheckEmail({ email }: { email: string }) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start gap-3 rounded-xl border border-accent/30 bg-accent/5 p-4 text-sm">
        <MailCheck className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
        <div>
          <p className="font-medium">Проверьте почту</p>
          <p className="mt-1 text-muted">
            Мы отправили письмо на <span className="break-all text-fg">{email}</span>. Откройте ссылку в нём, чтобы
            подтвердить адрес и войти. Ссылка действует 24 часа.
          </p>
        </div>
      </div>
      <p className="text-xs text-muted">Письма нет? Проверьте папку «Спам» или отправьте его ещё раз.</p>
      <ResendButton email={email} />
    </div>
  );
}
