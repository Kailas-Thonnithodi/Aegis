import { useState } from "react";

import { api, type CheckClaim, type CheckRunSummary } from "./api";
import { label, outcomeLabels, setLabels, time } from "./format";
import { usePolling } from "./hooks";

type FilterKey = "set" | "claim_type" | "difficulty" | "handler_outcome";
type Filters = Record<FilterKey, string>;

const noFilters: Filters = {
  set: "",
  claim_type: "",
  difficulty: "",
  handler_outcome: "",
};

function optionLabel(key: FilterKey, value: string): string {
  if (key === "set") return setLabels[value] ?? value;
  if (key === "handler_outcome" && value in outcomeLabels) {
    return outcomeLabels[value as keyof typeof outcomeLabels];
  }
  return label(value);
}

function Filter({
  name,
  filterKey,
  claims,
  filters,
  onChange,
}: Readonly<{
  name: string;
  filterKey: FilterKey;
  claims: CheckClaim[];
  filters: Filters;
  onChange: (filters: Filters) => void;
}>) {
  const values = [...new Set(claims.map((claim) => claim[filterKey]))].sort(
    (a, b) => a.localeCompare(b),
  );
  return (
    <label className="filter">
      <span className="muted">{name}</span>
      <select
        value={filters[filterKey]}
        onChange={(event) => {
          onChange({ ...filters, [filterKey]: event.target.value });
        }}
      >
        <option value="">All</option>
        {values.map((value) => (
          <option key={value} value={value}>
            {optionLabel(filterKey, value)}
          </option>
        ))}
      </select>
    </label>
  );
}

function picked(count: number): string {
  return count === 1 ? "1 claim picked" : `${String(count)} claims picked`;
}

function progress(run: CheckRunSummary): string {
  if (run.finished_at === null) {
    return `Checking, ${String(run.done)} of ${String(run.claims)} done`;
  }
  return `${String(run.matches)} of ${String(run.claims)} match`;
}

function RunsPanel() {
  const runs = usePolling(api.listCheckRuns, 2000).data ?? [];

  return (
    <section className="panel">
      <h2>Check runs</h2>
      {runs.length === 0 ? (
        <p className="muted">No check runs yet.</p>
      ) : (
        <ul className="runs">
          {runs.map((run) => (
            <li key={run.run_id}>
              <a href={`#/checks/${String(run.run_id)}`}>Run {run.run_id}</a>
              <span className="muted">{time(run.started_at)}</span>
              <span>{progress(run)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function ChecksPage() {
  const claims = usePolling(api.listCheckClaims, null).data;
  const [filters, setFilters] = useState<Filters>(noFilters);
  const [selection, setSelection] = useState<ReadonlySet<string>>(new Set());
  const [starting, setStarting] = useState(false);

  if (claims === undefined) {
    return <p className="muted">Loading the claims.</p>;
  }

  const shown = claims.filter((claim) =>
    (Object.keys(filters) as FilterKey[]).every(
      (key) => filters[key] === "" || claim[key] === filters[key],
    ),
  );
  const toggle = (claimId: string) => {
    const next = new Set(selection);
    if (next.has(claimId)) next.delete(claimId);
    else next.add(claimId);
    setSelection(next);
  };
  const start = () => {
    setStarting(true);
    const claimIds = claims
      .filter((claim) => selection.has(claim.claim_id))
      .map((claim) => claim.claim_id);
    void api.startCheck(claimIds).then((run) => {
      window.location.hash = `#/checks/${String(run.run_id)}`;
    });
  };

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Agent checks</h1>
          <p className="muted">
            Pick claims, and the agent works them fresh. Its decisions are
            scored against the handlers'.
          </p>
        </div>
        <div className="header-actions">
          <span className="muted">{picked(selection.size)}</span>
          <button
            type="button"
            disabled={selection.size === 0 || starting}
            onClick={start}
          >
            Run checks
          </button>
        </div>
      </header>
      <div className="stack">
        <section className="panel">
          <div className="filters">
            <Filter
              name="Set"
              filterKey="set"
              claims={claims}
              filters={filters}
              onChange={setFilters}
            />
            <Filter
              name="Claim type"
              filterKey="claim_type"
              claims={claims}
              filters={filters}
              onChange={setFilters}
            />
            <Filter
              name="Difficulty"
              filterKey="difficulty"
              claims={claims}
              filters={filters}
              onChange={setFilters}
            />
            <Filter
              name="Handler's decision"
              filterKey="handler_outcome"
              claims={claims}
              filters={filters}
              onChange={setFilters}
            />
            <div className="filter-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setSelection(
                    new Set([...selection, ...shown.map((c) => c.claim_id)]),
                  );
                }}
              >
                Select all shown
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setSelection(new Set());
                }}
              >
                Clear
              </button>
            </div>
          </div>
          <p className="muted shown-count">
            Showing {shown.length} of {claims.length} claims
          </p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col">
                    <span className="visually-hidden">Pick</span>
                  </th>
                  <th scope="col">Claim</th>
                  <th scope="col">Set</th>
                  <th scope="col">Type</th>
                  <th scope="col">Summary</th>
                  <th scope="col">Difficulty</th>
                  <th scope="col">Handler's decision</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((claim) => (
                  <tr key={claim.claim_id}>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={`Pick ${claim.claim_id}`}
                        checked={selection.has(claim.claim_id)}
                        onChange={() => {
                          toggle(claim.claim_id);
                        }}
                      />
                    </td>
                    <td className="mono">{claim.claim_id}</td>
                    <td className="nowrap">{setLabels[claim.set]}</td>
                    <td className="nowrap">{label(claim.claim_type)}</td>
                    <td className="summary">{claim.summary}</td>
                    <td>{label(claim.difficulty)}</td>
                    <td>{outcomeLabels[claim.handler_outcome]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <RunsPanel />
      </div>
    </>
  );
}
