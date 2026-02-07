"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDashStore } from "@/lib/stores/dash-store";
import { MessageBubble } from "./message-bubble";

interface Suggestion {
  label: string;
  prompt: string;
}

function getSuggestions(
  rfpId: number | null,
  messageCount: number
): Suggestion[] {
  if (!rfpId) {
    return [
      { label: "Recent opportunities", prompt: "Show me my most recent opportunities" },
      { label: "Pipeline overview", prompt: "Give me an overview of my pipeline" },
      { label: "Upload help", prompt: "How do I upload documents to my knowledge base?" },
    ];
  }
  if (messageCount === 0) {
    return [
      { label: "Summarize solicitation", prompt: "Summarize this opportunity with key details" },
      { label: "Compliance gaps", prompt: "What compliance gaps remain for this RFP?" },
      { label: "Draft executive summary", prompt: "Draft an executive summary for this proposal" },
      { label: "Competitive analysis", prompt: "What competitive intelligence do we have?" },
    ];
  }
  return [
    { label: "Go deeper", prompt: "Explain that in more detail" },
    { label: "Draft content", prompt: "Draft a proposal section addressing that" },
  ];
}

export function ChatPanel() {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { messages, isLoading, error, selectedRfpId, sendMessage, stopStreaming } =
    useDashStore();

  const suggestions = getSuggestions(selectedRfpId, messages.length);
  const isStreaming = messages[messages.length - 1]?.isStreaming ?? false;

  // Auto-scroll on new content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = (text?: string) => {
    const prompt = text ?? input.trim();
    if (!prompt || isLoading) return;
    setInput("");
    sendMessage(prompt);
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <h2 className="text-xl font-semibold text-foreground mb-2">
              Ask Dash anything
            </h2>
            <p className="text-sm text-muted-foreground mb-6 max-w-md">
              Get summaries, compliance analysis, draft content, and insights
              about your opportunities and proposals.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {suggestions.map((s) => (
                <Button
                  key={s.label}
                  variant="outline"
                  size="sm"
                  onClick={() => handleSend(s.prompt)}
                >
                  {s.label}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}

            {/* Typing indicator */}
            {isStreaming && messages[messages.length - 1]?.content === "" && (
              <div className="flex justify-start">
                <div className="bg-secondary rounded-lg px-4 py-3">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" />
                    <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:0.15s]" />
                    <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:0.3s]" />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="px-4 py-2 text-sm text-destructive bg-destructive/10">
          {error}
        </div>
      )}

      {/* Suggestion chips (after conversation started) */}
      {messages.length > 0 && !isLoading && (
        <div className="px-4 pb-2 flex flex-wrap gap-1.5">
          {suggestions.map((s) => (
            <Button
              key={s.label}
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => handleSend(s.prompt)}
            >
              {s.label}
            </Button>
          ))}
        </div>
      )}

      {/* Input bar */}
      <div className="border-t border-border p-4">
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            placeholder="Ask Dash a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !isLoading) {
                e.preventDefault();
                handleSend();
              }
            }}
            disabled={isLoading}
          />
          {isStreaming ? (
            <Button variant="destructive" size="sm" onClick={stopStreaming}>
              <Square className="w-4 h-4" />
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
            >
              <Send className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
