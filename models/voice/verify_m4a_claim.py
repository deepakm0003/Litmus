"""
Task 1 — Verify the format-artifact claim.
Re-run M1 + M2 on the 4 failing real samples, before (original) and after (.wav conversion).
If scores improve after conversion → format artifact confirmed.
If scores stay bad → real model weakness, not a format issue.
"""

import os
from pathlib import Path
from test_voice    import run_voice_detection    as run_m1
from test_voice_v2 import run_voice_detection_v2 as run_m2

BASE  = Path("kaggle_data")
CONV  = Path("m4a_test")

PAIRS = [
    {
        "label":    "UK/female/1  (.m4a → .wav)",
        "original": BASE / "UK/female/1/original.m4a",
        "converted": CONV / "UK_female_1.wav",
        "gt":       "real",
    },
    {
        "label":    "UK/female/4  (.m4a → .wav)",
        "original": BASE / "UK/female/4/original.m4a",
        "converted": CONV / "UK_female_4.wav",
        "gt":       "real",
    },
    {
        "label":    "UK/female/5  (.m4a → .wav)",
        "original": BASE / "UK/female/5/original.m4a",
        "converted": CONV / "UK_female_5.wav",
        "gt":       "real",
    },
    {
        "label":    "USA/female/1 (.mp3 → .wav)",
        "original": BASE / "USA/female/1/original.mp3",
        "converted": CONV / "USA_female_1.wav",
        "gt":       "real",
    },
]


def test_file(path):
    r1 = run_m1(str(path))
    r2 = run_m2(str(path))
    return r1, r2


def verdict_mark(verdict, gt):
    return "✓" if verdict == gt else "✗"


print("=" * 80)
print("  FORMAT ARTIFACT VERIFICATION — Before (.m4a/.mp3) vs After (.wav)")
print("=" * 80)
print(f"\n  {'Sample':<30} {'Ver':<5}  {'M1 score':>9}  {'M1 v':<6}  {'M2 score':>9}  {'M2 v':<6}  OK")
print(f"  {'-'*30}  {'-'*4}  {'-'*9}  {'-'*5}  {'-'*9}  {'-'*5}  --")

summary = []

for p in PAIRS:
    gt = p["gt"]
    for version, fpath in [("orig", p["original"]), ("wav", p["converted"])]:
        try:
            r1, r2 = test_file(fpath)
            m1_ok = verdict_mark(r1["verdict"], gt)
            m2_ok = verdict_mark(r2["verdict"], gt)
            both_ok = (r1["verdict"] == gt and r2["verdict"] == gt)
            print(f"  {p['label']:<30}  {version:<4}  "
                  f"{r1['real_score']:>8.1%}  {r1['verdict'].upper():<6}  "
                  f"{r2['real_score']:>8.1%}  {r2['verdict'].upper():<6}  "
                  f"{m1_ok}{m2_ok}")
            summary.append({
                "label": p["label"], "version": version,
                "m1_score": r1["real_score"], "m1_v": r1["verdict"],
                "m2_score": r2["real_score"], "m2_v": r2["verdict"],
                "both_ok": both_ok,
            })
        except Exception as e:
            print(f"  {p['label']:<30}  {version:<4}  ERROR: {e}")
    print()

# ── Verdict ────────────────────────────────────────────────────────────────────
print("=" * 80)
print("  VERDICT")
print("=" * 80)

orig_ok  = [s for s in summary if s["version"] == "orig"  and s["both_ok"]]
wav_ok   = [s for s in summary if s["version"] == "wav"   and s["both_ok"]]
improved = [s["label"] for s in summary if s["version"] == "wav" and s["both_ok"]
            and not any(o["label"] == s["label"] and o["both_ok"]
                        for o in summary if o["version"] == "orig")]
still_bad = [s["label"] for s in summary if s["version"] == "wav" and not s["both_ok"]]

print(f"\n  Original format — both models correct : {len(orig_ok)}/4")
print(f"  After .wav conversion — both correct  : {len(wav_ok)}/4")
print(f"  Improved by conversion                : {len(improved)}")
print(f"  Still failing after conversion        : {len(still_bad)}")
print()

if len(improved) > 0 and len(still_bad) == 0:
    print("  ✓ CONFIRMED: Format artifact — all failures fixed by .wav conversion")
    print("    Safe to write in deck: 'encoding artifact, not a model capability issue'")
    print("    Live demo uses .wav → clean performance expected")
elif len(improved) > 0 and len(still_bad) > 0:
    print(f"  ⚠ PARTIAL: {len(improved)} fixed by conversion, {len(still_bad)} still failing")
    print("    Conversion helps but doesn't fully explain the failures")
    print("    Be cautious: say 'encoding sensitivity' not 'format artifact'")
    for s in still_bad:
        print(f"    Still failing: {s}")
else:
    print("  ✗ NOT CONFIRMED: .wav conversion does not fix the failures")
    print("    This is a genuine model weakness, not a format issue")
    print("    Do NOT write 'format artifact' in the deck")
    print("    → Say: 'model shows sensitivity to certain female vocal profiles'")
