"""
Reproduces every accuracy claim FaceGuard makes.

Run:  python models/face/validate_faceguard.py

The point of this file is that nothing in the pitch has to be taken on trust.
Each number printed below is computed here, from the labelled scores in
meta_training_data.csv, with the threshold chosen on training folds only so no
test data leaks into the calibration.
"""

import csv
import os
import sys

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "meta_training_data.csv")

CURRENT_THRESHOLD = 0.50     # what the original pipeline used
LEGACY_CONF_FLOOR = 0.70     # the old "both models >70% confident" rule


def load():
    rows = list(csv.DictReader(open(CSV)))
    y = np.array([int(r["true_label"]) for r in rows])          # 1 = real
    m1 = np.array([float(r["m1_real_score"]) for r in rows])
    m2 = np.array([float(r["m2_real_score"]) for r in rows])
    return y, m1, m2


def rule(fmt, *args):
    print(fmt.format(*args))


def main():
    if not os.path.exists(CSV):
        sys.exit(f"Missing {CSV}")

    y, m1, m2 = load()
    n = len(y)

    print("=" * 68)
    print("  FaceGuard validation")
    print(f"  {n} labelled samples — {int(y.sum())} real, {int((1 - y).sum())} fake")
    print("=" * 68)

    # ---------------------------------------------------------------- 1
    print("\n1. IS THERE SIGNAL AT ALL?  (AUC: 0.5 = coin flip)")
    a1, a2 = roc_auc_score(y, m1), roc_auc_score(y, m2)
    rule("   Model 1            AUC {:.3f}   {}", a1,
         "usable ranking" if a1 > 0.65 else "weak")
    rule("   Model 2            AUC {:.3f}   {}", a2,
         "usable ranking" if a2 > 0.65 else "NO SIGNAL — coin flip")
    rule("   equal-weight mean  AUC {:.3f}   {}", roc_auc_score(y, (m1 + m2) / 2),
         "averaging M2 in DESTROYS signal" if roc_auc_score(y, (m1 + m2) / 2) < a1 else "")
    print("   -> Model 2 is demoted from voter to demographic context check.")

    # ---------------------------------------------------------------- 2
    print("\n2. WHY THE DEFAULT THRESHOLD FAILS")
    rule("   mean real-score on REAL images : M1 {:.3f}", m1[y == 1].mean())
    rule("   mean real-score on FAKE images : M1 {:.3f}", m1[y == 0].mean())
    print("   Both sit above 0.5, so at the default cut almost everything")
    print("   is called 'real'. The ranking is fine; the cut point is wrong.")
    rule("   accuracy @ {:.2f} : {:.1f}%  (chance)", CURRENT_THRESHOLD,
         ((m1 >= CURRENT_THRESHOLD).astype(int) == y).mean() * 100)

    # ---------------------------------------------------------------- 3
    print("\n3. CALIBRATION  (threshold picked on train folds, scored on held-out)")
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    grid = np.linspace(0.50, 0.999, 400)
    oof = np.zeros(n, dtype=int)
    picked = []
    for tr, te in cv.split(m1.reshape(-1, 1), y):
        accs = [((m1[tr] >= t).astype(int) == y[tr]).mean() for t in grid]
        t_best = float(grid[int(np.argmax(accs))])
        picked.append(round(t_best, 3))
        oof[te] = (m1[te] >= t_best).astype(int)

    held_out = (oof == y).mean() * 100
    shipped = float(np.median(picked))
    rule("   per-fold thresholds : {}", picked)
    rule("   held-out accuracy   : {:.1f}%", held_out)
    rule("   shipping threshold  : {:.3f}", shipped)
    rule("   IMPROVEMENT         : {:.1f}% -> {:.1f}%  (+{:.1f} points)",
         ((m1 >= CURRENT_THRESHOLD).astype(int) == y).mean() * 100,
         held_out,
         held_out - ((m1 >= CURRENT_THRESHOLD).astype(int) == y).mean() * 100)

    pred = (m1 >= shipped).astype(int)
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    rule("   fakes missed as real: {}   (the costly error)", fp)
    rule("   real wrongly flagged: {}   (routes to a human, not a rejection)", fn)

    # ---------------------------------------------------------------- 4
    print("\n4. THE OLD FIXED RULE, MEASURED HONESTLY")
    print("   'both models agree AND both >70% confident -> auto-decide'")

    def legacy(a, b):
        va, vb = a >= .5, b >= .5
        ca = a if va else 1 - a
        cb = b if vb else 1 - b
        if va == vb and ca >= LEGACY_CONF_FLOOR and cb >= LEGACY_CONF_FLOOR:
            return 1 if va else 0
        return -1

    lp = np.array([legacy(a, b) for a, b in zip(m1, m2)])
    decided = lp != -1
    correct = int((lp[decided] == y[decided]).sum())
    wrong = int(decided.sum()) - correct
    rule("   auto-decided        : {}/{}  ({:.1f}%)", int(decided.sum()), n, decided.mean() * 100)
    rule("   correct when auto   : {}", correct)
    rule("   SILENT WRONG        : {}   <- on THIS benchmark, not zero", wrong)
    print()
    print("   The 'zero silent wrong auto-approvals' result holds for the")
    print("   demo-condition samples it was measured on. On this harder")
    print("   FF++/DFDC-derived benchmark the same rule is wrong on")
    rule("   {:.0f}% of the cases it commits to. Both numbers are real; the", 100 * wrong / max(1, decided.sum()))
    print("   scope matters, and this is why the threshold was recalibrated.")

    print("\n" + "=" * 68)
    print("  Constants now shipping in faceguard.py:")
    rule("    M1_THRESHOLD = {:.3f}", shipped)
    print("=" * 68)


if __name__ == "__main__":
    main()
