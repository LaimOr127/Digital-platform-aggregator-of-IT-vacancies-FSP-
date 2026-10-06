import { Send, Users } from "lucide-react";
import { useState } from "react";
import { errorMessage } from "../../../api/errors";
import type { AiReview, CandidateCard, Company } from "../../../api/types";
import { Alert } from "../../../ui/Alert";
import { PageHeader } from "../../../ui/AppShell";
import { Button } from "../../../ui/Button";
import { CursorListView } from "../../../ui/CursorListView";
import { EmptyState } from "../../../ui/EmptyState";
import { Field, Select } from "../../../ui/form";
import { LoadingBlock } from "../../../ui/Spinner";
import { AiReviewBar } from "./AiReviewBar";
import { CandidateCardView } from "./CandidateCardView";
import { FiltersPanel } from "./CatalogFilters";
import { CategoryGrid, recommendedCategories } from "./CategoryGrid";
import {
  useCatalogCandidates,
  useCatalogCategories,
  useCatalogUrlState,
  useFspCategories,
  useNeedVacancies,
} from "./hooks";
import { InvitationDialog } from "../applications/InvitationDialog";

export function CatalogPage({ company }: { company: Company | undefined }) {
  if (!company) return <LoadingBlock />;
  if (company.status !== "approved") {
    return (
      <EmptyState
        icon={<Users className="size-5" />}
        title="Каталог откроется после модерации"
        text="Кандидатов видят только проверенные компании — так мы защищаем их от спама и фейковых работодателей."
      />
    );
  }
  return <Catalog company={company} />;
}

function Catalog({ company }: { company: Company }) {
  const { filters, need: chosen, update, reset, choose } = useCatalogUrlState();
  const [inviteTo, setInviteTo] = useState<CandidateCard | null>(null);
  // оценки ИИ — для выбранной вакансии; другая вакансия — другие оценки
  const [ai, setAi] = useState<{ vacancy: string; reviews: Map<string, AiReview> } | null>(null);
  // подбор «из коробки»: по первой вакансии (описанию потребности), пока работодатель не выберет другую
  const vacancies = useNeedVacancies();
  const matchVacancy = chosen ?? vacancies.data?.[0]?.id ?? "";
  const need = vacancies.data?.find((v) => v.id === matchVacancy);
  const recommended = need?.specialization ? recommendedCategories(need.specialization, need.grade) : [];
  const categories = useCatalogCategories(true);
  const fspCategories = useFspCategories();
  const candidates = useCatalogCandidates({ ...filters, vacancy_id: matchVacancy || undefined }, !vacancies.isPending);

  return (
    <>
      <PageHeader
        title="Каталог кандидатов"
        text="Выдача строится от категорий — специализация и грейд, подтверждённый тестом. С вакансией кандидаты отсортированы по соответствию ей, без вакансии — по силе подтверждённого профиля. Пригласите кандидата с вилкой и способом связи — его контакты откроются, когда он примет приглашение."
      />
      <Field
        label="Подбор под потребность"
        className="mb-6 max-w-xl"
        hint="Вакансия или черновик с описанием, кого вы ищете: специализация, грейд, стек"
      >
        <Select
          placeholder="Без вакансии — по силе профиля"
          options={(vacancies.data ?? []).map((v) => ({ value: v.id, label: v.title }))}
          value={matchVacancy}
          onChange={(e) => choose(e.target.value)}
        />
      </Field>
      {categories.error && <Alert>{errorMessage(categories.error)}</Alert>}
      {need && recommended.length > 0 && (
        <p className="mb-2 text-sm text-muted">
          Рамкой отмечены категории, рекомендованные под «{need.title}»: тот же грейд и соседние.
        </p>
      )}
      {categories.data && (
        <CategoryGrid
          categories={categories.data}
          selected={filters.category}
          recommended={recommended}
          onSelect={(category) => update({ category })}
        />
      )}
      <FiltersPanel
        filters={filters}
        fspCategories={fspCategories.data ?? []}
        onChange={update}
        onReset={reset}
      />
      {matchVacancy && (
        <AiReviewBar
          key={matchVacancy}
          vacancyId={matchVacancy}
          anonIds={candidates.items.map((c) => c.anon_id)}
          onReviews={(reviews) => setAi({ vacancy: matchVacancy, reviews: new Map(reviews.map((r) => [r.anon_id, r])) })}
        />
      )}
      <CursorListView
        query={candidates}
        className="grid gap-4 md:grid-cols-2"
        empty={{
          icon: <Users className="size-5" />,
          title: "Подходящих кандидатов пока нет",
          text: "Снимите часть фильтров или выберите соседнюю категорию.",
        }}
      >
        {(card) => (
          <CandidateCardView
            key={card.anon_id}
            card={card}
            aiReview={ai?.vacancy === matchVacancy ? ai.reviews.get(card.anon_id) : undefined}
            action={
              <Button size="sm" onClick={() => setInviteTo(card)}>
                <Send className="size-3.5" aria-hidden />
                Пригласить
              </Button>
            }
          />
        )}
      </CursorListView>
      <InvitationDialog
        key={inviteTo?.anon_id ?? "none"}
        candidate={inviteTo}
        vacancies={vacancies.data ?? []}
        vacancyId={matchVacancy || undefined}
        company={company}
        onClose={() => setInviteTo(null)}
      />
    </>
  );
}
