"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { useChatMutation } from "@/hooks/use-chat";
import { useT } from "@/i18n";
import Markdown from "react-markdown";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface Msg { role: "user" | "assistant"; content: string }

function TypingDots() {
  return (
    <span className="inline-flex gap-1 items-center">
      {[0, 1, 2].map((i) => (
        <span key={i} className="h-2 w-2 rounded-full bg-muted-foreground/60 animate-bounce" style={{ animationDelay: `${i * 150}ms` }} />
      ))}
    </span>
  );
}

export default function ChatPage() {
  const t = useT();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const phone = useAuthStore((s) => s.user?.subscriber?.phone_number ?? "");
  const chat = useChatMutation();
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scroll = useCallback(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), []);
  useEffect(() => { scroll(); }, [msgs, chat.isPending, scroll]);

  // Re-focus input when response arrives (isPending goes false)
  useEffect(() => {
    if (!chat.isPending) {
      inputRef.current?.focus();
    }
  }, [chat.isPending]);

  const send = (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || !phone) return;
    setMsgs((p) => [...p, { role: "user", content: msg }]);
    setInput("");
    chat.mutate({ phone, message: msg }, {
      onSuccess: (d) => setMsgs((p) => [...p, { role: "assistant", content: d.reply }]),
      onError: () => setMsgs((p) => [...p, { role: "assistant", content: "Error: could not get response" }]),
      onSettled: () => inputRef.current?.focus(),
    });
  };

  const quickActions = [
    t.chat.quickMyConsumption,
    t.chat.quickBillHigh,
    t.chat.quickMyPlan,
    t.chat.quickSaveTips,
    t.chat.quickCompare,
  ];

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold">{t.chat.title}</h1>
      <Card className="flex flex-col h-[calc(100dvh-180px)] md:h-[calc(100dvh-200px)]">
        <CardHeader className="border-b py-3 shrink-0">
          <CardTitle className="text-base">{t.chat.botName}</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
          {msgs.length === 0 && !chat.isPending && (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
              <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
                <svg className="h-7 w-7 text-primary" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <p className="text-sm text-muted-foreground max-w-sm">{t.chat.welcomeMsg}</p>
              <div className="flex flex-wrap justify-center gap-2 max-w-md">
                {quickActions.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="px-3 py-1.5 text-xs font-medium rounded-full border border-primary/30 text-primary bg-primary/5 hover:bg-primary/10 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className="max-w-[80%] space-y-1">
                {m.role === "assistant" && <p className="text-xs text-muted-foreground ps-1">{t.chat.botName}</p>}
                {m.role === "user" ? (
                  <div className="px-4 py-2.5 text-sm whitespace-pre-wrap bg-primary text-primary-foreground rounded-2xl rounded-ee-md">
                    {m.content}
                  </div>
                ) : (
                  <div className="px-4 py-2.5 text-sm bg-muted rounded-2xl rounded-es-md prose prose-sm prose-neutral max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                    <Markdown>{m.content}</Markdown>
                  </div>
                )}
              </div>
            </div>
          ))}
          {chat.isPending && (
            <div className="flex justify-start">
              <div className="max-w-[80%] space-y-1">
                <p className="text-xs text-muted-foreground ps-1">{t.chat.botName}</p>
                <div className="bg-muted px-4 py-3 rounded-2xl rounded-es-md"><TypingDots /></div>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </CardContent>
        <div className="border-t p-3 flex gap-2 shrink-0">
          <Input ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder={t.chat.placeholder} disabled={chat.isPending} className="text-sm" />
          <Button onClick={() => send()} disabled={chat.isPending || !input.trim()}>{t.common.send}</Button>
        </div>
      </Card>
    </div>
  );
}
