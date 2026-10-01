// Публичная проверка паспорта навыков: открывается без входа по ссылке или QR-коду.
import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, Printer, ShieldAlert, ShieldX } from "lucide-react";
import type { ReactNode } from "react";
import { useParams } from "react-router";
import { ApiError, errorMessage } from "../../api/errors";
import { publicApi } from "../../api/endpoints";
import type { PassportPayload, PassportVerify } from "../../api/types";
import { formatDate, labels } from "../../lib/format";
import { Alert } from "../../ui/Alert";
import { Badge } from "../../ui/Badge";
import { Button } from "../../ui/Button";
import { Card, CardTitle } from "../../ui/Card";
import { Logo } from "../../ui/Logo";
import { QrCode } from "../../ui/QrCode";
import { LoadingBlock } from "../../ui/Spinner";

export default function PublicPassport() {
  const { id = "" } = useParams();
  const query = useQuery({ queryKey: ["public-passport", id], queryFn: () => publicApi.passport(id), retry: false });
  const notFound = query.error instanceof ApiError && (query.error.status === 404 || query.error.status === 422);

  return (
    <div className="min-h-dvh">
      <header className="no-print border-b border-line">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between px-4 sm:px-6">
          <Logo />
          {query.data && (
            <Button variant="secondary" size="sm" onClick={() => window.print()}>
              <Printer className="size-4" aria-hidden />
              Сохранить PDF
            </Button>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <p className="text-sm text-muted">Проверка паспорта навыков</p>
        {query.isPending && <LoadingBlock />}
        {query.error && (
          <div className="mt-6">
            <Alert>{notFound ? "Паспорт не найден: проверьте ссылку." : errorMessage(query.error)}</Alert>
          </div>
        )}
        {query.data && <PassportView passport={query.data} />}
      </main>
    </div>
  );
}

function Verdict({ passport }: { passport: PassportVerify }) {
  if (passport.valid) {
    return (
      <div role="status" className="flex items-start gap-3 rounded-2xl border border-accent/40 bg-accent/10 p-5">
        <BadgeCheck className="mt-0.5 size-6 shrink-0 text-accent" aria-hidden />
        <div>
          <p className="font-semibold text-accent">Подлинность подтверждена</p>
          <p className="mt-1 text-sm text-muted">
            Электронная подпись совпадает, данные не менялись с момента выпуска, паспорт действует.
          </p>
        </div>
      </div>
    );
  }
  const revoked = Boolean(passport.revoked_at);
  const Icon = revoked ? ShieldX : ShieldAlert;
  return (
    <div role="alert" className="flex items-start gap-3 rounded-2xl border border-danger/40 bg-danger/10 p-5">
      <Icon className="mt-0.5 size-6 shrink-0 text-danger" aria-hidden />
      <div>
        <p className="font-semibold text-danger">{revoked ? "Паспорт отозван" : "Подпись не совпадает"}</p>
        <p className="mt-1 text-sm text-muted">
          {revoked
            ? `Владелец отозвал паспорт ${formatDate(passport.revoked_at!)} — данные ниже больше не подтверждаются.`
            : "Данные паспорта изменены после выпуска — доверять им нельзя."}
        </p>
      </div>
    </div>
  );
}

function PassportView({ passport }: { passport: PassportVerify }) {
  const p = passport.payload as PassportPayload;
  const headline = [p.title, p.grade ? labels.grade[p.grade] : null].filter(Boolean).join(" · ");
  return (
    <div className="mt-4 flex flex-col gap-6">
      <Verdict passport={passport} />
      <Card className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{p.holder.name ?? "Имя скрыто владельцем"}</h1>
          {headline && <p className="mt-2 text-lg text-muted">{headline}</p>}
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge tone={p.verification_tier === "verified_fsp" ? "accent" : "neutral"}>
              {labels.tier[p.verification_tier]}
            </Badge>
            {p.fsp.rank && <Badge tone="info">Разряд: {p.fsp.rank}</Badge>}
            {p.fsp.athlete_id && <Badge>ФСП {p.fsp.athlete_id}</Badge>}
          </div>
        </div>
        <QrCode value={window.location.href} size={120} label="QR-код этой страницы проверки" />
      </Card>

      {p.categories.length > 0 && (
        <Section title="Категории">
          <ul className="flex flex-col gap-2">
            {p.categories.map((c) => (
              <li key={c} className="rounded-xl border border-line bg-surface-2 px-4 py-2.5 text-sm">
                {c}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {p.fsp.achievements.length > 0 && (
        <Section title="Подтверждено Федерацией спортивного программирования">
          <ul className="flex flex-col gap-3">
            {p.fsp.achievements.map((a) => (
              <li key={a.summary} className="text-sm">
                <span className="text-muted">{a.discipline}: </span>
                {a.summary}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {p.skills.length > 0 && (
        <Section title="Навыки (заявлены кандидатом)">
          <ul className="flex flex-wrap gap-2">
            {p.skills.map((s) => (
              <li key={s} className="rounded-full border border-line px-3 py-1 text-sm">
                {s}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Как проверить подпись самостоятельно">
        <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[auto_1fr]">
          <dt className="text-muted">Выпущен</dt>
          <dd>{formatDate(passport.issued_at)} · {p.issuer}</dd>
          <dt className="text-muted">Номер паспорта</dt>
          <dd className="break-all font-mono text-xs">{passport.id}</dd>
          <dt className="text-muted">Ключ (Ed25519)</dt>
          <dd className="break-all font-mono text-xs">{passport.key_id}</dd>
          <dt className="text-muted">Подпись</dt>
          <dd className="break-all font-mono text-xs">{passport.signature}</dd>
        </dl>
        <p className="mt-4 text-sm text-muted">
          Подпись покрывает каноничный JSON содержимого (ключи по алфавиту, без пробелов). Публичный ключ:{" "}
          <a className="text-accent underline" href="/api/v1/public/passport-key" target="_blank" rel="noopener noreferrer">
            /api/v1/public/passport-key
          </a>
          , данные паспорта:{" "}
          <a className="text-accent underline" href={`/api/v1/public/passport/${passport.id}`} target="_blank" rel="noopener noreferrer">
            JSON
          </a>
          .
        </p>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <CardTitle>{title}</CardTitle>
      <div className="mt-4">{children}</div>
    </Card>
  );
}
