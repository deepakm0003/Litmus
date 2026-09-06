"""
Litmus — seeded demonstration numbers
=====================================

A demo needs numbers whose history is known in advance, otherwise showing the
fraud path means first manufacturing the fraud on stage. These are seeded at
startup so the adverse cases are there the moment the console opens.

They are deliberately patterned — five repeated digits then five of another —
so they are easy to read aloud, easy to type, and impossible to mistake for a
real subscriber. Nobody's actual number looks like 9999900000.

EVERY VALUE HERE IS FABRICATED. It is labelled as such in the API responses,
and the seeded reports carry `seeded: True` so no demonstration record can be
mistaken for a genuine fraud report about a real person.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Tier is what the DoT Financial Fraud Risk Indicator would return; members are
# the consortium institutions that have independently reported the number.
DEMO_NUMBERS: List[Dict[str, Any]] = [
    {
        "number": "9999900000",
        "tier": "very_high",
        "members": ["tvs_credit", "lender_b", "lender_c"],
        "purpose": "digital_arrest",
        "story": "Worst case. Reported by three institutions and flagged Very High by DoT.",
        "expect": "Assurance blocked outright. Fraud desk shows a confirmed campaign.",
    },
    {
        "number": "8888811111",
        "tier": "high",
        "members": ["tvs_credit", "lender_b"],
        "purpose": "otp_request",
        "story": "Corroborated across two lenders, asking customers for OTPs.",
        "expect": "Network corroborated; assurance blocked.",
    },
    {
        "number": "7777722222",
        "tier": "medium",
        "members": ["lender_c"],
        "purpose": "loan_processing_fee",
        "story": "One lender has reported it. Not yet corroborated.",
        "expect": "Single-member report. Watch, do not yet act network-wide.",
    },
    {
        "number": "6666633333",
        "tier": "clean",
        "members": [],
        "purpose": None,
        "story": "No history anywhere. The control case.",
        "expect": "Network check earns full credit; assurance can proceed.",
    },
    {
        "number": "5555544444",
        "tier": "clean",
        "members": ["tvs_credit", "lender_d"],
        "purpose": "remote_access",
        "story": (
            "The interesting one. DoT has nothing on it — a fresh SIM — but two "
            "lenders have already been hit. Consortium sees what the national "
            "database has not caught up to yet."
        ),
        "expect": "Clean FRI tier, but network corroborated. This is why sharing matters.",
    },
]

BY_NUMBER = {d["number"]: d for d in DEMO_NUMBERS}


def tier_for(number: str) -> str | None:
    """FRI tier for a seeded number, or None if it is not one of ours."""
    digits = "".join(c for c in str(number) if c.isdigit())[-10:]
    entry = BY_NUMBER.get(digits)
    return entry["tier"] if entry else None


def seed(consortium_module) -> Dict[str, Any]:
    """
    Populate the consortium with the seeded history.

    Idempotent: calling it twice does not double the reports, because a demo
    that inflates its own numbers on every reload is worse than no demo.
    """
    seeded = 0
    for entry in DEMO_NUMBERS:
        existing = consortium_module.lookup(entry["number"])
        if existing["reports_all_time"] >= len(entry["members"]):
            continue
        for member in entry["members"]:
            try:
                consortium_module.contribute(
                    member_id=member,
                    caller_number=entry["number"],
                    severity="critical" if entry["tier"] == "very_high" else "high",
                    claimed_purpose=entry["purpose"],
                )
                seeded += 1
            except ValueError:
                pass
    return {"seeded_signals": seeded, "numbers": len(DEMO_NUMBERS)}


def catalogue() -> Dict[str, Any]:
    """What the console shows the operator, so the demo needs no cheat sheet."""
    return {
        "note": (
            "Fabricated numbers seeded for demonstration. Patterned so they cannot "
            "be confused with a real subscriber. No real person is described here."
        ),
        "numbers": [
            {
                "number": d["number"],
                "display": f"{d['number'][:5]} {d['number'][5:]}",
                "fri_tier": d["tier"],
                "reported_by": len(d["members"]),
                "story": d["story"],
                "expect": d["expect"],
            }
            for d in DEMO_NUMBERS
        ],
    }
