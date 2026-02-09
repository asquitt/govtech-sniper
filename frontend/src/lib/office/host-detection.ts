const OFFICE_HOST_PATTERN = /\b(Office|Word|Excel|PowerPoint|Outlook)\b/i;

export function isLikelyOfficeHost(userAgent: string): boolean {
  if (!userAgent) {
    return false;
  }
  return OFFICE_HOST_PATTERN.test(userAgent);
}

