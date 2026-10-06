// Строки графика «рынок зарплат»: одни и те же источники у кандидата и у работодателя.
import type { SalaryRadar } from "../../api/types";
import type { RangeRow } from "./RangeChart";

/** withPeers — ожидания других кандидатов (их видит только кандидат). */
export function marketRows(radar: SalaryRadar, withPeers: boolean): RangeRow[] {
  const rows: RangeRow[] = [
    { key: "vacancies", label: "Вилки вакансий", band: radar.vacancies, unit: "вакансий" },
    { key: "offers", label: "Офферы", band: radar.offers, unit: "офферов" },
  ];
  return withPeers ? [...rows, { key: "peers", label: "Ожидания коллег", band: radar.peers, unit: "кандидатов" }] : rows;
}
