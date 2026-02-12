import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ExtractButton } from "@/components/contacts/extract-button";
import { contactApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  contactApi: {
    extract: vi.fn(),
  },
}));

const mockedContactApi = vi.mocked(contactApi);

describe("ExtractButton", () => {
  it("extracts and auto-links contacts for an RFP", async () => {
    const onContactsSaved = vi.fn();
    mockedContactApi.extract.mockResolvedValue([
      {
        name: "Contact extracted from document",
        title: "Contracting Officer",
        agency: "Department of Energy",
        role: "Contracting Officer",
      },
    ]);

    const user = userEvent.setup();
    render(<ExtractButton onContactsSaved={onContactsSaved} />);

    await user.click(screen.getByRole("button", { name: "Extract from RFP" }));
    await user.type(screen.getByPlaceholderText("Enter RFP ID"), "42");
    await user.click(screen.getByRole("button", { name: "Extract" }));

    expect(mockedContactApi.extract).toHaveBeenCalledWith(42);
    expect(await screen.findByText("1 contact extracted")).toBeInTheDocument();
    expect(
      screen.getByText(
        /Extracted contacts are linked automatically to this opportunity and agency directory\./
      )
    ).toBeInTheDocument();
    expect(onContactsSaved).toHaveBeenCalledTimes(1);
  });
});
