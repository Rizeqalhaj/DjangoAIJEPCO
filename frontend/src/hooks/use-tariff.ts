import { useQuery, useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import type { TouPeriod, TariffCalculation } from "@/types/api";

export function useCurrentTou() {
  return useQuery<TouPeriod>({
    queryKey: ["tariff", "current"],
    queryFn: () => api.get("/tariff/current/").then((r) => r.data),
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useCalculateBill() {
  return useMutation<TariffCalculation, Error, { monthly_kwh: number }>({
    mutationFn: async (body) => {
      const { data } = await api.post("/tariff/calculate/", body);
      return data;
    },
  });
}
