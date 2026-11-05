export type Status =
  "waiting" | "in_progress" | "waiting_for_signoff" | "decided";
export type Outcome = "approve" | "decline" | "refer";

export interface ClaimSummary {
  claim_id: string;
  policy_id: string;
  customer_id: string;
  claim_type: string;
  summary: string;
  submitted_on: string;
  amount_claimed: number;
  status: Status;
  outcome: Outcome | null;
  payout: number | null;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface ClaimDocument {
  name: string;
  type: string;
  content: string;
}

export interface Payment {
  amount: number;
  paid_at: string;
}

export interface Claim extends ClaimSummary {
  incident_date: string;
  incident_location: string;
  story: string;
  items: Item[];
  documents: ClaimDocument[];
  reasons: string | null;
  policy_section: string | null;
  signed_off_at: string | null;
  payment: Payment | null;
}

export interface Policy {
  policy_id: string;
  customer_id: string;
  plan: string;
  add_ons: string[];
  purchased_on: string;
  sold_through: string;
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
  status: string;
}

export interface Step {
  at: string;
  title: string;
  detail: string;
}

export interface QueueRun {
  running: boolean;
  claims_left: number;
}

export type ClaimSet = "queue" | "held_out";
export type Score = "match" | "payout_miss" | "outcome_miss" | "not_finished";

export interface CheckClaim {
  claim_id: string;
  set: ClaimSet;
  claim_type: string;
  summary: string;
  amount_claimed: number;
  difficulty: string;
  handler_outcome: Outcome;
}

export interface CheckRunSummary {
  run_id: number;
  started_at: string;
  finished_at: string | null;
  claims: number;
  done: number;
  matches: number;
}

export interface Tally {
  claims: number;
  matches: number;
  outcome_matches: number;
  payout_matches: number;
}

export interface CheckSummary {
  overall: Tally;
  without_manual: Tally;
  by_set: Record<string, Tally>;
  by_difficulty: Record<string, Tally>;
  by_claim_type: Record<string, Tally>;
}

export interface HandlerDecision {
  claim_id: string;
  set: ClaimSet;
  decision: Outcome;
  payout: number;
  reason: string;
  reference: string;
  calculation: { step: string; amount: number }[];
  tests: string;
  difficulty: string;
  needs: string[];
}

export interface CheckResult {
  claim_id: string;
  claim_type: string;
  summary: string;
  score: Score | null;
  agent: {
    outcome: Outcome | null;
    payout: number | null;
    reasons: string | null;
    policy_section: string | null;
  };
  handler: HandlerDecision;
  steps: Step[];
}

export interface CheckRun extends CheckRunSummary {
  summary: CheckSummary;
  results: CheckResult[];
}

async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(
    `/api${path}`,
    body === undefined
      ? { method }
      : {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  if (!response.ok) {
    throw new Error(`${method} ${path} failed with ${String(response.status)}`);
  }
  return (await response.json()) as T;
}

export const api = {
  listClaims: () => request<ClaimSummary[]>("/claims"),
  getClaim: (claimId: string) => request<Claim>(`/claims/${claimId}`),
  getPolicy: (policyId: string) => request<Policy>(`/policies/${policyId}`),
  listSteps: (claimId: string) => request<Step[]>(`/claims/${claimId}/steps`),
  getInstructions: () => request<{ text: string }>("/instructions"),
  getQueueRun: () => request<QueueRun>("/queue"),
  runAgent: (claimId: string) =>
    request<QueueRun>(`/claims/${claimId}/run`, "POST"),
  workQueue: () => request<{ queued: number }>("/queue/run", "POST"),
  signOff: (claimId: string) =>
    request<Claim>(`/claims/${claimId}/sign-off`, "POST"),
  listCheckClaims: () => request<CheckClaim[]>("/checks/claims"),
  listCheckRuns: () => request<CheckRunSummary[]>("/checks"),
  getCheckRun: (runId: string) => request<CheckRun>(`/checks/${runId}`),
  startCheck: (claimIds: string[]) =>
    request<CheckRunSummary>("/checks", "POST", { claim_ids: claimIds }),
};
