"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useT } from "@/i18n";
import { LanguageToggle } from "@/components/layout/language-toggle";
import { RtlProvider } from "@/components/layout/rtl-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { LoginResponse } from "@/types/api";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const setUser = useAuthStore((s) => s.setUser);
  const t = useT();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post<LoginResponse>("/auth/login/", {
        username,
        password,
      });
      localStorage.setItem("kahrabaai_access", data.access);
      localStorage.setItem("kahrabaai_refresh", data.refresh);
      setUser(data.user);
      router.push("/dashboard");
    } catch {
      setError(t.common.login === "Login"
        ? "Invalid username or password"
        : "\u0627\u0633\u0645 \u0627\u0644\u0645\u0633\u062A\u062E\u062F\u0645 \u0623\u0648 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631 \u063A\u064A\u0631 \u0635\u062D\u064A\u062D\u0629");
    } finally {
      setLoading(false);
    }
  };

  return (
    <RtlProvider>
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-900">
        <div className="absolute top-4 end-4">
          <LanguageToggle />
        </div>

        <Card className="w-full max-w-md shadow-2xl border-0 bg-white/95 backdrop-blur-sm">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-emerald-500 text-3xl shadow-lg">
              {"\u26A1"}
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight">
              KahrabaAI
            </CardTitle>
            <p className="text-muted-foreground text-sm mt-1">
              {"\u0645\u062D\u0642\u0642 \u0627\u0644\u0637\u0627\u0642\u0629 \u0627\u0644\u0630\u0643\u064A"}
            </p>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">{t.common.username}</Label>
                <Input
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="transition-shadow duration-200 focus-visible:shadow-md"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">{t.common.password}</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="transition-shadow duration-200 focus-visible:shadow-md"
                  required
                />
              </div>

              {error && (
                <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-[#ef4444] text-center border border-red-200">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                className="w-full transition-transform duration-150 active:scale-[0.98]"
                disabled={loading}
              >
                {loading ? t.common.loading : t.common.login}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </RtlProvider>
  );
}
