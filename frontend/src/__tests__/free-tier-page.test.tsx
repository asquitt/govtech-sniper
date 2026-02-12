import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import FreeTierPage from "@/app/free-tier/page";

describe("FreeTierPage", () => {
  it("renders free-tier feature marketing content", () => {
    render(<FreeTierPage />);

    expect(
      screen.getByText("Start winning contracts with zero upfront cost")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Create Free Account" })
    ).toHaveAttribute("href", "/register");
    expect(screen.getByText("Included at No Cost")).toBeInTheDocument();
  });
});
