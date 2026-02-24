"use client";

import React from "react";
import { FolderOpen, FileText, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { formatFileSize } from "@/lib/utils";

export interface KBStatsCardsProps {
  total: number;
  ready: number;
  totalCitations: number;
  totalSize: number;
}

export function KBStatsCards({ total, ready, totalCitations, totalSize }: KBStatsCardsProps) {
  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Documents</p>
              <p className="text-2xl font-bold">{total}</p>
            </div>
            <FolderOpen className="w-8 h-8 text-muted-foreground/30" />
          </div>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-accent/5 to-accent/10 border-accent/20">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Ready for AI</p>
              <p className="text-2xl font-bold text-accent">{ready}</p>
            </div>
            <Sparkles className="w-8 h-8 text-accent/30" />
          </div>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Citations</p>
              <p className="text-2xl font-bold text-primary">{totalCitations}</p>
            </div>
            <FileText className="w-8 h-8 text-primary/30" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Storage Used</p>
              <p className="text-2xl font-bold">{formatFileSize(totalSize)}</p>
            </div>
            <div className="w-8 h-8 flex items-center justify-center">
              <Progress value={15} className="w-8 h-8 rounded-full" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
