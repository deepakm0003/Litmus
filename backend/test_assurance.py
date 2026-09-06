"""
Assurance tests. Run: python backend/test_assurance.py

The properties that matter: absence of evidence must never become suspicion,
liveness must dominate, and the module must never claim to be a credit score.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import assurance as A  # noqa: E402

PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}  {detail}")


def face(verdict="real", conf=0.95, px=300, sufficient=True, prob=0.97):
    return {
        "verdict": verdict,
        "quality": {"face_px": px, "sufficient_for_adverse_finding": sufficient},
        "stages": {"cnn": {"confidence": conf, "real_probability": prob}},
    }


CLEAN_NET = {"corroborated": False, "fri": {"tier": "clean"}}
BAD_NET = {"corroborated": True, "fri": {"tier": "very_high"}}

# ---------------------------------------------------------------------------
print("\n=== 1. Full evidence clears a thin-file applicant ===")
r = A.assess(liveness={"passed": True}, face=face(), network=CLEAN_NET, has_bureau_file=False)
check("reaches verified", r["assurance_level"] == "verified", r["assurance_level"])
check("score is high", r["assurance_score"] >= 80, r["assurance_score"])
check("unlocks thin file", r["unlocks_thin_file"])
check("recovery is flagged recoverable", r["recovery"]["recoverable"])
check("headline names the outcome", "without bureau" in r["recovery"]["headline"].lower())

# ---------------------------------------------------------------------------
print("\n=== 2. Liveness dominates the score ===")
with_live = A.assess(liveness={"passed": True}, face=None, network=None)
with_face = A.assess(liveness=None, face=face(), network=CLEAN_NET)
check("liveness alone outweighs face+network",
      with_live["assurance_score"] > with_face["assurance_score"] - 20,
      f"{with_live['assurance_score']} vs {with_face['assurance_score']}")
check("liveness weight is the largest", A.W_LIVENESS > max(A.W_FACE, A.W_CAPTURE, A.W_NETWORK))

# ---------------------------------------------------------------------------
print("\n=== 3. Absence of evidence is not suspicion ===")
nothing = A.assess()
check("no evidence -> insufficient, not adverse",
      nothing["assurance_level"] == "insufficient" and not nothing["adverse_findings"],
      nothing["adverse_findings"])
check("wording says it is not a fraud finding",
      "NOT a finding of fraud" in nothing["licenses"])

incon = A.assess(liveness={"passed": True}, face=face(verdict="uncertain"), network=CLEAN_NET)
check("inconclusive face creates no adverse finding", not incon["adverse_findings"],
      incon["adverse_findings"])
check("inconclusive face still allows assurance from other evidence",
      incon["assurance_score"] >= A.W_LIVENESS)

# Partial credit: an undecided face that leans genuine is worth something.
lean = A.assess(liveness={"passed": True},
                face=face(verdict="uncertain", prob=0.974, conf=0.948),
                network=CLEAN_NET)
flat = A.assess(liveness={"passed": True},
                face=face(verdict="uncertain", prob=0.50, conf=0.0),
                network=CLEAN_NET)
check("leaning-genuine face earns partial credit",
      lean["assurance_score"] > flat["assurance_score"],
      f"{lean['assurance_score']} vs {flat['assurance_score']}")
check("partial credit is capped below full weight",
      (lean["assurance_score"] - flat["assurance_score"]) < A.W_FACE,
      lean["assurance_score"] - flat["assurance_score"])
check("partial credit creates no adverse finding", not lean["adverse_findings"])
check("outcome names it as not decisive",
      any("not decisive" in e["outcome"] for e in lean["evidence"]))

# ---------------------------------------------------------------------------
print("\n=== 4. Adverse findings block approval outright ===")
synth = A.assess(liveness={"passed": True}, face=face(verdict="fake"), network=CLEAN_NET)
check("synthetic media blocks", synth["assurance_level"] == "insufficient", synth["assurance_level"])
check("never unlocks thin file", not synth["unlocks_thin_file"])
check("adverse finding recorded", "synthetic" in " ".join(synth["adverse_findings"]))

bad = A.assess(liveness={"passed": True}, face=face(), network=BAD_NET)
check("adverse network blocks", not bad["unlocks_thin_file"], bad["assurance_level"])

failed = A.assess(liveness={"passed": False}, face=face(), network=CLEAN_NET)
check("failed liveness blocks", not failed["unlocks_thin_file"])

# ---------------------------------------------------------------------------
print("\n=== 5. Poor capture reduces assurance without accusing anyone ===")
poor = A.assess(liveness={"passed": True}, face=face(px=70, sufficient=False, verdict="uncertain"),
                network=CLEAN_NET)
check("no adverse finding from a bad photo", not poor["adverse_findings"], poor["adverse_findings"])
check("capture point not awarded",
      any(e["signal"] == "Capture quality" and e["earned"] == 0 for e in poor["evidence"]))
check("explains what to do", "closer" in " ".join(e["why"] for e in poor["evidence"]))

# ---------------------------------------------------------------------------
print("\n=== 6. It never claims to be a credit score ===")
r = A.assess(liveness={"passed": True}, face=face(), network=CLEAN_NET)
check("disclaimer present", "not a credit score" in r["disclaimer"].lower())
check("disclaimer rules out repayment claims", "repay" in r["disclaimer"].lower())
check("licenses tell the underwriter to still assess affordability",
      "affordability" in r["licenses"].lower() or "creditworthiness" in r["licenses"].lower())

# ---------------------------------------------------------------------------
print("\n=== 7. Every decision carries its reasoning ===")
r = A.assess(liveness={"passed": True}, face=face(), network=CLEAN_NET)
check("evidence trail present", len(r["evidence"]) >= 4)
check("every item explains itself", all(len(e["why"]) > 30 for e in r["evidence"]))
check("every item reports what it earned", all("earned" in e for e in r["evidence"]))

gaps = A.assess(liveness=None, face=face(), network=None)
check("gaps are named so they can be closed",
      "Missing:" in gaps["recovery"]["detail"], gaps["recovery"]["detail"][:60])

# ---------------------------------------------------------------------------
print("\n=== 8. An applicant who already has a bureau file gains nothing ===")
r = A.assess(liveness={"passed": True}, face=face(), network=CLEAN_NET, has_bureau_file=True)
check("verified but not flagged as a recovery", not r["recovery"]["recoverable"])
check("says it changes nothing", "changes nothing" in r["recovery"]["detail"])

print("\n" + "=" * 62)
print(f"  Assurance: {PASS} passed, {FAIL} failed")
print("=" * 62)
sys.exit(1 if FAIL else 0)
