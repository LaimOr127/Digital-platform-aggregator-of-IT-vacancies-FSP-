import { BadgeCheck, CircleCheck, CircleDashed, Link2 } from "lucide-react";
import { motion } from "motion/react";
import { useSkills } from "../../api/queries";
import type { Profile } from "../../api/types";
import { errorMessage } from "../../api/errors";
import { labels } from "../../lib/format";
import { Alert } from "../../ui/Alert";
import { AppShell, PageHeader } from "../../ui/AppShell";
import { Badge } from "../../ui/Badge";
import { Card, CardTitle } from "../../ui/Card";
import { Spinner } from "../../ui/Spinner";
import { CHECKS, completeness } from "./completeness";
import { useProfile } from "./hooks";
import { ProfileForm } from "./ProfileForm";

export default function CandidatePortal() {
  const profile = useProfile();
  const skills = useSkills();
  const error = profile.error ?? skills.error;

  return (
    <AppShell>
      <PageHeader
        title="Мой профиль"
        text="Работодатели видят профиль анонимно и приходят к вам сами — с вакансией и зарплатной вилкой."
      />
      {error && <Alert>{errorMessage(error)}</Alert>}
      {!error && (!profile.data || !skills.data) && (
        <div className="flex justify-center py-20 text-muted">
          <Spinner className="size-6" />
        </div>
      )}
      {profile.data && skills.data && (
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <ProfileForm profile={profile.data} skills={skills.data} />
          <aside className="flex flex-col gap-6 lg:sticky lg:top-24">
            <StatusCard profile={profile.data} />
            <PassportCard />
          </aside>
        </div>
      )}
    </AppShell>
  );
}

function StatusCard({ profile }: { profile: Profile }) {
  const { percent } = completeness(profile);
  const verified = profile.verification_tier === "verified_fsp";
  return (
    <Card>
      <div className="flex items-center justify-between">
        <CardTitle>Статус профиля</CardTitle>
        {profile.is_hidden ? <Badge tone="warn">Скрыт</Badge> : <Badge tone="accent">В каталоге</Badge>}
      </div>
      <div className="mt-5">
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-muted">Заполненность</span>
          <span className="font-semibold tabular">{percent}%</span>
        </div>
        <div
          className="mt-2 h-2 overflow-hidden rounded-full bg-surface-2"
          role="progressbar"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Заполненность профиля"
        >
          <motion.div
            className="h-full rounded-full bg-accent"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: percent / 100 }}
            style={{ originX: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        </div>
      </div>
      <ul className="mt-5 flex flex-col gap-2 text-sm">
        {CHECKS.map((check) => {
          const done = check.done(profile);
          const Icon = done ? CircleCheck : CircleDashed;
          return (
            <li key={check.label} className={done ? "flex items-center gap-2" : "flex items-center gap-2 text-muted"}>
              <Icon className={done ? "size-4 text-accent" : "size-4"} aria-hidden />
              {check.label}
              <span className="sr-only">{done ? "— заполнено" : "— не заполнено"}</span>
            </li>
          );
        })}
      </ul>
      <div className="mt-5 border-t border-line pt-4 text-sm">
        <span className="text-muted">Уровень подтверждения: </span>
        <span className={verified ? "text-accent" : undefined}>{labels.tier[profile.verification_tier]}</span>
      </div>
    </Card>
  );
}

function PassportCard() {
  return (
    <Card className="border-accent/30 bg-accent/5">
      <BadgeCheck className="size-6 text-accent" aria-hidden />
      <CardTitle className="mt-3">Паспорт навыков</CardTitle>
      <p className="mt-2 text-sm leading-relaxed text-muted">
        Привяжите аккаунт ФСП — результаты соревнований подтвердят навыки, а профиль получит отметку «Подтверждено ФСП».
      </p>
      <button
        type="button"
        disabled
        className="mt-4 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-line text-sm text-muted"
      >
        <Link2 className="size-4" aria-hidden />
        Привязка ФСП — на следующем этапе
      </button>
    </Card>
  );
}
