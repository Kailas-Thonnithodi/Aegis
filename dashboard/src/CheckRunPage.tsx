import { useCallback } from "react";

import {
  api,
  type CheckResult,
  type CheckRun,
  type Outcome,
  type Score,
  type Tally,
} from "./api";
import { label, money, outcomeLabels, setLabels, time } from "./format";
import { usePolling } from "./hooks";

const scoreLabels: Record<Score, string> = {
  match: "Match",
  payout_miss: "Payout miss",
  outcome_miss: "Outcome miss",
  not_finished: "Not finished",
};

const stillRunning = (run: CheckRun) => run.finished_at === null;

function percent(part: number, whole: number): string {
  if (whole === 0) return "";
  return `${String(Math.round((part / whole) * 100))}%`;
}

function decision(outcome: Outcome | null, payout: number | null): string {
  if (outcome === null) return "Not decided";
  if (outcome === "approve") return `Approved, ${money(payout ?? 0)}`;
  return outcomeLabels[outcome];
}

function needsText(needs: string[]): string {
  if (needs.length === 0) return "";
  const names = needs.map((need) =>
    need === "manual" ? "the claims manual" : "the claim history",
  );
  return `. Needs ${names.join(" and ")}`;
}

function ScorePill({ score }: Readonly<{ score: Score | null }>) {
  if (score === null) return <span className="pill pill-pending">Pending</span>;
  return (
    <span className={`pill pill-score-${score}`}>{scoreLabels[score]}</span>
  );
}

function ScoreTile({
  name,
  count,
  all,
  withoutManual,
}: Readonly<{
  name: string;
  count: (tally: Tally) => number;
  all: Tally;
  withoutManual: Tally;
}>) {
  return (
    <div className="panel count">
      <span className="muted">{name}</span>
      <span className="count-value">
        {count(all)} of {all.claims}
      </span>
      <span className="muted">{percent(count(all), all.claims)}</span>
      <span className="muted tile-note">
        Without manual claims: {count(withoutManual)} of {withoutManual.claims}
        {withoutManual.claims > 0 &&
          `, ${percent(count(withoutManual), withoutManual.claims)}`}
      </span>
    </div>
  );
}

function Breakdown({ run }: Readonly<{ run: CheckRun }>) {
  const groups = [
    ...Object.entries(run.summary.by_set).map(
      ([key, tally]) => [setLabels[key] ?? key, tally] as const,
    ),
    ...Object.entries(run.summary.by_difficulty).map(
      ([key, tally]) => [label(key), tally] as const,
    ),
  ];

  return (
    <section className="panel">
      <h2>By set and difficulty</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">Group</th>
            <th scope="col" className="number">
              Claims
            </th>
            <th scope="col" className="number">
              Matches
            </th>
            <th scope="col" className="number">
              Outcome matches
            </th>
            <th scope="col" className="number">
              Payout matches
            </th>
          </tr>
        </thead>
        <tbody>
          {groups.map(([name, tally]) => (
            <tr key={name}>
              <th scope="row">{name}</th>
              <td className="number">{tally.claims}</td>
              <td className="number">{tally.matches}</td>
              <td className="number">{tally.outcome_matches}</td>
              <td className="number">{tally.payout_matches}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function ResultDetail({ result }: Readonly<{ result: CheckResult }>) {
  const { agent, handler } = result;

  return (
    <div className="result-detail">
      <div className="compare">
        <div>
          <h3>Agent</h3>
          <p className="outcome-line">
            {decision(agent.outcome, agent.payout)}
          </p>
          <p>{agent.reasons ?? "The agent didn't record a decision."}</p>
          {agent.policy_section && (
            <p className="muted">{agent.policy_section}</p>
          )}
        </div>
        <div>
          <h3>Handler</h3>
          <p className="outcome-line">
            {decision(handler.decision, handler.payout)}
          </p>
          <p>{handler.reason}</p>
          <p className="muted">{handler.reference}</p>
          {handler.calculation.length > 0 && (
            <ul className="calculation">
              {handler.calculation.map((line) => (
                <li key={line.step}>
                  <span>{line.step}</span>
                  <span className="mono">{money(line.amount)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <p className="muted">
        Tests: {handler.tests}
        {needsText(handler.needs)}
      </p>
      {result.steps.length > 0 && (
        <ol className="result-steps">
          {result.steps.map((step, index) => (
            <li key={`${step.at}-${String(index)}`}>
              <span>{step.title}</span>
              <span className="step-time">{time(step.at)}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function ResultRow({ result }: Readonly<{ result: CheckResult }>) {
  return (
    <li>
      <details className="result">
        <summary>
          <span className="mono">{result.claim_id}</span>
          <span className="muted nowrap">{setLabels[result.handler.set]}</span>
          <span className="result-summary">{result.summary}</span>
          <span className="nowrap">
            Agent: {decision(result.agent.outcome, result.agent.payout)}
          </span>
          <span className="nowrap">
            Handler: {decision(result.handler.decision, result.handler.payout)}
          </span>
          <ScorePill score={result.score} />
        </summary>
        <ResultDetail result={result} />
      </details>
    </li>
  );
}

export function CheckRunPage({ runId }: Readonly<{ runId: string }>) {
  const load = useCallback(() => api.getCheckRun(runId), [runId]);
  const { data: run, failed } = usePolling(load, 2000, stillRunning);

  if (run === undefined) {
    return (
      <p className="muted">
        {failed ? `Check run ${runId} can't be loaded.` : "Loading the run."}
      </p>
    );
  }

  const { overall, without_manual: withoutManual } = run.summary;

  return (
    <>
      <a className="back" href="#/checks">
        Back to checks
      </a>
      <header className="page-header">
        <div>
          <h1>Check run {run.run_id}</h1>
          <p className="muted">
            Started {time(run.started_at)}, {run.claims} claims
          </p>
        </div>
        <p className="working">
          {run.finished_at === null
            ? `Checking ${String(run.done)} of ${String(run.claims)} claims`
            : `Finished ${time(run.finished_at)}`}
        </p>
      </header>
      <section className="counts" aria-label="Scores">
        <ScoreTile
          name="Matches"
          count={(tally) => tally.matches}
          all={overall}
          withoutManual={withoutManual}
        />
        <ScoreTile
          name="Outcome matches"
          count={(tally) => tally.outcome_matches}
          all={overall}
          withoutManual={withoutManual}
        />
        <ScoreTile
          name="Payout matches"
          count={(tally) => tally.payout_matches}
          all={overall}
          withoutManual={withoutManual}
        />
      </section>
      <div className="stack">
        <Breakdown run={run} />
        <section className="panel">
          <h2>Claims</h2>
          <ul className="results">
            {run.results.map((result) => (
              <ResultRow key={result.claim_id} result={result} />
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}
