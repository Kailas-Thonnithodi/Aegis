import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test } from "vitest";

import { ChecksPage } from "./ChecksPage";
import { checkClaims, mockApi } from "./testing";

const routes = {
  "GET /api/checks/claims": checkClaims,
  "GET /api/checks": [],
};

async function showPage(extra: Record<string, unknown> = {}) {
  const fetchMock = mockApi({ ...routes, ...extra });
  render(<ChecksPage />);
  await screen.findByText("Showing 4 of 4 claims");
  return fetchMock;
}

function choose(name: string, value: string) {
  fireEvent.change(screen.getByLabelText(name), { target: { value } });
}

function checkbox(claimId: string) {
  return screen.getByLabelText<HTMLInputElement>(`Pick ${claimId}`);
}

test("shows every claim from both sets", async () => {
  await showPage();

  expect(screen.getAllByRole("cell", { name: "Queue" })).toHaveLength(2);
  expect(screen.getAllByRole("cell", { name: "Held-out" })).toHaveLength(2);
  expect(screen.getByText("Typhoon canceled a flight")).toBeTruthy();
  expect(screen.getByRole("cell", { name: "Declined" })).toBeTruthy();
  expect(screen.getByText("No check runs yet.")).toBeTruthy();
});

test("filters by set, difficulty, claim type and the handler's decision", async () => {
  await showPage();

  choose("Set", "held_out");
  expect(screen.getByText("Showing 2 of 4 claims")).toBeTruthy();
  choose("Difficulty", "hard");
  expect(screen.getByText("Showing 1 of 4 claims")).toBeTruthy();
  expect(screen.getByText("Bag left in a car")).toBeTruthy();

  choose("Set", "");
  choose("Difficulty", "");
  choose("Claim type", "trip_delay");
  expect(screen.getByText("Showing 2 of 4 claims")).toBeTruthy();

  choose("Claim type", "");
  choose("Handler's decision", "decline");
  expect(screen.getByText("Showing 1 of 4 claims")).toBeTruthy();
});

test("selects every claim shown and counts the picks", async () => {
  await showPage();

  choose("Set", "held_out");
  fireEvent.click(screen.getByRole("button", { name: "Select all shown" }));
  expect(screen.getByText("2 claims picked")).toBeTruthy();

  choose("Set", "");
  expect(checkbox("CLM-1101").checked).toBe(true);
  expect(checkbox("CLM-1001").checked).toBe(false);

  fireEvent.click(checkbox("CLM-1101"));
  expect(screen.getByText("1 claim picked")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "Clear" }));
  expect(screen.getByText("0 claims picked")).toBeTruthy();
});

test("can't run checks with nothing picked", async () => {
  await showPage();

  const button = screen.getByRole("button", { name: "Run checks" });
  expect((button as HTMLButtonElement).disabled).toBe(true);
});

test("starts a run on the picked claims and opens it", async () => {
  const fetchMock = await showPage({
    "POST /api/checks": {
      run_id: 7,
      started_at: "2026-11-05T00:00:00+00:00",
      finished_at: null,
      claims: 2,
      done: 0,
      matches: 0,
    },
  });

  fireEvent.click(checkbox("CLM-1101"));
  fireEvent.click(checkbox("CLM-1001"));
  fireEvent.click(screen.getByRole("button", { name: "Run checks" }));

  await waitFor(() => {
    expect(window.location.hash).toBe("#/checks/7");
  });
  const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  const body = post?.[1]?.body;
  expect(typeof body === "string" ? JSON.parse(body) : body).toEqual({
    claim_ids: ["CLM-1001", "CLM-1101"],
  });
});

test("lists past runs with their progress or result", async () => {
  await showPage({
    "GET /api/checks": [
      {
        run_id: 2,
        started_at: "2026-11-05T01:00:00+00:00",
        finished_at: null,
        claims: 4,
        done: 1,
        matches: 1,
      },
      {
        run_id: 1,
        started_at: "2026-11-05T00:00:00+00:00",
        finished_at: "2026-11-05T00:05:00+00:00",
        claims: 2,
        done: 2,
        matches: 1,
      },
    ],
  });

  expect(await screen.findByText("Checking, 1 of 4 done")).toBeTruthy();
  expect(screen.getByText("1 of 2 match")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Run 1" }).getAttribute("href")).toBe(
    "#/checks/1",
  );
});
