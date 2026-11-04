import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import type { Claim } from "./api";
import { ClaimPage } from "./ClaimPage";
import { claim, mockApi, policy, steps } from "./testing";

function show(shown: Claim) {
  mockApi({
    "GET /api/claims/CLM-1001": shown,
    "GET /api/policies/POL-2001": { ...policy, add_ons: ["electronics_plus"] },
    "GET /api/claims/CLM-1001/steps": steps,
  });
  render(<ClaimPage claimId="CLM-1001" />);
}

test("shows the claim in full with its policy", async () => {
  show(claim);

  expect(
    await screen.findByRole("heading", {
      name: "Flight home canceled by the airline",
    }),
  ).toBeTruthy();
  expect(
    screen.getByText("My flight home from Rome was canceled."),
  ).toBeTruthy();
  expect(screen.getByText("Airport hotel, one night")).toBeTruthy();
  expect(screen.getByText("Meridian Air cancellation notice")).toBeTruthy();
  expect(screen.getByText("Carrier report")).toBeTruthy();
  expect(screen.getByText("Waiting")).toBeTruthy();
  expect(
    screen.getByText("The agent hasn't decided this claim yet."),
  ).toBeTruthy();
  expect(await screen.findByText("Premium")).toBeTruthy();
  expect(screen.getByText("Electronics plus")).toBeTruthy();
  expect(screen.getByText("Maya Patel")).toBeTruthy();
  expect(screen.getByText("$3,100.00")).toBeTruthy();
});

test("shows an approval that was paid", async () => {
  show({
    ...claim,
    status: "decided",
    outcome: "approve",
    payout: 420,
    reasons: "The delay was over six hours.",
    policy_section: "Section 3, Trip Delay",
    payment: { amount: 420, paid_at: "2026-11-04T23:30:49+00:00" },
  });

  expect(await screen.findByText("Approved")).toBeTruthy();
  expect(screen.getByText("The delay was over six hours.")).toBeTruthy();
  expect(screen.getByText("Section 3, Trip Delay")).toBeTruthy();
  expect(screen.getByText(/^Paid \$420\.00 on Nov/)).toBeTruthy();
});

test("shows a payout held for sign-off", async () => {
  show({
    ...claim,
    status: "waiting_for_signoff",
    outcome: "approve",
    payout: 1150,
    reasons: "Lost by the carrier.",
    policy_section: "Section 5",
  });

  expect(await screen.findByText("Held for sign-off")).toBeTruthy();
  expect(screen.getAllByText("Waiting for sign-off").length).toBeGreaterThan(0);
});

test("shows when a payout was signed off", async () => {
  show({
    ...claim,
    status: "decided",
    outcome: "approve",
    payout: 1150,
    reasons: "Lost by the carrier.",
    policy_section: "Section 5",
    signed_off_at: "2026-11-05T01:00:00+00:00",
    payment: { amount: 1150, paid_at: "2026-11-05T01:00:00+00:00" },
  });

  expect(await screen.findByText("Signed off")).toBeTruthy();
});

test("shows a referral with no payment", async () => {
  show({
    ...claim,
    status: "decided",
    outcome: "refer",
    payout: 0,
    reasons: "The police report is missing.",
    policy_section: "Section 11",
  });

  expect(await screen.findByText("Referred")).toBeTruthy();
  expect(screen.getByText("None")).toBeTruthy();
});

test("says when the claim can't be loaded", async () => {
  mockApi({});
  render(<ClaimPage claimId="CLM-9999" />);

  expect(
    await screen.findByText("Claim CLM-9999 can't be loaded."),
  ).toBeTruthy();
});
