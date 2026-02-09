"use client";

import Script from "next/script";
import { isLikelyOfficeHost } from "@/lib/office/host-detection";

export function OfficeScriptLoader() {
  const shouldLoadOfficeScript =
    typeof navigator !== "undefined" &&
    isLikelyOfficeHost(navigator.userAgent);

  if (!shouldLoadOfficeScript) {
    return null;
  }

  return (
    <Script
      src="https://appsforoffice.microsoft.com/lib/1.1/hosted/office.js"
      strategy="afterInteractive"
    />
  );
}

