// Состояния списка с курсорной пагинацией: загрузка, ошибка, пусто, «Показать ещё».
import { AnimatePresence } from "motion/react";
import type { ComponentProps, ReactNode } from "react";
import { errorMessage } from "../api/errors";
import type { useCursorList } from "../api/queries";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { EmptyState } from "./EmptyState";
import { LoadingBlock } from "./Spinner";

type Props<T> = {
  query: ReturnType<typeof useCursorList<T>>;
  empty: ComponentProps<typeof EmptyState>;
  children: (item: T) => ReactNode;
  className?: string;
};

export function CursorListView<T>({ query, empty, children, className = "flex flex-col gap-4" }: Props<T>) {
  // ошибка без данных — вместо списка; ошибка догрузки — под уже загруженным списком
  if (query.error && !query.data) return <Alert>{errorMessage(query.error)}</Alert>;
  if (!query.data) return <LoadingBlock />;
  if (query.items.length === 0) return <EmptyState {...empty} />;
  return (
    <>
      <div className={className}>
        <AnimatePresence initial={false}>{query.items.map(children)}</AnimatePresence>
      </div>
      {query.error && (
        <div className="mt-4">
          <Alert>{errorMessage(query.error)}</Alert>
        </div>
      )}
      {query.hasNextPage && (
        <div className="mt-6 flex justify-center">
          <Button variant="secondary" onClick={() => query.fetchNextPage()} loading={query.isFetchingNextPage}>
            Показать ещё
          </Button>
        </div>
      )}
    </>
  );
}
