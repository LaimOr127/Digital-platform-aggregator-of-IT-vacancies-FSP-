import { useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "../../../api/endpoints";
import { useCursorList } from "../../../api/queries";
import type { TaskInput } from "../../../api/types";

const TASKS = ["employer-tasks"] as const;

export const useEmployerTasks = () => useCursorList([...TASKS], (cursor) => tasksApi.list(cursor));
export const useTaskAnswers = (taskId: string) =>
  useCursorList([...TASKS, taskId, "answers"], (cursor) => tasksApi.answers(taskId, cursor));

/** Изменения задачи и оценки ответов обновляют и список задач, и ответы. */
function useTaskMutation<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => client.invalidateQueries({ queryKey: TASKS }) });
}

export const useCreateTask = () => useTaskMutation((body: TaskInput) => tasksApi.create(body));
export const useCloseTask = () => useTaskMutation(tasksApi.close);
export const useRateAnswer = () =>
  useTaskMutation(({ taskId, answerId, rating }: { taskId: string; answerId: string; rating: number }) =>
    tasksApi.rate(taskId, answerId, rating),
  );
