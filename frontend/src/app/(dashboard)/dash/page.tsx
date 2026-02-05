"use client";

import React, { useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { dashApi } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export default function DashPage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAsk = async () => {
    if (!question.trim()) return;
    setIsLoading(true);
    setError(null);
    const userMessage = { role: "user" as const, content: question.trim() };
    setMessages((prev) => [...prev, userMessage]);
    try {
      const response = await dashApi.ask({ question: question.trim() });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer },
      ]);
      setQuestion("");
    } catch (err) {
      console.error("Dash ask failed", err);
      setError("Failed to get response from Dash.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Dash" description="Your AI assistant for GovCon workflows" />

      <div className="flex-1 p-6 overflow-auto space-y-4">
        {error && <p className="text-destructive">{error}</p>}

        <Card className="border border-border">
          <CardContent className="p-4 space-y-3">
            <div className="space-y-2">
              {messages.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Ask Dash to summarize opportunities, draft capability statements,
                  or explain compliance gaps.
                </p>
              ) : (
                messages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`rounded-md px-3 py-2 text-sm ${
                      message.role === "user"
                        ? "bg-primary/10 text-foreground"
                        : "bg-secondary text-foreground"
                    }`}
                  >
                    <p className="font-medium capitalize mb-1">
                      {message.role}
                    </p>
                    <p>{message.content}</p>
                  </div>
                ))
              )}
            </div>

            <div className="flex gap-2">
              <input
                className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Ask Dash a question..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
              <Button onClick={handleAsk} disabled={isLoading}>
                {isLoading ? "Thinking..." : "Ask"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
