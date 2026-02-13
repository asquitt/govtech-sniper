"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  Download,
  ExternalLink,
  FileText,
  PenLine,
  Shield,
  SplitSquareHorizontal,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const FEATURES = [
  {
    icon: PenLine,
    title: "AI Draft & Rewrite",
    description:
      "Select text in Word, choose a rewrite mode (shorten, expand, improve), and let AI refine your proposal language to be clear, compliant, and persuasive.",
  },
  {
    icon: Shield,
    title: "Compliance Check",
    description:
      "Scan proposal sections for FAR/DFARS compliance issues. Get severity-ranked findings with fix suggestions and automatic document highlighting.",
  },
  {
    icon: SplitSquareHorizontal,
    title: "Section Sync",
    description:
      "Pull proposal sections from RFP Sniper into Word or push edits back. Keep your Word document and RFP Sniper workspace in sync without copy-pasting.",
  },
] as const;

const INSTALL_STEPS = [
  "Download the manifest XML file using the button below.",
  'In Word, go to Insert > My Add-ins > Upload My Add-in.',
  "Browse to the downloaded manifest file and click OK.",
  'The RFP Sniper tab will appear in the Word ribbon with AI Draft, Compliance Check, and Insert Section buttons.',
] as const;

export default function WordAddinPage() {
  const handleDownloadManifest = () => {
    const link = document.createElement("a");
    link.href = "/word-addin-manifest.xml";
    link.download = "rfpsniper-word-addin-manifest.xml";
    link.click();
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Link href="/settings/integrations">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div className="flex items-center gap-3">
          <FileText className="w-5 h-5 text-primary" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold">Microsoft Word Add-in</h1>
              <Badge variant="default">v1.0.0</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Draft, review, and refine proposals directly in Microsoft Word.
            </p>
          </div>
        </div>
      </div>

      {/* Features */}
      <Card className="border border-border">
        <CardHeader>
          <CardTitle className="text-base">Features</CardTitle>
          <CardDescription>
            Everything you need to write winning proposals without leaving Word.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {FEATURES.map((feature) => (
            <div key={feature.title} className="flex gap-3">
              <div className="mt-0.5 rounded-md border border-border bg-card p-2 h-fit">
                <feature.icon className="w-4 h-4 text-primary" />
              </div>
              <div>
                <p className="text-sm font-medium">{feature.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {feature.description}
                </p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Installation */}
      <Card className="border border-border">
        <CardHeader>
          <CardTitle className="text-base">Installation</CardTitle>
          <CardDescription>
            Sideload the add-in for your organization, or install from AppSource when available.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ol className="space-y-2">
            {INSTALL_STEPS.map((step, i) => (
              <li key={i} className="flex gap-2 text-sm">
                <CheckCircle2 className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                <span className="text-muted-foreground">{step}</span>
              </li>
            ))}
          </ol>

          <div className="flex flex-wrap gap-3 pt-2">
            <Button size="sm" onClick={handleDownloadManifest}>
              <Download className="w-4 h-4" />
              Download Manifest
            </Button>
            <Button size="sm" variant="outline" asChild>
              <a
                href="https://appsource.microsoft.com"
                target="_blank"
                rel="noopener noreferrer"
              >
                <ExternalLink className="w-4 h-4" />
                View on AppSource
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Requirements */}
      <Card className="border border-border">
        <CardHeader>
          <CardTitle className="text-base">Requirements</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            <li>Microsoft Word 2016 or later (Desktop or Web)</li>
            <li>WordApi requirement set 1.3 or higher</li>
            <li>Active RFP Sniper account with at least one proposal</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
