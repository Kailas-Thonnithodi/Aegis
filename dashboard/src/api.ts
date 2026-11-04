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

async function request<T>(path: string, method = "GET"): Promise<T> {
  const response = await fetch(`/api${path}`, { method });
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
};
