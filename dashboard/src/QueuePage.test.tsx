import { render, screen, within } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { QueuePage } from "./QueuePage";
import { calls, mockApi, summary } from "./testing";

const claims = [
  summary,
  {
    ...summary,
    claim_id: "CLM-1002",
    status: "waiting_for_signoff",
    outcome: "approve",
    payout: 1150,
  },
  {
    ...summary,
    claim_id: "CLM-1003",
    status: "decided",
    outcome: "refer",
    payout: 0,
  },
  { ...summary, claim_id: "CLM-1004", status: "in_progress" },
];

function rowOf(claimId: string) {
  const row = screen.getByRole("link", { name: claimId }).closest("tr");
  if (row === null) throw new Error(`No row for ${claimId}`);
  return within(row);
}

test("shows each claim with its status and decision", async () => {
  mockApi({ "GET /api/claims": claims });
  render(<QueuePage />);

  expect(await screen.findByText("4 claims")).toBeTruthy();
  expect(rowOf("CLM-1001").getByText("Waiting")).toBeTruthy();
  expect(rowOf("CLM-1001").getByText("$420.00")).toBeTruthy();
  expect(rowOf("CLM-1001").getByText("Trip delay")).toBeTruthy();
  expect(rowOf("CLM-1002").getByText("Waiting for sign-off")).toBeTruthy();
  expect(rowOf("CLM-1002").getByText("Approved, $1,150.00")).toBeTruthy();
  expect(rowOf("CLM-1003").getByText("Referred")).toBeTruthy();
  expect(rowOf("CLM-1004").getByText("In progress")).toBeTruthy();
  expect(
    screen.getByRole("link", { name: "CLM-1002" }).getAttribute("href"),
  ).toBe("#/claims/CLM-1002");
});

test("counts the claims by status", async () => {
  mockApi({ "GET /api/claims": claims });
  render(<QueuePage />);

  const counts = within(await screen.findByLabelText("Claims by status"));
  expect(counts.getAllByText("1")).toHaveLength(4);
});

test("says when the backend can't be reached", async () => {
  mockApi({});
  render(<QueuePage />);

  expect(await screen.findByText("The backend can't be reached.")).toBeTruthy();
});

test("polls the queue every 2 seconds", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const fetchMock = mockApi({ "GET /api/claims": claims });
  render(<QueuePage />);
  await screen.findByText("4 claims");

  await vi.advanceTimersByTimeAsync(4000);

  expect(calls(fetchMock, "GET /api/claims")).toBe(3);
});
