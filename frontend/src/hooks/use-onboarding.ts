"use client";

import { useCallback, useState, useEffect } from "react";

const STORAGE_KEY = "onboarding_complete";

export function useOnboarding() {
  const [isComplete, setIsComplete] = useState(true);

  useEffect(() => {
    setIsComplete(localStorage.getItem(STORAGE_KEY) === "true");
  }, []);

  const markComplete = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, "true");
    setIsComplete(true);
  }, []);

  const reset = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setIsComplete(false);
  }, []);

  return { isComplete, markComplete, reset };
}
