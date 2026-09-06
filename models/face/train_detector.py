"""
Train and honestly evaluate the Litmus face detector.

    python models/face/train_detector.py --n 3000

Extracts frequency-domain and capture-quality features from the labelled Kaggle
pools, fits a calibrated gradient-boosted classifier, and reports cross-validated
performance. Nothing here is tuned on the test fold.

The output is written to face_detector.joblib and loaded by faceguard.py.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_DIR = os.path.join(HERE, "kaggle_data", "Real faces")
FAKE_DIR = os.path.join(HERE, "kaggle_data", "Fake faces")
BOLLY_DIR = os.path.join(HERE, "kaggle_data", "bollywood")
OUT = os.path.join(HERE, "face_detector.joblib")
META = os.path.join(HERE, "face_detector_metrics.json")


def collect(folder, limit, seed=0):
    files = sorted(glob.glob(os.path.join(folder, "**", "*.*"), recursive=True))
    files = [f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    random.Random(seed).shuffle(files)
    return files[:limit]


def build_matrix(files, label, tag):
    X, kept = [], []
    t0 = time.time()
    for i, f in enumerate(files):
        d = F.extract(f)
        if not d:
            continue
        X.append(d)
        kept.append(f)
        if (i + 1) % 500 == 0:
            print(f"    {tag}: {i + 1}/{len(files)}  ({time.time() - t0:.0f}s)", flush=True)
    return X, [label] * len(X), kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000, help="images per class")
    args = ap.parse_args()

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import roc_auc_score, accuracy_score
    import joblib

    print(f"Extracting features ({args.n} per class)…", flush=True)
    real_files = collect(REAL_DIR, args.n, seed=1)
    fake_files = collect(FAKE_DIR, args.n, seed=2)
    print(f"  found {len(real_files)} real, {len(fake_files)} fake", flush=True)

    Xr, yr, _ = build_matrix(real_files, 1, "real")
    Xf, yf, _ = build_matrix(fake_files, 0, "fake")

    rows = Xr + Xf
    y = np.array(yr + yf)
    names = sorted(rows[0].keys())
    X = np.array([[r.get(k, 0.0) for k in names] for r in rows])
    print(f"  matrix {X.shape}, {len(names)} features\n", flush=True)

    clf = CalibratedClassifierCV(
        HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08,
                                       max_depth=6, random_state=0),
        method="isotonic", cv=3,
    )

    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    print("Cross-validating (5-fold, no leakage)…", flush=True)
    proba = cross_val_predict(clf, X, y, cv=cv, method="predict_proba")[:, 1]

    auc = roc_auc_score(y, proba)
    acc = accuracy_score(y, (proba >= 0.5).astype(int))
    print(f"\n  held-out AUC      : {auc:.4f}")
    print(f"  held-out accuracy : {acc * 100:.1f}%")

    # Operating points: how decisive can we be at what error cost?
    print(f"\n  {'band':>7}{'decides':>10}{'accuracy':>11}{'fakes approved':>17}")
    ops = {}
    for band in (0.50, 0.70, 0.80, 0.90, 0.95):
        conf = np.maximum(proba, 1 - proba)
        dec = conf >= band
        if dec.sum() == 0:
            continue
        p = (proba >= 0.5).astype(int)
        a = accuracy_score(y[dec], p[dec])
        fa = int(((p == 1) & (y == 0) & dec).sum())
        ops[band] = {"coverage": float(dec.mean()), "accuracy": float(a), "fakes_approved": fa}
        print(f"  {band:>7.2f}{dec.mean() * 100:>9.1f}%{a * 100:>10.1f}%{fa:>17}")

    # Fit the shipping model on everything.
    print("\nFitting final model on all data…", flush=True)
    clf.fit(X, y)
    joblib.dump({"model": clf, "feature_names": names}, OUT)

    # Bias check on Indian faces — all genuine, so every prediction should be real.
    bolly = collect(BOLLY_DIR, 300, seed=3)
    if bolly:
        print(f"\nBias check on {len(bolly)} Bollywood (Indian, all genuine) faces…", flush=True)
        Xb, _, _ = build_matrix(bolly, 1, "bolly")
        Xb = np.array([[r.get(k, 0.0) for k in names] for r in Xb])
        pb = clf.predict_proba(Xb)[:, 1]
        rate = float((pb >= 0.5).mean())
        print(f"  correctly called real : {rate * 100:.1f}%")
        print(f"  mean real-probability : {pb.mean():.3f}")
    else:
        rate = None

    json.dump({
        "auc": float(auc), "accuracy": float(acc),
        "n_per_class": args.n, "n_features": len(names),
        "operating_points": ops,
        "indian_face_real_rate": rate,
        "feature_names": names,
    }, open(META, "w"), indent=2)

    print(f"\nSaved {OUT}")
    print(f"Saved {META}")


if __name__ == "__main__":
    main()
