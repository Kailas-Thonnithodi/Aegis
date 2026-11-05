# Status

The claims pilot from `docs/PLAN.md` and the agent checker from `docs/PLAN_HARNESS.md` are built.

- `backend/`: FastAPI and SQLite (`aegis.db`, or the path in `AEGIS_DB`), seeded from `data/` on startup when empty. Only `backend/checker.py` reads `data/evals/`, and the agent never sees it.
  - Read operations: `list_claims`, `get_claim`, `get_claim_history`, `get_policy`, `get_policy_wording`, `get_agent_instructions` (serves `backend/agent_instructions.md`, read only) and `get_health`.
  - Write operations: `start_claim`, `record_decision`, `pay_claim`, `sign_off_claim`, `reset_claim`, `record_step` and `list_steps`.
  - Runs: `run_agent` queues one waiting claim, `work_queue` queues every waiting claim, and `get_queue_run` reports progress. One background worker runs them one at a time.
  - Status moves `waiting` → `in_progress` → `decided`, or through `waiting_for_signoff` for approvals over $1,000. `pay_claim` refuses any payout over $1,000; only `sign_off_claim` releases it.
- `agent/`: the Aegis Agent. `run(claim_id, thread_id)` starts the claim, works it with six tools over the backend's API (`get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `record_decision`, `pay_claim`) and posts each step. A run that ends with the claim still in progress returns it to the queue. `MODEL_NAME=stub` selects a scripted model for tests. Model calls are paced at about 18 a minute, because OpenRouter limits new accounts to 20 a minute per model.
- `dashboard/`:
  - The queue (`#/`) shows counts by status, a Run agent button on each waiting claim and a Work the queue button with progress. It polls every 2 seconds.
  - Each claim (`#/claims/CLM-1001`) shows the claim in full, the decision with its reasons and policy section, the agent's steps as they arrive, the policy and, for approvals over $1,000, Sign off and pay. It polls every second.
  - The agent's instructions (`#/instructions`) are read only.
  - Brand colors and fonts, light and dark mode.
- Agent checker:
  - `backend/checker.py` is the only code that reads the handlers' decisions in `data/evals/`, and it reads them only to score.
  - `start_check` records a check run. The worker rebuilds `checks.db` (or the path in `AEGIS_CHECK_DB`) with all 50 claims (queue and held-out), runs the agent on each picked claim through the same API mounted at `/check`, and stores each result with its score: match, payout miss, outcome miss or not finished. The live queue is never touched.
  - `list_check_claims`, `list_check_runs` and `get_check_run` serve the picker, the runs and each run's results.
  - `agent.run` takes `base_url` to choose which backend the agent works against.
  - Checks page (`#/checks`): pick claims by hand or with filters (set, claim type, difficulty, handler's decision), run checks and see past runs. Each run (`#/checks/1`) shows its progress, its scores over all claims and without the claims that need the claims manual, a breakdown by set and difficulty, and each claim's decision beside the handler's.
- `e2e/`: Playwright tests of the pages, a run, sign-off and working the queue, and of checks, on their own backend (port 8001, `e2e.db`, `e2e-checks.db`, `MODEL_NAME=stub`) and dashboard (port 5174)

## Running

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `npm run reset` rebuilds the database from `data/`.
- `uv run -m agent CLM-1001` runs the agent on one claim from the command line. The backend must be running.
