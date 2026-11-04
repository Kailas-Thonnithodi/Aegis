# Status

Building the pilot from `docs/PLAN.md`. Phase 1 of 6 is done.

- `backend/`: Aegis's records in SQLite (`aegis.db`, or the path in `AEGIS_DB`), seeded from `data/` on startup when empty. Read operations: `list_claims`, `get_claim`, `get_claim_history`, `get_policy`, `get_policy_wording`, plus `get_health`.
- `agent/`: the skeleton entry point `run(claim_id, thread_id)`, with one tool that calls the health route
- `dashboard/`: one page that shows whether the backend is up
- `e2e/`: one test of that page

## Running

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `npm run reset` rebuilds the database from `data/`.
