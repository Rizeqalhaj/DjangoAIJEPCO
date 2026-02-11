import { useMutation } from "@tanstack/react-query";
import api from "@/lib/api";

interface ChatResponse {
  reply: string;
  phone: string;
}

export function useChatMutation() {
  return useMutation<ChatResponse, Error, { phone: string; message: string }>({
    mutationFn: async ({ phone, message }) => {
      const { data } = await api.post("/agent/chat/", { phone, message });
      return data;
    },
  });
}
