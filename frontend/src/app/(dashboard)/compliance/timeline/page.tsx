"use client";

import React from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type MilestoneStatus = "complete" | "in_progress" | "upcoming";

interface Milestone {
  label: string;
  date: string;
  status: MilestoneStatus;
  description?: string;
}

interface ComplianceTrack {
  name: string;
  icon: string;
  milestones: Milestone[];
}

const STATUS_STYLES: Record<MilestoneStatus, { dot: string; line: string; badge: string; badgeVariant: "success" | "default" | "secondary" }> = {
  complete: {
    dot: "bg-green-500 border-green-300 shadow-[0_0_8px_rgba(34,197,94,0.4)]",
    line: "bg-green-500",
    badge: "",
    badgeVariant: "success",
  },
  in_progress: {
    dot: "bg-blue-500 border-blue-300 shadow-[0_0_8px_rgba(59,130,246,0.4)]",
    line: "bg-blue-500",
    badge: "",
    badgeVariant: "default",
  },
  upcoming: {
    dot: "bg-muted-foreground/40 border-muted-foreground/20",
    line: "bg-muted-foreground/20",
    badge: "",
    badgeVariant: "secondary",
  },
};

const STATUS_LABEL: Record<MilestoneStatus, string> = {
  complete: "Complete",
  in_progress: "In Progress",
  upcoming: "Upcoming",
};

const TRACKS: ComplianceTrack[] = [
  {
    name: "FedRAMP Moderate",
    icon: "shield",
    milestones: [
      {
        label: "Complete System Security Plan (SSP)",
        date: "Q2 2026",
        status: "upcoming",
        description: "Full SSP documentation covering all 325 moderate baseline controls.",
      },
      {
        label: "Engage 3PAO for readiness assessment",
        date: "Q3 2026",
        status: "upcoming",
        description: "Third-party assessment organization engagement and readiness review.",
      },
      {
        label: "Submit FedRAMP Moderate package",
        date: "Q4 2026",
        status: "upcoming",
        description: "Final package submission to the FedRAMP PMO for authorization.",
      },
    ],
  },
  {
    name: "CMMC Level 2",
    icon: "lock",
    milestones: [
      {
        label: "Self-assessment complete",
        date: "Q2 2026",
        status: "upcoming",
        description: "Internal self-assessment against all 110 CMMC Level 2 practices.",
      },
      {
        label: "C3PAO engagement",
        date: "Q3 2026",
        status: "upcoming",
        description: "Certified third-party assessor organization contracted for formal assessment.",
      },
      {
        label: "Certification target",
        date: "Q4 2026",
        status: "upcoming",
        description: "CMMC Level 2 certification achieved for CUI handling.",
      },
    ],
  },
  {
    name: "SOC 2 Type II",
    icon: "clipboard",
    milestones: [
      {
        label: "Controls documentation",
        date: "Q1 2026",
        status: "in_progress",
        description: "Documenting all security, availability, and confidentiality controls.",
      },
      {
        label: "Gap remediation",
        date: "Q2 2026",
        status: "upcoming",
        description: "Addressing identified gaps in control implementation.",
      },
      {
        label: "Audit engagement",
        date: "Q3 2026",
        status: "upcoming",
        description: "Engaging CPA firm for the formal SOC 2 Type II audit period.",
      },
      {
        label: "Type II report",
        date: "Q1 2027",
        status: "upcoming",
        description: "SOC 2 Type II report issued after observation period.",
      },
    ],
  },
  {
    name: "NIST 800-171",
    icon: "book",
    milestones: [
      {
        label: "Controls aligned",
        date: "Current",
        status: "complete",
        description: "All 110 security requirements mapped to platform controls.",
      },
      {
        label: "Documentation in progress",
        date: "Ongoing",
        status: "in_progress",
        description: "System Security Plan and POA&M documentation being finalized.",
      },
    ],
  },
];

function TrackIcon({ icon }: { icon: string }) {
  switch (icon) {
    case "shield":
      return (
        <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      );
    case "lock":
      return (
        <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      );
    case "clipboard":
      return (
        <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
          <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
        </svg>
      );
    case "book":
      return (
        <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
      );
    default:
      return null;
  }
}

function TimelineTrack({ track }: { track: ComplianceTrack }) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-lg">
          <span className="text-primary">
            <TrackIcon icon={track.icon} />
          </span>
          {track.name}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative">
          {track.milestones.map((milestone, idx) => {
            const styles = STATUS_STYLES[milestone.status];
            const isLast = idx === track.milestones.length - 1;

            return (
              <div key={milestone.label} className="relative flex gap-4 pb-8 last:pb-0">
                {/* Vertical line */}
                <div className="flex flex-col items-center">
                  <div
                    className={`w-3.5 h-3.5 rounded-full border-2 flex-shrink-0 ${styles.dot}`}
                  />
                  {!isLast && (
                    <div className={`w-0.5 flex-1 mt-1 ${styles.line}`} />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 -mt-0.5 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="text-sm font-medium">{milestone.label}</span>
                    <Badge variant={styles.badgeVariant} className="text-[10px]">
                      {STATUS_LABEL[milestone.status]}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mb-1">{milestone.date}</p>
                  {milestone.description && (
                    <p className="text-xs text-muted-foreground/80">{milestone.description}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default function ComplianceTimelinePage() {
  const completedCount = TRACKS.reduce(
    (sum, t) => sum + t.milestones.filter((m) => m.status === "complete").length,
    0
  );
  const inProgressCount = TRACKS.reduce(
    (sum, t) => sum + t.milestones.filter((m) => m.status === "in_progress").length,
    0
  );
  const totalCount = TRACKS.reduce((sum, t) => sum + t.milestones.length, 0);

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Compliance Roadmap"
        description="FedRAMP, CMMC, SOC 2, and NIST 800-171 certification timeline"
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Summary bar */}
        <div className="flex flex-wrap items-center gap-4">
          <Link href="/compliance">
            <Button variant="outline" size="sm">
              &larr; Back to Dashboard
            </Button>
          </Link>
          <div className="flex items-center gap-3 ml-auto text-sm">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
              {completedCount} Complete
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
              {inProgressCount} In Progress
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-muted-foreground/40" />
              {totalCount - completedCount - inProgressCount} Upcoming
            </span>
          </div>
        </div>

        {/* Timeline tracks */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {TRACKS.map((track) => (
            <TimelineTrack key={track.name} track={track} />
          ))}
        </div>

        {/* Footer note */}
        <p className="text-xs text-muted-foreground text-center pt-2">
          Timeline updated February 2026. Dates are targets and subject to change based on assessor availability.
        </p>
      </div>
    </div>
  );
}
