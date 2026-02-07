"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FileSearch,
  FileText,
  Sparkles,
  Target,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface MobileTab {
  title: string;
  href: string;
  icon: React.ElementType;
}

const tabs: MobileTab[] = [
  { title: "Opportunities", href: "/opportunities", icon: FileSearch },
  { title: "Proposals", href: "/proposals", icon: FileText },
  { title: "Dash", href: "/dash", icon: Sparkles },
  { title: "Capture", href: "/capture", icon: Target },
  { title: "Settings", href: "/settings", icon: Settings },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-zinc-800 bg-zinc-950/95 backdrop-blur-sm md:hidden">
      <ul className="flex items-center justify-around">
        {tabs.map((tab) => {
          const isActive =
            pathname === tab.href || pathname.startsWith(tab.href + "/");
          const Icon = tab.icon;

          return (
            <li key={tab.href} className="flex-1">
              <Link
                href={tab.href}
                className={cn(
                  "flex flex-col items-center gap-0.5 py-2 text-xs transition-colors",
                  isActive
                    ? "text-indigo-400"
                    : "text-zinc-500 hover:text-zinc-300"
                )}
              >
                <Icon className="h-5 w-5" />
                <span className="truncate">{tab.title}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
