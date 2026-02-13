"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Sparkles, ArrowRight, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";

const fadeUp = {
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
};

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center pt-16">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,hsl(199_89%_48%/0.08),transparent_50%)]" />

      <div className="relative max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-0">
        <div className="lg:grid lg:grid-cols-2 lg:gap-16 items-center">
          {/* Left — Text */}
          <motion.div
            initial="initial"
            animate="animate"
            transition={{ staggerChildren: 0.12 }}
            className="text-center lg:text-left"
          >
            <motion.div variants={fadeUp} transition={{ duration: 0.5 }}>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 px-3 py-1 text-xs font-medium text-primary">
                <Sparkles className="w-3 h-3" />
                AI-Powered Proposal Automation
              </span>
            </motion.div>

            <motion.h1
              variants={fadeUp}
              transition={{ duration: 0.5 }}
              className="mt-6 text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground"
            >
              Win Government Contracts{" "}
              <span className="text-gradient">Faster</span>
            </motion.h1>

            <motion.p
              variants={fadeUp}
              transition={{ duration: 0.5 }}
              className="mt-6 text-lg text-muted-foreground max-w-xl mx-auto lg:mx-0"
            >
              From opportunity discovery to compliant proposal submission. RFP
              Sniper automates the entire GovTech capture lifecycle.
            </motion.p>

            <motion.div
              variants={fadeUp}
              transition={{ duration: 0.5 }}
              className="mt-8 flex flex-col sm:flex-row gap-3 justify-center lg:justify-start"
            >
              <Button size="lg" asChild>
                <Link href="/register">
                  Get Started Free <ArrowRight className="w-4 h-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="#how-it-works">
                  <Calendar className="w-4 h-4" /> Book a Demo
                </Link>
              </Button>
            </motion.div>
          </motion.div>

          {/* Right — Mockup */}
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-12 lg:mt-0"
          >
            <div className="glass rounded-xl p-4 glow-primary">
              {/* Simulated dashboard header */}
              <div className="flex items-center gap-2 mb-3 pb-3 border-b border-border/50">
                <div className="w-3 h-3 rounded-full bg-destructive/60" />
                <div className="w-3 h-3 rounded-full bg-warning/60" />
                <div className="w-3 h-3 rounded-full bg-accent/60" />
                <span className="ml-2 text-xs text-muted-foreground font-mono">
                  opportunities
                </span>
              </div>
              {/* Simulated rows */}
              {[
                { title: "DoD Cloud Migration", badge: "New", cls: "bg-primary/20 text-primary border-primary/30" },
                { title: "VA Health Records Modernization", badge: "Analyzing", cls: "bg-warning/20 text-warning border-warning/30" },
                { title: "USAF Cybersecurity Support", badge: "Ready", cls: "bg-accent/20 text-accent border-accent/30" },
                { title: "GSA IT Professional Services", badge: "Drafting", cls: "bg-primary/20 text-primary border-primary/30" },
              ].map((row) => (
                <div
                  key={row.title}
                  className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-muted/30 transition-colors"
                >
                  <span className="text-sm text-foreground">{row.title}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border ${row.cls}`}
                  >
                    {row.badge}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
