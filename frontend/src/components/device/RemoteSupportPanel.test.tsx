import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "../../lib/api";
import { RemoteSupportPanel } from "./RemoteSupportPanel";

vi.mock("../../lib/api", () => ({ apiFetch: vi.fn() }));
const api = vi.mocked(apiFetch);
const config = { enabled: true, rustdesk_id: "123456789" };

beforeEach(() => { api.mockReset(); });
afterEach(cleanup);

describe("RemoteSupportPanel", () => {
  it("saves the selected computer's configuration before allowing launch", async () => {
    api.mockResolvedValueOnce({ enabled: false, rustdesk_id: "" }).mockResolvedValueOnce(config);
    render(<RemoteSupportPanel computerId="pc-1" />);
    const input = await screen.findByLabelText("RustDesk ID");
    expect(screen.getByText("Desktop control")).toBeDisabled();
    fireEvent.change(input, { target: { value: "123456789" } });
    fireEvent.change(screen.getByLabelText("Remote support"), { target: { value: "enabled" } });
    expect(screen.getByText("Desktop control")).toBeDisabled();
    fireEvent.click(screen.getByText("Save settings"));
    await waitFor(() => expect(screen.getByText("Desktop control")).toBeEnabled());
    expect(api).toHaveBeenLastCalledWith("/computers/pc-1/remote-support", { method: "PUT", body: JSON.stringify(config) });
  });

  it.each([['desktop', 'connect', 'Desktop control', 'Open RustDesk desktop'], ['file_transfer', 'file-transfer', 'File transfer', 'Open RustDesk file transfer']])("prepares %s with an explicit native-app link", async (mode, command, button, link) => {
    api.mockResolvedValueOnce(config).mockResolvedValueOnce({ uri: `rustdesk://${command}/123456789`, mode, rustdesk_id: "123456789" });
    render(<RemoteSupportPanel computerId="pc-1" />);
    fireEvent.click(await screen.findByText(button));
    expect(await screen.findByRole("link", { name: link })).toHaveAttribute("href", `rustdesk://${command}/123456789`);
    expect(api).toHaveBeenLastCalledWith("/computers/pc-1/remote-support/launch", { method: "POST", body: JSON.stringify({ mode }) });
    fireEvent.change(screen.getByLabelText("RustDesk ID"), { target: { value: "987654321" } });
    expect(screen.queryByRole("link", { name: link })).not.toBeInTheDocument();
    expect(screen.getByText(button)).toBeDisabled();
  });

  it("shows permission errors without connection controls", async () => {
    api.mockRejectedValueOnce(new Error("Insufficient permissions"));
    render(<RemoteSupportPanel computerId="pc-1" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Insufficient permissions");
    expect(screen.queryByText("Desktop control")).not.toBeInTheDocument();
  });

  it("does not open an arbitrary URL from the server", async () => {
    api.mockResolvedValueOnce(config).mockResolvedValueOnce({ uri: "https://example.test", mode: "desktop", rustdesk_id: "123456789" });
    render(<RemoteSupportPanel computerId="pc-1" />);
    fireEvent.click(await screen.findByText("Desktop control"));
    expect(await screen.findByRole("alert")).toHaveTextContent("invalid RustDesk link");
    expect(screen.queryByRole("link", { name: "Open RustDesk desktop" })).not.toBeInTheDocument();
  });

  it("keeps unsaved changes disabled after a failed save", async () => {
    api.mockResolvedValueOnce(config).mockRejectedValueOnce(new Error("Unable to save"));
    render(<RemoteSupportPanel computerId="pc-1" />);
    fireEvent.change(await screen.findByLabelText("RustDesk ID"), { target: { value: "987654321" } });
    fireEvent.click(screen.getByText("Save settings"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to save");
    expect(screen.getByText("Desktop control")).toBeDisabled();
  });
});
