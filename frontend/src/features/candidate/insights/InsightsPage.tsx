import { TrendingUp } from "lucide-react";
import { Link } from "react-router";
import { ApiError, errorMessage } from "../../../api/errors";
import { Alert } from "../../../ui/Alert";
import { PageHeader } from "../../../ui/AppShell";
import { buttonClasses } from "../../../ui/Button";
import { EmptyState } from "../../../ui/EmptyState";
import { LoadingBlock } from "../../../ui/Spinner";
import { GrowthCard } from "./GrowthCard";
import { useGrowth, useSalaryRadar } from "./hooks";
import { LadderCard, SalaryCard } from "./SalaryCard";

export function InsightsPage() {
  const radar = useSalaryRadar();
  const growth = useGrowth();
  // 409 — в профиле нет грейда: это подсказка заполнить профиль, а не сбой
  const growthNeedsGrade = growth.error instanceof ApiError && growth.error.status === 409;
  const error = radar.error ?? (growthNeedsGrade ? null : growth.error);
  const noGrade = radar.data?.grade === null || growthNeedsGrade;

  return (
    <>
      <PageHeader
        title="Рост и зарплаты"
        text="Сколько платят специалистам вашего уровня и стека и что подтянуть до следующего грейда — по вакансиям, офферам и анкетам платформы."
      />
      {error && <Alert>{errorMessage(error)}</Alert>}
      {!error && (radar.isPending || growth.isPending) && <LoadingBlock />}
      {!error && noGrade && (
        <EmptyState
          icon={<TrendingUp className="size-5" aria-hidden />}
          title="Укажите грейд и навыки"
          text="Радар и путь роста строятся от вашего уровня и стека — заполните их в профиле."
          action={
            <Link to="/app" className={buttonClasses("primary", "md")}>
              Заполнить профиль
            </Link>
          }
        />
      )}
      {!error && radar.data && growth.data && !noGrade && (
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="flex flex-col gap-6">
            <SalaryCard radar={radar.data} />
            <LadderCard radar={radar.data} />
          </div>
          <aside className="flex flex-col gap-4 lg:sticky lg:top-32">
            <GrowthCard growth={growth.data} />
            <p className="text-xs leading-relaxed text-muted">
              Данные обезличены: распределение показывается, только когда в группе не меньше{" "}
              {radar.data.min_group} значений, а вилки и офферы — не меньше чем от трёх компаний.
            </p>
          </aside>
        </div>
      )}
    </>
  );
}
