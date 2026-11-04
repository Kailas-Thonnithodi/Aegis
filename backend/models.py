from typing import Literal

from pydantic import BaseModel

Status = Literal["waiting", "in_progress", "waiting_for_signoff", "decided"]
Outcome = Literal["approve", "decline", "refer"]


class Item(BaseModel):
    description: str
    category: str
    amount: float


class Document(BaseModel):
    name: str
    type: str
    content: str


class Trip(BaseModel):
    destination: str
    departs_on: str
    returns_on: str
    trip_cost: float


class Policy(BaseModel):
    policy_id: str
    customer_id: str
    plan: str
    add_ons: list[str]
    purchased_on: str
    sold_through: str
    trip: Trip
    travelers: list[str]
    status: str


class Payment(BaseModel):
    amount: float
    paid_at: str


class ClaimSummary(BaseModel):
    claim_id: str
    policy_id: str
    customer_id: str
    claim_type: str
    summary: str
    submitted_on: str
    amount_claimed: float
    status: Status
    outcome: Outcome | None
    payout: float | None


class Claim(ClaimSummary):
    incident_date: str
    incident_location: str
    story: str
    items: list[Item]
    documents: list[Document]
    reasons: str | None
    policy_section: str | None
    signed_off_at: str | None
    payment: Payment | None


class Text(BaseModel):
    text: str


class Decision(BaseModel):
    outcome: Outcome
    payout: float
    reasons: str
    policy_section: str


class PaymentRequest(BaseModel):
    amount: float


class StepRequest(BaseModel):
    title: str
    detail: str


class Step(StepRequest):
    at: str


class QueueRun(BaseModel):
    running: bool
    claims_left: int


class Queued(BaseModel):
    queued: int
