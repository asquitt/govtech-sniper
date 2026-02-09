import { isLikelyOfficeHost } from "@/lib/office/host-detection";

describe("isLikelyOfficeHost", () => {
  it("returns true for Office-like user agents", () => {
    expect(
      isLikelyOfficeHost(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Office/16.0 Word"
      )
    ).toBe(true);
    expect(
      isLikelyOfficeHost(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Outlook Addin"
      )
    ).toBe(true);
  });

  it("returns false for non-Office user agents", () => {
    expect(
      isLikelyOfficeHost(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/122.0 Safari/537.36"
      )
    ).toBe(false);
    expect(isLikelyOfficeHost("")).toBe(false);
  });
});

