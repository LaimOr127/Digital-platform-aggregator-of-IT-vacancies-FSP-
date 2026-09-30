// Запросы, общие для нескольких порталов.
import { useQuery } from "@tanstack/react-query";
import { publicApi } from "./endpoints";

export const useSkills = () => useQuery({ queryKey: ["skills"], queryFn: publicApi.skills, staleTime: Infinity });
