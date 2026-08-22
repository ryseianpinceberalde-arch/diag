import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders the provided status", () => {
    render(<StatusBadge value="critical" />);
    expect(screen.getByText("critical")).toBeInTheDocument();
  });
});
