import { screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { mockApi } from "./testing";

test("renders the app into the root element", async () => {
  mockApi({ "GET /api/claims": [] });
  document.body.innerHTML = '<div id="root"></div>';
  await import("./main");
  expect(
    await screen.findByRole("heading", { name: "Claims queue" }),
  ).toBeTruthy();
  vi.unstubAllGlobals();
});
