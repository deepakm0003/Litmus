"""
Litmus — TrustLine Consortium
=============================

THE IDEA
--------
Scam campaigns do not respect brand boundaries. The same call centre that dials
a TVS Credit customer at 11am dials a Bajaj customer at 11:04 and a Shriram
customer at 11:09, reading the same script from the same number.

Today each lender discovers that number independently, hours apart, and each one
pays the full cost of learning it.

TrustLine already turns every failed verification into a labelled fraud signal.
The consortium shares that signal across members, so the *first* customer at
*any* member lender to check a code protects customers at *every* member lender.

WHY THIS IS A NETWORK GOOD, NOT A FEATURE
-----------------------------------------
Detection value grows superlinearly with membership. One lender sees the slice
of a campaign aimed at its own customers; ten lenders see the campaign. And it
is structurally hard for a KYC vendor to build, because it would require
competing lenders to route fraud intelligence through a commercial third party
that also sells to their competitors. An industry body, or the DoT Digital
Intelligence Platform itself, is the natural host.

WHY IT IS LEGALLY STRAIGHTFORWARD
---------------------------------
This is the part that usually kills data-sharing proposals, and the reason this
one survives: **the shared record contains the attacker, never the customer.**

  shared      caller number, claimed purpose, timestamp, contributing member
  never       customer identity, phone number, loan account, or any PII

The attacker's number is not the lender's customer data. Members contribute
evidence about someone attacking them — closer to sharing a threat-intel
indicator than to sharing a customer record.

Member attribution is pseudonymous by default (a stable hashed member id), so a
member can prove it contributed without publishing its fraud volumes to
competitors, which is the other thing that normally blocks these schemes.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_MEMBER_SALT = os.environ.get(
    "LITMUS_CONSORTIUM_SALT", "litmus-demo-consortium-salt"
).encode()

# A number becomes a consortium-level alert once independent members corroborate.
CORROBORATION_THRESHOLD = 2      # distinct members
CAMPAIGN_WINDOW_SECONDS = 6 * 3600
RETENTION_SECONDS = 30 * 24 * 3600


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

@dataclass
class Member:
    member_id: str
    display_name: str
    joined_at: float = field(default_factory=time.time)
    contributions: int = 0
    alerts_received: int = 0

    @property
    def pseudonym(self) -> str:
        """Stable, non-reversible handle used in shared records."""
        return hmac.new(_MEMBER_SALT, self.member_id.encode(), hashlib.sha256).hexdigest()[:12]


# Demo membership. In production this is an onboarding registry with signed
# member certificates; the shape of the record is the same.
_MEMBERS: Dict[str, Member] = {
    "tvs_credit": Member("tvs_credit", "TVS Credit"),
    "lender_b": Member("lender_b", "Member Lender B"),
    "lender_c": Member("lender_c", "Member Lender C"),
    "lender_d": Member("lender_d", "Member Lender D"),
}


@dataclass
class SharedSignal:
    """One member's report about one attacking number. Contains no customer data."""
    signal_id: str
    caller_number: str
    claimed_purpose: Optional[str]
    severity: str
    member_pseudonym: str
    member_display: str
    reported_at: float

    def to_dict(self, reveal_member: bool = True) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "caller_number": self.caller_number,
            "claimed_purpose": self.claimed_purpose,
            "severity": self.severity,
            "member": self.member_display if reveal_member else self.member_pseudonym,
            "reported_at": datetime.fromtimestamp(
                self.reported_at, tz=timezone.utc
            ).isoformat(timespec="seconds"),
        }


_SIGNALS: List[SharedSignal] = []


# ---------------------------------------------------------------------------
# Contribution
# ---------------------------------------------------------------------------

def contribute(
    member_id: str,
    caller_number: str,
    severity: str,
    claimed_purpose: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Publish one failed-verification signal to the consortium.

    Deliberately takes no customer argument. The function signature is the
    privacy guarantee: a caller cannot leak customer identity through an API
    that never accepts it.
    """
    member = _MEMBERS.get(member_id)
    if not member:
        raise ValueError(f"Unknown consortium member '{member_id}'")

    digits = "".join(c for c in caller_number if c.isdigit())[-10:]
    if not digits:
        raise ValueError("A caller number is required to contribute a signal")

    signal = SharedSignal(
        signal_id=f"cs_{hashlib.sha256(f'{digits}{time.time()}'.encode()).hexdigest()[:10]}",
        caller_number=digits,
        claimed_purpose=claimed_purpose,
        severity=severity,
        member_pseudonym=member.pseudonym,
        member_display=member.display_name,
        reported_at=time.time(),
    )
    _SIGNALS.append(signal)
    member.contributions += 1
    _prune()

    intel = lookup(digits)
    return {
        "contributed": True,
        "signal_id": signal.signal_id,
        "member": member.display_name,
        "network_view": intel,
    }


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def lookup(caller_number: str) -> Dict[str, Any]:
    """
    What the whole network knows about one number.

    The value that no single member can produce on its own is
    `distinct_members` — corroboration across independent institutions. One
    member reporting a number is an incident; three members reporting it inside
    six hours is a campaign running against the industry.
    """
    digits = "".join(c for c in caller_number if c.isdigit())[-10:]
    now = time.time()
    window_start = now - CAMPAIGN_WINDOW_SECONDS

    matches = [s for s in _SIGNALS if s.caller_number == digits]
    recent = [s for s in matches if s.reported_at >= window_start]
    members = {s.member_pseudonym for s in recent}

    corroborated = len(members) >= CORROBORATION_THRESHOLD
    first_seen = min((s.reported_at for s in matches), default=None)

    if corroborated:
        status_ = "network_confirmed"
        recommendation = (
            f"{len(members)} independent member institutions reported this number "
            f"within {CAMPAIGN_WINDOW_SECONDS // 3600}h. Block at the telecom "
            f"partner, warn customers proactively, and file to I4C / DoT FRI."
        )
    elif recent:
        status_ = "single_member"
        recommendation = (
            "Reported by one member only. Monitor for corroboration before "
            "network-wide action."
        )
    else:
        status_ = "unknown"
        recommendation = "No network history for this number."

    return {
        "caller_number": digits,
        "status": status_,
        "corroborated": corroborated,
        "distinct_members": len(members),
        "reports_in_window": len(recent),
        "reports_all_time": len(matches),
        "first_seen": (
            datetime.fromtimestamp(first_seen, tz=timezone.utc).isoformat(timespec="seconds")
            if first_seen else None
        ),
        "window_hours": CAMPAIGN_WINDOW_SECONDS // 3600,
        "recommendation": recommendation,
        "privacy_note": (
            "Consortium records describe the attacking number only. No customer "
            "identity, phone number or account is shared between members."
        ),
    }


# ---------------------------------------------------------------------------
# Network view
# ---------------------------------------------------------------------------

def network_stats() -> Dict[str, Any]:
    """Dashboard summary — the argument for joining, in numbers."""
    now = time.time()
    window_start = now - CAMPAIGN_WINDOW_SECONDS

    by_number: Dict[str, set] = defaultdict(set)
    for s in _SIGNALS:
        if s.reported_at >= window_start:
            by_number[s.caller_number].add(s.member_pseudonym)

    confirmed = {n: m for n, m in by_number.items() if len(m) >= CORROBORATION_THRESHOLD}

    campaigns = sorted(
        (
            {
                "caller_number": number,
                "distinct_members": len(members),
                "reports": sum(
                    1 for s in _SIGNALS
                    if s.caller_number == number and s.reported_at >= window_start
                ),
            }
            for number, members in confirmed.items()
        ),
        key=lambda c: -c["distinct_members"],
    )

    # The headline: how much of the network's knowledge a single member would
    # have missed on its own.
    solo_visible = sum(1 for members in by_number.values() if len(members) == 1)
    total_numbers = len(by_number)
    amplification = round(total_numbers / solo_visible, 2) if solo_visible else None

    return {
        "members": [
            {
                "name": m.display_name,
                "pseudonym": m.pseudonym,
                "contributions": m.contributions,
                "joined": datetime.fromtimestamp(
                    m.joined_at, tz=timezone.utc
                ).isoformat(timespec="seconds"),
            }
            for m in _MEMBERS.values()
        ],
        "member_count": len(_MEMBERS),
        "total_signals": len(_SIGNALS),
        "numbers_tracked": total_numbers,
        "network_confirmed_campaigns": len(confirmed),
        "campaigns": campaigns[:20],
        "coverage_multiple": amplification,
        "coverage_note": (
            "Numbers visible to the whole network divided by numbers a single "
            "member would have seen alone. Above 1.0 is intelligence a member "
            "gets only by participating."
        ),
        "corroboration_threshold": CORROBORATION_THRESHOLD,
        "window_hours": CAMPAIGN_WINDOW_SECONDS // 3600,
    }


def members() -> List[Dict[str, Any]]:
    return [
        {"member_id": m.member_id, "name": m.display_name, "pseudonym": m.pseudonym}
        for m in _MEMBERS.values()
    ]


def _prune() -> None:
    cutoff = time.time() - RETENTION_SECONDS
    global _SIGNALS
    _SIGNALS = [s for s in _SIGNALS if s.reported_at >= cutoff]


def reset_state() -> None:
    _SIGNALS.clear()
    for m in _MEMBERS.values():
        m.contributions = 0
        m.alerts_received = 0
