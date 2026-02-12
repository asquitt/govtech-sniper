import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ChatPanel } from "@/app/(dashboard)/dash/_components/chat-panel";

const sendMessage = vi.fn();
const stopStreaming = vi.fn();

vi.mock("@/lib/stores/dash-store", () => ({
  useDashStore: (selector?: (state: any) => unknown) => {
    const state = {
      messages: [],
      isLoading: false,
      error: null,
      selectedRfpId: null,
      sendMessage,
      stopStreaming,
    };
    return selector ? selector(state) : state;
  },
}));

class MockSpeechRecognition {
  continuous = false;
  interimResults = false;
  lang = "en-US";
  onstart: (() => void) | null = null;
  onresult: ((event: any) => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  onend: (() => void) | null = null;

  start() {
    this.onstart?.();
    this.onresult?.({
      results: [[{ transcript: "Show my pipeline" }]],
    });
    this.onend?.();
  }

  stop() {
    this.onend?.();
  }
}

describe("ChatPanel voice controls", () => {
  beforeEach(() => {
    sendMessage.mockReset();
    stopStreaming.mockReset();

    (window as any).SpeechRecognition = MockSpeechRecognition;
    (window as any).speechSynthesis = {
      cancel: vi.fn(),
      speak: vi.fn((utterance: any) => {
        utterance.onstart?.();
        utterance.onend?.();
      }),
    };
  });

  it("sends transcript through chat when voice input is used", async () => {
    const user = userEvent.setup();
    render(<ChatPanel />);

    await user.click(screen.getByRole("button", { name: "Voice" }));

    await waitFor(() => {
      expect(sendMessage).toHaveBeenCalledWith("Show my pipeline");
    });
  });
});
