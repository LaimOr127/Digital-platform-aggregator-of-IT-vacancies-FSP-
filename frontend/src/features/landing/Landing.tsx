import { ArrowRight, BadgeCheck, Building2, CalendarClock, EyeOff, Scale, ShieldCheck, UserRound } from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { useAuth } from "../../auth/AuthProvider";
import { portalPath } from "../../auth/portal";
import { Badge } from "../../ui/Badge";
import { Logo } from "../../ui/Logo";

const primaryLink =
  "inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-accent px-6 font-medium text-on-accent transition-colors hover:bg-accent-strong";
const secondaryLink =
  "inline-flex h-12 items-center justify-center gap-2 rounded-lg border border-line bg-surface-2 px-6 font-medium transition-colors hover:border-muted/60";

const steps = {
  candidate: [
    "Отвечаете на опрос: специализация, стек, грейд. Профиль можно заполнить из резюме.",
    "Проходите тест на свой грейд — и попадаете в категорию. Аккаунт ФСП поднимает вас внутри неё.",
    "Компании сами приглашают вас с описанием и вилкой. Пока приглашений нет — откликайтесь сами.",
  ],
  employer: [
    "Описываете, кого ищете: специализация, грейд, стек — вакансией или черновиком.",
    "Получаете подборку из категории: выше — лучший результат теста и достижения ФСП, у каждого «Почему».",
    "Видите анонимные карточки с результатом теста и приглашаете с вилкой. Контакты — после согласия кандидата.",
  ],
};

const principles = [
  { icon: Scale, title: "Вилка обязательна", text: "Без зарплаты вакансию не опубликовать, оффер без вилки не отправить." },
  { icon: CalendarClock, title: "Вакансия живёт 14 дней", text: "Далее компания подтверждает её или закрывает." },
  { icon: EyeOff, title: "Анонимность до согласия", text: "Имя и контакты кандидата открываются, только когда он примет приглашение." },
  { icon: ShieldCheck, title: "Только проверенные компании", text: "Каждая компания проходит модерацию, заблокированные теряют доступ." },
];

function fadeUp(delay = 0) {
  return {
    initial: { opacity: 0, y: 16 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, margin: "-60px" },
    transition: { duration: 0.45, ease: "easeOut" as const, delay },
  };
}

export function Landing() {
  const auth = useAuth();
  return (
    <div className="min-h-dvh overflow-x-clip">
      <header className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <nav className="flex items-center gap-2 text-sm">
          {auth.status === "authenticated" ? (
            <Link to={portalPath(auth.user.role)} className="rounded-lg bg-surface-2 px-4 py-2 font-medium hover:bg-line">
              В кабинет
            </Link>
          ) : (
            <>
              <Link to="/login" className="rounded-lg px-3 py-2 text-muted hover:text-fg">
                Войти
              </Link>
              <Link to="/register" className="rounded-lg bg-surface-2 px-4 py-2 font-medium hover:bg-line">
                Регистрация
              </Link>
            </>
          )}
        </nav>
      </header>

      <section className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 pb-20 pt-12 sm:px-6 lg:grid-cols-[1.15fr_1fr] lg:pt-20">
        <div aria-hidden className="pointer-events-none absolute -top-40 left-1/3 -z-10 size-[36rem] rounded-full bg-accent/10 blur-3xl" />
        <motion.div {...fadeUp()}>
          <Badge tone="accent">
            <BadgeCheck className="size-3.5" aria-hidden />
            Профиль, подтверждённый ФСП
          </Badge>
          <h1 className="mt-5 text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
            Не рассылайте отклики.
            <br />
            <span className="text-accent">Работа найдёт вас сама.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
            Результаты соревнований Федерации спортивного программирования подтверждают навыки. Работодатель выбирает
            категорию и сам приходит к кандидату — с вакансией и зарплатой.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link to="/register?role=candidate" className={primaryLink}>
              <UserRound className="size-4" aria-hidden />Я ищу работу
            </Link>
            <Link to="/register?role=employer" className={secondaryLink}>
              <Building2 className="size-4" aria-hidden />Я нанимаю
            </Link>
          </div>
        </motion.div>
        <motion.div {...fadeUp(0.15)}>
          <SampleCard />
        </motion.div>
      </section>

      <section aria-labelledby="how" className="border-y border-line bg-white/5">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <motion.h2 id="how" {...fadeUp()} className="text-3xl font-semibold tracking-tight">
            Обратная механика подбора
          </motion.h2>
          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <Steps title="Кандидату" icon={<UserRound className="size-5" />} items={steps.candidate} />
            <Steps title="Работодателю" icon={<Building2 className="size-5" />} items={steps.employer} delay={0.1} />
          </div>
        </div>
      </section>

      <section aria-labelledby="fair" className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <motion.h2 id="fair" {...fadeUp()} className="text-3xl font-semibold tracking-tight">
          Честный найм — правило платформы
        </motion.h2>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {principles.map(({ icon: Icon, title, text }, i) => (
            <motion.article key={title} {...fadeUp(i * 0.06)} className="rounded-2xl border border-line bg-surface p-5">
              <Icon className="size-5 text-accent" aria-hidden />
              <h3 className="mt-4 font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{text}</p>
            </motion.article>
          ))}
        </div>
        <motion.div {...fadeUp()} className="mt-14 flex flex-col items-start gap-4 rounded-2xl border border-accent/30 bg-accent/5 p-8 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-xl font-semibold">Начните с профиля — это пять минут</h3>
            <p className="mt-1 text-sm text-muted">Компании увидят вас анонимно, контакты — только с вашего согласия.</p>
          </div>
          <Link to="/register?role=candidate" className={primaryLink}>
            Создать профиль <ArrowRight className="size-4" aria-hidden />
          </Link>
        </motion.div>
      </section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-8 text-sm text-muted sm:px-6">
          <span>IT Match</span>
          <a href="/api-docs/" className="hover:text-fg">
            Документация API
          </a>
        </div>
      </footer>
    </div>
  );
}

function Steps({ title, icon, items, delay = 0 }: { title: string; icon: ReactNode; items: string[]; delay?: number }) {
  return (
    <motion.div {...fadeUp(delay)} className="rounded-2xl border border-line bg-surface p-6">
      <div className="flex items-center gap-3">
        <span className="grid size-10 place-items-center rounded-xl bg-accent/10 text-accent" aria-hidden>
          {icon}
        </span>
        <h3 className="text-lg font-semibold">{title}</h3>
      </div>
      <ol className="mt-6 flex flex-col gap-4">
        {items.map((text, i) => (
          <li key={text} className="flex gap-4">
            <span className="grid size-7 shrink-0 place-items-center rounded-full border border-line text-sm tabular text-muted">
              {i + 1}
            </span>
            <p className="pt-0.5 text-sm leading-relaxed">{text}</p>
          </li>
        ))}
      </ol>
    </motion.div>
  );
}

/** Иллюстрация: так работодатель видит кандидата в каталоге (пример, не реальные данные). */
function SampleCard() {
  return (
    <figure className="relative mx-auto max-w-md">
      <div className="rounded-2xl border border-line bg-surface p-6 shadow-2xl shadow-black/40">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted">Кандидат · анонимно</span>
          <Badge tone="accent">
            <BadgeCheck className="size-3.5" aria-hidden />
            Подтверждено ФСП
          </Badge>
        </div>
        <p className="mt-4 text-xl font-semibold">Backend-разработчик · Middle</p>
        <p className="mt-1 text-sm text-muted">Удалённо · ожидания 250–320 тыс. ₽</p>
        <div className="mt-5 flex flex-wrap gap-2">
          {["Python", "Go", "PostgreSQL", "Алгоритмы"].map((s) => (
            <span key={s} className="rounded-full border border-line px-3 py-1 text-sm">
              {s}
            </span>
          ))}
        </div>
        <div className="mt-5 rounded-xl bg-surface-2 p-4 text-sm">
          <p className="text-muted">Достижения ФСП</p>
          <p className="mt-1">Призёр всероссийских соревнований, продуктовое программирование</p>
        </div>
        <div className="mt-5 flex h-11 items-center justify-center rounded-lg bg-accent font-medium text-on-accent">
          Предложить оффер
        </div>
      </div>
      <figcaption className="mt-3 text-center text-xs text-muted">Пример карточки в каталоге работодателя</figcaption>
    </figure>
  );
}
