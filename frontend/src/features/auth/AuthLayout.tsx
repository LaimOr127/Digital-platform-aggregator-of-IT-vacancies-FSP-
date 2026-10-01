import { BadgeCheck, EyeOff, Scale } from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { Logo } from "../../ui/Logo";

const points = [
  { icon: BadgeCheck, text: "Навыки подтверждаются результатами соревнований ФСП" },
  { icon: Scale, text: "Каждое предложение — с зарплатной вилкой" },
  { icon: EyeOff, text: "Контакты открываются только с вашего согласия" },
];

type Props = { title: string; subtitle?: ReactNode; children: ReactNode };

/** Общая разметка страниц входа, регистрации и операций по почте. */
export function AuthLayout({ title, subtitle, children }: Props) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <aside className="relative hidden flex-col justify-between overflow-hidden border-r border-line bg-surface p-10 lg:flex">
        <div aria-hidden className="absolute -bottom-40 -left-20 size-[32rem] rounded-full bg-accent/10 blur-3xl" />
        <Logo />
        <div className="relative">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight">
            Работодатель приходит к вам
            <br />с вакансией и зарплатой
          </h2>
          <ul className="mt-8 flex flex-col gap-4">
            {points.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-muted">
                <Icon className="size-5 shrink-0 text-accent" aria-hidden />
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-muted">Трек Федерации спортивного программирования</p>
      </aside>

      <main className="flex flex-col px-4 py-8 sm:px-10">
        <div className="lg:hidden">
          <Logo />
        </div>
        <motion.div
          key={title}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="m-auto w-full max-w-md py-10"
        >
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-muted">{subtitle}</p>}
          <div className="mt-8">{children}</div>
        </motion.div>
      </main>
    </div>
  );
}
