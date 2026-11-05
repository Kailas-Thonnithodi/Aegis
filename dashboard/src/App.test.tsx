import { act, render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { App } from "./App";
import { claim, mockApi, policy, summary } from "./testing";

const routes = {
  "GET /api/claims": [summary],
  "GET /api/claims/CLM-1001": claim,
  "GET /api/policies/POL-2001": policy,
  "GET /api/claims/CLM-1001/steps": [],
  "GET /api/instructions": { text: "# Aegis Agent instructions" },
  "GET /api/queue": { running: false, claims_left: 0 },
  "GET /api/checks/claims": [],
  "GET /api/checks": [],
};

test("shows the queue by default", async () => {
  mockApi(routes);
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "Claims queue" }),
  ).toBeTruthy();
  expect(
    screen.getByRole("link", { name: "Queue" }).getAttribute("aria-current"),
  ).toBe("page");
});

test("follows the hash to a claim and to the instructions", async () => {
  mockApi(routes);
  render(<App />);
  await screen.findByRole("heading", { name: "Claims queue" });

  act(() => {
    window.location.hash = "#/claims/CLM-1001";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  expect(
    await screen.findByRole("heading", {
      name: "Flight home canceled by the airline",
    }),
  ).toBeTruthy();

  act(() => {
    window.location.hash = "#/instructions";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  expect(
    await screen.findByRole("heading", { name: "Agent instructions" }),
  ).toBeTruthy();
  expect(
    screen
      .getByRole("link", { name: "Agent instructions" })
      .getAttribute("aria-current"),
  ).toBe("page");
});

test("opens the checks page from the hash", async () => {
  mockApi(routes);
  window.location.hash = "#/checks";
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "Agent checks" }),
  ).toBeTruthy();
  expect(
    screen.getByRole("link", { name: "Checks" }).getAttribute("aria-current"),
  ).toBe("page");
});
