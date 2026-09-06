"""
Litmus — DoT Financial Fraud Risk Indicator (FRI) client
========================================================

WHAT THIS IS
------------
The Department of Telecommunications' Digital Intelligence Unit launched the
Financial Fraud Risk Indicator in May 2025. It classifies mobile numbers by how
strongly they are associated with financial fraud, drawing on the Digital
Intelligence Platform: citizen reports through Sanchar Saathi, bank reporting,
and telecom-side signals.

On 30 June 2025 the RBI issued an advisory directing banks to integrate FRI
into their systems. Within six months of rollout it was credited with
preventing roughly Rs 660 crore of fraud losses. PhonePe, HDFC, ICICI, PNB and
Paytm already query it.

WHY LITMUS USES IT
------------------
TrustLine already detects that *something* is wrong: a customer checks a code
and it fails, so somebody is impersonating the lender right now. What TrustLine
cannot tell on its own is whether that caller is a one-off or a number the rest
of the country has already reported.

FRI closes that loop. A failed verification from a number DoT has already
flagged Very High is not an incident to log — it is a known-bad actor mid-attack,
and it justifies immediate escalation rather than queued review.

The reverse direction matters too. Litmus contributes its own failed-verification
evidence back, which is exactly the "continuous feedback to refine the fraud risk
models" the DIP integration guidance asks for.

CREDENTIALS
-----------
Live FRI access requires an onboarded DIP account and a mutually-authenticated
channel — it is not a public API. So this client has two modes:

  configured    LITMUS_FRI_BASE_URL + LITMUS_FRI_API_KEY are set, and it makes
                a real signed request.
  unconfigured  no credentials, so it runs a clearly-labelled local heuristic
                and marks every response `simulated: True`.

Nothing downstream is allowed to forget which mode produced a verdict — the
flag travels with the result and surfaces in the console. A demo that silently
passes off simulated government data as real is the exact dishonesty this
project exists to argue against.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:  # requests is optional — the simulated path needs no HTTP at all
    import requests
except ImportError:  # pragma: no cover
    requests = None


FRI_BASE_URL = os.environ.get("LITMUS_FRI_BASE_URL", "").rstrip("/")
FRI_API_KEY = os.environ.get("LITMUS_FRI_API_KEY", "")
FRI_TIMEOUT_SECONDS = float(os.environ.get("LITMUS_FRI_TIMEOUT", "2.5"))

CACHE_TTL_SECONDS = 900          # 15 min — FRI tiers move slowly
REQUEST_BUDGET_MS = 2500         # never let a lookup stall a live call


# ---------------------------------------------------------------------------
# Risk model
# ---------------------------------------------------------------------------
#
# DoT publishes three tiers. Litmus adds "clean" for a number that returns no
# association at all, so the absence of a signal is never confused with a
# low-risk signal.

RISK_TIERS = {
    "very_high": {
        "label": "Very High",
        "rank": 3,
        "meaning": "Number is strongly associated with reported financial fraud.",
        "action": "block_and_escalate",
        "guidance": (
            "Treat as a confirmed hostile caller. Escalate to the fraud desk "
            "immediately and push a proactive warning to customers this number "
            "has dialled."
        ),
    },
    "high": {
        "label": "High",
        "rank": 2,
        "meaning": "Multiple independent fraud reports associated with this number.",
        "action": "escalate",
        "guidance": "Escalate to the fraud desk ahead of the standard review queue.",
    },
    "medium": {
        "label": "Medium",
        "rank": 1,
        "meaning": "Some fraud association reported; not yet corroborated.",
        "action": "review_priority",
        "guidance": "Raise review priority and watch for a second report.",
    },
    "clean": {
        "label": "No association",
        "rank": 0,
        "meaning": "No fraud association currently recorded against this number.",
        "action": "proceed",
        "guidance": (
            "No external signal. This does NOT mean the caller is genuine — a "
            "fresh SIM has no history yet, which is precisely why attackers "
            "rotate numbers."
        ),
    },
}


@dataclass
class FRIResult:
    number: str
    tier: str
    simulated: bool
    checked_at: float = field(default_factory=time.time)
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    @property
    def rank(self) -> int:
        return RISK_TIERS[self.tier]["rank"]

    def to_dict(self) -> Dict[str, Any]:
        meta = RISK_TIERS[self.tier]
        return {
            "number": _mask(self.number),
            "tier": self.tier,
            "label": meta["label"],
            "rank": meta["rank"],
            "meaning": meta["meaning"],
            "action": meta["action"],
            "guidance": meta["guidance"],
            "source": "DoT Financial Fraud Risk Indicator (Digital Intelligence Platform)",
            "simulated": self.simulated,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "disclosure": (
                "SIMULATED — no DIP credentials configured. Heuristic result for "
                "demonstration only; not a government risk classification."
                if self.simulated
                else "Live DIP lookup."
            ),
        }


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_CACHE: Dict[str, FRIResult] = {}


def _mask(number: str) -> str:
    digits = "".join(c for c in number if c.isdigit())
    if len(digits) < 4:
        return "****"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def _normalise(number: str) -> str:
    """Strip to national significant digits so +91-98400 12345 == 9840012345."""
    digits = "".join(c for c in number if c.isdigit())
    if len(digits) > 10 and digits.startswith("91"):
        digits = digits[2:]
    return digits[-10:] if len(digits) >= 10 else digits


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def is_configured() -> bool:
    return bool(FRI_BASE_URL and FRI_API_KEY and requests is not None)


def check_number(number: str, use_cache: bool = True) -> FRIResult:
    """
    Look up one number's fraud-risk tier.

    Never raises. A verification call is in flight while this runs, so an FRI
    outage must degrade to "no signal" rather than break the customer's check —
    the challenge-response result stands on its own regardless.
    """
    key = _normalise(number)
    if not key:
        return FRIResult(number=number, tier="clean", simulated=True,
                         error="unparseable number")

    if use_cache:
        hit = _CACHE.get(key)
        if hit and (time.time() - hit.checked_at) < CACHE_TTL_SECONDS:
            return hit

    result = _live_lookup(key) if is_configured() else _simulated_lookup(key)
    _CACHE[key] = result
    return result


def _live_lookup(key: str) -> FRIResult:
    started = time.time()
    try:
        response = requests.post(
            f"{FRI_BASE_URL}/v1/fri/check",
            json={"msisdn": key},
            headers={
                "Authorization": f"Bearer {FRI_API_KEY}",
                "Content-Type": "application/json",
                "X-Litmus-Purpose": "outbound-call-verification",
            },
            timeout=FRI_TIMEOUT_SECONDS,
        )
        latency = (time.time() - started) * 1000
        response.raise_for_status()
        payload = response.json()

        # DIP returns its own tier vocabulary; map defensively so an unexpected
        # value degrades to "clean" rather than crashing a live verification.
        tier = str(payload.get("risk_indicator", "")).strip().lower().replace(" ", "_")
        if tier not in RISK_TIERS:
            tier = "clean"

        return FRIResult(number=key, tier=tier, simulated=False, latency_ms=round(latency, 1))

    except Exception as exc:  # noqa: BLE001 — deliberately total
        latency = (time.time() - started) * 1000
        return FRIResult(
            number=key,
            tier="clean",
            simulated=False,
            latency_ms=round(latency, 1),
            error=f"FRI lookup failed, treated as no-signal: {type(exc).__name__}",
        )


def _simulated_lookup(key: str) -> FRIResult:
    # Seeded demonstration numbers resolve to a fixed tier so the fraud path can
    # be shown without first manufacturing the fraud on stage.
    try:
        import demo_data
        seeded = demo_data.tier_for(key)
        if seeded:
            return FRIResult(number=key, tier=seeded, simulated=True, latency_ms=0.2)
    except Exception:
        pass

    """
    Deterministic stand-in used only when no DIP credentials are present.

    Deterministic rather than random on purpose: the same number must produce
    the same tier every time, so a live demo is reproducible and a judge can
    re-enter a number and see it behave consistently.
    """
    digest = hashlib.sha256(f"litmus-fri-sim:{key}".encode()).digest()
    bucket = digest[0] % 100

    if bucket < 6:
        tier = "very_high"
    elif bucket < 16:
        tier = "high"
    elif bucket < 32:
        tier = "medium"
    else:
        tier = "clean"

    return FRIResult(number=key, tier=tier, simulated=True, latency_ms=0.2)


# ---------------------------------------------------------------------------
# Contribution back to the platform
# ---------------------------------------------------------------------------

def report_fraud_signal(
    number: str,
    reason: str,
    severity: str,
    customer_count: int = 1,
) -> Dict[str, Any]:
    """
    Push a failed-verification signal back toward DIP.

    Note what is and is not sent: the *caller's* number, why the verification
    failed, and how many distinct customers it targeted. Never a customer
    identity. The attacker's number is not the lender's customer data, which is
    what makes this contribution clean to make.
    """
    payload = {
        "msisdn": _normalise(number),
        "reason": reason,
        "severity": severity,
        "distinct_targets": customer_count,
        "reported_by": "litmus",
        "reported_at": time.time(),
    }

    if not is_configured():
        return {
            "submitted": False,
            "simulated": True,
            "payload": {**payload, "msisdn": _mask(number)},
            "note": (
                "No DIP credentials configured — the report was composed but not "
                "transmitted. Wire LITMUS_FRI_BASE_URL and LITMUS_FRI_API_KEY to "
                "enable live contribution."
            ),
        }

    try:
        response = requests.post(
            f"{FRI_BASE_URL}/v1/fri/report",
            json=payload,
            headers={"Authorization": f"Bearer {FRI_API_KEY}"},
            timeout=FRI_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return {"submitted": True, "simulated": False,
                "reference": response.json().get("reference")}
    except Exception as exc:  # noqa: BLE001
        return {"submitted": False, "simulated": False,
                "error": f"{type(exc).__name__}: {exc}"}


def status() -> Dict[str, Any]:
    """Surfaced in the console so the operator always knows which mode is live."""
    return {
        "configured": is_configured(),
        "mode": "live" if is_configured() else "simulated",
        "base_url": FRI_BASE_URL or None,
        "cache_entries": len(_CACHE),
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "tiers": {k: v["label"] for k, v in RISK_TIERS.items()},
        "note": (
            "Live FRI access requires an onboarded DoT Digital Intelligence "
            "Platform account. Without credentials Litmus runs a deterministic "
            "local heuristic and flags every result as simulated."
        ),
    }


def reset_cache() -> None:
    _CACHE.clear()
