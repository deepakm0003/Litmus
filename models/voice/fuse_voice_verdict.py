"""
Litmus VoicePrint — Ensemble Fusion with Confidence-Aware Routing

Adapts the face ensemble pattern to the voice domain.

Key difference from face fusion:
  Face: both models are discriminative — symmetric agree/disagree logic works.
  Voice: M1 (MelodyMachine) is reliable on real (90%) but never fires on fakes.
         M2 (motheecreator) is noisier on real (80%) but catches ~35% of fakes.
         → Asymmetric rule: ANY spoof signal from either model → route to review.
           Only auto-approve when BOTH say real with high confidence.

This is not a limitation — it's the correct safety posture for a document
verification system: false negatives (missed fakes) are more costly than
false positives (flagged real clips sent to human review).
"""


CONFIDENCE_THRESHOLD = 0.70   # Minimum real_score to confidently call "real"
SPOOF_TRIGGER       = 0.30   # Any spoof confidence above this triggers review


def fuse_voice_verdict(model1_result: dict, model2_result: dict) -> dict:
    """
    Fuse verdicts from two voice deepfake detection models.

    Args:
        model1_result: {"real_score": float, "verdict": "real"|"spoof"}
                       from MelodyMachine/Deepfake-audio-detection-V2 (M1)
        model2_result: {"real_score": float, "verdict": "real"|"spoof"}
                       from motheecreator/Deepfake-audio-detection (M2)

    Returns:
        {
          "final_verdict":   "real" | "spoof" | "uncertain",
          "confidence":      "high" | "low",
          "action":          "auto-approve" | "route-to-review",
          "explanation":     str,
          "model1_verdict":  str,
          "model2_verdict":  str,
          "model1_confidence": float,   # confidence in whichever verdict M1 gave
          "model2_confidence": float,
          "agreement":       bool
        }
    """

    m1_verdict = model1_result["verdict"]
    m2_verdict = model2_result["verdict"]
    m1_real    = model1_result["real_score"]
    m2_real    = model2_result["real_score"]

    # Confidence in each model's stated verdict
    m1_conf = m1_real if m1_verdict == "real" else (1.0 - m1_real)
    m2_conf = m2_real if m2_verdict == "real" else (1.0 - m2_real)

    models_agree   = (m1_verdict == m2_verdict)
    both_say_real  = (m1_verdict == "real" and m2_verdict == "real")
    either_spoof   = (m1_verdict == "spoof" or m2_verdict == "spoof")

    # --- Decision logic ---------------------------------------------------

    # Rule 1: Both confidently say real → auto-approve
    if both_say_real and m1_real >= CONFIDENCE_THRESHOLD and m2_real >= CONFIDENCE_THRESHOLD:
        return _result(
            final_verdict="real",
            confidence="high",
            action="auto-approve",
            explanation=(
                f"Both models agree: REAL  "
                f"(M1: {m1_real*100:.1f}%, M2: {m2_real*100:.1f}%)"
            ),
            m1_verdict=m1_verdict, m2_verdict=m2_verdict,
            m1_conf=m1_conf, m2_conf=m2_conf,
            agree=models_agree,
        )

    # Rule 2: Either model says spoof with meaningful confidence → route
    if either_spoof:
        spoof_source = []
        if m1_verdict == "spoof":
            spoof_source.append(f"M1 {(1-m1_real)*100:.1f}%")
        if m2_verdict == "spoof":
            spoof_source.append(f"M2 {(1-m2_real)*100:.1f}%")
        return _result(
            final_verdict="spoof",
            confidence="high" if not models_agree else "low",
            action="route-to-review",
            explanation=(
                f"Spoof signal detected ({', '.join(spoof_source)}) — "
                f"routed to human review"
            ),
            m1_verdict=m1_verdict, m2_verdict=m2_verdict,
            m1_conf=m1_conf, m2_conf=m2_conf,
            agree=models_agree,
        )

    # Rule 3: Both say real but at least one is below confidence threshold
    # (e.g. M1=real@55%, M2=real@80% — agree but uncertain)
    return _result(
        final_verdict="uncertain",
        confidence="low",
        action="route-to-review",
        explanation=(
            f"Both models say REAL but confidence too low  "
            f"(M1: {m1_real*100:.1f}%, M2: {m2_real*100:.1f}%) — "
            f"routed to human review"
        ),
        m1_verdict=m1_verdict, m2_verdict=m2_verdict,
        m1_conf=m1_conf, m2_conf=m2_conf,
        agree=models_agree,
    )


def _result(final_verdict, confidence, action, explanation,
            m1_verdict, m2_verdict, m1_conf, m2_conf, agree):
    return {
        "final_verdict":     final_verdict,
        "confidence":        confidence,
        "action":            action,
        "explanation":       explanation,
        "model1_verdict":    m1_verdict,
        "model2_verdict":    m2_verdict,
        "model1_confidence": m1_conf,
        "model2_confidence": m2_conf,
        "agreement":         agree,
    }


# ── self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cases = [
        ("Both confidently REAL",
         {"real_score": 1.00, "verdict": "real"},
         {"real_score": 0.999, "verdict": "real"}),
        ("M1 REAL, M2 SPOOF (disagree — typical fake pattern)",
         {"real_score": 1.00, "verdict": "real"},
         {"real_score": 0.00, "verdict": "spoof"}),
        ("Both SPOOF (rare but strong signal)",
         {"real_score": 0.05, "verdict": "spoof"},
         {"real_score": 0.03, "verdict": "spoof"}),
        ("Both REAL but M2 low confidence",
         {"real_score": 0.85, "verdict": "real"},
         {"real_score": 0.55, "verdict": "real"}),
        ("Encoding-artefact case: both say SPOOF on a real clip",
         {"real_score": 0.00, "verdict": "spoof"},
         {"real_score": 0.00, "verdict": "spoof"}),
    ]

    for title, m1, m2 in cases:
        r = fuse_voice_verdict(m1, m2)
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}")
        print(f"  M1: {m1['verdict'].upper():5s}  real_score={m1['real_score']:.3f}")
        print(f"  M2: {m2['verdict'].upper():5s}  real_score={m2['real_score']:.3f}")
        print(f"  → verdict={r['final_verdict'].upper():9s}  "
              f"action={r['action']}  confidence={r['confidence']}")
        print(f"  {r['explanation']}")
