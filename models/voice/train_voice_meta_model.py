"""
Train voice meta-model on single-model scores.
Voice uses one model (MelodyMachine), so this is a 1-feature threshold optimizer
that finds the optimal real_score cutoff via logistic regression + CV,
then compares against the naive 0.5 cutoff.

Reads collect_voice_scores.py output CSV.
Saves voice_meta_model.pkl.
"""

import os, sys, pickle, warnings
import numpy  as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.linear_model    import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics         import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing   import StandardScaler
from sklearn.pipeline        import Pipeline

warnings.filterwarnings("ignore")

BASE        = os.path.dirname(__file__)
SCORES_CSV  = os.path.join(BASE, "voice_meta_training_data.csv")
MODEL_PATH  = os.path.join(BASE, "voice_meta_model.pkl")
PLOT_PATH   = os.path.join(BASE, "voice_threshold_plot.png")


def threshold_sweep(y_true, scores):
    """Return accuracy at each threshold, find best."""
    print(f"\n{'Threshold':>12s}  {'Accuracy':>10s}  {'TP':>5s}  {'TN':>5s}  {'FP':>5s}  {'FN':>5s}")
    print("-"*60)
    best_t, best_acc = 0.5, 0.0
    for t in np.arange(0.10, 0.91, 0.05):
        preds = (scores > t).astype(int)
        acc   = accuracy_score(y_true, preds)
        cm    = confusion_matrix(y_true, preds)
        tn, fp, fn, tp = cm.ravel()
        marker = " <--" if acc > best_acc else ""
        print(f"{t:12.2f}  {acc*100:9.1f}%  {tp:5d}  {tn:5d}  {fp:5d}  {fn:5d}{marker}")
        if acc > best_acc:
            best_acc = acc
            best_t   = t
    print("-"*60)
    print(f"Best threshold: {best_t:.2f}  accuracy: {best_acc*100:.1f}%")
    return best_t, best_acc


def main():
    print("="*70)
    print("LITMUS VOICEPRINT — META-MODEL TRAINING")
    print("="*70)

    if not os.path.exists(SCORES_CSV):
        print(f"[ERROR] Scores CSV not found: {SCORES_CSV}")
        print("Run collect_voice_scores.py first.")
        sys.exit(1)

    df = pd.read_csv(SCORES_CSV)
    print(f"\nLoaded {len(df)} samples from {SCORES_CSV}")
    print(f"  Real samples : {(df['true_label']==1).sum()}")
    print(f"  Spoof samples: {(df['true_label']==0).sum()}")

    if len(df) < 10:
        print("[ERROR] Need at least 10 samples.")
        sys.exit(1)

    X = df[["real_score"]].values
    y = df["true_label"].values

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)

    # ── train logistic regression (finds optimal sigmoid threshold) ───────────
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("lr",     LogisticRegression(max_iter=1000, random_state=42,
                                      class_weight="balanced")),
    ])
    pipe.fit(X_tr, y_tr)

    y_pred = pipe.predict(X_te)
    meta_acc = accuracy_score(y_te, y_pred)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipe, X, y, cv=cv, scoring="accuracy")

    naive_acc = accuracy_score(y_te, (X_te[:, 0] > 0.5).astype(int))

    print(f"\n{'='*70}")
    print("RESULTS")
    print("="*70)
    print(f"  Naive 0.50 threshold accuracy : {naive_acc*100:.1f}%")
    print(f"  Meta-model test accuracy      : {meta_acc*100:.1f}%")
    print(f"  5-fold CV accuracy            : {cv_scores.mean()*100:.1f}%  "
          f"(+/- {cv_scores.std()*100:.1f}%)")
    print(f"  Improvement over naive        : {(meta_acc - naive_acc)*100:+.1f} pp")
    print()
    print(classification_report(y_te, y_pred, target_names=["Spoof", "Real"]))

    # ── threshold sweep on full set ───────────────────────────────────────────
    print(f"\n{'='*70}")
    print("THRESHOLD SWEEP (full dataset)")
    print("="*70)
    best_t, best_sweep_acc = threshold_sweep(y, X[:, 0])

    # ── save ──────────────────────────────────────────────────────────────────
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipe, f)
    print(f"\n[SAVED] Voice meta-model -> {MODEL_PATH}")

    # ── plot score distributions ───────────────────────────────────────────────
    real_scores  = X[y == 1, 0]
    spoof_scores = X[y == 0, 0]

    fig, ax = plt.subplots(figsize=(9, 5))
    bins = np.linspace(0, 1, 40)
    ax.hist(real_scores,  bins=bins, alpha=0.6, color="green", label="Real")
    ax.hist(spoof_scores, bins=bins, alpha=0.6, color="red",   label="Spoof")
    ax.axvline(0.5,    color="orange",  ls="--", lw=1.5, label="Naive 0.50 cutoff")
    ax.axvline(best_t, color="black",   ls="--", lw=1.5,
               label=f"Optimal threshold {best_t:.2f} ({best_sweep_acc*100:.1f}% acc)")
    ax.set_xlabel("Model real score", fontsize=11)
    ax.set_ylabel("Count",            fontsize=11)
    ax.set_title("VoicePrint — Real vs Spoof score distributions\n"
                 "(MelodyMachine/Deepfake-audio-detection-V2)", fontsize=11)
    ax.legend()
    plt.tight_layout()
    plt.savefig(PLOT_PATH, dpi=150)
    print(f"[SAVED] Score distribution plot -> {PLOT_PATH}")
    print("="*70)


if __name__ == "__main__":
    main()
