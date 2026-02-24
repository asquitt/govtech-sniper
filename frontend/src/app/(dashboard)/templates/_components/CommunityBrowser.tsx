"use client";

import { Button } from "@/components/ui/button";
import type { MarketplaceTemplate } from "@/types";
import { TemplateSummary } from "./TemplateSummary";

interface CommunityBrowserProps {
  search: string;
  category: string;
  communityFilters: string[];
  marketplaceTemplates: MarketplaceTemplate[];
  marketplaceTotal: number;
  ratingByTemplate: Record<number, number>;
  saving: boolean;
  onSearchChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
  onRefresh: () => void;
  onFork: (templateId: number) => void;
  onRate: (templateId: number) => void;
  onRatingChange: (templateId: number, rating: number) => void;
}

export function CommunityBrowser({
  search,
  category,
  communityFilters,
  marketplaceTemplates,
  marketplaceTotal,
  ratingByTemplate,
  saving,
  onSearchChange,
  onCategoryChange,
  onRefresh,
  onFork,
  onRate,
  onRatingChange,
}: CommunityBrowserProps) {
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search community templates..."
          className="w-72 rounded-md border border-border px-3 py-2 text-sm"
        />
        <select
          value={category}
          onChange={(event) => onCategoryChange(event.target.value)}
          className="rounded-md border border-border px-3 py-2 text-sm"
        >
          <option value="">All categories</option>
          {communityFilters.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <Button size="sm" onClick={onRefresh}>
          Refresh Community
        </Button>
      </div>

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
                      onRatingChange(template.id, Number(event.target.value))
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
                    onClick={() => onRate(template.id)}
                    disabled={saving || !ratingByTemplate[template.id]}
                  >
                    Rate
                  </Button>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onFork(template.id)}
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
  );
}
