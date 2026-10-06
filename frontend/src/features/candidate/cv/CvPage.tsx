// Стандартизированный профиль кандидата на одну страницу A4: одинаковая структура для всех,
// подтверждённое (тест, ФСП) отделено от заявленного. PDF — через печать браузера,
// как и паспорт навыков: без серверной генерации и шрифтов в образе.
import { ArrowLeft, Printer } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { useDictionaries } from "../../../api/queries";
import { errorMessage } from "../../../api/errors";
import type { AssessmentState, FspStatus, Profile } from "../../../api/types";
import { formatDate, formatSalaryRange, labels, outcomeLabel } from "../../../lib/format";
import { Alert } from "../../../ui/Alert";
import { Button } from "../../../ui/Button";
import { Logo } from "../../../ui/Logo";
import { LoadingBlock } from "../../../ui/Spinner";
import { useAssessment } from "../assessment/hooks";
import { useFspStatus } from "../fsp/hooks";
import { useProfile } from "../hooks";

export default function CvPage() {
  const profile = useProfile();
  const assessment = useAssessment();
  const fsp = useFspStatus();
  const error = profile.error ?? assessment.error ?? fsp.error;
  const ready = profile.data && assessment.data && fsp.data;
  return (
    <div className="min-h-dvh">
      <header className="no-print border-b border-line">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between gap-3 px-4 sm:px-6">
          <Link to="/app" className="inline-flex items-center gap-2 text-sm text-muted hover:text-fg">
            <ArrowLeft className="size-4" aria-hidden />В профиль
          </Link>
          <Button size="sm" onClick={() => window.print()} disabled={!ready}>
            <Printer className="size-4" aria-hidden />
            Сохранить PDF
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        {error && <Alert>{errorMessage(error)}</Alert>}
        {!error && !ready && <LoadingBlock />}
        {ready && <Cv profile={profile.data} assessment={assessment.data} fsp={fsp.data} />}
      </main>
    </div>
  );
}

type CvProps = { profile: Profile; assessment: AssessmentState; fsp: FspStatus };

function Cv({ profile: p, assessment, fsp }: CvProps) {
  const dictionaries = useDictionaries().data;
  const label = (list: { value: string; label: string }[] | undefined, keys: string[]) =>
    keys.map((k) => list?.find((o) => o.value === k)?.label ?? k).join(", ");
  const confirmed = new Set(assessment.confirmed_skills);
  const contacts = [p.contacts.telegram, p.contacts.phone, p.contacts.email].filter(Boolean).join(" · ");
  const category = assessment.category;
  const facts = [
    p.city,
    p.relocation && "готов к переезду",
    p.work_formats.map((f) => labels.workFormat[f]).join(" / "),
    p.education && labels.education[p.education],
    p.experience_years !== null && p.experience_years !== undefined && `опыт ${p.experience_years} лет`,
  ].filter(Boolean);

  return (
    <article className="flex flex-col gap-6 text-sm">
      <div className="flex items-start justify-between gap-4 border-b border-line pb-5">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight">{p.full_name ?? "Имя не указано"}</h1>
          <p className="mt-1 text-base">{p.title ?? (p.specialization ? labels.specialization[p.specialization] : "")}</p>
          {facts.length > 0 && <p className="mt-1 text-muted">{facts.join(" · ")}</p>}
          {contacts && <p className="mt-1">{contacts}</p>}
        </div>
        <Logo />
      </div>

      <Block title="Категория">
        {category ? (
          <p>
            <span className="font-medium">{category.title}</span>
            <span className="text-muted">
              {" "}
              — тест на грейд: {category.score ?? "—"} из 100
              {category.confirmed_at && `, подтверждено ${formatDate(category.confirmed_at)}`}
            </span>
          </p>
        ) : (
          <p className="text-muted">Тест на грейд ещё не пройден{p.grade && ` — заявлен грейд ${labels.grade[p.grade]}`}</p>
        )}
      </Block>

      <Block title="Достижения ФСП">
        {fsp.achievements.length === 0 ? (
          <p className="text-muted">Нет данных ФСП — навыки подтверждены тестом платформы</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {fsp.achievements.slice(0, 6).map((a) => (
              <li key={a.external_id}>
                {a.competition_title}{" "}
                <span className="text-muted">
                  · {a.discipline_title} · {a.date} · {outcomeLabel(a.place, a.stage)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Block>

      <Block title="Навыки">
        <p>
          {p.skills.map((s, i) => (
            <span key={s.slug}>
              {i > 0 && ", "}
              {confirmed.has(s.slug) ? <strong>{s.name}</strong> : s.name}
            </span>
          ))}
          {p.custom_skills.map((name, i) => (
            <span key={`own-${name}`}>
              {(p.skills.length > 0 || i > 0) && ", "}
              {name}
            </span>
          ))}
          {p.skills.length === 0 && p.custom_skills.length === 0 && <span className="text-muted">Не указаны</span>}
        </p>
        {confirmed.size > 0 && <p className="mt-1 text-xs text-muted">Жирным — подтверждены ответами теста</p>}
      </Block>

      {(p.roles.length > 0 || p.soft_skills.length > 0 || p.industries.length > 0) && (
        <Block title="Роли и качества">
          {p.roles.length > 0 && <p>Роли: {label(dictionaries?.roles, p.roles)}</p>}
          {p.soft_skills.length > 0 && <p>Софт-скиллы: {label(dictionaries?.soft_skills, p.soft_skills)}</p>}
          {p.industries.length > 0 && <p>Отрасли: {label(dictionaries?.industries, p.industries)}</p>}
        </Block>
      )}

      {(p.salary_min || p.salary_max) && (
        <Block title="Ожидания по зарплате">
          <p>{formatSalaryRange(p.salary_min, p.salary_max)} в месяц</p>
        </Block>
      )}

      {p.about && (
        <Block title="О себе">
          <p className="whitespace-pre-line leading-relaxed">{p.about}</p>
        </Block>
      )}

      <p className="border-t border-line pt-4 text-xs text-muted">
        Профиль IT Match · сформирован {formatDate(new Date().toISOString())} · категория и навыки подтверждаются
        тестом платформы и данными Федерации спортивного программирования
      </p>
    </article>
  );
}

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="break-inside-avoid">
      <h2 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted">{title}</h2>
      {children}
    </section>
  );
}
