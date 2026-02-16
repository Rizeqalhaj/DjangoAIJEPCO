import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface TimeState {
  current_time: string;
  is_overridden: boolean;
  real_time: string;
}

async function fetchTime(): Promise<TimeState> {
  const res = await fetch(`${BASE}/debug/time/`);
  if (!res.ok) throw new Error("Failed to fetch time");
  return res.json();
}

export function useTimeOverride() {
  const queryClient = useQueryClient();

  const query = useQuery<TimeState>({
    queryKey: ["debug-time"],
    queryFn: fetchTime,
    refetchInterval: 30000,
    retry: false,
    enabled: process.env.NODE_ENV === "development",
  });

  const setTime = useMutation({
    mutationFn: async (date: string) => {
      const res = await fetch(`${BASE}/debug/time/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date }),
      });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });

  const resetTime = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${BASE}/debug/time/`, { method: "DELETE" });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });

  return {
    currentTime: query.data?.current_time,
    isOverridden: query.data?.is_overridden ?? false,
    realTime: query.data?.real_time,
    isLoading: query.isLoading,
    setTime: setTime.mutate,
    resetTime: resetTime.mutate,
    isSettingTime: setTime.isPending,
  };
}
