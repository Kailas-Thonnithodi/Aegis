import { useCallback, useState } from "react";

import { api, type Claim } from "./api";
import { date, label, money, outcomeLabels, time } from "./format";
import { usePolling } from "./hooks";
import { StatusPill } from "./StatusPill";

function Fact({
  name,
  children,
}: Readonly<{ name: string; children: React.ReactNode }>) {
  return (
    <div className="fact">
      <dt>{name}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function payment(claim: Claim): string {
  if (claim.payment !== null) {
    return `Paid ${money(claim.payment.amount)} on ${time(claim.payment.paid_at)}`;
  }
  if (claim.status === "waiting_for_signoff") return "Held for sign-off";
  return "None";
}

function SignOff({
  claimId,
  onSignedOff,
}: Readonly<{ claimId: string; onSignedOff: () => void }>) {
  const [signing, setSigning] = useState(false);

  return (
    <div className="signoff">
      <p className="muted">
        This payout is over $1,000 and waits for a handler's sign-off.
      </p>
      <button
        type="button"
        disabled={signing}
        onClick={() => {
          setSigning(true);
          void api.signOff(claimId).then(onSignedOff);
        }}
      >
        Sign off and pay
      </button>
    </div>
  );
}

function DecisionPanel({
  claim,
  onChanged,
}: Readonly<{ claim: Claim; onChanged: () => void }>) {
  if (claim.outcome === null) {
    return (
      <section className="panel">
        <h2>Decision</h2>
        <p className="muted">The agent hasn't decided this claim yet.</p>
      </section>
    );
  }
  return (
    <section className="panel">
      <h2>Decision</h2>
      <p className="outcome">{outcomeLabels[claim.outcome]}</p>
      <p>{claim.reasons}</p>
      <dl className="facts">
        <Fact name="Payout">
          <span className="mono">{money(claim.payout ?? 0)}</span>
        </Fact>
        <Fact name="Policy section">{claim.policy_section}</Fact>
        <Fact name="Payment">{payment(claim)}</Fact>
        {claim.signed_off_at !== null && (
          <Fact name="Signed off">{time(claim.signed_off_at)}</Fact>
        )}
      </dl>
      {claim.status === "waiting_for_signoff" && (
        <SignOff claimId={claim.claim_id} onSignedOff={onChanged} />
      )}
    </section>
  );
}

function StepsPanel({
  claimId,
  status,
}: Readonly<{ claimId: string; status: Claim["status"] }>) {
  const load = useCallback(() => api.listSteps(claimId), [claimId]);
  const working = status === "waiting" || status === "in_progress";
  const steps = usePolling(load, working ? 1000 : null).data ?? [];

  return (
    <section className="panel">
      <h2>Agent steps</h2>
      {steps.length === 0 ? (
        <p className="muted">
          {status === "in_progress"
            ? "The agent's first step will show here."
            : "The agent hasn't worked this claim yet."}
        </p>
      ) : (
        <ol className="steps">
          {steps.map((step, index) => (
            <li key={`${step.at}-${String(index)}`}>
              <details className="step">
                <summary>
                  <span>{step.title}</span>
                  <span className="step-time">{time(step.at)}</span>
                </summary>
                <p className="step-detail">{step.detail}</p>
              </details>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function PolicyPanel({ policyId }: Readonly<{ policyId: string }>) {
  const load = useCallback(() => api.getPolicy(policyId), [policyId]);
  const policy = usePolling(load, null).data;

  return (
    <section className="panel">
      <h2>
        Policy <span className="mono muted">{policyId}</span>
      </h2>
      {policy && (
        <dl className="facts">
          <Fact name="Plan">{label(policy.plan)}</Fact>
          <Fact name="Add-ons">
            {policy.add_ons.length > 0
              ? policy.add_ons.map(label).join(", ")
              : "None"}
          </Fact>
          <Fact name="Travelers">{policy.travelers.join(", ")}</Fact>
          <Fact name="Trip">{policy.trip.destination}</Fact>
          <Fact name="Dates">
            {date(policy.trip.departs_on)} to {date(policy.trip.returns_on)}
          </Fact>
          <Fact name="Trip cost">
            <span className="mono">{money(policy.trip.trip_cost)}</span>
          </Fact>
          <Fact name="Bought">
            {date(policy.purchased_on)}, {policy.sold_through}
          </Fact>
        </dl>
      )}
    </section>
  );
}

function ClaimDetails({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <div className="stack">
      <section className="panel">
        <h2>Story</h2>
        <p>{claim.story}</p>
      </section>
      <section className="panel">
        <h2>Items claimed</h2>
        <table>
          <thead>
            <tr>
              <th scope="col">Item</th>
              <th scope="col">Category</th>
              <th scope="col" className="number">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.description}>
                <td>{item.description}</td>
                <td>{label(item.category)}</td>
                <td className="number">{money(item.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row" colSpan={2}>
                Total claimed
              </th>
              <td className="number">{money(claim.amount_claimed)}</td>
            </tr>
          </tfoot>
        </table>
      </section>
      <section className="panel">
        <h2>Documents</h2>
        <ul className="documents">
          {claim.documents.map((document) => (
            <li key={document.name}>
              <p className="document-name">
                {document.name}{" "}
                <span className="muted">{label(document.type)}</span>
              </p>
              <p className="document-content">{document.content}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const load = useCallback(() => api.getClaim(claimId), [claimId]);
  const { data: claim, failed, refresh } = usePolling(load, 1000);
  const [queued, setQueued] = useState(false);

  if (claim === undefined) {
    return (
      <p className="muted">
        {failed ? `Claim ${claimId} can't be loaded.` : "Loading the claim."}
      </p>
    );
  }

  return (
    <>
      <a className="back" href="#/">
        Back to the queue
      </a>
      <header className="page-header">
        <div>
          <p className="eyebrow">
            <span className="mono">{claim.claim_id}</span>
            <StatusPill status={claim.status} />
          </p>
          <h1>{claim.summary}</h1>
          <p className="muted">
            {label(claim.claim_type)}, {claim.incident_location},{" "}
            {date(claim.incident_date)}. Submitted {date(claim.submitted_on)}.
          </p>
        </div>
        {claim.status === "waiting" && (
          <button
            type="button"
            disabled={queued}
            onClick={() => {
              setQueued(true);
              void api.runAgent(claimId).then(refresh, refresh);
            }}
          >
            {queued ? "Queued" : "Run agent"}
          </button>
        )}
        {claim.status === "in_progress" && (
          <p className="working">The agent is working on this claim.</p>
        )}
      </header>
      <div className="columns">
        <ClaimDetails claim={claim} />
        <div className="stack">
          <DecisionPanel claim={claim} onChanged={refresh} />
          <StepsPanel claimId={claim.claim_id} status={claim.status} />
          <PolicyPanel policyId={claim.policy_id} />
        </div>
      </div>
    </>
  );
}
