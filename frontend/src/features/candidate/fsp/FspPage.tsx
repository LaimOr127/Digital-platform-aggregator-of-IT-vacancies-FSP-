import { errorMessage } from "../../../api/errors";
import { Alert } from "../../../ui/Alert";
import { PageHeader } from "../../../ui/AppShell";
import { LoadingBlock } from "../../../ui/Spinner";
import { AchievementsCard, CategoriesCard } from "./AchievementsCard";
import { FspLinkCard } from "./FspLinkCard";
import { useFspStatus, usePassport } from "./hooks";
import { PassportCard } from "./PassportCard";

export function FspPage() {
  const status = useFspStatus();
  const passport = usePassport();
  const error = status.error ?? passport.error;

  return (
    <>
      <PageHeader
        title="ФСП и паспорт навыков"
        text="Результаты соревнований Федерации спортивного программирования подтверждают навыки и определяют категории, в которых вас находят работодатели."
      />
      {error && <Alert>{errorMessage(error)}</Alert>}
      {!error && (!status.data || passport.data === undefined) && <LoadingBlock />}
      {status.data && passport.data !== undefined && (
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="flex flex-col gap-6">
            <FspLinkCard status={status.data} />
            {status.data.linked && (
              <>
                <CategoriesCard categories={status.data.categories} />
                <AchievementsCard achievements={status.data.achievements} />
              </>
            )}
          </div>
          <aside className="lg:sticky lg:top-32">
            <PassportCard passport={passport.data} tier={status.data.verification_tier} />
          </aside>
        </div>
      )}
    </>
  );
}
