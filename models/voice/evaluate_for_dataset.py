"""
FoR Dataset Baseline Evaluation - Steps 3 & 4
Tests MelodyMachine/Deepfake-audio-detection-V2 (M1) on:
  - 20 real (original) samples from FoR dataset
  - 20 fake (older TTS/VC) samples from FoR dataset
Produces accuracy comparison: FoR-era fakes vs modern Edge-TTS fakes
"""

import os
import sys
from pathlib import Path
from test_voice import run_voice_detection

KAGGLE_DIR = Path("kaggle_data")

def collect_samples():
    """Walk UK/ and USA/ folders, collect originals and synthetics."""
    real_files = []
    fake_files = []

    for root, dirs, files in os.walk(KAGGLE_DIR):
        for f in sorted(files):
            fp = Path(root) / f
            if f.startswith("original"):
                real_files.append(fp)
            elif f.startswith("synthetic_"):
                fake_files.append(fp)

    return real_files, fake_files


def run_batch(files, ground_truth, label):
    """Run M1 on a list of files, return results list."""
    results = []
    print(f"\n{'='*65}")
    print(f"  TESTING: {label}  ({len(files)} samples)")
    print(f"{'='*65}")

    for fp in files:
        tag = f"{fp.parts[-3]}/{fp.parts[-2]}/{fp.name}"  # e.g. UK/female/1/original.m4a
        print(f"\n  [{tag}]")
        try:
            out = run_voice_detection(str(fp))
            real_score = out["real_score"]
            verdict    = out["verdict"]
            correct    = (verdict == ground_truth)
            mark       = "✓" if correct else "✗"
            print(f"  real_score={real_score:.3f}  verdict={verdict.upper()}  {mark}")
            results.append({
                "file": tag,
                "ground_truth": ground_truth,
                "real_score": real_score,
                "verdict": verdict,
                "correct": correct,
            })
        except Exception as e:
            print(f"  ERROR: {e}")

    return results


def print_summary(results, label):
    correct = sum(1 for r in results if r["correct"])
    total   = len(results)
    acc     = correct / total * 100 if total else 0
    avg_rs  = sum(r["real_score"] for r in results) / total if total else 0

    print(f"\n{'─'*65}")
    print(f"  {label} SUMMARY")
    print(f"{'─'*65}")
    print(f"  {'File':<35} {'Score':>7}  {'Verdict':<8}  OK")
    print(f"  {'─'*35}  {'─'*7}  {'─'*8}  ──")
    for r in results:
        mark = "✓" if r["correct"] else "✗"
        print(f"  {r['file']:<35} {r['real_score']:>6.1%}  {r['verdict'].upper():<8}  {mark}")
    print(f"{'─'*65}")
    print(f"  Accuracy : {correct}/{total}  ({acc:.0f}%)")
    print(f"  Avg real_score : {avg_rs:.3f}")
    return acc, avg_rs


if __name__ == "__main__":
    real_files, fake_files = collect_samples()
    print(f"Found {len(real_files)} real files, {len(fake_files)} fake files in kaggle_data/")

    # Cap at 20 each for speed; take a spread across UK/USA/gender
    real_sample = real_files[:20]
    fake_sample = fake_files[:20]   # first 20 of 60 synthetic clips

    # ── Step 3: Real voice baseline ──────────────────────────────────────────
    real_results = run_batch(real_sample, ground_truth="real",  label="REAL (human originals)")
    real_acc, real_avg = print_summary(real_results, "REAL")

    # ── Step 4: Older-era fake baseline ──────────────────────────────────────
    fake_results = run_batch(fake_sample, ground_truth="spoof", label="FAKE (FoR-era TTS/VC)")
    fake_acc, fake_avg = print_summary(fake_results, "FAKE")

    # ── Overall interpretation ────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("  BASELINE INTERPRETATION")
    print(f"{'='*65}")
    print(f"  Real voice accuracy (FoR originals)  : {real_acc:.0f}%")
    print(f"  Fake voice accuracy (FoR-era TTS/VC) : {fake_acc:.0f}%")
    print(f"  Modern TTS accuracy (Edge-TTS, known) : ~0%  (from prior tests)")
    print()

    if real_acc >= 75:
        print("  ✓ Model correctly identifies real human speech at scale")
        print("    → Domain mismatch confirmed: good on real, struggles on modern TTS")
        print("    → Same pattern as face model — proceed to Step 2 (ensemble)")
    else:
        print("  ⚠ Model also struggles with real speech")
        print("    → Broader calibration issue, not just modern-TTS domain gap")
        print("    → Threshold tuning needed before ensemble")

    if fake_acc >= 60:
        print(f"\n  ✓ Detects FoR-era (2019) synthesis at {fake_acc:.0f}%")
        print(f"    Modern neural TTS accuracy: ~0% → accuracy gap = {fake_acc:.0f}pp")
        print("    Deck-worthy data point: older detection, newer generation outpaces it")
    else:
        print(f"\n  ⚠ Even FoR-era fakes only {fake_acc:.0f}% — model has general issues")

    print(f"\n  Next: run setup_voice_v2.py to load motheecreator model (Step 2)")
    print(f"{'='*65}")
