import { BadgeCheck, Clock, KeyRound, ShieldAlert, ShieldX } from "lucide-react";
import type { PassportVerify } from "../../api/types";
import { formatDate } from "../../lib/format";

type Tone = "ok" | "warn" | "bad";

const TONES: Record<Tone, string> = {
  ok: "border-accent/40 bg-accent/10 [&_.title]:text-accent [&_svg]:text-accent",
  warn: "border-warn/40 bg-warn/10 [&_.title]:text-warn [&_svg]:text-warn",
  bad: "border-danger/40 bg-danger/10 [&_.title]:text-danger [&_svg]:text-danger",
};

function describe(p: PassportVerify, verifiedByFsp: boolean) {
  switch (p.status) {
    case "valid":
      return {
        tone: "ok" as Tone,
        Icon: BadgeCheck,
        title: "Подпись подлинная, паспорт действует",
        text: verifiedByFsp
          ? "Данные не менялись с момента выпуска. Достижения подтверждены ФСП; должность, грейд и навыки указаны кандидатом."
          : "Данные не менялись с момента выпуска, но указаны кандидатом и не подтверждены ФСП.",
      };
    case "revoked":
      return {
        tone: "bad" as Tone,
        Icon: ShieldX,
        title: "Паспорт отозван",
        text: `Владелец отозвал паспорт ${p.revoked_at ? formatDate(p.revoked_at) : ""} — его данные больше не показываются и не подтверждаются.`,
      };
    case "expired":
      return { tone: "warn" as Tone, Icon: Clock, title: "Срок действия истёк", text: "Попросите кандидата выпустить новый паспорт." };
    case "unknown_key":
      return {
        tone: "warn" as Tone,
        Icon: KeyRound,
        title: "Подписан неактуальным ключом",
        text: "Паспорт выпущен до смены ключа подписи — подтвердить его сейчас нельзя. Попросите кандидата перевыпустить паспорт.",
      };
    default:
      return {
        tone: "bad" as Tone,
        Icon: ShieldAlert,
        title: "Подпись не совпадает",
        text: "Данные паспорта изменены после выпуска — доверять им нельзя.",
      };
  }
}

/** Итог проверки подлинности паспорта. */
export function Verdict({ passport, verifiedByFsp }: { passport: PassportVerify; verifiedByFsp: boolean }) {
  const { tone, Icon, title, text } = describe(passport, verifiedByFsp);
  return (
    <div role={tone === "ok" ? "status" : "alert"} className={`flex items-start gap-3 rounded-2xl border p-5 ${TONES[tone]}`}>
      <Icon className="mt-0.5 size-6 shrink-0" aria-hidden />
      <div>
        <p className="title font-semibold">{title}</p>
        <p className="mt-1 text-sm text-muted">{text}</p>
      </div>
    </div>
  );
}
