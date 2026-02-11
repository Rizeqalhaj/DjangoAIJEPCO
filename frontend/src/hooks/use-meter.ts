import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  ConsumptionSummary,
  DailySeriesItem,
  SpikesResponse,
  BillForecast,
  HourlyProfile,
} from "@/types/api";

export function useConsumptionSummary(sub: string, days = 30) {
  return useQuery<ConsumptionSummary>({
    queryKey: ["meter", "summary", sub, days],
    queryFn: () => api.get(`/meter/${sub}/summary/?days=${days}`).then((r) => r.data),
    enabled: !!sub,
    staleTime: 5 * 60 * 1000,
  });
}

export function useDailySeries(sub: string, days = 14) {
  return useQuery<DailySeriesItem[]>({
    queryKey: ["meter", "daily-series", sub, days],
    queryFn: () => api.get(`/meter/${sub}/daily-series/?days=${days}`).then((r) => r.data),
    enabled: !!sub,
    staleTime: 5 * 60 * 1000,
  });
}

export function useSpikes(sub: string, days = 7) {
  return useQuery<SpikesResponse>({
    queryKey: ["meter", "spikes", sub, days],
    queryFn: () => api.get(`/meter/${sub}/spikes/?days=${days}`).then((r) => r.data),
    enabled: !!sub,
  });
}

export function useBillForecast(sub: string) {
  return useQuery<BillForecast>({
    queryKey: ["meter", "forecast", sub],
    queryFn: () => api.get(`/meter/${sub}/forecast/`).then((r) => r.data),
    enabled: !!sub,
  });
}

export function useHourlyProfile(sub: string, days = 14) {
  return useQuery<HourlyProfile>({
    queryKey: ["meter", "hourly-profile", sub, days],
    queryFn: () => api.get(`/meter/${sub}/hourly-profile/?days=${days}`).then((r) => r.data),
    enabled: !!sub,
  });
}
