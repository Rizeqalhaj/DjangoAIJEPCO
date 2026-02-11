import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { OptimizationPlan } from "@/types/api";

export function usePlans(sub: string) {
  return useQuery<OptimizationPlan[]>({
    queryKey: ["plans", sub],
    queryFn: () => api.get(`/plans/${sub}/`).then((r) => r.data),
    enabled: !!sub,
  });
}
