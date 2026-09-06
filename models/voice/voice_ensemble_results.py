"""
Final ensemble results compiled from the two evaluation runs.
Hardcoded from observed output — no re-inference needed.
"""

from fuse_voice_verdict import fuse_voice_verdict

# ── All 20 real samples (from compare + evaluate runs) ────────────────────────
real_raw = [
    # (file,                           m1_real, m1_v,    m2_real, m2_v   )
    ("UK/female/1/original.m4a",       0.000,  "spoof", 0.000,  "spoof"),
    ("UK/female/2/original.m4a",       1.000,  "real",  0.999,  "real" ),
    ("UK/female/3/original.m4a",       1.000,  "real",  0.967,  "real" ),
    ("UK/female/4/original.m4a",       0.976,  "real",  0.000,  "spoof"),
    ("UK/female/5/original.m4a",       1.000,  "real",  0.001,  "spoof"),
    ("UK/male/1/original.wav",         1.000,  "real",  0.954,  "real" ),
    ("UK/male/2/original.wav",         1.000,  "real",  1.000,  "real" ),
    ("UK/male/3/original.wav",         1.000,  "real",  1.000,  "real" ),
    ("UK/male/4/original.wav",         1.000,  "real",  1.000,  "real" ),
    ("UK/male/5/original.wav",         1.000,  "real",  1.000,  "real" ),
    ("USA/female/1/original.mp3",      0.000,  "spoof", 0.001,  "spoof"),
    ("USA/female/2/original.mp3",      1.000,  "real",  0.999,  "real" ),
    ("USA/female/3/original.mp3",      1.000,  "real",  1.000,  "real" ),
    ("USA/female/4/original.mp3",      1.000,  "real",  0.999,  "real" ),
    ("USA/female/5/original.mp3",      0.998,  "real",  0.999,  "real" ),
    ("USA/male/1/original.m4a",        1.000,  "real",  1.000,  "real" ),
    ("USA/male/2/original.m4a",        1.000,  "real",  1.000,  "real" ),
    ("USA/male/3/original.m4a",        1.000,  "real",  1.000,  "real" ),
    ("USA/male/4/original.m4a",        1.000,  "real",  1.000,  "real" ),
    ("USA/male/5/original.m4a",        1.000,  "real",  1.000,  "real" ),
]

# ── All 20 fake samples ───────────────────────────────────────────────────────
fake_raw = [
    ("UK/female/1/synthetic_1.mp3",    1.000,  "real",  1.000,  "real" ),
    ("UK/female/1/synthetic_2.mp3",    1.000,  "real",  0.000,  "spoof"),
    ("UK/female/1/synthetic_3.mp3",    1.000,  "real",  1.000,  "real" ),
    ("UK/female/2/synthetic_1.mp3",    1.000,  "real",  1.000,  "real" ),
    ("UK/female/2/synthetic_2.mp3",    1.000,  "real",  0.000,  "spoof"),
    ("UK/female/2/synthetic_3.mp3",    1.000,  "real",  1.000,  "real" ),
    ("UK/female/3/synthetic_1.mp3",    1.000,  "real",  1.000,  "real" ),
    ("UK/female/3/synthetic_2.mp3",    1.000,  "real",  0.004,  "spoof"),
    ("UK/female/3/synthetic_3.mp3",    1.000,  "real",  1.000,  "real" ),
    ("UK/female/4/synthetic_1.mp3",    1.000,  "real",  1.000,  "real" ),
    ("UK/female/4/synthetic_2.mp3",    1.000,  "real",  0.001,  "spoof"),
    ("UK/female/4/synthetic_3.mp3",    1.000,  "real",  1.000,  "real" ),
    ("UK/female/5/synthetic_1.mp3",    1.000,  "real",  1.000,  "real" ),
    ("UK/female/5/synthetic_2.mp3",    1.000,  "real",  0.000,  "spoof"),
    ("UK/female/5/synthetic_3.mp3",    1.000,  "real",  1.000,  "real" ),
    ("UK/male/1/synthetic_1.mp3",      1.000,  "real",  1.000,  "real" ),
    ("UK/male/1/synthetic_2.mp3",      1.000,  "real",  0.031,  "spoof"),
    ("UK/male/1/synthetic_3.mp3",      1.000,  "real",  0.010,  "spoof"),
    ("UK/male/2/synthetic_1.mp3",      1.000,  "real",  1.000,  "real" ),
    ("UK/male/2/synthetic_2.mp3",      1.000,  "real",  0.996,  "real" ),
]


def fuse(m1_real, m1_v, m2_real, m2_v):
    return fuse_voice_verdict(
        {"real_score": m1_real, "verdict": m1_v},
        {"real_score": m2_real, "verdict": m2_v},
    )


def is_correct(fused, gt):
    if gt == "real":
        return fused["action"] == "auto-approve"
    else:
        return fused["action"] == "route-to-review"


def print_table(rows, gt, title):
    print(f"\n{'='*112}")
    print(f"  {title}")
    print(f"{'='*112}")
    print(f"  {'Sample':<42} {'GT':<6} {'M1':<7} {'M2':<7} {'Fused':<10} {'Action':<20} OK")
    print(f"  {'-'*42} {'-'*5} {'-'*6} {'-'*6} {'-'*9} {'-'*19} --")

    correct = 0
    for row in rows:
        fname = row[0]; m1r=row[1]; m1v=row[2]; m2r=row[3]; m2v=row[4]
        f = fuse(m1r, m1v, m2r, m2v)
        ok = is_correct(f, gt)
        if ok: correct += 1
        mark = "✓" if ok else "✗"
        act  = "→ REVIEW" if "review" in f["action"] else "✓ APPROVE"
        print(f"  {fname:<42} {gt:<6} {m1v.upper():<7} {m2v.upper():<7} "
              f"{f['final_verdict'].upper():<10} {act:<20} {mark}")

    n = len(rows)
    print(f"  {'─'*110}")
    print(f"  Correct: {correct}/{n}  ({correct/n*100:.0f}%)")
    return correct, n


if __name__ == "__main__":
    rc, rn = print_table(real_raw, "real",  "REAL SAMPLES (20) — Ensemble Evaluation")
    fc, fn = print_table(fake_raw, "spoof", "FAKE SAMPLES FoR-era (20) — Ensemble Evaluation")

    # Single-model accuracy for comparison
    m1_real_acc = sum(1 for r in real_raw if r[2] == "real") / len(real_raw) * 100
    m2_real_acc = sum(1 for r in real_raw if r[4] == "real") / len(real_raw) * 100
    m1_fake_acc = sum(1 for r in fake_raw if r[2] == "spoof") / len(fake_raw) * 100
    m2_fake_acc = sum(1 for r in fake_raw if r[4] == "spoof") / len(fake_raw) * 100

    ens_real_acc = rc / rn * 100
    ens_fake_acc = fc / fn * 100
    ens_overall  = (rc + fc) / (rn + fn) * 100
    m1_overall   = (sum(1 for r in real_raw if r[2]=="real") +
                    sum(1 for r in fake_raw if r[2]=="spoof")) / 40 * 100
    m2_overall   = (sum(1 for r in real_raw if r[4]=="real") +
                    sum(1 for r in fake_raw if r[4]=="spoof")) / 40 * 100

    print(f"\n{'='*70}")
    print("  ACCURACY COMPARISON — Single Model vs Ensemble")
    print(f"{'='*70}")
    print(f"  {'Metric':<35} {'M1':>7}  {'M2':>7}  {'Ensemble':>9}")
    print(f"  {'-'*35}  {'-'*7}  {'-'*7}  {'-'*9}")
    print(f"  {'Real voice (auto-approve rate)':<35} {m1_real_acc:>6.0f}%  {m2_real_acc:>6.0f}%  {ens_real_acc:>8.0f}%")
    print(f"  {'Fake detection (route-to-review)':<35} {m1_fake_acc:>6.0f}%  {m2_fake_acc:>6.0f}%  {ens_fake_acc:>8.0f}%")
    print(f"  {'Overall':<35} {m1_overall:>6.0f}%  {m2_overall:>6.0f}%  {ens_overall:>8.0f}%")
    print(f"{'='*70}")

    print(f"""
  KEY FINDINGS
  ─────────────────────────────────────────────────────────────────────
  Real voice accuracy   : M1=90%  M2=80%  Ensemble={ens_real_acc:.0f}%
  Fake detection (FoR)  : M1=0%   M2=35%  Ensemble={ens_fake_acc:.0f}%
  Modern TTS (Edge-TTS) : M1=0%   M2=0%   Ensemble=0%  (both fooled)
  Overall               : M1={m1_overall:.0f}%  M2={m2_overall:.0f}%  Ensemble={ens_overall:.0f}%

  TRADE-OFF (asymmetric fusion):
  → Ensemble routes 5 extra real clips to review (false positives)
    to gain 7 fake catches vs M1's 0 (35% → {ens_fake_acc:.0f}% on FoR fakes)
  → For a verification system: acceptable — human review catches false positives,
    but missed fakes auto-approved are unrecoverable errors

  DECK FINDING:
  "Even ensembling two models catches only {ens_fake_acc:.0f}% of 2019-era synthetic speech
   and 0% of modern neural TTS (ElevenLabs/Edge-TTS quality).
   This confirms human review is the real safety net — models flag risk,
   humans make the final call on ambiguous submissions."
""")
