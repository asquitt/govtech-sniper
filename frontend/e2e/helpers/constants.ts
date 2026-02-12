export const TEST_USER = {
  fullName: "E2E Test User",
  email: `e2e-test-${Date.now()}@example.com`,
  password: "TestPassword1!",
  companyName: "E2E Corp",
};

export const STORAGE_KEYS = {
  accessToken: "rfp_sniper_access_token",
  refreshToken: "rfp_sniper_refresh_token",
};

export const NAV_ITEMS = [
  { title: "Opportunities", href: "/opportunities" },
  { title: "Analysis", href: "/analysis" },
  { title: "Proposals", href: "/proposals" },
  { title: "Knowledge Base", href: "/knowledge-base" },
  { title: "Dash", href: "/dash" },
  { title: "Agents", href: "/agents" },
  { title: "Capture", href: "/capture" },
  { title: "Teaming", href: "/teaming" },
  { title: "Collaboration", href: "/collaboration" },
  { title: "Contacts", href: "/contacts" },
  { title: "Contracts", href: "/contracts" },
  { title: "Revenue", href: "/revenue" },
  { title: "Pipeline", href: "/pipeline" },
  { title: "Forecasts", href: "/forecasts" },
  { title: "Analytics", href: "/analytics" },
  { title: "Intelligence", href: "/intelligence" },
  { title: "Events", href: "/events" },
  { title: "Signals", href: "/signals" },
  { title: "Compliance", href: "/compliance" },
  { title: "Reports", href: "/reports" },
  { title: "Templates", href: "/templates" },
  { title: "Word Add-in", href: "/word-addin" },
  { title: "Admin", href: "/admin" },
  { title: "Diagnostics", href: "/diagnostics" },
  { title: "Help", href: "/help" },
  { title: "Settings", href: "/settings" },
  { title: "Notifications", href: "/settings/notifications" },
] as const;
