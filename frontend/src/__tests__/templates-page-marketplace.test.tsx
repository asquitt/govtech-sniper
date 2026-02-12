import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import TemplatesPage from "@/app/(dashboard)/templates/page";
import { templateApi, templateMarketplaceApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  templateApi: {
    list: vi.fn(),
    create: vi.fn(),
  },
  templateMarketplaceApi: {
    browse: vi.fn(),
    popular: vi.fn(),
    fork: vi.fn(),
    publish: vi.fn(),
    rate: vi.fn(),
  },
}));

const mockedTemplateApi = vi.mocked(templateApi);
const mockedMarketplaceApi = vi.mocked(templateMarketplaceApi);

describe("Templates marketplace page", () => {
  beforeEach(() => {
    mockedTemplateApi.list.mockImplementation(async (params?: { category?: string }) => {
      if (params?.category === "Proposal Structure") {
        return [
          {
            id: 101,
            name: "Proposal Structure - IT Services",
            category: "Proposal Structure",
            subcategory: "IT Services",
            description: "IT structure",
            template_text: "Content",
            placeholders: {},
            keywords: ["proposal"],
            is_system: true,
            is_public: true,
            rating_sum: 0,
            rating_count: 0,
            forked_from_id: null,
            user_id: null,
            usage_count: 3,
            created_at: "2026-02-10T00:00:00Z",
            updated_at: "2026-02-10T00:00:00Z",
          },
        ];
      }
      if (params?.category === "Compliance Matrix") {
        return [];
      }
      return [
        {
          id: 201,
          name: "My Private Template",
          category: "Technical",
          subcategory: null,
          description: "Private user template",
          template_text: "Private",
          placeholders: {},
          keywords: ["private"],
          is_system: false,
          is_public: false,
          rating_sum: 0,
          rating_count: 0,
          forked_from_id: null,
          user_id: 1,
          usage_count: 1,
          created_at: "2026-02-10T00:00:00Z",
          updated_at: "2026-02-10T00:00:00Z",
        },
      ];
    });

    mockedMarketplaceApi.browse.mockResolvedValue({
      data: {
        items: [
          {
            id: 301,
            name: "Community Matrix",
            category: "Compliance Matrix",
            subcategory: "GSA MAS",
            description: "Shared matrix",
            placeholders: {},
            keywords: ["matrix"],
            usage_count: 4,
            is_public: true,
            rating_sum: 10,
            rating_count: 2,
            forked_from_id: null,
            user_id: 10,
            created_at: "2026-02-10T00:00:00Z",
          },
        ],
        total: 1,
      },
    });
    mockedMarketplaceApi.popular.mockResolvedValue({ data: [] });
    mockedMarketplaceApi.publish.mockResolvedValue({ data: {} as never });
    mockedMarketplaceApi.fork.mockResolvedValue({ data: {} as never });
    mockedMarketplaceApi.rate.mockResolvedValue({ data: {} as never });
  });

  it("renders proposal kits and allows publishing private library templates", async () => {
    render(<TemplatesPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Proposal Kits" }));
    expect(await screen.findByText("Proposal Structure - IT Services")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "My Library" }));
    expect(await screen.findByText("My Private Template")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Share to Community" }));

    await waitFor(() => expect(mockedMarketplaceApi.publish).toHaveBeenCalledWith(201));
  });
});
