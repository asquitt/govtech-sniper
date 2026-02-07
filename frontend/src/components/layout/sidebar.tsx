"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Target,
  FileSearch,
  BarChart3,
  FolderOpen,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  LogOut,
  User,
  Users,
  DollarSign,
  GitBranch,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAuth } from "@/contexts/auth-context";

interface NavItem {
  title: string;
  href: string;
  icon: React.ElementType;
  badge?: string | number;
}

const navItems: NavItem[] = [
  {
    title: "Opportunities",
    href: "/opportunities",
    icon: FileSearch,
  },
  {
    title: "Analysis",
    href: "/analysis",
    icon: BarChart3,
  },
  {
    title: "Proposals",
    href: "/proposals",
    icon: FileSearch,
  },
  {
    title: "Knowledge Base",
    href: "/knowledge-base",
    icon: FolderOpen,
  },
  {
    title: "Dash",
    href: "/dash",
    icon: Sparkles,
  },
  {
    title: "Capture",
    href: "/capture",
    icon: Target,
  },
  {
    title: "Teaming",
    href: "/teaming",
    icon: Users,
  },
  {
    title: "Contracts",
    href: "/contracts",
    icon: FileSearch,
  },
  {
    title: "Revenue",
    href: "/revenue",
    icon: DollarSign,
  },
  {
    title: "Pipeline",
    href: "/pipeline",
    icon: GitBranch,
  },
  {
    title: "Forecasts",
    href: "/forecasts",
    icon: TrendingUp,
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
  },
];

interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

export function Sidebar({ collapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "flex flex-col h-screen bg-card border-r border-border transition-all duration-300",
          collapsed ? "w-16" : "w-64"
        )}
      >
        {/* Logo */}
        <div className="flex items-center h-16 px-4 border-b border-border">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/20 glow-primary">
              <Target className="w-5 h-5 text-primary" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span className="font-bold text-foreground">RFP Sniper</span>
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                  GovTech AI
                </span>
              </div>
            )}
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            const Icon = item.icon;

            const linkContent = (
              <Link
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                  isActive
                    ? "bg-primary/20 text-primary glow-primary"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                )}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!collapsed && (
                  <>
                    <span className="flex-1">{item.title}</span>
                    {item.badge && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-primary/20 text-primary">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </Link>
            );

            if (collapsed) {
              return (
                <Tooltip key={item.href}>
                  <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                  <TooltipContent side="right">{item.title}</TooltipContent>
                </Tooltip>
              );
            }

            return <React.Fragment key={item.href}>{linkContent}</React.Fragment>;
          })}
        </nav>

        {/* Feature Cards (when expanded) */}
        {!collapsed && (
          <div className="px-3 py-4 space-y-2">
            <div className="p-3 rounded-lg bg-gradient-to-br from-primary/10 to-accent/10 border border-primary/20">
              <div className="flex items-center gap-2 mb-1">
                <Sparkles className="w-4 h-4 text-primary" />
                <span className="text-xs font-semibold text-primary">
                  AI Powered
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground">
                Gemini 1.5 Pro analyzing your proposals
              </p>
            </div>
          </div>
        )}

        {/* Collapse Toggle */}
        <div className="p-2 border-t border-border">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-center"
            onClick={onToggle}
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4" />
                <span className="ml-2">Collapse</span>
              </>
            )}
          </Button>
        </div>

        {/* User Section */}
        <div
          className={cn(
            "border-t border-border",
            collapsed ? "px-2 py-3" : "px-3 py-3"
          )}
        >
          {user && (
            <div className={cn("flex items-center gap-3", collapsed && "justify-center")}>
              <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-primary" />
              </div>
              {!collapsed && (
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {user.full_name || user.email}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {user.tier} tier
                  </p>
                </div>
              )}
              {collapsed ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={logout}
                      className="h-8 w-8"
                    >
                      <LogOut className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">Sign out</TooltipContent>
                </Tooltip>
              ) : (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={logout}
                  className="h-8 w-8 flex-shrink-0"
                >
                  <LogOut className="w-4 h-4" />
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Status Bar */}
        <div
          className={cn(
            "flex items-center gap-2 px-4 py-3 border-t border-border bg-muted/30",
            collapsed && "justify-center px-2"
          )}
        >
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            {!collapsed && (
              <span className="text-xs text-muted-foreground">System Online</span>
            )}
          </div>
        </div>
      </aside>
    </TooltipProvider>
  );
}
