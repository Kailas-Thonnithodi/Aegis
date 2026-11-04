# Plan: the claims pilot

The pilot builds on the hello-world skeleton (commit `ecae0dc`). By the end, a handler can open the dashboard, see the queue, run the Aegis Agent on one claim or on the whole queue, follow what the agent does step by step, read its decision and reasons, sign off payouts over $1,000, and read the agent's instructions.

## Decisions already made

These close gaps the spec leaves open. Kailas settled them on 2026-11-03.

- **Trigger.** The agent runs only when asked: a "Run agent" button on each waiting claim, and a "Work the queue" button that runs every waiting claim in turn. Nothing runs on its own.
- **Handler actions.** Sign-off is the only handler action, and only for approvals over $1,000. Signing off releases the payment and records the time. It doesn't record who signed, because there's no sign-in. Referred claims show as decided, with the reason. There's no reject or override.
- **Referral rule.** The agent refers a claim when a document the wording requires is missing (section 11 says the claim waits until it arrives) or when the wording doesn't settle the claim.
- **Evals.** Checking the agent against `data/evals/` is a later build with its own plan (`docs/PLAN_HARNESS.md`). The pilot never reads that folder.
- **Node.** The tech stack says Node 26. This Mac has v24.19.0, which `package.json` still accepts. Kailas installs Node 26 (`brew install node@26` or `nvm install 26`) before the pilot ships. Nothing in the plan depends on Node 26 features.

## Approach

**The backend owns every rule.** Claim status, the decision and the payment all live in SQLite behind the API. The agent can only change them through API operations, and each operation checks the rules itself. The $1,000 sign-off rule is a check inside `pay_claim`, so it holds no matter what the model tries. Prompts guide the agent and the backend enforces.

**Claim status** moves like this:

```
waiting ──run──▶ in_progress ──decline / refer──────────────────▶ decided
                     │
                     ├──approve ≤ $1,000 ──pay_claim──────────────▶ decided (paid)
                     │
                     └──approve > $1,000 ──▶ waiting_for_signoff ──sign off──▶ decided (paid)
```

If a run ends with the claim still `in_progress` (the model errored or stopped without finishing), the runner clears the half-finished decision, returns the claim to `waiting` and records a step saying why. That one rule covers crashes and incomplete runs, so the queue never has stuck claims.

**The agent reads through the API too.** Its tools are thin `httpx` wrappers over backend operations. Its instructions live in `backend/agent_instructions.md`, served by `get_agent_instructions`, the same operation the dashboard uses to show them read only. The backend loads only `claims.json`, `policies.json` and `policy_wording.md`, so the agent has no route to `data/evals/`.

**Steps are recorded by the runner, not the model.** The entry point `run(claim_id, thread_id)` streams the agent's graph. For each tool call, tool result and model message, it posts a short step (a title and a detail) to the backend. The model doesn't need a "log this" tool and can't skip a step.

**The backend triggers runs.** `run_agent` and `work_queue` hand claims to a single background worker (a one-thread pool), so runs happen one at a time in the order asked. That's simple, it matches "in turn" and it avoids two runs racing on one claim. The dashboard polls: the queue every 2 seconds and an open claim every second while it's in progress. Polling is enough at this scale, and it's easier to test than server-sent events.

**Tests never call a model.** Unit tests use a fake chat model. For end-to-end tests, `MODEL_NAME=stub` selects a scripted model in `agent/stub_model.py`. It reads the claim, approves `amount_claimed`, then tries to pay. That gives a deterministic run that exercises both the under-$1,000 and the over-$1,000 paths through the real backend.

**SQLite through the standard library.** Using `sqlite3` with Pydantic models at the API edge means no ORM. Items and documents are stored as JSON text on the claim row. The database file is `aegis.db` at the repo root (gitignored), or the path in `AEGIS_DB`. It's seeded from `data/` on startup when empty, and `npm run reset` rebuilds it.

## Phase 1: Records and the read API

Load Aegis's records into SQLite and serve them.

- `backend/db.py`: schema (`policies`, `claims`, `steps`, `payments`) and a seed from `data/claims.json`, `data/policies.json`. A claim's `open` status becomes `waiting`.
- `backend/seed.py`, run with `uv run -m backend.seed`, rebuilds the database. Add the `npm run reset` script and gitignore `aegis.db`.
- Operations, each with an `operation_id`, a one-line docstring and no optional inputs:
  - `GET /api/claims` → `list_claims`: the queue, each claim's id, type, summary, submitted date, amount claimed, status, outcome and payout
  - `GET /api/claims/{claim_id}` → `get_claim`: the full claim with its decision and payment
  - `GET /api/claims/{claim_id}/history` → `get_claim_history`: the customer's other claims
  - `GET /api/policies/{policy_id}` → `get_policy`
  - `GET /api/policy-wording` → `get_policy_wording`: the text of `policy_wording.md`
- Tests use a temporary database per test.

Success criteria:

- [x] `uv run pytest backend` passes with tests for every operation, the seed, and 404 for an unknown claim or policy.
- [x] `uv run -m backend.seed` prints that it loaded 25 claims and 50 policies.
- [x] `curl -s localhost:8000/api/claims` returns 25 claims, all `waiting`.
- [x] `curl -s localhost:8000/api/claims/CLM-1001` returns the claim with its 3 items and 4 documents, and `outcome`, `payout` and `payment` set to null.
- [x] `curl -s localhost:8000/api/claims/CLM-1005/history` returns exactly CLM-1006, and CLM-1001's history is empty.
- [x] `curl -s localhost:8000/api/policy-wording` returns text that starts with `# Aegis Travel Insurance: Policy Wording`.
- [x] `grep -rn "evals" backend agent dashboard` prints nothing.
- [x] `npm run check` passes.

## Phase 2: Decisions, payments and sign-off

The write side of the API, with the status rules and the $1,000 rule enforced in the backend.

- `POST /api/claims/{claim_id}/start` → `start_claim`: `waiting` to `in_progress`.
- `POST /api/claims/{claim_id}/decision` → `record_decision`, taking `outcome` (`approve`, `decline` or `refer`), `payout`, `reasons` and `policy_section`. Payout must be 0 unless the outcome is approve. Decline and refer go to `decided`. Approve over $1,000 goes to `waiting_for_signoff`. Approve at $1,000 or less stays `in_progress` until paid.
- `POST /api/claims/{claim_id}/payment` → `pay_claim`, taking `amount`. Refused with 409 unless the claim is approved, unpaid and the amount equals the payout. Refused with 409 "This payout needs a handler's sign-off" when the payout is over $1,000. On success, records the payment and moves the claim to `decided`.
- `POST /api/claims/{claim_id}/sign-off` → `sign_off_claim`: only from `waiting_for_signoff`. Records the sign-off time, releases the payment and moves the claim to `decided`.
- `POST /api/claims/{claim_id}/steps` → `record_step` and `GET /api/claims/{claim_id}/steps` → `list_steps`. A step has a time, a title and a detail.
- `POST /api/claims/{claim_id}/reset` → `reset_claim`: from `in_progress` back to `waiting`, clearing the decision. The runner uses it for unfinished runs.
- `GET /api/instructions` → `get_agent_instructions`: the text of `backend/agent_instructions.md` (drafted here, refined in phase 3). There's no operation to change it.

Success criteria:

- [x] `uv run pytest backend` passes, with a test for every transition above and every refusal.
- [x] A test shows that for a claim approved at $1,150.00, `pay_claim` returns 409 and leaves no payment row, and that after `sign_off_claim` there's exactly one payment of $1,150.00 and the claim is `decided`.
- [x] A test shows that `pay_claim` with an amount other than the payout returns 409, and that paying twice returns 409.
- [x] Against the running backend, curl walks CLM-1001 through start, approve $420.00 and pay to `decided` with a payment.
- [x] Against the running backend, curl walks CLM-1002 through start and approve $1,150.00 to `waiting_for_signoff`. `pay_claim` returns 409 with the sign-off message, and `sign_off_claim` then moves it to `decided` with `signed_off_at` set.
- [x] `curl -s localhost:8000/api/instructions` returns the instructions text.
- [x] `npm run check` passes, and `npm run reset` restores 25 waiting claims.

## Phase 3: The Aegis Agent

Replace the skeleton agent with one that works a claim through the API.

- Tools, each a call to one backend operation: `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `record_decision` and `pay_claim`. The model gets no tools for start, sign-off, reset or steps.
- `run(claim_id, thread_id)`: fetches the instructions from the API, starts the claim, streams the agent, posts each step, and resets the claim if the run ends with it still `in_progress`.
- Step titles read like a handler's notes: "Read the claim", "Read policy POL-2002", "Read the customer's claim history", "Read the policy wording", "Decided: approve, $1,150.00", "Paid $420.00", "Payment held for sign-off".
- `backend/agent_instructions.md` covers: read everything before deciding; check the trip dates, plan, add-ons and exclusions; the referral rule; working out the payout by section 10 (per-item limit, amounts already paid, deductible once per claim for baggage and medical, the benefit maximum); reasons in two or three plain sentences with the policy section; pay after approving, and when payment is held for sign-off, stop.
- `agent/stub_model.py`: the scripted model for `MODEL_NAME=stub`.
- `uv run -m agent CLM-1001` runs one claim from the command line.
- Tests use the fake model and route the agent's `httpx` client to the backend's `TestClient` with a temporary database, so they exercise the real API without a server or a model.

Success criteria:

- [x] `uv run pytest agent` passes, including a test where the fake model approves CLM-1002 at $1,150.00 and calls `pay_claim`. The claim ends `waiting_for_signoff` with no payment, and a "Payment held for sign-off" step is recorded.
- [x] A test where the fake model stops without deciding leaves the claim `waiting`, with a step explaining why.
- [x] A test with `MODEL_NAME=stub` runs CLM-1001 to `decided` and paid.
- [x] `grep -rn "data/" agent` prints nothing, so the agent reads only through the API.
- [x] With the real model and the backend running, `uv run -m agent CLM-1001` approves $420.00 under section 3 (Premium plan, a crew cancellation, a delay well over 6 hours, under the $800 maximum) and pays it. `curl -s localhost:8000/api/claims/CLM-1001/steps` lists each step in order.
- [x] With the real model, one claim with a payout over $1,000 ends `waiting_for_signoff` with no payment.
- [x] `npm run check` passes.

## Phase 4: Running the agent from the backend

Let the dashboard start runs.

- `POST /api/claims/{claim_id}/run` → `run_agent`: queues one waiting claim and returns 202. Returns 409 if the claim isn't waiting.
- `POST /api/queue/run` → `work_queue`: queues every waiting claim, in claim order, and returns how many it queued.
- `GET /api/queue` → `get_queue_run`: whether a run is going and how many claims are left.
- One background worker runs claims one at a time with a new thread id per run. A claim that was queued twice, or is no longer waiting when its turn comes, is skipped.

Success criteria:

- [x] `uv run pytest` passes, with tests (stub model, worker run inline) for `run_agent`, `work_queue`, the 409, and skipping a claim that's no longer waiting.
- [x] With `MODEL_NAME=stub`, `curl -X POST localhost:8000/api/queue/run` returns 25 queued, and within a minute every claim is `decided` or `waiting_for_signoff`. Each claim with a payout over $1,000 has no payment.
- [x] While that run is going, `curl -s localhost:8000/api/queue` shows it running with a falling count, then idle.
- [x] `npm run check` passes.

## Phase 5: The dashboard: queue, claims and instructions

The read side of the dashboard, in the Aegis brand.

- Hash routes with no router library: `#/` for the queue, `#/claims/CLM-1001` for a claim, `#/instructions` for the instructions.
- **Queue:** a table of claims with id, type, summary, submitted date, amount claimed, payout and a status pill (waiting muted, in progress cerulean, waiting for sign-off amber, decided jade). It polls every 2 seconds.
- **Claim:** the story, items, documents and policy, then the decision: outcome, payout, reasons, policy section, and payment status (paid, held for sign-off, or none).
- **Instructions:** the agent's instructions, read only, in a monospace panel.
- Brand tokens for light and dark mode from `docs/BRAND.md`. Money shows as `$1,250.00` in Geist Mono with tabular figures.
- A small typed API module (`dashboard/src/api.ts`) with one function per operation and types matching the backend's responses.

Success criteria:

- [ ] `vitest` passes at 80% coverage or more, with tests for each page, the status pills, money formatting and polling.
- [ ] `tsc` and ESLint pass with no `any`.
- [ ] Through the Playwright MCP server, `http://localhost:5173/` shows 25 claims with status pills, and a screenshot in light mode and in dark mode matches the brand: panels with 12px radius, no outlines and jade as the only accent.
- [ ] Clicking CLM-1001 opens its page with the story, 3 items, 4 documents and the Premium policy.
- [ ] `#/instructions` shows the instructions text, and the page has no edit control.
- [ ] `npm run check` passes.

## Phase 6: The dashboard: running, steps and sign-off, end to end

The actions and the live view, then the whole pilot checked end to end.

- **Run agent** on each waiting claim (on the queue and on the claim page) and **Work the queue** above the queue, which shows "Working the queue, 12 claims left" while it runs.
- On the claim page, the agent's steps appear in order as it works, polled every second while the claim is in progress.
- **Sign off and pay** on a claim waiting for sign-off. Afterwards the page shows the payment and the sign-off time.
- Playwright end-to-end tests run against their own backend and dashboard (ports 8001 and 5174, a fresh `test-results/e2e.db`, `MODEL_NAME=stub`), so they never reuse a dev server or call a model. The Vite proxy target comes from `BACKEND_URL`.
- Update `README.md` (how to install, run and check, briefly) and `docs/STATUS.md`.

Success criteria:

- [ ] Playwright: running the agent on CLM-1001 shows its steps, then "Decided", an approved payout of $420.00 and "Paid".
- [ ] Playwright: running the agent on CLM-1002 ends in "Waiting for sign-off" with no payment. Clicking "Sign off and pay" shows "Paid" and the sign-off time.
- [ ] Playwright: "Work the queue" ends with no waiting claims.
- [ ] `vitest` passes at 80% coverage or more, with tests for the buttons, the steps view and sign-off.
- [ ] Through the Playwright MCP server with the real model: after `npm run reset`, run the agent on a claim from the dashboard and watch its steps arrive while it works. Then click "Work the queue" and let it finish. Every claim ends `decided` or `waiting_for_signoff`, each decision has reasons and a policy section, and every referral states its reason.
- [ ] After that run, `sqlite3 aegis.db "select count(*) from payments p join claims c using (claim_id) where p.amount > 1000 and c.signed_off_at is null"` prints `0`.
- [ ] `npm run check` passes and the results are reported.

## Not in the pilot

- Checking the agent against `data/evals/`, in `docs/PLAN_HARNESS.md`
- The claims manual, sign-in, real payments and messages to customers, as the spec says
- Overriding or rejecting the agent's decisions
- Deploying to AWS
