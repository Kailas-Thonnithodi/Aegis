# Status

Building the pilot from `docs/PLAN.md`. Phases 1 to 4 of 6 are done.

- `backend/`: Aegis's records in SQLite (`aegis.db`, or the path in `AEGIS_DB`), seeded from `data/` on startup when empty. Read operations: `list_claims`, `get_claim`, `get_claim_history`, `get_policy`, `get_policy_wording`, plus `get_health`.
  - Write operations: `start_claim`, `record_decision`, `pay_claim`, `sign_off_claim`, `reset_claim`, `record_step`, `list_steps`, and `get_agent_instructions`, which serves `backend/agent_instructions.md` read only.
  - Runs: `run_agent` queues one waiting claim, `work_queue` queues every waiting claim, and `get_queue_run` reports progress. One background worker runs them one at a time.
  - Status moves `waiting` → `in_progress` → `decided`, or through `waiting_for_signoff` for approvals over $1,000. `pay_claim` refuses any payout over $1,000; only `sign_off_claim` releases it.
- `agent/`: the Aegis Agent. `run(claim_id, thread_id)` starts the claim, works it with six tools over the backend's API (`get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `record_decision`, `pay_claim`) and posts each step. A run that ends with the claim still in progress returns it to the queue. `MODEL_NAME=stub` selects a scripted model for tests.
- `dashboard/`: one page that shows whether the backend is up
- `e2e/`: one test of that page

## Running

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `npm run reset` rebuilds the database from `data/`.
- `uv run -m agent CLM-1001` runs the agent on one claim. The backend must be running.
