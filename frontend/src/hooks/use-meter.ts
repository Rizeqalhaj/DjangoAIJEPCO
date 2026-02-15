import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  ConsumptionSummary,
  DailySeriesItem,
  SpikesResponse,
  BillForecast,
  HourlyProfile,
} from "@/types/api";

export interface DateRange {
  startDate: string; // YYYY-MM-DD
  endDate: string;   // YYYY-MM-DD
}

function buildParams(days: number, range?: DateRange): string {
  if (range) {
    return `start_date=${range.startDate}&end_date=${range.endDate}`;
  }
  return `days=${days}`;
}

export function useConsumptionSummary(sub: string, days = 30, range?: DateRange) {
  return useQuery<ConsumptionSummary>({
    queryKey: ["meter", "summary", sub, range ? `${range.startDate}_${range.endDate}` : days],
    queryFn: () => api.get(`/meter/${sub}/summary/?${buildParams(days, range)}`).then((r) => r.data),
    enabled: !!sub,
    staleTime: 5 * 60 * 1000,
  });
}

export function useDailySeries(sub: string, days = 14, range?: DateRange) {
  return useQuery<DailySeriesItem[]>({
    queryKey: ["meter", "daily-series", sub, range ? `${range.startDate}_${range.endDate}` : days],
    queryFn: () => api.get(`/meter/${sub}/daily-series/?${buildParams(days, range)}`).then((r) => r.data),
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
