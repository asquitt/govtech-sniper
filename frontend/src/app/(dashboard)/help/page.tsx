"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { supportApi } from "@/lib/api";
import type { HelpArticle, InteractiveTutorial } from "@/types";

export default function HelpCenterPage() {
  const [articles, setArticles] = useState<HelpArticle[]>([]);
  const [tutorials, setTutorials] = useState<InteractiveTutorial[]>([]);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [selectedTutorialId, setSelectedTutorialId] = useState<string | null>(null);
  const [tutorialStepIndex, setTutorialStepIndex] = useState(0);
  const [search, setSearch] = useState("");
  const [chatPrompt, setChatPrompt] = useState("");
  const [chatReply, setChatReply] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [articleData, tutorialData] = await Promise.all([
        supportApi.listArticles(),
        supportApi.listTutorials(),
      ]);
      setArticles(articleData);
      setTutorials(tutorialData);
      setSelectedArticleId((prev) => prev ?? articleData[0]?.id ?? null);
      setSelectedTutorialId((prev) => prev ?? tutorialData[0]?.id ?? null);
      setError(null);
    } catch {
      setError("Failed to load help center content.");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const filteredArticles = useMemo(() => {
    if (!search.trim()) return articles;
    const query = search.toLowerCase();
    return articles.filter(
      (article) =>
        article.title.toLowerCase().includes(query) ||
        article.summary.toLowerCase().includes(query) ||
        article.tags.some((tag) => tag.toLowerCase().includes(query))
    );
  }, [articles, search]);

  const activeArticle =
    articles.find((article) => article.id === selectedArticleId) ?? filteredArticles[0] ?? null;

  const activeTutorial =
    tutorials.find((tutorial) => tutorial.id === selectedTutorialId) ?? tutorials[0] ?? null;
  const activeStep = activeTutorial?.steps[tutorialStepIndex] ?? null;

  useEffect(() => {
    setTutorialStepIndex(0);
  }, [selectedTutorialId]);

  const handleChatAsk = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!chatPrompt.trim()) return;
    try {
      const response = await supportApi.chat({ message: chatPrompt.trim(), current_route: "/help" });
      setChatReply(response.reply);
      if (response.suggested_tutorial_id) {
        setSelectedTutorialId(response.suggested_tutorial_id);
      }
      if (response.suggested_article_ids.length > 0) {
        setSelectedArticleId(response.suggested_article_ids[0]);
      }
      setChatPrompt("");
    } catch {
      setChatReply("Support chat is temporarily unavailable.");
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <Header
        title="Help Center"
        description="Guides, interactive tutorials, and quick chat support."
      />

      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[320px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Knowledge Base</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search guides..."
              className="w-full rounded-md border border-border px-3 py-2 text-sm"
            />
            <div className="space-y-2">
              {filteredArticles.map((article) => (
                <button
                  key={article.id}
                  type="button"
                  onClick={() => setSelectedArticleId(article.id)}
                  className={`w-full rounded-md border px-3 py-2 text-left text-sm ${
                    selectedArticleId === article.id
                      ? "border-primary bg-primary/10"
                      : "border-border hover:bg-muted/50"
                  }`}
                >
                  <p className="font-medium">{article.title}</p>
                  <p className="text-xs text-muted-foreground">{article.summary}</p>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {activeArticle?.title ?? "Select an article"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {activeArticle ? (
                <>
                  <div className="flex flex-wrap gap-1">
                    <Badge variant="secondary">{activeArticle.category}</Badge>
                    {activeArticle.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                  <p className="text-sm text-muted-foreground">{activeArticle.content}</p>
                  <p className="text-xs text-muted-foreground">
                    Updated {activeArticle.last_updated}
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No article selected.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Interactive Tutorials</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {tutorials.map((tutorial) => (
                  <Button
                    key={tutorial.id}
                    size="sm"
                    variant={tutorial.id === selectedTutorialId ? "default" : "outline"}
                    onClick={() => setSelectedTutorialId(tutorial.id)}
                  >
                    {tutorial.title}
                  </Button>
                ))}
              </div>
              {activeTutorial && activeStep ? (
                <div className="space-y-3 rounded-md border border-border p-3">
                  <p className="text-sm font-semibold">{activeTutorial.title}</p>
                  <p className="text-xs text-muted-foreground">
                    Step {tutorialStepIndex + 1} of {activeTutorial.steps.length}
                  </p>
                  <div>
                    <p className="text-sm font-medium">{activeStep.title}</p>
                    <p className="text-sm text-muted-foreground">{activeStep.instruction}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setTutorialStepIndex((prev) => Math.max(0, prev - 1))}
                      disabled={tutorialStepIndex === 0}
                    >
                      Previous
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setTutorialStepIndex((prev) =>
                          Math.min(activeTutorial.steps.length - 1, prev + 1)
                        )
                      }
                      disabled={tutorialStepIndex >= activeTutorial.steps.length - 1}
                    >
                      Next
                    </Button>
                    <Link href={activeStep.route} className="inline-flex">
                      <Button size="sm">{activeStep.action_label ?? "Open Route"}</Button>
                    </Link>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No tutorials available.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Chat Support</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <form onSubmit={handleChatAsk} className="space-y-2">
                <textarea
                  value={chatPrompt}
                  onChange={(event) => setChatPrompt(event.target.value)}
                  placeholder="Ask support anything about onboarding, templates, or reports..."
                  className="min-h-20 w-full rounded-md border border-border px-3 py-2 text-sm"
                />
                <Button type="submit" size="sm">
                  Ask Support
                </Button>
              </form>
              {chatReply && (
                <p className="rounded-md bg-muted p-3 text-sm text-muted-foreground">{chatReply}</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
