import { create } from "zustand";
import type { User } from "@/types/api";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  setUser: (user: User) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isAdmin: false,
  setUser: (user) =>
    set({ user, isAuthenticated: true, isAdmin: user.is_staff }),
  clear: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("kahrabaai_access");
      localStorage.removeItem("kahrabaai_refresh");
    }
    set({ user: null, isAuthenticated: false, isAdmin: false });
  },
}));
