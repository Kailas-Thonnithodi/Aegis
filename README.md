# Aegis

The claims platform for Aegis Travel Insurance: a backend, a dashboard for the claims handlers and the Aegis Agent, which decides claims.

## Setup

Needs Python 3.12 or later with uv, and Node 26. Put your OpenRouter key in `.env`:

```
OPENROUTER_API_KEY=...
```

Then install everything, including the pre-commit hook:

```
uv sync
npm install
```

## Run

```
npm run dev
```

This starts the backend on port 8000 and the dashboard at http://localhost:5173. From the queue, run the agent on one claim or click "Work the queue". On the Checks page, pick claims and click "Run checks" to score the agent's decisions against the handlers'. `npm run reset` rebuilds the database from `data/`.

Set `MODEL_NAME` to use another model, such as `MODEL_NAME=openrouter/free`, or `MODEL_NAME=stub` for a scripted model that calls no API.

## Check

```
npm run check
```

Runs ruff, pyright, pytest, ESLint, Prettier, tsc, vitest and the Playwright tests. See `docs/` for the spec, the plan and what's built.
