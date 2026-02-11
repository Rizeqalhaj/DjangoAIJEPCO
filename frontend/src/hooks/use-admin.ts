import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { AdminStats, AdminSubscriber } from "@/types/api";

export function useAdminStats() {
  return useQuery<AdminStats>({
    queryKey: ["admin", "stats"],
    queryFn: () => api.get("/admin/stats/").then((r) => r.data),
    staleTime: 60 * 1000,
  });
}

export function useAdminSubscribers() {
  return useQuery<AdminSubscriber[]>({
    queryKey: ["admin", "subscribers"],
    queryFn: () => api.get("/admin/subscribers/").then((r) => r.data),
    staleTime: 60 * 1000,
  });
}

export function useAdminSubscriberDetail(id: number) {
  return useQuery({
    queryKey: ["admin", "subscriber", id],
    queryFn: () => api.get(`/admin/subscribers/${id}/`).then((r) => r.data),
    enabled: !!id,
  });
}
