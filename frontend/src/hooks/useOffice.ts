"use client";

import { useEffect, useState } from "react";

interface OfficeState {
  /** Whether Office.onReady() has resolved */
  isReady: boolean;
  /** Whether running inside an Office host (Word, Excel, etc.) */
  isInOffice: boolean;
  /** The Office host type (e.g., "Word") or null if not in Office */
  hostType: string | null;
  /** Whether Office.js is still initializing */
  isLoading: boolean;
}

/**
 * Custom hook that wraps Office.onReady().
 * Gracefully handles running outside of Office (standalone browser).
 */
export function useOffice(): OfficeState {
  const [state, setState] = useState<OfficeState>({
    isReady: false,
    isInOffice: false,
    hostType: null,
    isLoading: true,
  });

  useEffect(() => {
    // Check if Office.js is loaded from CDN
    if (typeof Office === "undefined" || !Office.onReady) {
      setState({
        isReady: true,
        isInOffice: false,
        hostType: null,
        isLoading: false,
      });
      return;
    }

    Office.onReady((info) => {
      const isInOffice = !!info.host;
      setState({
        isReady: true,
        isInOffice,
        hostType: info.host || null,
        isLoading: false,
      });
    }).catch(() => {
      // Office.onReady failed — running outside Office
      setState({
        isReady: true,
        isInOffice: false,
        hostType: null,
        isLoading: false,
      });
    });
  }, []);

  return state;
}
