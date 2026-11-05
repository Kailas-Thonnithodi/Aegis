import { vi } from "vitest";

import type { CheckClaim, Claim, ClaimSummary, Policy, Step } from "./api";

export const summary: ClaimSummary = {
  claim_id: "CLM-1001",
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  claim_type: "trip_delay",
  summary: "Flight home canceled by the airline",
  submitted_on: "2026-06-24",
  amount_claimed: 420,
  status: "waiting",
  outcome: null,
  payout: null,
};

export const claim: Claim = {
  ...summary,
  incident_date: "2026-06-18",
  incident_location: "Rome, Italy",
  story: "My flight home from Rome was canceled.",
  items: [
    {
      description: "Airport hotel, one night",
      category: "accommodation",
      amount: 245,
    },
    { description: "Dinner and breakfast", category: "meals", amount: 175 },
  ],
  documents: [
    {
      name: "Meridian Air cancellation notice",
      type: "carrier_report",
      content: "Flight MA 611 was canceled.",
    },
  ],
  reasons: null,
  policy_section: null,
  signed_off_at: null,
  payment: null,
};

export const policy: Policy = {
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  plan: "premium",
  add_ons: [],
  purchased_on: "2026-04-22",
  sold_through: "Meridian Air checkout",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
  status: "active",
};

export const steps: Step[] = [
  { at: "2026-11-04T23:30:40+00:00", title: "Read the claim", detail: "{}" },
  {
    at: "2026-11-04T23:30:47+00:00",
    title: "Decided: approve, $420.00",
    detail: "{}",
  },
];

export type Routes = Record<string, unknown>;

export function mockApi(routes: Routes) {
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${input}`;
    if (!(key in routes)) {
      return Promise.resolve(new Response("{}", { status: 404 }));
    }
    return Promise.resolve(new Response(JSON.stringify(routes[key])));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function calls(fetchMock: ReturnType<typeof mockApi>, key: string) {
  return fetchMock.mock.calls.filter(
    ([input, init]) => `${init?.method ?? "GET"} ${input}` === key,
  ).length;
}

export const checkClaims: CheckClaim[] = [
  {
    claim_id: "CLM-1001",
    set: "queue",
    claim_type: "trip_delay",
    summary: "Flight home canceled",
    amount_claimed: 420,
    difficulty: "routine",
    handler_outcome: "approve",
  },
  {
    claim_id: "CLM-1002",
    set: "queue",
    claim_type: "baggage",
    summary: "Suitcase lost",
    amount_claimed: 1150,
    difficulty: "hard",
    handler_outcome: "approve",
  },
  {
    claim_id: "CLM-1101",
    set: "held_out",
    claim_type: "trip_delay",
    summary: "Typhoon canceled a flight",
    amount_claimed: 2580,
    difficulty: "routine",
    handler_outcome: "approve",
  },
  {
    claim_id: "CLM-1102",
    set: "held_out",
    claim_type: "baggage",
    summary: "Bag left in a car",
    amount_claimed: 900,
    difficulty: "hard",
    handler_outcome: "decline",
  },
];
