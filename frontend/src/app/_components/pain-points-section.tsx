"use client";

import { motion } from "framer-motion";
import { XCircle, CheckCircle2 } from "lucide-react";

const BEFORE = [
  "Hours searching SAM.gov manually every day",
  "Reading 200-page RFPs line by line",
  "Writing proposals from scratch every time",
  "Missing compliance requirements in final review",
];

const AFTER = [
  "AI monitors SAM.gov and alerts you to matches",
  "Automated section extraction in minutes",
  "AI-drafted sections with compliance tracing",
  "Built-in requirement tracking — nothing missed",
];

export function PainPointsSection() {
  return (
    <section className="py-20 scroll-mt-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-3xl sm:text-4xl font-bold text-center mb-12"
        >
          Stop Losing Proposals to{" "}
          <span className="text-gradient">Manual Processes</span>
        </motion.h2>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Before */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="glass rounded-xl p-6 border-destructive/30"
          >
            <h3 className="text-lg font-semibold text-destructive mb-4">
              Before RFP Sniper
            </h3>
            <ul className="space-y-3">
              {BEFORE.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <XCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
                  <span className="text-sm text-muted-foreground">{item}</span>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* After */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="glass rounded-xl p-6 border-accent/30"
          >
            <h3 className="text-lg font-semibold text-accent mb-4">
              With RFP Sniper
            </h3>
            <ul className="space-y-3">
              {AFTER.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-accent shrink-0 mt-0.5" />
                  <span className="text-sm text-muted-foreground">{item}</span>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
