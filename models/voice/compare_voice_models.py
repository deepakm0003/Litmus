"""
Step 2 — Side-by-side M1 vs M2 comparison on FoR dataset
M1: MelodyMachine/Deepfake-audio-detection-V2
M2: motheecreator/Deepfake-audio-detection

Tests the same 20 real + 20 fake samples used in the M1 baseline.
"""

import os
from pathlib import Path
import librosa

from test_voice    import run_voice_detection    as run_m1
from test_voice_v2 import run_voice_detection_v2 as run_m2

KAGGLE_DIR = Path("kaggle_data")

# ── helpers ──────────────────────────────────────────────────────────────────

def collect_samples(n_real=20, n_fake=20):
    real_files, fake_files = [], []
    for root, _, files in os.walk(KAGGLE_DIR):
        for f in sorted(files):
            fp = Path(root) / f
            if f.startswith("original"):
                real_files.append(fp)
            elif f.startswith("synthetic_"):
                fake_files.append(fp)
    return real_files[:n_real], fake_files[:n_fake]


def tag(fp):
    """Short label like UK/female/1/original.m4a"""
    parts = fp.parts
    return "/".join(parts[-4:])


def run_both(fp, ground_truth):
    t = tag(fp)
    print(f"\n  {t}")
    try:
        r1 = run_m1(str(fp))
    except Exception as e:
        r1 = {"real_score": -1, "verdict": "error"}
        print(f"  M1 ERROR: {e}")
    try:
        r2 = run_m2(str(fp))
    except Exception as e:
        r2 = {"real_score": -1, "verdict": "error"}
        print(f"  M2 ERROR: {e}")

    ok1 = (r1["verdict"] == ground_truth)
    ok2 = (r2["verdict"] == ground_truth)
    print(f"  M1: {r1['verdict'].upper():5s} ({r1['real_score']:5.1%})  {'✓' if ok1 else '✗'}  |  "
          f"M2: {r2['verdict'].upper():5s} ({r2['real_score']:5.1%})  {'✓' if ok2 else '✗'}")
    return {"file": t, "gt": ground_truth,
            "m1_verdict": r1["verdict"], "m1_score": r1["real_score"], "m1_ok": ok1,
            "m2_verdict": r2["verdict"], "m2_score": r2["real_score"], "m2_ok": ok2}


def print_table(rows, title):
    print(f"\n{'='*90}")
    print(f"  {title}")
    print(f"{'='*90}")
    print(f"  {'File':<40} {'GT':<6} {'M1':>7} {'V1':<6} {'✓1':<3}  {'M2':>7} {'V2':<6} {'✓2':<3}")
    print(f"  {'-'*40}  {'-'*5}  {'-'*7} {'-'*5} {'-'*3}  {'-'*7} {'-'*5} {'-'*3}")
    for r in rows:
        print(f"  {r['file']:<40} {r['gt']:<6} "
              f"{r['m1_score']:>6.1%} {r['m1_verdict'].upper():<6} {'✓' if r['m1_ok'] else '✗':<3}  "
              f"{r['m2_score']:>6.1%} {r['m2_verdict'].upper():<6} {'✓' if r['m2_ok'] else '✗':<3}")

    m1_acc = sum(r["m1_ok"] for r in rows) / len(rows) * 100
    m2_acc = sum(r["m2_ok"] for r in rows) / len(rows) * 100
    print(f"  {'─'*88}")
    print(f"  Accuracy — M1: {m1_acc:.0f}%   M2: {m2_acc:.0f}%   (n={len(rows)})")
    return m1_acc, m2_acc


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    real_files, fake_files = collect_samples(20, 20)
    print(f"Collected {len(real_files)} real, {len(fake_files)} fake samples")

    print("\n>>> REAL SAMPLES — loading both models on first file...")
    real_rows = [run_both(fp, "real")  for fp in real_files]

    print("\n>>> FAKE SAMPLES (FoR-era TTS/VC)...")
    fake_rows = [run_both(fp, "spoof") for fp in fake_files]

    # ── summary tables ────────────────────────────────────────────────────────
    r_m1, r_m2 = print_table(real_rows, "REAL SAMPLES — M1 vs M2")
    f_m1, f_m2 = print_table(fake_rows, "FAKE SAMPLES (FoR-era TTS/VC) — M1 vs M2")

    print(f"\n{'='*90}")
    print("  OVERALL COMPARISON")
    print(f"{'='*90}")
    print(f"  {'Category':<30} {'M1 acc':>8}  {'M2 acc':>8}")
    print(f"  {'-'*30}  {'-'*8}  {'-'*8}")
    print(f"  {'Real voice (FoR originals)':<30} {r_m1:>7.0f}%  {r_m2:>7.0f}%")
    print(f"  {'Fake voice (FoR-era TTS/VC)':<30} {f_m1:>7.0f}%  {f_m2:>7.0f}%")
    all_m1 = (sum(r["m1_ok"] for r in real_rows+fake_rows)) / (len(real_rows)+len(fake_rows)) * 100
    all_m2 = (sum(r["m2_ok"] for r in real_rows+fake_rows)) / (len(real_rows)+len(fake_rows)) * 100
    print(f"  {'Overall (40 samples)':<30} {all_m1:>7.0f}%  {all_m2:>7.0f}%")
    print(f"{'='*90}")

    # ── interpretation ────────────────────────────────────────────────────────
    print("\n  INTERPRETATION")
    print(f"  {'─'*86}")
    if r_m2 >= 75 and f_m2 >= 60:
        print("  ✓ M2 handles both real and FoR-era fakes well → strong ensemble candidate")
    elif r_m2 >= 75 and f_m2 < 30:
        print("  ⚠ M2 good on real, also blind to FoR-era fakes → same domain gap as M1")
        print("    Ensemble may not add value unless models disagree on different samples")
    elif r_m2 < 50:
        print("  ✗ M2 unreliable on real voice — not a suitable ensemble partner")
    else:
        print(f"  ? Mixed M2 results — examine per-sample disagreements below")

    # Show where M1 and M2 disagree (most useful for ensemble)
    all_rows = [(r, "real") for r in real_rows] + [(r, "spoof") for r in fake_rows]
    disagree = [(r, gt) for r, gt in all_rows if r["m1_verdict"] != r["m2_verdict"]]
    print(f"\n  Models disagree on {len(disagree)}/{len(all_rows)} samples:")
    for r, gt in disagree:
        correct_model = []
        if r["m1_ok"]: correct_model.append("M1")
        if r["m2_ok"]: correct_model.append("M2")
        winner = ", ".join(correct_model) if correct_model else "neither"
        print(f"    {r['file']:<42} GT={gt:<6} M1={r['m1_verdict']:<6} M2={r['m2_verdict']:<6} correct={winner}")

    print(f"\n  → Next: run build_voice_ensemble.py (Step 3 — fuse_voice_verdict)")
