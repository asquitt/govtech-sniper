import { describe, expect, it } from "vitest";

import { getApiErrorDetail, getApiErrorMessage } from "./error";

describe("api error helpers", () => {
  it("returns detail when present in axios-like error response", () => {
    const error = {
      response: {
        data: {
          detail: "SAM.gov rate limit reached. Retry in about 60 seconds.",
        },
      },
    };

    expect(getApiErrorDetail(error)).toBe(
      "SAM.gov rate limit reached. Retry in about 60 seconds."
    );
  });

  it("returns null detail for malformed error payloads", () => {
    expect(getApiErrorDetail(null)).toBeNull();
    expect(getApiErrorDetail(new Error("boom"))).toBeNull();
    expect(getApiErrorDetail({ response: { data: { detail: 123 } } })).toBeNull();
  });

  it("falls back when no detail is available", () => {
    expect(getApiErrorMessage(new Error("boom"), "Fallback")).toBe("Fallback");
  });
});
