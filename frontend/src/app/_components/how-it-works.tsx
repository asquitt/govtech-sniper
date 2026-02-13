"use client";

import { motion } from "framer-motion";
import { FileSearch, BarChart3, Sparkles, Target } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface Step {
  icon: LucideIcon;
  label: string;
  title: string;
  description: string;
}

const STEPS: Step[] = [
  {
    icon: FileSearch,
    label: "01",
    title: "Find",
    description:
      "AI scans SAM.gov daily and surfaces opportunities matched to your capabilities.",
  },
  {
    icon: BarChart3,
    label: "02",
    title: "Analyze",
    description:
      "Deep Read extracts every requirement, evaluation criterion, and compliance need.",
  },
  {
    icon: Sparkles,
    label: "03",
    title: "Draft",
    description:
      "AI generates compliant proposal sections with source tracing to the RFP.",
  },
  {
    icon: Target,
    label: "04",
    title: "Win",
    description:
      "Export polished proposals to Word, ready for review and submission.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 scroll-mt-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-3xl sm:text-4xl font-bold text-center mb-16"
        >
          From Discovery to Award in{" "}
          <span className="text-gradient">Four Steps</span>
        </motion.h2>

        <div className="relative">
          {/* Connecting line — desktop */}
          <div className="hidden lg:block absolute top-7 left-[10%] right-[10%] h-px bg-gradient-to-r from-primary/30 via-primary/60 to-accent/30" />

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-10 lg:gap-6">
            {STEPS.map((step, i) => {
              const Icon = step.icon;
              return (
                <motion.div
                  key={step.title}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.12 }}
                  className="flex flex-col items-center text-center relative"
                >
                  <div className="relative mb-4">
                    <div className="w-14 h-14 rounded-full bg-primary/20 flex items-center justify-center glow-primary">
                      <Icon className="w-6 h-6 text-primary" />
                    </div>
                    <span className="absolute -top-2 -right-2 text-[10px] font-mono text-primary bg-background px-1 rounded">
                      {step.label}
                    </span>
                  </div>
                  <h3 className="font-semibold text-foreground mb-2">
                    {step.title}
                  </h3>
                  <p className="text-sm text-muted-foreground max-w-xs">
                    {step.description}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
