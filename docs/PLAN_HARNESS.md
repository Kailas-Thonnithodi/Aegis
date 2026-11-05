# Plan: the agent checker

The spec says the handlers' own decisions in `data/evals/` are there "to check the agent's work". This build adds that check. On a new Checks page, a handler picks claims, by hand or with filters, and clicks **Run checks**. The Aegis Agent then works each picked claim fresh, and the page shows how its decisions compare with the handlers': outcome, payout, and both sets of reasons side by side.

It builds on the pilot in `docs/PLAN.md`.

## Decisions already made

Kailas settled these on 2026-11-05:

- **What the checker does:** it scores the agent's decisions against the handlers' decisions.
- **Which claims:** the handler picks them, one by one or through filters. Both sets are available: the 25 queue claims (answer key `decisions.json`) and the 25 held-out claims (`held_out_claims.json`, answer key `held_out_decisions.json`).
- **Process:** this plan comes first, and the build starts only when Kailas says so.

## What's in `data/evals/`

Each handler decision has `claim_id`, `decision` (`approve`, `decline` or `refer`), `payout`, `over_approval_limit`, `reason`, `reference`, `calculation` (the payout steps), `tests` (what the claim tests), `difficulty` (`routine`, `hard` or `manual`), `failure_class`, `needs` (`manual`, `history`), `tone`, `tiny`, `handler_id` and `decided_on`. Both sets have 14 approvals, 5 declines and 6 referrals. The held-out claims use policies already in `policies.json`, and no held-out customer appears in the queue.

**A difficulty to keep in mind:** in each set, 5 decisions are marked `difficulty: manual`. They rest on the claims manual, which the pilot spec leaves out ("the agent works from the policy wording alone"). The agent can't be expected to match those, so every score is shown twice: over all picked claims, and over the picked claims that don't need the manual.

## Approach

**Check runs never touch the live queue.** A check run works its claims in a separate database, `checks.db`, rebuilt at the start of each run from `claims.json`, `held_out_claims.json` and `policies.json`, with every claim waiting. The same API is mounted a second time at `/check`, with `checks.db` behind it. For a check, the agent runs against `http://localhost:8000/check`, so its tools, instructions and rules are exactly what it uses on the queue. The $1,000 sign-off rule still holds, and payments in `checks.db` are only records.

**Every check is a fresh run.** Queue claims are run again in `checks.db` rather than scored from the decisions already on the live queue. That way every result reflects the current instructions, and the two sets are scored the same way.

**The agent never sees the answer key.** The answer key is read only by `backend/checker.py`, and only after a claim is worked, to score it. The agent's six tools stay the same, none of them reaches a check result, and the API mounted at `/check` serves claims, not handler decisions. The held-out claims become visible to the agent only as claims to work, which is their purpose.

**Scoring is plain and strict.**
- A claim's **outcome matches** when the agent's outcome equals the handler's.
- Its **payout matches** when the amounts are equal to the cent. Declines and referrals pay $0.00.
- It **matches** when both do.

A run reports each of these as a count and a percentage, over all its claims and over those that don't need the manual. It also breaks them down by set, by difficulty and by claim type. A claim the agent didn't finish, for example after a model error, is reported as not finished and counts as a miss.

**Runs share the one worker.** Check runs join the same single background worker as queue runs. They run one claim at a time, behind any queue run, and stay inside the OpenRouter rate limit. At about 4 claims a minute, all 50 claims take roughly 12 to 15 minutes.

**The agent's entry point gains one keyword.** `run(claim_id, thread_id, base_url=BACKEND_URL)` selects which backend the agent talks to, so a check points it at `/check`. Everything else about the agent stays as it is.

## Phase 1: The answer key and scoring

- `backend/checker.py` loads both answer keys and the held-out claims, and has a pure function that scores one agent decision against one handler decision.
- A summary function totals a list of scored claims: overall, without the manual claims, by set, by difficulty and by claim type.

Success criteria:

- [x] `uv run pytest backend` passes, with tests for each scoring case: outcome and payout match, outcome matches but payout differs, outcome differs, not finished.
- [x] A test shows the summary over a mix of results gives the right counts and percentages, both overall and without the manual claims.
- [x] A test shows the checker loads 25 queue decisions and 25 held-out decisions, and their claim ids match `claims.json` and `held_out_claims.json`.
- [x] `grep -rn "evals" agent` prints nothing.
- [x] `npm run check` passes.

## Phase 2: The check database and check runs

- `checks.db` (gitignored, or the path in `AEGIS_CHECK_DB`), rebuilt at the start of each run with all 50 claims and all policies.
- The API mounted at `/check` with `checks.db` behind it. Its claims list holds both sets, and claim history stays within each set.
- New tables in `aegis.db`: `check_runs` (id, started and finished times, claim count) and `check_results` (run, claim, set, the agent's outcome, payout, reasons and policy section, its steps, and the score).
- `POST /api/checks` → `start_check`, taking `claim_ids`: refuses an empty list or an unknown claim, records the run and hands it to the worker. The worker rebuilds `checks.db`, runs the agent on each claim against `/check`, scores each claim as it finishes and marks the run finished.
- The keyword `base_url` on `agent.run`.

Success criteria:

- [x] `uv run pytest` passes, with tests (stub model, worker run inline) showing that a check run on CLM-1001 and CLM-1101 scores both claims and stores their steps.
- [x] A test shows a check run leaves the live queue untouched: every claim's status, decision and payment in `aegis.db` is the same before and after.
- [x] A test shows `start_check` returns 422 for an empty list and 404 for an unknown claim id.
- [x] A test shows no response from the `/check` API includes a handler's decision, reason or calculation.
- [x] With `MODEL_NAME=stub`, a curl to `POST /api/checks` with `["CLM-1001", "CLM-1101"]` returns the run, and within seconds the run is finished with 2 results.
- [x] `npm run check` passes.

## Phase 3: The check API

- `GET /api/checks/claims` → `list_check_claims`: all 50 claims, each with its set, claim type, summary, amount claimed, difficulty and the handler's outcome, for the picker and its filters.
- `GET /api/checks` → `list_check_runs`: every run, newest first, with its progress (claims done out of picked) and headline score.
- `GET /api/checks/{run_id}` → `get_check_run`: the run's summary, its breakdowns and one result per claim. Each result shows the agent's and the handler's outcome, payout, reasons and policy reference side by side, plus what the claim tests and the agent's steps.

Success criteria:

- [x] `uv run pytest backend` passes, with tests for each operation and for 404 on an unknown run.
- [x] `curl -s localhost:8000/api/checks/claims` returns 50 claims, 25 in each set, with 5 marked `manual` in each.
- [x] After a stub-model run on CLM-1001 and CLM-1101, `curl -s localhost:8000/api/checks/1` shows CLM-1001 as a match (the stub approves the $420.00 claimed, which is the handler's payout) and CLM-1101 as a payout miss (the stub approves $2,580.00, the handler $580.00).
- [x] `npm run check` passes.

## Phase 4: The Checks page: picking claims

- A **Checks** link in the top navigation, at `#/checks`.
- The claim picker: a table of all 50 claims with a checkbox on each, and filters for set (queue, held-out), claim type, difficulty and the handler's outcome. "Select all shown" picks every claim the filters show. The selection count reads "12 claims picked".
- **Run checks** starts a run on the picked claims and opens its results page. It's disabled when nothing is picked.
- Below the picker, a list of past runs with their progress and headline score, each linking to its results.

Success criteria:

- [x] `vitest` passes at 80% coverage or more, with tests for each filter, "Select all shown", the selection count, the disabled button and starting a run.
- [x] Through the Playwright MCP server, `#/checks` shows 50 claims. Filtering to held-out, then hard, leaves only those claims, and "Select all shown" picks them all. Screenshots in light and dark mode match the brand.
- [x] `npm run check` passes.

## Phase 5: The Checks page: results, end to end

- **Run results** at `#/checks/1`:
  - Progress while the run goes ("Checking 7 of 12 claims"), polled every 2 seconds.
  - Score tiles: matches, outcome matches and payout matches, each over all claims and over claims that don't need the manual.
  - A breakdown by set and by difficulty.
  - One row per claim, marked match, payout miss, outcome miss or not finished. A row opens to show both decisions side by side, the handler's calculation, what the claim tests and the agent's steps.
- Playwright tests with the stub model.
- Update `docs/STATUS.md` and `README.md`.

Success criteria:

- [x] Playwright: picking CLM-1001 and CLM-1101 and clicking "Run checks" opens the results page. It ends with CLM-1001 marked a match, CLM-1101 a payout miss, and a score of 1 of 2.
- [x] Playwright: the live queue shows the same statuses before and after a check run.
- [x] `vitest` passes at 80% coverage or more, with tests for the progress, the score tiles, the breakdown and an opened row.
- [x] Through the Playwright MCP server with the real model: run checks on all 25 held-out claims and let the run finish. Every claim has a result, and the score is shown overall and without the manual claims. Report the scores to Kailas, along with the claims the agent missed and why.
- [x] `npm run check` passes and the results are reported.

## Not in this build

- Changing the agent's instructions to raise the score. That comes after Kailas has seen the first results.
- Giving the agent the claims manual, which is still out of scope
- Comparing the wording of reasons with the handlers' (tone, length). Results show both reasons side by side for a person to read.
- Scheduled or automatic check runs
