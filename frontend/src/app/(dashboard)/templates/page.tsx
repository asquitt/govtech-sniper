"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { templateApi, templateMarketplaceApi } from "@/lib/api";
import type { ProposalTemplate } from "@/lib/api";
import type { MarketplaceTemplate } from "@/types";

type TemplateTab =
  | "community"
  | "popular"
  | "proposal-kits"
  | "compliance-matrices"
  | "my-library";

const PROPOSAL_CATEGORIES = ["IT Services", "Construction", "Professional Services"];

const COMMUNITY_FILTERS = [
  "Past Performance",
  "Technical",
  "Quality",
  "Personnel",
  "Security",
  "Proposal Structure",
  "Compliance Matrix",
];

function averageRating(template: { rating_sum: number; rating_count: number }) {
  if (template.rating_count <= 0) return 0;
  return template.rating_sum / template.rating_count;
}

function TemplateSummary({
  title,
  category,
  subcategory,
  description,
  keywords,
  usageCount,
  ratingSum,
  ratingCount,
  footer,
}: {
  title: string;
  category: string;
  subcategory?: string | null;
  description: string;
  keywords: string[];
  usageCount: number;
  ratingSum: number;
  ratingCount: number;
  footer?: React.ReactNode;
}) {
  const rating = averageRating({ rating_sum: ratingSum, rating_count: ratingCount });
  return (
    <Card className="h-full">
      <CardHeader className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{title}</CardTitle>
          <Badge variant="secondary">{category}</Badge>
        </div>
        {subcategory && <p className="text-xs text-muted-foreground">{subcategory}</p>}
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">{description}</p>
        <div className="flex flex-wrap gap-1">
          {keywords.slice(0, 5).map((keyword) => (
            <Badge key={keyword} variant="outline" className="text-xs">
              {keyword}
            </Badge>
          ))}
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{usageCount} uses</span>
          <span>
            {rating.toFixed(1)} / 5.0 ({ratingCount})
          </span>
        </div>
        {footer}
      </CardContent>
    </Card>
  );
}

export default function TemplatesPage() {
  const [tab, setTab] = useState<TemplateTab>("community");
  const [marketplaceTemplates, setMarketplaceTemplates] = useState<MarketplaceTemplate[]>([]);
  const [marketplaceTotal, setMarketplaceTotal] = useState(0);
  const [myTemplates, setMyTemplates] = useState<ProposalTemplate[]>([]);
  const [proposalKits, setProposalKits] = useState<ProposalTemplate[]>([]);
  const [complianceMatrices, setComplianceMatrices] = useState<ProposalTemplate[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [ratingByTemplate, setRatingByTemplate] = useState<Record<number, number>>({});
  const [newTemplateName, setNewTemplateName] = useState("");
  const [newTemplateDescription, setNewTemplateDescription] = useState("");
  const [newTemplateContent, setNewTemplateContent] = useState("");
  const [newTemplateCategory, setNewTemplateCategory] = useState("Proposal Structure");
  const [shareOnCreate, setShareOnCreate] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchLibrary = useCallback(async () => {
    const [library, proposalStructures, compliance] = await Promise.all([
      templateApi.list(),
      templateApi.list({ category: "Proposal Structure" }),
      templateApi.list({ category: "Compliance Matrix" }),
    ]);

    setMyTemplates(library.filter((template) => !template.is_system));
    setProposalKits(
      proposalStructures.sort((a, b) => {
        const aRank = PROPOSAL_CATEGORIES.indexOf(a.subcategory ?? "");
        const bRank = PROPOSAL_CATEGORIES.indexOf(b.subcategory ?? "");
        return (aRank === -1 ? 99 : aRank) - (bRank === -1 ? 99 : bRank);
      })
    );
    setComplianceMatrices(compliance);
  }, []);

  const fetchCommunity = useCallback(async () => {
    if (tab === "popular") {
      const response = await templateMarketplaceApi.popular();
      setMarketplaceTemplates(response.data);
      setMarketplaceTotal(response.data.length);
      return;
    }
    const response = await templateMarketplaceApi.browse({
      q: search || undefined,
      category: category || undefined,
      limit: 50,
      offset: 0,
    });
    setMarketplaceTemplates(response.data.items);
    setMarketplaceTotal(response.data.total);
  }, [category, search, tab]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([fetchLibrary(), fetchCommunity()]);
    } catch {
      setError("Failed to load templates.");
    } finally {
      setLoading(false);
    }
  }, [fetchCommunity, fetchLibrary]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (tab === "community" || tab === "popular") {
      fetchCommunity().catch(() => {
        setError("Failed to load community templates.");
      });
    }
  }, [fetchCommunity, tab]);

  const handleFork = async (templateId: number) => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await templateMarketplaceApi.fork(templateId);
      setSuccess("Template forked to your library.");
      await refresh();
    } catch {
      setError("Failed to fork template.");
    } finally {
      setSaving(false);
    }
  };

  const handleRate = async (templateId: number) => {
    const rating = ratingByTemplate[templateId];
    if (!rating) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await templateMarketplaceApi.rate(templateId, { rating });
      setSuccess("Template rating submitted.");
      await fetchCommunity();
    } catch {
      setError("Failed to submit template rating.");
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async (templateId: number) => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await templateMarketplaceApi.publish(templateId);
      setSuccess("Template shared with the community marketplace.");
      await refresh();
    } catch {
      setError("Failed to publish template.");
    } finally {
      setSaving(false);
    }
  };

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newTemplateName.trim() || !newTemplateDescription.trim() || !newTemplateContent.trim()) {
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const created = await templateApi.create({
        name: newTemplateName.trim(),
        category: newTemplateCategory,
        description: newTemplateDescription.trim(),
        template_text: newTemplateContent.trim(),
        keywords: newTemplateCategory === "Compliance Matrix"
          ? ["community", "compliance-matrix"]
          : ["community", "proposal-structure"],
      });
      if (shareOnCreate) {
        await templateMarketplaceApi.publish(created.id);
      }
      setNewTemplateName("");
      setNewTemplateDescription("");
      setNewTemplateContent("");
      setSuccess(
        shareOnCreate
          ? "Template created and shared to community."
          : "Template created in your private library."
      );
      await refresh();
    } catch {
      setError("Failed to create template.");
    } finally {
      setSaving(false);
    }
  };

  const proposalGroups = useMemo(() => {
    return PROPOSAL_CATEGORIES.map((group) => ({
      group,
      templates: proposalKits.filter((template) => template.subcategory === group),
    })).filter((item) => item.templates.length > 0);
  }, [proposalKits]);

  return (
    <div className="flex flex-col gap-6 p-6">
      <Header
        title="Template Marketplace"
        description="Discover vertical proposal kits, compliance matrices, and community-shared templates."
      />

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={tab === "community" ? "default" : "outline"}
          onClick={() => setTab("community")}
        >
          Community
        </Button>
        <Button
          size="sm"
          variant={tab === "popular" ? "default" : "outline"}
          onClick={() => setTab("popular")}
        >
          Popular
        </Button>
        <Button
          size="sm"
          variant={tab === "proposal-kits" ? "default" : "outline"}
          onClick={() => setTab("proposal-kits")}
        >
          Proposal Kits
        </Button>
        <Button
          size="sm"
          variant={tab === "compliance-matrices" ? "default" : "outline"}
          onClick={() => setTab("compliance-matrices")}
        >
          Compliance Matrices
        </Button>
        <Button
          size="sm"
          variant={tab === "my-library" ? "default" : "outline"}
          onClick={() => setTab("my-library")}
        >
          My Library
        </Button>
      </div>

      {(tab === "community" || tab === "popular") && (
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search community templates..."
            className="w-72 rounded-md border border-border px-3 py-2 text-sm"
          />
          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className="rounded-md border border-border px-3 py-2 text-sm"
          >
            <option value="">All categories</option>
            {COMMUNITY_FILTERS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <Button size="sm" onClick={() => fetchCommunity()}>
            Refresh Community
          </Button>
        </div>
      )}

      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      {success && (
        <div className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{success}</div>
      )}

      {loading ? (
        <div className="py-12 text-center text-muted-foreground">Loading templates...</div>
      ) : null}

      {!loading && (tab === "community" || tab === "popular") && (
        <>
          <p className="text-sm text-muted-foreground">
            {marketplaceTotal} community template{marketplaceTotal === 1 ? "" : "s"} found
          </p>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {marketplaceTemplates.map((template) => (
              <TemplateSummary
                key={template.id}
                title={template.name}
                category={template.category}
                subcategory={template.subcategory}
                description={template.description}
                keywords={template.keywords}
                usageCount={template.usage_count}
                ratingSum={template.rating_sum}
                ratingCount={template.rating_count}
                footer={
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <select
                        className="w-full rounded-md border border-border px-2 py-1 text-xs"
                        value={ratingByTemplate[template.id] ?? ""}
                        onChange={(event) =>
                          setRatingByTemplate((prev) => ({
                            ...prev,
                            [template.id]: Number(event.target.value),
                          }))
                        }
                      >
                        <option value="">Rate...</option>
                        {[1, 2, 3, 4, 5].map((value) => (
                          <option key={value} value={value}>
                            {value} star{value === 1 ? "" : "s"}
                          </option>
                        ))}
                      </select>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleRate(template.id)}
                        disabled={saving || !ratingByTemplate[template.id]}
                      >
                        Rate
                      </Button>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleFork(template.id)}
                      disabled={saving}
                      className="w-full"
                    >
                      Fork to Library
                    </Button>
                  </div>
                }
              />
            ))}
          </div>
          {marketplaceTemplates.length === 0 && (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No community templates match your filters.
            </div>
          )}
        </>
      )}

      {!loading && tab === "proposal-kits" && (
        <div className="space-y-5">
          {proposalGroups.map((group) => (
            <section key={group.group} className="space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {group.group}
              </h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {group.templates.map((template) => (
                  <TemplateSummary
                    key={template.id}
                    title={template.name}
                    category={template.category}
                    subcategory={template.subcategory}
                    description={template.description}
                    keywords={template.keywords}
                    usageCount={template.usage_count}
                    ratingSum={template.rating_sum}
                    ratingCount={template.rating_count}
                    footer={
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleFork(template.id)}
                        disabled={saving}
                        className="w-full"
                      >
                        Fork Proposal Kit
                      </Button>
                    }
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      {!loading && tab === "compliance-matrices" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {complianceMatrices.map((template) => (
            <TemplateSummary
              key={template.id}
              title={template.name}
              category={template.category}
              subcategory={template.subcategory}
              description={template.description}
              keywords={template.keywords}
              usageCount={template.usage_count}
              ratingSum={template.rating_sum}
              ratingCount={template.rating_count}
              footer={
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleFork(template.id)}
                  disabled={saving}
                  className="w-full"
                >
                  Fork Compliance Matrix
                </Button>
              }
            />
          ))}
        </div>
      )}

      {!loading && tab === "my-library" && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Create Community Template</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="space-y-3" onSubmit={handleCreate}>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <input
                    value={newTemplateName}
                    onChange={(event) => setNewTemplateName(event.target.value)}
                    placeholder="Template name"
                    className="rounded-md border border-border px-3 py-2 text-sm"
                    required
                  />
                  <select
                    value={newTemplateCategory}
                    onChange={(event) => setNewTemplateCategory(event.target.value)}
                    className="rounded-md border border-border px-3 py-2 text-sm"
                  >
                    <option value="Proposal Structure">Proposal Structure</option>
                    <option value="Compliance Matrix">Compliance Matrix</option>
                    <option value="Technical">Technical</option>
                    <option value="Past Performance">Past Performance</option>
                  </select>
                </div>
                <input
                  value={newTemplateDescription}
                  onChange={(event) => setNewTemplateDescription(event.target.value)}
                  placeholder="Short description"
                  className="w-full rounded-md border border-border px-3 py-2 text-sm"
                  required
                />
                <textarea
                  value={newTemplateContent}
                  onChange={(event) => setNewTemplateContent(event.target.value)}
                  placeholder="Template content"
                  className="min-h-28 w-full rounded-md border border-border px-3 py-2 text-sm"
                  required
                />
                <label className="flex items-center gap-2 text-sm text-muted-foreground">
                  <input
                    type="checkbox"
                    checked={shareOnCreate}
                    onChange={(event) => setShareOnCreate(event.target.checked)}
                  />
                  Share to community after creation
                </label>
                <Button type="submit" disabled={saving}>
                  Create Template
                </Button>
              </form>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {myTemplates.map((template) => (
              <TemplateSummary
                key={template.id}
                title={template.name}
                category={template.category}
                subcategory={template.subcategory}
                description={template.description}
                keywords={template.keywords}
                usageCount={template.usage_count}
                ratingSum={template.rating_sum}
                ratingCount={template.rating_count}
                footer={
                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground">
                      {template.is_public ? "Shared to community" : "Private to your workspace"}
                    </p>
                    {!template.is_public && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handlePublish(template.id)}
                        disabled={saving}
                        className="w-full"
                      >
                        Share to Community
                      </Button>
                    )}
                  </div>
                }
              />
            ))}
          </div>
          {myTemplates.length === 0 && (
            <div className="rounded-md border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
              No private templates yet. Fork a community template or create one above.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
