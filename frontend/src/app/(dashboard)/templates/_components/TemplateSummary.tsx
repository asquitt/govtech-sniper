"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface TemplateSummaryProps {
  title: string;
  category: string;
  subcategory?: string | null;
  description: string;
  keywords: string[];
  usageCount: number;
  ratingSum: number;
  ratingCount: number;
  footer?: React.ReactNode;
}

function averageRating(ratingSum: number, ratingCount: number) {
  if (ratingCount <= 0) return 0;
  return ratingSum / ratingCount;
}

export function TemplateSummary({
  title,
  category,
  subcategory,
  description,
  keywords,
  usageCount,
  ratingSum,
  ratingCount,
  footer,
}: TemplateSummaryProps) {
  const rating = averageRating(ratingSum, ratingCount);
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
