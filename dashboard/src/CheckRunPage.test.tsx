import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import type { CheckResult, CheckRun, HandlerDecision } from "./api";
import { CheckRunPage } from "./CheckRunPage";
import { calls, mockApi } from "./testing";

const handler: HandlerDecision = {
  claim_id: "CLM-1001",
  set: "queue",
  decision: "approve",
  payout: 420,
  reason: "The delay was 19 hours.",
  reference: "Policy wording, section 3",
  calculation: [{ step: "Eligible expenses with receipts", amount: 420 }],
  tests: "A routine trip delay",
  difficulty: "routine",
  needs: [],
};

const match: CheckResult = {
  claim_id: "CLM-1001",
  claim_type: "trip_delay",
  summary: "Flight home canceled",
  score: "match",
  agent: {
    outcome: "approve",
    payout: 420,
    reasons: "Approved under section 3.",
    policy_section: "Section 3, Trip Delay",
  },
  handler,
  steps: [
    { at: "2026-11-05T00:00:00+00:00", title: "Read the claim", detail: "" },
  ],
};

const miss: CheckResult = {
  claim_id: "CLM-1101",
  claim_type: "trip_delay",
  summary: "Typhoon canceled a flight",
  score: "outcome_miss",
  agent: {
    outcome: "refer",
    payout: 0,
    reasons: "Referred for the wager.",
    policy_section: "Section 9",
  },
  handler: {
    ...handler,
    claim_id: "CLM-1101",
    set: "held_out",
    payout: 580,
    difficulty: "manual",
    needs: ["manual", "history"],
    calculation: [],
  },
  steps: [],
};

const tally = (claims: number, matches: number) => ({
  claims,
  matches,
  outcome_matches: matches,
  payout_matches: matches,
});

const run: CheckRun = {
  run_id: 3,
  started_at: "2026-11-05T00:00:00+00:00",
  finished_at: "2026-11-05T00:05:00+00:00",
  claims: 2,
  done: 2,
  matches: 1,
  summary: {
    overall: tally(2, 1),
    without_manual: tally(1, 1),
    by_set: { held_out: tally(1, 0), queue: tally(1, 1) },
    by_difficulty: { manual: tally(1, 0), routine: tally(1, 1) },
    by_claim_type: { trip_delay: tally(2, 1) },
  },
  results: [match, miss],
};

function show(shown: CheckRun) {
  const fetchMock = mockApi({ "GET /api/checks/3": shown });
  render(<CheckRunPage runId="3" />);
  return fetchMock;
}

test("shows the scores overall and without manual claims", async () => {
  show(run);

  const scores = within(await screen.findByLabelText("Scores"));
  expect(scores.getAllByText("1 of 2")).toHaveLength(3);
  expect(scores.getAllByText("50%")).toHaveLength(3);
  expect(
    scores.getAllByText("Without manual claims: 1 of 1, 100%"),
  ).toHaveLength(3);
  expect(screen.getByText(/^Finished /)).toBeTruthy();
});

test("breaks the scores down by set and difficulty", async () => {
  show(run);

  await screen.findByText("By set and difficulty");
  expect(screen.getByRole("rowheader", { name: "Held-out" })).toBeTruthy();
  expect(screen.getByRole("rowheader", { name: "Queue" })).toBeTruthy();
  expect(screen.getByRole("rowheader", { name: "Manual" })).toBeTruthy();
});

test("lists each claim with both decisions and its score", async () => {
  show(run);

  expect(await screen.findByText("Match")).toBeTruthy();
  expect(screen.getByText("Outcome miss")).toBeTruthy();
  expect(screen.getAllByText("Agent: Approved, $420.00")).toHaveLength(1);
  expect(screen.getByText("Agent: Referred")).toBeTruthy();
  expect(screen.getByText("Handler: Approved, $580.00")).toBeTruthy();
});

function row(claimId: string) {
  const details = screen.getByText(claimId).closest("details");
  if (details === null) throw new Error(`No row for ${claimId}`);
  return within(details);
}

test("opens a claim to compare the reasons", async () => {
  show(run);

  fireEvent.click(await screen.findByText("CLM-1001"));

  const first = row("CLM-1001");
  expect(first.getByText("Approved under section 3.")).toBeTruthy();
  expect(first.getByText("The delay was 19 hours.")).toBeTruthy();
  expect(first.getByText("Eligible expenses with receipts")).toBeTruthy();
  expect(first.getByText("Read the claim")).toBeTruthy();
  expect(first.getByText("Tests: A routine trip delay")).toBeTruthy();
  expect(
    row("CLM-1101").getByText(
      "Tests: A routine trip delay. Needs the claims manual and the claim history",
    ),
  ).toBeTruthy();
});

test("shows progress and pending claims while the run goes", async () => {
  show({
    ...run,
    finished_at: null,
    done: 0,
    summary: {
      overall: tally(0, 0),
      without_manual: tally(0, 0),
      by_set: {},
      by_difficulty: {},
      by_claim_type: {},
    },
    results: [
      {
        ...match,
        score: null,
        agent: {
          outcome: null,
          payout: null,
          reasons: null,
          policy_section: null,
        },
      },
    ],
  });

  expect(await screen.findByText("Checking 0 of 2 claims")).toBeTruthy();
  expect(screen.getByText("Pending")).toBeTruthy();
  expect(screen.getByText("Agent: Not decided")).toBeTruthy();
  expect(screen.getAllByText("Without manual claims: 0 of 0")).toHaveLength(3);
  fireEvent.click(screen.getByText("CLM-1001"));
  expect(screen.getByText("The agent didn't record a decision.")).toBeTruthy();
});

test("marks a claim the agent didn't finish", async () => {
  show({ ...run, results: [{ ...miss, score: "not_finished" }] });

  expect(await screen.findByText("Not finished")).toBeTruthy();
});

test("keeps polling while running and stops once finished", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const running = show({ ...run, finished_at: null });
  await screen.findByText("Checking 2 of 2 claims");
  await vi.advanceTimersByTimeAsync(4000);
  expect(calls(running, "GET /api/checks/3")).toBe(3);
});

test("stops polling a finished run", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const finished = show(run);
  await screen.findByText(/^Finished /);
  await vi.advanceTimersByTimeAsync(4000);
  expect(calls(finished, "GET /api/checks/3")).toBe(1);
});

test("says when the run can't be loaded", async () => {
  mockApi({});
  render(<CheckRunPage runId="9" />);

  expect(await screen.findByText("Check run 9 can't be loaded.")).toBeTruthy();
});
