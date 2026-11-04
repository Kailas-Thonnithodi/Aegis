import { api, type ClaimSummary, type Status } from "./api";
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

export function QueuePage() {
  const claims = usePolling(api.listClaims, 2000);

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
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
