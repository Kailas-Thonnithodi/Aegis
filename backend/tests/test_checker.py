import json

import pytest

from backend import checker
from backend.db import DATA


def handler(decision="approve", payout=420.0):
    return checker.HandlerDecision.model_validate(
        {
            "claim_id": "CLM-1001",
            "set": "queue",
            "decision": decision,
            "payout": payout,
            "reason": "The reason.",
            "reference": "Policy wording, section 3",
            "calculation": [],
            "tests": "A routine trip delay",
            "difficulty": "routine",
            "needs": [],
        }
    )


@pytest.mark.parametrize(
    ("outcome", "payout", "expected"),
    [
        ("approve", 420.0, ("match", True, True)),
        ("approve", 420.004, ("match", True, True)),
        ("approve", 400.0, ("payout_miss", True, False)),
        ("refer", 0.0, ("outcome_miss", False, False)),
        (None, None, ("not_finished", False, False)),
    ],
)
def test_score(outcome, payout, expected):
    assert checker.score(outcome, payout, handler()) == expected


def test_a_different_outcome_with_the_same_payout_still_misses():
    assert checker.score("decline", 0.0, handler("refer", 0.0)) == (
        "outcome_miss",
        False,
        True,
    )


def scored(claim_set, difficulty, claim_type, score):
    return checker.Scored.model_validate(
        {
            "set": claim_set,
            "claim_type": claim_type,
            "difficulty": difficulty,
            "score": score,
            "outcome_match": score in {"match", "payout_miss"},
            "payout_match": score == "match",
        }
    )


def test_summarize_totals_overall_without_manual_and_by_group():
    results = [
        scored("queue", "routine", "baggage", "match"),
        scored("queue", "manual", "baggage", "outcome_miss"),
        scored("held_out", "hard", "trip_delay", "payout_miss"),
        scored("held_out", "routine", "trip_delay", "not_finished"),
    ]

    summary = checker.summarize(results)

    assert summary.overall == checker.Tally(
        claims=4, matches=1, outcome_matches=2, payout_matches=1
    )
    assert summary.without_manual.claims == 3
    assert summary.without_manual.matches == 1
    assert summary.by_set["queue"].matches == 1
    assert summary.by_set["held_out"].outcome_matches == 1
    assert list(summary.by_difficulty) == ["hard", "manual", "routine"]
    assert summary.by_claim_type["trip_delay"].claims == 2


def test_summarize_of_no_results_is_all_zero():
    summary = checker.summarize([])

    assert summary.overall.claims == 0
    assert summary.by_set == {}


def test_answer_key_covers_both_sets():
    key = checker.answer_key()
    queue_ids = {c["claim_id"] for c in json.loads((DATA / "claims.json").read_text())}
    held_out_ids = {c["claim_id"] for c in checker.held_out_claims()}

    assert {k for k, d in key.items() if d.set == "queue"} == queue_ids
    assert {k for k, d in key.items() if d.set == "held_out"} == held_out_ids
    assert len(queue_ids) == len(held_out_ids) == 25
