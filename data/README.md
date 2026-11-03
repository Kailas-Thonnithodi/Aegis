# Data

The business data the backend starts from. Amounts are in AUD.

| File | What it holds |
|---|---|
| `claims.json` | The claims queue: 25 claims, all `open` |
| `policies.json` | 50 policies, one per customer trip, all `active` |
| `policy_wording.md` | The policy wording the agent decides from. Section 1 sets out the three plans and their limits |
| `policy_wording_short.md` | A shorter version of the wording, for reference only |
| `evals/` | The handlers' decisions and held-out claims. The agent never sees these |

## Claims

Each claim has `claim_id`, `policy_id`, `customer_id`, `claim_type`, `status`, `submitted_on`, `incident_date`, `incident_location`, `summary`, the customer's `story`, the `items` claimed (`description`, `category`, `amount`), `amount_claimed` and the supporting `documents` (`name`, `type`, `content`).

Claim types: `baggage`, `baggage_delay`, `trip_delay`, `trip_cancellation`, `trip_interruption`, `passport` and `emergency_medical`.

## Policies

Each policy has `policy_id`, `customer_id`, `plan` (`economy`, `premium` or `first`), `add_ons` (`electronics_plus`, `adventure_sports`, `pre_existing_waiver`), `purchased_on`, `sold_through`, the `trip` (`destination`, `departs_on`, `returns_on`, `trip_cost`), the `travelers` and `status`.

There's no separate customers file: a customer is identified by `customer_id`, the policy's `travelers` lists who is covered, and the customer's claim history is their other claims in `claims.json`.
