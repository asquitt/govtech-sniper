import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import SettingsPage from "@/app/(dashboard)/settings/page";
import { integrationApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  integrationApi: {
    list: vi.fn(),
    create: vi.fn(),
  },
}));

const mockedIntegrationApi = vi.mocked(integrationApi);

describe("SettingsPage", () => {
  beforeEach(() => {
    mockedIntegrationApi.list.mockResolvedValue([]);
  });

  it("renders settings header", async () => {
    render(<SettingsPage />);
    expect(
      await screen.findByText("Manage integrations and admin configuration")
    ).toBeInTheDocument();
  });
});
