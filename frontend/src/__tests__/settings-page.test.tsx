import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import SettingsPage from "@/app/(dashboard)/settings/page";
import { integrationApi, teamApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  integrationApi: {
    list: vi.fn(),
    create: vi.fn(),
  },
  teamApi: {
    list: vi.fn(),
    get: vi.fn(),
    updateMemberRole: vi.fn(),
  },
}));

const mockedIntegrationApi = vi.mocked(integrationApi);
const mockedTeamApi = vi.mocked(teamApi);

describe("SettingsPage", () => {
  beforeEach(() => {
    mockedIntegrationApi.list.mockResolvedValue([]);
    mockedTeamApi.list.mockResolvedValue([]);
  });

  it("renders settings header", async () => {
    render(<SettingsPage />);
    expect(
      await screen.findByText("Manage integrations and admin configuration")
    ).toBeInTheDocument();
    expect(await screen.findByText("Team Roles")).toBeInTheDocument();
  });
});
