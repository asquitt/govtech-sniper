export function getApiErrorDetail(error: unknown): string | null {
  if (typeof error !== "object" || error === null) {
    return null;
  }

  const detail = (
    error as { response?: { data?: { detail?: unknown } } }
  ).response?.data?.detail;

  return typeof detail === "string" ? detail : null;
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  return getApiErrorDetail(error) ?? fallback;
}

export function isStepUpRequiredError(error: unknown): boolean {
  if (typeof error !== "object" || error === null) {
    return false;
  }
  const headers = (
    error as { response?: { headers?: Record<string, unknown> } }
  ).response?.headers;
  if (!headers) {
    return false;
  }
  const rawHeaderValue =
    headers["x-step-up-required"] ?? headers["X-Step-Up-Required"];
  return String(rawHeaderValue ?? "").toLowerCase() === "true";
}
