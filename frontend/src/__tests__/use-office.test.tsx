import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { useOffice } from "@/hooks/useOffice";

function Probe() {
  const { isReady, isInOffice, hostType, isLoading } = useOffice();
  return (
    <div>
      <span data-testid="ready">{String(isReady)}</span>
      <span data-testid="inOffice">{String(isInOffice)}</span>
      <span data-testid="host">{hostType ?? ""}</span>
      <span data-testid="loading">{String(isLoading)}</span>
    </div>
  );
}

describe("useOffice", () => {
  afterEach(() => {
    delete (globalThis as { Office?: unknown }).Office;
    vi.restoreAllMocks();
  });

  it("falls back to browser mode when Office is unavailable", async () => {
    render(<Probe />);

    await waitFor(() => {
      expect(screen.getByTestId("ready")).toHaveTextContent("true");
      expect(screen.getByTestId("inOffice")).toHaveTextContent("false");
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });
  });

  it("does not update state after unmount when Office.onReady resolves later", async () => {
    let resolveReady: (() => void) | null = null;

    (globalThis as { Office?: { onReady: (cb: (info: { host: string | null }) => void) => Promise<void> } }).Office = {
      onReady: (cb) =>
        new Promise<void>((resolve) => {
          resolveReady = () => {
            cb({ host: "Word" });
            resolve();
          };
        }),
    };

    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { unmount } = render(<Probe />);

    unmount();
    await act(async () => {
      resolveReady?.();
      await Promise.resolve();
    });

    const warningSeen = consoleErrorSpy.mock.calls.some((call) =>
      call.some(
        (arg) =>
          typeof arg === "string" &&
          arg.includes("Can't perform a React state update on a component that hasn't mounted yet")
      )
    );

    expect(warningSeen).toBe(false);
  });
});

