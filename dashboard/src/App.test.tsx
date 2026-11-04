import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("shows the backend is up when the health check passes", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}")));
  render(<App />);
  expect(await screen.findByText("The backend is up.")).toBeTruthy();
});

test("shows the backend is down when the health check fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response("", { status: 500 })),
  );
  render(<App />);
  expect(await screen.findByText("The backend is down.")).toBeTruthy();
});

test("shows the backend is down when it cannot be reached", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
  );
  render(<App />);
  expect(await screen.findByText("The backend is down.")).toBeTruthy();
});
