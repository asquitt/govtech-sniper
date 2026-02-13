"use client";

import { motion } from "framer-motion";
import {
  FileSearch,
  BarChart3,
  Sparkles,
  GitBranch,
  Users,
  ClipboardCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface Feature {
  icon: LucideIcon;
  name: string;
  description: string;
  bullets: string[];
  span: number; // 1 or 2 columns on lg
}

const FEATURES: Feature[] = [
  {
    icon: FileSearch,
    name: "Opportunity Intelligence",
    description: "AI-powered SAM.gov monitoring and matching",
    bullets: [
      "Daily scans with smart filters",
      "Capability matching scores",
      "Set-aside and NAICS tracking",
    ],
    span: 2,
  },
  {
    icon: BarChart3,
    name: "RFP Analysis",
    description: "Extract requirements from complex solicitations",
    bullets: [
      "Sections C/H/L/M/PWS parsing",
      "Evaluation criteria extraction",
      "Compliance matrix generation",
    ],
    span: 1,
  },
  {
    icon: Sparkles,
    name: "Proposal Drafting",
    description: "AI-generated compliant proposal sections",
    bullets: [
      "Writing plans per section",
      "Source tracing to RFP",
      "Rich text editor with export",
    ],
    span: 1,
  },
  {
    icon: GitBranch,
    name: "Capture Management",
    description: "Plan and track your capture pipeline",
    bullets: [
      "Capture plans with milestones",
      "Partner and resource tracking",
      "Custom fields per opportunity",
    ],
    span: 2,
  },
  {
    icon: Users,
    name: "Teaming Network",
    description: "Find and evaluate teaming partners",
    bullets: [
      "Partner fit analysis",
      "Teaming request workflow",
      "Past performance matching",
    ],
    span: 2,
  },
  {
    icon: ClipboardCheck,
    name: "Contract Management",
    description: "Track deliverables from award to closeout",
    bullets: [
      "CLINs, mods, and deliverables",
      "CPARS evidence tracking",
      "Status reporting dashboard",
    ],
    span: 1,
  },
];

export function FeatureGrid() {
  return (
    <section id="features" className="py-20 scroll-mt-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl sm:text-4xl font-bold">
            Everything You Need to{" "}
            <span className="text-gradient">Win</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
            Six integrated modules that take you from opportunity to award.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={feature.name}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className={`glass rounded-xl p-6 hover:border-primary/50 transition-all duration-300 ${
                  feature.span === 2 ? "lg:col-span-2" : ""
                }`}
              >
                <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-primary" />
                </div>
                <h3 className="font-semibold text-foreground mb-1">
                  {feature.name}
                </h3>
                <p className="text-sm text-muted-foreground mb-3">
                  {feature.description}
                </p>
                <ul className="space-y-1">
                  {feature.bullets.map((b) => (
                    <li
                      key={b}
                      className="text-xs text-muted-foreground/80 flex items-center gap-1.5"
                    >
                      <span className="w-1 h-1 rounded-full bg-primary/60" />
                      {b}
                    </li>
                  ))}
                </ul>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
