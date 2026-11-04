import { screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

test("renders the app into the root element", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}")));
  document.body.innerHTML = '<div id="root"></div>';
  await import("./main");
  expect(
    await screen.findByRole("heading", { name: "Aegis Claims" }),
  ).toBeTruthy();
  vi.unstubAllGlobals();
});
