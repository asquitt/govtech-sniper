import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import CollaborationPortalPage from "@/app/(dashboard)/collaboration/portal/[workspaceId]/page";
import { collaborationApi } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useParams: () => ({ workspaceId: "12" }),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  collaborationApi: {
    getPortal: vi.fn(),
    listWorkspaces: vi.fn(),
  },
}));

const mockedCollaborationApi = vi.mocked(collaborationApi);

describe("CollaborationPortalPage", () => {
  it("renders shared contract feed labels from portal payload", async () => {
    mockedCollaborationApi.listWorkspaces.mockResolvedValue([
      {
        id: 12,
        owner_id: 1,
        name: "Partner Workspace",
        description: "Shared artifacts",
        member_count: 2,
        created_at: "2026-02-10T12:00:00Z",
        updated_at: "2026-02-10T12:00:00Z",
      },
    ]);
    mockedCollaborationApi.getPortal.mockResolvedValue({
      workspace_name: "Partner Workspace",
      workspace_description: "Shared artifacts",
      rfp_title: "Modernization Support",
      shared_items: [
        {
          id: 1,
          workspace_id: 12,
          data_type: "contract_feed",
          entity_id: 1003,
          label: "NASA SEWP V",
          requires_approval: false,
          approval_status: "approved",
          approved_by_user_id: 1,
          approved_at: "2026-02-10T12:00:00Z",
          expires_at: null,
          partner_user_id: null,
          created_at: "2026-02-10T12:00:00Z",
        },
      ],
      members: [],
    });

    render(<CollaborationPortalPage />);

    expect(await screen.findByText("Partner Workspace")).toBeInTheDocument();
    expect(await screen.findByText("NASA SEWP V")).toBeInTheDocument();
  });

  it("renders workspace switcher when multiple portal workspaces are accessible", async () => {
    mockedCollaborationApi.listWorkspaces.mockResolvedValue([
      {
        id: 12,
        owner_id: 1,
        name: "Workspace One",
        description: null,
        member_count: 2,
        created_at: "2026-02-10T12:00:00Z",
        updated_at: "2026-02-10T12:00:00Z",
      },
      {
        id: 44,
        owner_id: 1,
        name: "Workspace Two",
        description: null,
        member_count: 2,
        created_at: "2026-02-10T12:00:00Z",
        updated_at: "2026-02-10T12:00:00Z",
      },
    ]);
    mockedCollaborationApi.getPortal.mockResolvedValue({
      workspace_name: "Workspace One",
      workspace_description: null,
      rfp_title: null,
      shared_items: [],
      members: [],
    });

    render(<CollaborationPortalPage />);

    expect(await screen.findByLabelText("Switch Workspace")).toBeInTheDocument();
    expect(await screen.findByRole("option", { name: "Workspace Two" })).toBeInTheDocument();
  });
});
