import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Header } from "@/components/layout/header";
import { GLOBAL_SEARCH_TOGGLE_EVENT } from "@/components/layout/global-search";

vi.mock("@/components/notifications/notification-center", () => ({
  NotificationCenter: () => <div>Notifications</div>,
}));

describe("Header Search Trigger", () => {
  it("dispatches the global search toggle event", () => {
    const eventSpy = vi.fn();
    window.addEventListener(GLOBAL_SEARCH_TOGGLE_EVENT, eventSpy);

    render(<Header title="Test" description="Header test" />);
    fireEvent.click(screen.getByLabelText("Open global search"));

    expect(eventSpy).toHaveBeenCalledTimes(1);
    window.removeEventListener(GLOBAL_SEARCH_TOGGLE_EVENT, eventSpy);
  });
});
