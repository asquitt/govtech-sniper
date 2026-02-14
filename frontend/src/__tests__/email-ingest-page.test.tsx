import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import EmailIngestPage from "@/app/(dashboard)/settings/email-ingest/page";
import { collaborationApi } from "@/lib/api";
import { emailIngestApi } from "@/lib/api/email-ingest";

vi.mock("@/lib/api", () => ({
  collaborationApi: {
    listWorkspaces: vi.fn(),
  },
}));

vi.mock("@/lib/api/email-ingest", () => ({
  emailIngestApi: {
    createConfig: vi.fn(),
    listConfigs: vi.fn(),
    listHistory: vi.fn(),
    updateConfig: vi.fn(),
    deleteConfig: vi.fn(),
    testConnection: vi.fn(),
    reprocess: vi.fn(),
    syncNow: vi.fn(),
  },
}));

const mockedCollaborationApi = vi.mocked(collaborationApi);
const mockedEmailIngestApi = vi.mocked(emailIngestApi);

describe("EmailIngestPage", () => {
  beforeEach(() => {
    mockedEmailIngestApi.listConfigs.mockResolvedValue([]);
    mockedEmailIngestApi.listHistory.mockResolvedValue({ items: [], total: 0 });
    mockedEmailIngestApi.createConfig.mockResolvedValue({
      id: 1,
      user_id: 1,
      workspace_id: 7,
      imap_server: "imap.example.com",
      imap_port: 993,
      email_address: "capture@example.com",
      folder: "INBOX",
      is_enabled: true,
      auto_create_rfps: true,
      min_rfp_confidence: 0.6,
      last_checked_at: null,
      created_at: "2026-02-14T00:00:00Z",
      updated_at: "2026-02-14T00:00:00Z",
    });
    mockedEmailIngestApi.syncNow.mockResolvedValue({
      configs_checked: 1,
      fetched: 2,
      duplicates: 0,
      poll_errors: 0,
      processed: 2,
      created_rfps: 1,
      inbox_forwarded: 1,
      process_errors: 0,
    });
    mockedCollaborationApi.listWorkspaces.mockResolvedValue([
      {
        id: 7,
        owner_id: 1,
        rfp_id: null,
        name: "Capture Workspace",
        description: null,
        member_count: 1,
        created_at: "2026-02-14T00:00:00Z",
        updated_at: "2026-02-14T00:00:00Z",
      },
    ]);
  });

  it("runs sync now and renders summary", async () => {
    render(<EmailIngestPage />);

    const syncButton = await screen.findByRole("button", { name: "Run Sync Now" });
    fireEvent.click(syncButton);

    await waitFor(() => {
      expect(mockedEmailIngestApi.syncNow).toHaveBeenCalledWith({
        run_poll: true,
        run_process: true,
        poll_limit: 50,
        process_limit: 100,
      });
    });

    expect(
      await screen.findByText(
        "Sync complete: fetched 2, processed 2, created 1 opportunities.",
      ),
    ).toBeInTheDocument();
  });

  it("creates a config with workspace routing and confidence threshold", async () => {
    render(<EmailIngestPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Add Account" }));

    fireEvent.change(screen.getByLabelText("IMAP Server"), {
      target: { value: "imap.example.com" },
    });
    fireEvent.change(screen.getByLabelText("IMAP Port"), {
      target: { value: "993" },
    });
    fireEvent.change(screen.getByLabelText("Email Address"), {
      target: { value: "capture@example.com" },
    });
    fireEvent.change(screen.getByLabelText("App Password"), {
      target: { value: "secret" },
    });
    fireEvent.change(screen.getByLabelText("Folder"), {
      target: { value: "INBOX" },
    });
    fireEvent.change(screen.getByLabelText("Team Workspace (Optional)"), {
      target: { value: "7" },
    });
    fireEvent.change(screen.getByLabelText("Minimum RFP Confidence (0-1)"), {
      target: { value: "0.6" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save Configuration" }));

    await waitFor(() => {
      expect(mockedEmailIngestApi.createConfig).toHaveBeenCalledWith({
        imap_server: "imap.example.com",
        imap_port: 993,
        email_address: "capture@example.com",
        password: "secret",
        folder: "INBOX",
        workspace_id: 7,
        auto_create_rfps: true,
        min_rfp_confidence: 0.6,
      });
    });
  });
});
