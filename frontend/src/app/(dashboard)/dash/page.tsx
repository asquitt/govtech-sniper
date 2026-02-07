"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Loader2 } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { dashApi, rfpApi } from "@/lib/api";
import { VoiceControls } from "@/components/dash/voice-controls";
import type { RFPListItem } from "@/types";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: { type?: string; title?: string; filename?: string }[];
}

const suggestions = [
  {
    label: "Summarize solicitation",
    prompt: "Summarize this opportunity.",
  },
  {
    label: "Compliance gaps",
    prompt: "What compliance gaps remain?",
  },
  {
    label: "Draft capability statement",
    prompt: "Draft a capability statement for this opportunity.",
  },
];

export default function DashPage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [opportunities, setOpportunities] = useState<RFPListItem[]>([]);
  const [selectedRfpId, setSelectedRfpId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingRfps, setIsLoadingRfps] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleVoiceTranscript = useCallback((text: string) => {
    if (text.trim()) {
      setQuestion(text);
    }
  }, []);

  const lastAssistantMessage = messages
    .filter((m) => m.role === "assistant")
    .pop()?.content;

  useEffect(() => {
    const fetchRfps = async () => {
      try {
        setIsLoadingRfps(true);
        const list = await rfpApi.list({ limit: 50 });
        setOpportunities(list);
        if (list.length > 0) {
          setSelectedRfpId(list[0].id);
        }
      } catch (err) {
        console.error("Failed to load opportunities", err);
      } finally {
        setIsLoadingRfps(false);
      }
    };

    fetchRfps();
  }, []);

  const handleAsk = async (overridePrompt?: string) => {
    const prompt = overridePrompt ?? question.trim();
    if (!prompt) return;
    setIsLoading(true);
    setError(null);
    const userMessage = { role: "user" as const, content: prompt };
    setMessages((prev) => [...prev, userMessage]);
    try {
      const response = await dashApi.ask({
        question: prompt,
        rfp_id: selectedRfpId ?? undefined,
      });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          citations: response.citations,
        },
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
          <CardContent className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-foreground">Opportunity Context</p>
                <p className="text-xs text-muted-foreground">
                  Select the opportunity Dash should reference
                </p>
              </div>
              {isLoadingRfps && <Loader2 className="w-4 h-4 animate-spin" />}
            </div>
            <div className="flex items-center gap-2">
              <select
                className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
                value={selectedRfpId ?? ""}
                onChange={(e) =>
                  setSelectedRfpId(e.target.value ? Number(e.target.value) : null)
                }
              >
                <option value="">No opportunity selected</option>
                {opportunities.map((rfp) => (
                  <option key={rfp.id} value={rfp.id}>
                    {rfp.title}
                  </option>
                ))}
              </select>
              {selectedRfpId && (
                <Badge variant="outline">ID {selectedRfpId}</Badge>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border">
          <CardContent className="p-4 space-y-3">
            <div className="flex flex-wrap gap-2">
              {suggestions.map((suggestion) => (
                <Button
                  key={suggestion.label}
                  variant="outline"
                  size="sm"
                  onClick={() => handleAsk(suggestion.prompt)}
                >
                  {suggestion.label}
                </Button>
              ))}
            </div>

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
                    <p className="whitespace-pre-line">{message.content}</p>
                    {message.role === "assistant" && message.citations?.length ? (
                      <div className="mt-2 text-xs text-muted-foreground">
                        <p className="font-medium">Citations</p>
                        <ul className="list-disc ml-4">
                          {message.citations.map((citation, idx) => (
                            <li key={`citation-${idx}`}>
                              {citation.title || citation.filename || "Internal source"}
                              {citation.type ? ` (${citation.type})` : ""}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                ))
              )}
            </div>

            <div className="flex gap-2">
              <input
                className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Ask Dash a question..."
                value={question}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuestion(e.target.value)}
                onKeyDown={(e: React.KeyboardEvent) => {
                  if (e.key === "Enter" && !isLoading) handleAsk();
                }}
              />
              <Button onClick={() => handleAsk()} disabled={isLoading}>
                {isLoading ? "Thinking..." : "Ask"}
              </Button>
            </div>
            <VoiceControls
              onTranscript={handleVoiceTranscript}
              lastAssistantMessage={lastAssistantMessage}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
