// Удаление аккаунта по 152-ФЗ: необратимо, подтверждается паролем; после — выход из кабинета.
import { useMutation } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { candidateApi } from "../../api/endpoints";
import { ApiError, errorMessage } from "../../api/errors";
import { useAuth } from "../../auth/AuthProvider";
import { Button } from "../../ui/Button";
import { Card, CardTitle } from "../../ui/Card";
import { Dialog } from "../../ui/Dialog";
import { Field, Input } from "../../ui/form";
import { useToast } from "../../ui/Toast";

const REMOVED = [
  "профиль, резюме и контакты",
  "привязка ФСП и паспорт навыков — ссылки на него перестанут проверяться",
  "собеседования и офферы — они исчезнут и из кабинетов компаний",
];

export function DeleteAccountCard() {
  const [open, setOpen] = useState(false);
  return (
    <Card className="border-danger/30">
      <CardTitle>Удаление аккаунта</CardTitle>
      <p className="mt-2 text-sm leading-relaxed text-muted">
        Удалим аккаунт и все ваши данные без возможности восстановления.
      </p>
      <Button variant="danger" className="mt-4 w-full" onClick={() => setOpen(true)}>
        <Trash2 className="size-4" aria-hidden />
        Удалить аккаунт
      </Button>
      <DeleteDialog open={open} onClose={() => setOpen(false)} />
    </Card>
  );
}

function DeleteDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const auth = useAuth();
  const notify = useToast();
  const [password, setPassword] = useState("");
  const [fieldError, setFieldError] = useState<string>();
  const remove = useMutation({ mutationFn: candidateApi.deleteAccount });

  const close = () => {
    setPassword("");
    setFieldError(undefined);
    onClose();
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!password) return setFieldError("Введите пароль");
    try {
      await remove.mutateAsync(password);
    } catch (err) {
      if (err instanceof ApiError && err.code === "wrong_password") setFieldError("Неверный пароль");
      else notify(errorMessage(err), "error");
      return;
    }
    notify("Аккаунт и данные удалены");
    // сервер уже завершил сессию: выход только очищает её в браузере и во вкладках
    await auth.signOut().catch(() => undefined);
  };

  return (
    <Dialog open={open} title="Удалить аккаунт?" onClose={close} busy={remove.isPending}>
      <form onSubmit={submit} noValidate>
        <p className="text-sm text-muted">Будут удалены без возможности восстановления:</p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
          {REMOVED.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <Field label="Пароль для подтверждения" error={fieldError} className="mt-5">
          <Input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              setFieldError(undefined);
            }}
          />
        </Field>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="ghost" onClick={close} disabled={remove.isPending}>
            Отмена
          </Button>
          <Button type="submit" variant="danger" loading={remove.isPending}>
            Удалить навсегда
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
