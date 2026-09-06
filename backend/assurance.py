"""
Litmus Assurance — turning verification evidence into an approval signal
=======================================================================

WHAT THIS IS, AND WHAT IT IS EMPHATICALLY NOT
---------------------------------------------
This is NOT a credit score. It makes no claim about whether an applicant will
repay, and it must never be used as one. Confusing identity assurance with
creditworthiness is how a lender ends up approving a confidently-verified
person who cannot afford the loan.

What it produces is an ASSURANCE LEVEL: how strongly the evidence supports the
claim that this applicant is a real, unique, physically-present human. The
underwriter still decides the credit question.

WHY THAT IS COMMERCIALLY USEFUL
-------------------------------
Between 70% and 85% of first-time borrowers in India are declined at the bureau
check. Some of those are genuinely uncreditworthy. But a meaningful share are
declined because a thin file leaves the lender unable to establish who the
person is at all — the identity question, not the repayment question.

Every fraud control in this market answers that question only in the negative:
it produces a rejection. The same evidence, read the other way, is exactly what
an underwriter needs to extend credit to someone with no bureau history.

So this module reads the evidence in the positive direction.

THE EVIDENCE IT READS
---------------------
  liveness      Did the applicant pass LiveChallenge? This is the strongest
                single signal available, because it is a verifiable fact rather
                than a model's opinion — a pre-generated stream cannot answer a
                challenge minted after it was made.
  face          FaceGuard's calibrated verdict on the capture.
  capture       Was the capture good enough to support any conclusion at all?
  network       Does the applicant's contact number appear in consortium fraud
                history or DoT's Financial Fraud Risk Indicator?

DESIGN RULES
------------
  1. Liveness dominates. A passed physical challenge outweighs any classifier
     score, because we measured that classifiers are the unreliable part.
  2. Absence of evidence is never treated as evidence. A missing signal lowers
     assurance; it does not create suspicion.
  3. Every level states what it does and does not license, in words an
     underwriter can act on and an auditor can follow.
  4. The output always carries its reasoning. An applicant declined on identity
     grounds is entitled to know which specific evidence was missing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Weights are ordered by measured reliability, not by intuition. LiveChallenge
# is a verifiable fact (blind-guess probability 0.44%); FaceGuard is a model at
# 0.934 AUC; the network check is a lookup against third-party data.
W_LIVENESS = 45
W_FACE = 25
W_CAPTURE = 15
W_NETWORK = 15

# How much of the face weight an undecided-but-leaning-genuine reading can
# earn. Deliberately below 1.0: partial evidence is worth less than a
# decisive result, but far more than nothing.
PARTIAL_CAP = 0.6

LEVELS = {
    "verified": {
        "min_score": 80,
        "label": "Identity Verified",
        "licenses": (
            "Identity assurance is sufficient to underwrite this applicant without "
            "relying on bureau history. Assess creditworthiness on income and "
            "affordability as normal."
        ),
        "unlocks_thin_file": True,
    },
    "provisional": {
        "min_score": 55,
        "label": "Provisionally Verified",
        "licenses": (
            "Identity is probable but not established. Proceed under standard "
            "requirements, including bureau history. Do not use this as a substitute "
            "for a thin file."
        ),
        "unlocks_thin_file": False,
    },
    "insufficient": {
        "min_score": 0,
        "label": "Identity Not Established",
        "licenses": (
            "The evidence does not establish who this applicant is. This is NOT a "
            "finding of fraud — it usually means a poor capture. Request a better "
            "capture or route to a branch officer."
        ),
        "unlocks_thin_file": False,
    },
}


def _level_for(score: float) -> str:
    for name in ("verified", "provisional", "insufficient"):
        if score >= LEVELS[name]["min_score"]:
            return name
    return "insufficient"


def assess(
    liveness: Optional[Dict[str, Any]] = None,
    face: Optional[Dict[str, Any]] = None,
    network: Optional[Dict[str, Any]] = None,
    has_bureau_file: bool = False,
) -> Dict[str, Any]:
    """
    Read verification evidence in the positive direction.

    Every argument is optional. Missing evidence reduces assurance without
    implying anything adverse, which is the difference between "we could not
    confirm" and "we found something wrong".
    """
    earned = 0.0
    evidence: List[Dict[str, Any]] = []
    adverse: List[str] = []

    # --- liveness: the strongest signal, because it is not a model opinion ---
    if liveness and liveness.get("passed"):
        earned += W_LIVENESS
        evidence.append({
            "signal": "Liveness challenge",
            "outcome": "passed",
            "weight": W_LIVENESS,
            "earned": W_LIVENESS,
            "why": (
                "The applicant answered a physical challenge generated after the "
                "session opened. A pre-recorded or pre-generated stream cannot "
                "contain that answer, so presence is established rather than "
                "estimated."
            ),
        })
    elif liveness and liveness.get("passed") is False:
        evidence.append({
            "signal": "Liveness challenge",
            "outcome": "failed",
            "weight": W_LIVENESS,
            "earned": 0,
            "why": "The response did not match the challenge that was issued.",
        })
        adverse.append("liveness challenge failed")
    else:
        evidence.append({
            "signal": "Liveness challenge",
            "outcome": "not attempted",
            "weight": W_LIVENESS,
            "earned": 0,
            "why": (
                "No challenge was run. This is the single largest source of "
                "assurance available and costs the applicant about twenty seconds."
            ),
        })

    # --- face: a model, weighted accordingly --------------------------------
    if face:
        verdict = face.get("verdict")
        cnn = (face.get("stages", {}) or {}).get("cnn") or {}
        conf = float(cnn.get("confidence", 0.0) or 0.0)

        if verdict == "real":
            got = W_FACE * min(1.0, max(0.0, conf))
            earned += got
            evidence.append({
                "signal": "Face analysis",
                "outcome": "consistent with a genuine capture",
                "weight": W_FACE,
                "earned": round(got, 1),
                "why": (
                    f"Fine-tuned detector reports {cnn.get('real_probability', 0) * 100:.1f}% "
                    f"real at {conf * 100:.0f}% confidence. Held-out AUC 0.934 — a strong "
                    f"signal, but a model, so it is weighted below the liveness proof."
                ),
            })
        elif verdict == "fake":
            evidence.append({
                "signal": "Face analysis",
                "outcome": "synthetic media indicated",
                "weight": W_FACE,
                "earned": 0,
                "why": "The detector positively identified synthesis with confidence.",
            })
            adverse.append("synthetic media indicated in the capture")
        else:
            # Uncertain, but the model still produced a number. If it leans REAL,
            # that is partial evidence and earns partial credit — discarding it
            # entirely was throwing away a 97%-confident reading because it fell
            # a fraction under the decide threshold.
            p_real = float(cnn.get("real_probability", 0.5) or 0.5)
            if p_real > 0.5:
                got = W_FACE * PARTIAL_CAP * min(1.0, (p_real - 0.5) / 0.5)
                earned += got
                evidence.append({
                    "signal": "Face analysis",
                    "outcome": f"leans genuine ({p_real * 100:.1f}%), not decisive",
                    "weight": W_FACE,
                    "earned": round(got, 1),
                    "why": (
                        f"The detector reads {p_real * 100:.1f}% real but below its "
                        f"decide threshold, so this counts as partial evidence — "
                        f"capped at {int(PARTIAL_CAP * 100)}% of the full weight. "
                        f"Graded evidence earns graded credit rather than nothing."
                    ),
                })
            else:
                evidence.append({
                    "signal": "Face analysis",
                    "outcome": "inconclusive",
                    "weight": W_FACE,
                    "earned": 0,
                    "why": (
                        "The detector could not decide and does not lean genuine. "
                        "Treated as absent evidence, not as suspicion — our model "
                        "over-flags under-represented faces and poor captures, so an "
                        "inconclusive result says more about the photograph than the "
                        "person."
                    ),
                })

        # --- capture quality: gates how much anything else is worth ---------
        q = face.get("quality") or {}
        px = int(q.get("face_px", 0) or 0)
        if q.get("sufficient_for_adverse_finding"):
            earned += W_CAPTURE
            evidence.append({
                "signal": "Capture quality",
                "outcome": f"sufficient ({px}px face)",
                "weight": W_CAPTURE,
                "earned": W_CAPTURE,
                "why": "Above the resolution floor, so the analysis above is meaningful.",
            })
        else:
            evidence.append({
                "signal": "Capture quality",
                "outcome": f"below floor ({px}px face)" if px else "no face located",
                "weight": W_CAPTURE,
                "earned": 0,
                "why": (
                    "Detector scores fall with resolution on genuine faces too, so a "
                    "small or recompressed capture cannot support a conclusion either "
                    "way. Ask for a closer photograph."
                ),
            })

    # --- network: third-party adverse history -------------------------------
    if network is not None:
        corroborated = bool(network.get("corroborated"))
        fri_tier = (network.get("fri") or {}).get("tier", "clean")
        if not corroborated and fri_tier in ("clean", "medium"):
            earned += W_NETWORK
            evidence.append({
                "signal": "Network history",
                "outcome": "no adverse history",
                "weight": W_NETWORK,
                "earned": W_NETWORK,
                "why": (
                    "No consortium fraud reports and no elevated DoT Financial Fraud "
                    "Risk Indicator tier against the contact number."
                ),
            })
        else:
            evidence.append({
                "signal": "Network history",
                "outcome": "adverse history present",
                "weight": W_NETWORK,
                "earned": 0,
                "why": (
                    f"Consortium corroboration: {corroborated}. DoT FRI tier: {fri_tier}."
                ),
            })
            adverse.append("adverse network history against the contact number")
    else:
        evidence.append({
            "signal": "Network history",
            "outcome": "not checked",
            "weight": W_NETWORK,
            "earned": 0,
            "why": "No contact number was supplied for the network lookup.",
        })

    score = round(min(100.0, earned), 1)
    level = "insufficient" if adverse else _level_for(score)
    meta = LEVELS[level]

    # --- the commercial statement -------------------------------------------
    if meta["unlocks_thin_file"] and not has_bureau_file:
        recovery = {
            "recoverable": True,
            "headline": "Approvable without bureau history",
            "detail": (
                "This applicant has no bureau file and would normally be declined at "
                "the bureau check. Identity is established well enough to underwrite "
                "on income and affordability instead. This is the population where "
                "70-85% of first-time borrowers are currently rejected."
            ),
        }
    elif meta["unlocks_thin_file"]:
        recovery = {
            "recoverable": False,
            "headline": "Identity established; standard underwriting applies",
            "detail": "A bureau file already exists, so this changes nothing about the decision.",
        }
    else:
        missing = [e["signal"] for e in evidence if e["earned"] == 0 and e["outcome"] in
                   ("not attempted", "inconclusive", "not checked")]
        recovery = {
            "recoverable": False,
            "headline": "Not yet approvable on identity alone",
            "detail": (
                "Missing: " + ", ".join(missing) + ". Collecting these would raise "
                "assurance without asking the applicant for more documents."
                if missing else
                "Adverse findings present; this is a review case, not an approval case."
            ),
        }

    return {
        "assurance_score": score,
        "assurance_level": level,
        "label": meta["label"],
        "licenses": meta["licenses"],
        "unlocks_thin_file": meta["unlocks_thin_file"] and not adverse,
        "adverse_findings": adverse,
        "evidence": evidence,
        "recovery": recovery,
        "weights": {
            "liveness": W_LIVENESS,
            "face": W_FACE,
            "capture": W_CAPTURE,
            "network": W_NETWORK,
        },
        "disclaimer": (
            "This is an IDENTITY ASSURANCE score, not a credit score. It says how "
            "strongly the evidence supports that this is a real, unique, present "
            "human. It makes no claim about ability or willingness to repay, and "
            "must never be used as a substitute for affordability assessment."
        ),
    }
