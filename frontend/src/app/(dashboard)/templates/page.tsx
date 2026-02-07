"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { templateMarketplaceApi } from "@/lib/api";
import type { MarketplaceTemplate } from "@/types";

type TabView = "browse" | "popular";

function StarRating({ ratingSum, ratingCount }: { ratingSum: number; ratingCount: number }) {
  const avg = ratingCount > 0 ? ratingSum / ratingCount : 0;
  const fullStars = Math.floor(avg);
  const hasHalf = avg - fullStars >= 0.5;

  return (
    <div className="flex items-center gap-1 text-sm text-gray-500">
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={i <= fullStars ? "text-yellow-500" : i === fullStars + 1 && hasHalf ? "text-yellow-300" : "text-gray-300"}>
          ★
        </span>
      ))}
      <span className="ml-1">({ratingCount})</span>
    </div>
  );
}

function TemplateCard({
  template,
  onFork,
  forking,
}: {
  template: MarketplaceTemplate;
  onFork: (id: number) => void;
  forking: number | null;
}) {
  return (
    <Card className="flex flex-col justify-between">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base leading-tight">{template.name}</CardTitle>
          <Badge variant="secondary" className="shrink-0 text-xs">
            {template.category}
          </Badge>
        </div>
        {template.subcategory && (
          <span className="text-xs text-gray-500">{template.subcategory}</span>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm text-gray-600 line-clamp-2">{template.description}</p>
        <div className="flex flex-wrap gap-1">
          {template.keywords.slice(0, 4).map((kw) => (
            <Badge key={kw} variant="outline" className="text-xs">
              {kw}
            </Badge>
          ))}
        </div>
        <div className="flex items-center justify-between">
          <StarRating ratingSum={template.rating_sum} ratingCount={template.rating_count} />
          <span className="text-xs text-gray-400">{template.usage_count} uses</span>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => onFork(template.id)}
          disabled={forking === template.id}
        >
          {forking === template.id ? "Forking..." : "Fork to Library"}
        </Button>
      </CardContent>
    </Card>
  );
}

export default function TemplatesPage() {
  const [tab, setTab] = useState<TabView>("browse");
  const [templates, setTemplates] = useState<MarketplaceTemplate[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [forking, setForking] = useState<number | null>(null);

  const fetchBrowse = useCallback(async (q?: string, cat?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = { limit: 40, offset: 0 };
      if (q) params.q = q;
      if (cat) params.category = cat;
      const res = await templateMarketplaceApi.browse(params);
      setTemplates(res.data.items);
      setTotal(res.data.total);
    } catch {
      setError("Failed to load marketplace templates.");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPopular = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await templateMarketplaceApi.popular();
      setTemplates(res.data);
      setTotal(res.data.length);
    } catch {
      setError("Failed to load popular templates.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === "browse") {
      fetchBrowse(search || undefined, category || undefined);
    } else {
      fetchPopular();
    }
  }, [tab, fetchBrowse, fetchPopular, search, category]);

  const handleFork = async (id: number) => {
    setForking(id);
    try {
      await templateMarketplaceApi.fork(id);
      // Refresh to update counts
      if (tab === "browse") {
        await fetchBrowse(search || undefined, category || undefined);
      } else {
        await fetchPopular();
      }
    } catch {
      setError("Failed to fork template.");
    } finally {
      setForking(null);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchBrowse(search || undefined, category || undefined);
  };

  const categories = [
    "Past Performance",
    "Technical",
    "Quality",
    "Personnel",
    "Security",
  ];

  return (
    <div className="flex flex-col gap-6 p-6">
      <Header
        title="Template Marketplace"
        description="Browse, fork, and rate community templates for your proposals."
      />

      {/* Tabs */}
      <div className="flex gap-2">
        <Button
          variant={tab === "browse" ? "default" : "outline"}
          size="sm"
          onClick={() => setTab("browse")}
        >
          Browse
        </Button>
        <Button
          variant={tab === "popular" ? "default" : "outline"}
          size="sm"
          onClick={() => setTab("popular")}
        >
          Popular
        </Button>
      </div>

      {/* Search & Filter (browse tab only) */}
      {tab === "browse" && (
        <form onSubmit={handleSearch} className="flex flex-wrap gap-3">
          <input
            type="text"
            placeholder="Search templates..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <Button type="submit" size="sm">
            Search
          </Button>
        </form>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {/* Loading */}
      {loading && (
        <div className="py-12 text-center text-gray-500">Loading templates...</div>
      )}

      {/* Results */}
      {!loading && templates.length === 0 && (
        <div className="py-12 text-center text-gray-500">
          No templates found. Try adjusting your search.
        </div>
      )}

      {!loading && templates.length > 0 && (
        <>
          <p className="text-sm text-gray-500">{total} template{total !== 1 ? "s" : ""} found</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {templates.map((t) => (
              <TemplateCard key={t.id} template={t} onFork={handleFork} forking={forking} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
