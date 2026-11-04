import { useState } from "react";

import { api, type ClaimSummary, type QueueRun, type Status } from "./api";
import { date, label, money, outcomeLabels, statusLabels } from "./format";
import { usePolling } from "./hooks";
import { StatusPill } from "./StatusPill";

const statuses: Status[] = [
  "waiting",
  "in_progress",
  "waiting_for_signoff",
  "decided",
];

function decision(claim: ClaimSummary): string {
  if (claim.outcome === null) return "";
  if (claim.outcome === "approve" && claim.payout !== null) {
    return `Approved, ${money(claim.payout)}`;
  }
  return outcomeLabels[claim.outcome];
}

function QueueControl({
  run,
  waiting,
  onStarted,
}: Readonly<{
  run: QueueRun | undefined;
  waiting: number;
  onStarted: () => void;
}>) {
  if (run?.running) {
    return (
      <p className="working">
        Working the queue, {run.claims_left} claims left
      </p>
    );
  }
  return (
    <button
      type="button"
      disabled={waiting === 0}
      onClick={() => {
        void api.workQueue().then(onStarted);
      }}
    >
      Work the queue
    </button>
  );
}

function RunButton({
  claimId,
  onStarted,
}: Readonly<{ claimId: string; onStarted: () => void }>) {
  const [queued, setQueued] = useState(false);

  return (
    <button
      type="button"
      className="small"
      disabled={queued}
      aria-label={`Run agent on ${claimId}`}
      onClick={() => {
        setQueued(true);
        void api.runAgent(claimId).then(onStarted, onStarted);
      }}
    >
      {queued ? "Queued" : "Run agent"}
    </button>
  );
}

export function QueuePage() {
  const claims = usePolling(api.listClaims, 2000);
  const run = usePolling(api.getQueueRun, 2000);
  const queueRunning = run.data?.running ?? false;
  const refresh = () => {
    claims.refresh();
    run.refresh();
  };

  if (claims.data === undefined) {
    return (
      <p className="muted">
        {claims.failed ? "The backend can't be reached." : "Loading the queue."}
      </p>
    );
  }

  const count = (status: Status) =>
    claims.data?.filter((claim) => claim.status === status).length ?? 0;

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Claims queue</h1>
          <p className="muted">{claims.data.length} claims</p>
        </div>
        <QueueControl
          run={run.data}
          waiting={count("waiting")}
          onStarted={refresh}
        />
      </header>
      <section className="counts" aria-label="Claims by status">
        {statuses.map((status) => (
          <div className="panel count" key={status}>
            <span className="count-value">{count(status)}</span>
            <span className="muted">{statusLabels[status]}</span>
          </div>
        ))}
      </section>
      <section className="panel table-panel">
        <table>
          <thead>
            <tr>
              <th scope="col">Claim</th>
              <th scope="col">Type</th>
              <th scope="col">Summary</th>
              <th scope="col">Submitted</th>
              <th scope="col" className="number">
                Claimed
              </th>
              <th scope="col">Decision</th>
              <th scope="col">Status</th>
              <th scope="col">
                <span className="visually-hidden">Action</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {claims.data.map((claim) => (
              <tr key={claim.claim_id}>
                <td>
                  <a className="mono" href={`#/claims/${claim.claim_id}`}>
                    {claim.claim_id}
                  </a>
                </td>
                <td className="nowrap">{label(claim.claim_type)}</td>
                <td className="summary">{claim.summary}</td>
                <td className="nowrap">{date(claim.submitted_on)}</td>
                <td className="number">{money(claim.amount_claimed)}</td>
                <td className="nowrap">{decision(claim)}</td>
                <td>
                  <StatusPill status={claim.status} />
                </td>
                <td>
                  {claim.status === "waiting" && !queueRunning && (
                    <RunButton claimId={claim.claim_id} onStarted={refresh} />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
