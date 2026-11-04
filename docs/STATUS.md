# Status

Building the pilot from `docs/PLAN.md`. Phases 1 and 2 of 6 are done.

- `backend/`: Aegis's records in SQLite (`aegis.db`, or the path in `AEGIS_DB`), seeded from `data/` on startup when empty. Read operations: `list_claims`, `get_claim`, `get_claim_history`, `get_policy`, `get_policy_wording`, plus `get_health`.
  - Write operations: `start_claim`, `record_decision`, `pay_claim`, `sign_off_claim`, `reset_claim`, `record_step`, `list_steps`, and `get_agent_instructions`, which serves `backend/agent_instructions.md` read only.
  - Status moves `waiting` → `in_progress` → `decided`, or through `waiting_for_signoff` for approvals over $1,000. `pay_claim` refuses any payout over $1,000; only `sign_off_claim` releases it.
- `agent/`: the skeleton entry point `run(claim_id, thread_id)`, with one tool that calls the health route
- `dashboard/`: one page that shows whether the backend is up
- `e2e/`: one test of that page

## Running

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `npm run reset` rebuilds the database from `data/`.
