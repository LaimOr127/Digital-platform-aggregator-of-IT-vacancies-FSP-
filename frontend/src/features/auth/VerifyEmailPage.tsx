import { useMutation } from "@tanstack/react-query";
import { MailCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { authApi } from "../../api/endpoints";
import { errorMessage } from "../../api/errors";
import { forgetLinkToken, readLinkToken } from "../../lib/linkToken";
import { Button } from "../../ui/Button";
import { AuthLayout } from "./AuthLayout";
import { StatusPanel } from "./StatusPanel";

const RETRY = "Войдите с email и паролем — на экране входа можно отправить новое письмо.";

/** Подтверждение почты по ссылке из письма. Только по нажатию кнопки: почтовые сканеры,
 * открывающие ссылки сами, не подтвердят чужой аккаунт. */
export default function VerifyEmailPage() {
  const [token] = useState(() => readLinkToken());
  useEffect(forgetLinkToken, []);
  const verify = useMutation({ mutationFn: authApi.verifyEmail });

  return (
    <AuthLayout title="Подтверждение почты">
      {!token && (
        <StatusPanel ok={false} title="Ссылка неполная" action={{ to: "/login", label: "Ко входу" }}>
          Откройте ссылку из письма целиком. {RETRY}
        </StatusPanel>
      )}
      {token && verify.isSuccess && (
        <StatusPanel ok title="Почта подтверждена" action={{ to: "/login", label: "Войти" }}>
          Теперь можно войти в аккаунт с вашим email и паролем.
        </StatusPanel>
      )}
      {token && verify.isError && (
        <StatusPanel ok={false} title="Не удалось подтвердить" action={{ to: "/login", label: "Ко входу" }}>
          {errorMessage(verify.error)}. {RETRY}
        </StatusPanel>
      )}
      {token && verify.isIdle && (
        <div className="flex flex-col gap-5">
          <div className="flex items-start gap-3 text-sm text-muted">
            <MailCheck className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
            Осталось подтвердить, что это ваш адрес.
          </div>
          <Button size="lg" onClick={() => verify.mutate(token)}>
            Подтвердить почту
          </Button>
        </div>
      )}
      {token && verify.isPending && (
        <Button size="lg" loading>
          Подтверждаем…
        </Button>
      )}
    </AuthLayout>
  );
}
