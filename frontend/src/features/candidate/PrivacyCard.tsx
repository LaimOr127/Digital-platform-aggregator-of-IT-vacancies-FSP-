// Приватность: что из анонимной карточки видит работодатель. Сохраняется сразу.
import type { Profile } from "../../api/types";
import { Card, CardTitle } from "../../ui/Card";
import { Switch } from "../../ui/form";
import { useAction } from "../../ui/useAction";
import { useUpdateProfile } from "./hooks";

const OPTIONS = [
  { field: "show_salary", label: "Ожидания по зарплате", description: "Скрытые ожидания не влияют на подбор" },
  { field: "show_fsp", label: "Достижения ФСП", description: "Уровень подтверждения виден всегда" },
  { field: "show_about", label: "Раздел «О себе»", description: "Текст не участвует в подборе, если скрыт" },
] as const;

export function PrivacyCard({ profile }: { profile: Profile }) {
  const update = useUpdateProfile();
  const run = useAction();
  return (
    <Card>
      <CardTitle>Что видит работодатель</CardTitle>
      <p className="mt-1 text-sm text-muted">Имя и контакты — только после того, как вы примете приглашение или откликнетесь.</p>
      <div className="mt-4 flex flex-col gap-4">
        {OPTIONS.map((o) => (
          <Switch
            key={o.field}
            label={o.label}
            description={o.description}
            checked={profile[o.field]}
            disabled={update.isPending}
            onChange={(e) => run(update, { [o.field]: e.target.checked }, "Настройки приватности сохранены")}
          />
        ))}
      </div>
    </Card>
  );
}
