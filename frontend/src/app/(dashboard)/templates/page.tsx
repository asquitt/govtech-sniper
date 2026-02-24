"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { templateApi, templateMarketplaceApi } from "@/lib/api";
import type { ProposalTemplate } from "@/lib/api";
import type { MarketplaceTemplate } from "@/types";
import { TemplateSummary } from "./_components/TemplateSummary";
import { CommunityBrowser } from "./_components/CommunityBrowser";
import { CreateTemplateForm } from "./_components/CreateTemplateForm";

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
        {(
          [
            { key: "community", label: "Community" },
            { key: "popular", label: "Popular" },
            { key: "proposal-kits", label: "Proposal Kits" },
            { key: "compliance-matrices", label: "Compliance Matrices" },
            { key: "my-library", label: "My Library" },
          ] as const
        ).map((item) => (
          <Button
            key={item.key}
            size="sm"
            variant={tab === item.key ? "default" : "outline"}
            onClick={() => setTab(item.key)}
          >
            {item.label}
          </Button>
        ))}
      </div>

      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      {success && (
        <div className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{success}</div>
      )}

      {loading ? (
        <div className="py-12 text-center text-muted-foreground">Loading templates...</div>
      ) : null}

      {!loading && (tab === "community" || tab === "popular") && (
        <CommunityBrowser
          search={search}
          category={category}
          communityFilters={COMMUNITY_FILTERS}
          marketplaceTemplates={marketplaceTemplates}
          marketplaceTotal={marketplaceTotal}
          ratingByTemplate={ratingByTemplate}
          saving={saving}
          onSearchChange={setSearch}
          onCategoryChange={setCategory}
          onRefresh={() => fetchCommunity()}
          onFork={handleFork}
          onRate={handleRate}
          onRatingChange={(templateId, rating) =>
            setRatingByTemplate((prev) => ({ ...prev, [templateId]: rating }))
          }
        />
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
          <CreateTemplateForm
            name={newTemplateName}
            description={newTemplateDescription}
            content={newTemplateContent}
            category={newTemplateCategory}
            shareOnCreate={shareOnCreate}
            saving={saving}
            onNameChange={setNewTemplateName}
            onDescriptionChange={setNewTemplateDescription}
            onContentChange={setNewTemplateContent}
            onCategoryChange={setNewTemplateCategory}
            onShareOnCreateChange={setShareOnCreate}
            onSubmit={handleCreate}
          />

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
