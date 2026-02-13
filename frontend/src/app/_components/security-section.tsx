"use client";

import { motion } from "framer-motion";
import { ShieldCheck, Lock, Shield, UserCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface Badge {
  icon: LucideIcon;
  title: string;
  description: string;
}

const BADGES: Badge[] = [
  {
    icon: ShieldCheck,
    title: "SOC 2 Type II",
    description: "Annual audit compliance",
  },
  {
    icon: Lock,
    title: "AES-256 Encryption",
    description: "Data encrypted at rest and in transit",
  },
  {
    icon: Shield,
    title: "CMMC Readiness",
    description: "Level 2 aligned controls",
  },
  {
    icon: UserCheck,
    title: "RBAC",
    description: "Role-based access on every endpoint",
  },
];

export function SecuritySection() {
  return (
    <section id="security" className="py-20 scroll-mt-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl sm:text-4xl font-bold">
            Enterprise-Grade{" "}
            <span className="text-gradient">Security</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
            Built for organizations handling controlled unclassified information.
          </p>
        </motion.div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {BADGES.map((badge, i) => {
            const Icon = badge.icon;
            return (
              <motion.div
                key={badge.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="glass rounded-xl p-6 text-center"
              >
                <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center mx-auto mb-3">
                  <Icon className="w-5 h-5 text-primary" />
                </div>
                <h3 className="font-semibold text-foreground text-sm mb-1">
                  {badge.title}
                </h3>
                <p className="text-xs text-muted-foreground">
                  {badge.description}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
