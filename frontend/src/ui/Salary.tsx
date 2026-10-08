// Вилка с пометкой: по требованию организаторов видно, что сумма — до вычета налогов.
import { formatSalaryRange, SALARY_NOTE } from "../lib/format";

export function Salary({ min, max }: { min?: number | null; max?: number | null }) {
  return (
    <>
      {formatSalaryRange(min, max)}
      {(min || max) && <span className="ml-1.5 text-xs font-normal text-muted">{SALARY_NOTE}</span>}
    </>
  );
}
