"use client";

import { motion } from "framer-motion";

export function SocialProofBar() {
  return (
    <motion.section
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      className="py-12 border-y border-border/50"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <p className="text-sm text-muted-foreground mb-8">
          Trusted by government contractors nationwide
        </p>
        <div className="flex items-center justify-center gap-8 flex-wrap">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="w-28 h-10 rounded-lg bg-muted/50 flex items-center justify-center"
            >
              <span className="text-xs text-muted-foreground/50">
                Partner {i}
              </span>
            </div>
          ))}
        </div>
      </div>
    </motion.section>
  );
}
