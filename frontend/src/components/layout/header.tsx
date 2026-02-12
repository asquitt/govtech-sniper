"use client";

import React from "react";
import Link from "next/link";
import { Search, User, HelpCircle } from "lucide-react";
import { NotificationCenter } from "@/components/notifications/notification-center";
import { Button } from "@/components/ui/button";
import { GLOBAL_SEARCH_TOGGLE_EVENT } from "@/components/layout/global-search";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface HeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export function Header({ title, description, actions }: HeaderProps) {
  const handleSearchClick = () => {
    if (typeof window === "undefined") return;
    window.dispatchEvent(new Event(GLOBAL_SEARCH_TOGGLE_EVENT));
  };

  return (
    <TooltipProvider>
      <header className="flex items-center justify-between h-16 px-6 border-b border-border bg-card/50 backdrop-blur-sm">
        <div className="flex flex-col">
          <h1 className="text-xl font-bold text-foreground">{title}</h1>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {actions}

          {/* Search */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Open global search"
                onClick={handleSearchClick}
              >
                <Search className="w-5 h-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Search (Ctrl+K)</TooltipContent>
          </Tooltip>

          {/* Notifications */}
          <NotificationCenter />

          {/* Help */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button asChild variant="ghost" size="icon">
                <Link href="/help">
                  <HelpCircle className="w-5 h-5" />
                </Link>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Help & Documentation</TooltipContent>
          </Tooltip>

          {/* User Menu */}
          <Button variant="ghost" size="icon" className="ml-2">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <User className="w-4 h-4 text-primary" />
            </div>
          </Button>
        </div>
      </header>
    </TooltipProvider>
  );
}
