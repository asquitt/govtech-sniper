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
