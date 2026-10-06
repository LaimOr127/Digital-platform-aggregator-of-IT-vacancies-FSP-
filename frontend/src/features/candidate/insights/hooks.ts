import { useQuery } from "@tanstack/react-query";
import { insightsApi } from "../../../api/endpoints";

export const useSalaryRadar = () => useQuery({ queryKey: ["insights", "salary"], queryFn: insightsApi.salary });
export const useGrowth = () => useQuery({ queryKey: ["insights", "growth"], queryFn: insightsApi.growth });
