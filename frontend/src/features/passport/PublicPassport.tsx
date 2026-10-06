// Публичная проверка паспорта навыков: открывается без входа по ссылке или QR-коду.
import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";
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
import { Verdict } from "./Verdict";

export default function PublicPassport() {
  const { id = "" } = useParams();
  const query = useQuery({ queryKey: ["public-passport", id], queryFn: () => publicApi.passport(id), retry: false });
  const notFound = query.error instanceof ApiError && (query.error.status === 404 || query.error.status === 422);

  return (
    <div className="min-h-dvh">
      <header className="no-print border-b border-line">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between px-4 sm:px-6">
          <Logo />
          {query.data?.payload && (
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

function PassportView({ passport }: { passport: PassportVerify }) {
  const p = passport.payload as PassportPayload | null;
  if (!p) {
    return (
      <div className="mt-4">
        <Verdict passport={passport} verifiedByFsp={false} />
      </div>
    );
  }
  const verified = p.verification_tier === "verified_fsp";
  const declared = [p.title, p.grade ? labels.grade[p.grade] : null].filter(Boolean).join(" · ");
  return (
    <div className="mt-4 flex flex-col gap-6">
      {p.demo && (
        <Alert tone="warn">Паспорт выпущен на демо-стенде: данные ФСП тестовые, для найма не используются.</Alert>
      )}
      <Verdict passport={passport} verifiedByFsp={verified} />
      <Card className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{p.holder.name ?? "Имя скрыто владельцем"}</h1>
          <p className="mt-1 text-sm text-muted">{holderNote(p)}</p>
          {declared && (
            <p className="mt-3 text-lg">
              {declared} <span className="text-sm text-muted">· заявлено кандидатом</span>
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge tone={verified ? "success" : "neutral"}>{labels.tier[p.verification_tier]}</Badge>
            {p.fsp.rank && <Badge tone="info">Разряд: {p.fsp.rank}</Badge>}
            {p.fsp.athlete_id && <Badge>ФСП {p.fsp.athlete_id}</Badge>}
          </div>
        </div>
        <QrCode value={window.location.href} size={120} label="QR-код этой страницы проверки" />
      </Card>

      {!p.holder.name && (
        <Alert tone="info">
          Анонимный паспорт подтверждает навыки, но не удостоверяет личность того, кто его показывает. Попросите
          кандидата выпустить паспорт с именем или подтвердить его в кабинете.
        </Alert>
      )}

      {p.categories.length > 0 && (
        <Section title="Категории (по данным ФСП)">
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
            {p.fsp.achievements.map((a, i) => (
              <li key={i} className="text-sm">
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
          <dd>
            {formatDate(passport.issued_at)} · {p.issuer}
          </dd>
          {p.expires_at && (
            <>
              <dt className="text-muted">Действует до</dt>
              <dd>{formatDate(p.expires_at)}</dd>
            </>
          )}
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

function holderNote(p: PassportPayload): string {
  if (!p.holder.name) return "Анонимный паспорт";
  return p.holder.source === "fsp" ? "Имя подтверждено ФСП" : "Имя указано кандидатом, ФСП не подтверждено";
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <CardTitle>{title}</CardTitle>
      <div className="mt-4">{children}</div>
    </Card>
  );
}
