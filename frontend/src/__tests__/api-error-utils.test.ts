import { describe, expect, it } from "vitest";
import { getApiErrorMessage, isStepUpRequiredError } from "@/lib/api/error";

describe("API error helpers", () => {
  it("detects step-up-required headers", () => {
    expect(
      isStepUpRequiredError({
        response: { headers: { "x-step-up-required": "true" } },
      })
    ).toBe(true);

    expect(
      isStepUpRequiredError({
        response: { headers: { "X-Step-Up-Required": "true" } },
      })
    ).toBe(true);

    expect(
      isStepUpRequiredError({
        response: { headers: { "x-step-up-required": "false" } },
      })
    ).toBe(false);
  });

  it("returns fallback message when detail is unavailable", () => {
    expect(getApiErrorMessage({}, "fallback")).toBe("fallback");
    expect(
      getApiErrorMessage({ response: { data: { detail: "boom" } } }, "fallback")
    ).toBe("boom");
  });
});
