"""
Train a stacked logistic-regression meta-model on [m1_score, m2_score] -> real/fake.
Reads collect_scores.py output CSV. Replaces the hand-picked 70% threshold.

Result:
  - meta_model.pkl              (saved sklearn model)
  - meta_model_boundary.png     (decision boundary visualisation)
  - Printed accuracy comparison: meta-model vs fixed-rule
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

BASE         = os.path.dirname(__file__)
SCORES_CSV   = os.path.join(BASE, "meta_training_data.csv")
MODEL_PATH   = os.path.join(BASE, "meta_model.pkl")
PLOT_PATH    = os.path.join(BASE, "meta_model_boundary.png")


# ─── helpers ──────────────────────────────────────────────────────────────────

def fixed_rule_predict(m1_scores, m2_scores, threshold=0.70):
    """
    The rule we validated manually:
      both models agree AND both confident (>threshold) → their verdict
      otherwise → 'uncertain', mapped to majority class for accuracy comparison
    """
    preds = []
    for m1, m2 in zip(m1_scores, m2_scores):
        m1_says_real = m1 > 0.5
        m2_says_real = m2 > 0.5
        m1_conf = m1 if m1_says_real else 1 - m1
        m2_conf = m2 if m2_says_real else 1 - m2
        if m1_says_real == m2_says_real and m1_conf >= threshold and m2_conf >= threshold:
            preds.append(1 if m1_says_real else 0)
        else:
            # uncertain → abstain; for accuracy comparison count as wrong
            preds.append(-1)
    return np.array(preds)


def fixed_rule_accuracy(y_true, m1_scores, m2_scores, threshold=0.70):
    preds = fixed_rule_predict(m1_scores, m2_scores, threshold)
    # Only count cases where the rule committed; abstentions treated as wrong
    committed = preds != -1
    n_committed  = committed.sum()
    n_abstained  = (~committed).sum()
    n_correct    = (preds[committed] == y_true[committed]).sum() if n_committed else 0
    # Overall safety metric: fraction of total samples answered correctly
    overall_acc  = n_correct / len(y_true) if len(y_true) else 0
    # Precision among committed
    commit_acc   = n_correct / n_committed if n_committed else 0
    return overall_acc, commit_acc, n_committed, n_abstained


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print("="*70)
    print("LITMUS FACEGUARD — META-MODEL TRAINING")
    print("="*70)

    if not os.path.exists(SCORES_CSV):
        print(f"[ERROR] Scores CSV not found: {SCORES_CSV}")
        print("Run collect_scores.py first.")
        sys.exit(1)

    df = pd.read_csv(SCORES_CSV)
    print(f"\nLoaded {len(df)} samples from {SCORES_CSV}")
    print(f"  Real samples : {(df['true_label']==1).sum()}")
    print(f"  Fake samples : {(df['true_label']==0).sum()}")

    if len(df) < 10:
        print("[ERROR] Need at least 10 samples. Collect more.")
        sys.exit(1)

    X = df[["m1_real_score", "m2_real_score"]].values
    y = df["true_label"].values

    # ── train / test split ────────────────────────────────────────────────────
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)

    # ── meta-model: logistic regression with standard scaling ─────────────────
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("lr",     LogisticRegression(max_iter=1000, random_state=42,
                                      class_weight="balanced")),
    ])
    pipe.fit(X_tr, y_tr)

    # ── evaluate ──────────────────────────────────────────────────────────────
    y_pred_meta = pipe.predict(X_te)
    meta_acc    = accuracy_score(y_te, y_pred_meta)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipe, X, y, cv=cv, scoring="accuracy")

    print(f"\n{'='*70}")
    print("META-MODEL RESULTS (test set)")
    print("="*70)
    print(f"  Test accuracy     : {meta_acc*100:.1f}%")
    print(f"  5-fold CV accuracy: {cv_scores.mean()*100:.1f}%  "
          f"(+/- {cv_scores.std()*100:.1f}%)")

    print("\nClassification report:")
    print(classification_report(y_te, y_pred_meta, target_names=["Fake","Real"]))

    cm = confusion_matrix(y_te, y_pred_meta)
    tn, fp, fn, tp = cm.ravel()
    print(f"Confusion matrix (test):")
    print(f"              Predicted")
    print(f"              Fake  Real")
    print(f"Actual Fake   {tn:4d}  {fp:4d}")
    print(f"Actual Real   {fn:4d}  {tp:4d}")

    # ── compare against fixed rule ────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("COMPARISON: Meta-Model vs Fixed 70% Rule (test set)")
    print("="*70)
    fr_overall, fr_commit, n_commit, n_abstain = fixed_rule_accuracy(
        y_te, X_te[:, 0], X_te[:, 1], threshold=0.70)

    print(f"  Meta-model test accuracy   : {meta_acc*100:.1f}%  (answers every sample)")
    print(f"  Fixed rule overall accuracy: {fr_overall*100:.1f}%  "
          f"({n_commit} committed, {n_abstain} abstained as uncertain)")
    print(f"  Fixed rule commit accuracy : {fr_commit*100:.1f}%  "
          f"(on the {n_commit} samples it was confident enough to decide)")
    improvement = (meta_acc - fr_overall) * 100
    print(f"  Meta-model improvement     : {improvement:+.1f} pp  "
          f"(covers all samples, not just high-confidence ones)")

    # ── save model ────────────────────────────────────────────────────────────
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipe, f)
    print(f"\n[SAVED] Meta-model -> {MODEL_PATH}")

    # ── decision boundary plot ────────────────────────────────────────────────
    h = 0.005
    xx, yy = np.meshgrid(np.arange(-0.05, 1.05, h),
                         np.arange(-0.05, 1.05, h))
    Z = pipe.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.contourf(xx, yy, Z, alpha=0.25, cmap="RdYlGn")
    ax.contour(xx, yy, Z, levels=[0.5], colors="black", linewidths=1.5,
               linestyles="--")

    # plot training + test points
    for xi, yi in zip(X, y):
        color = "green" if yi == 1 else "red"
        marker = "o" if yi == 1 else "x"
        ax.scatter(xi[0], xi[1], c=color, marker=marker, s=40,
                   edgecolors="black", linewidths=0.4, alpha=0.7)

    # fixed-rule boundary lines
    ax.axhline(0.70, color="steelblue", ls=":", lw=1.5,
               label="Fixed rule M2 = 0.70")
    ax.axvline(0.70, color="orange",    ls=":", lw=1.5,
               label="Fixed rule M1 = 0.70")

    # demo pair markers
    demo_pairs = [
        (0.111, 0.9987, "Real photo (GT:real)"),
        (0.186, 0.9991, "Fake photo (GT:fake)"),
    ]
    for x0, y0, lbl in demo_pairs:
        ax.scatter(x0, y0, s=200, zorder=5, marker="*",
                   c="purple", edgecolors="black", linewidths=0.8)
        ax.annotate(lbl, (x0, y0), textcoords="offset points",
                    xytext=(8, 6), fontsize=8)

    from matplotlib.patches import Patch
    from matplotlib.lines   import Line2D
    legend_elements = [
        Patch(facecolor="green", alpha=0.5, label="Real"),
        Patch(facecolor="red",   alpha=0.5, label="Fake"),
        Line2D([0],[0], color="black",    ls="--", lw=1.5, label="Meta-model boundary"),
        Line2D([0],[0], color="steelblue",ls=":",  lw=1.5, label="Fixed rule M2=0.70"),
        Line2D([0],[0], color="orange",   ls=":",  lw=1.5, label="Fixed rule M1=0.70"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9)
    ax.set_xlabel("Model 1 real score (prithivMLmods)", fontsize=11)
    ax.set_ylabel("Model 2 real score (dima806)",        fontsize=11)
    ax.set_title("FaceGuard Meta-Model Decision Boundary\n"
                 "Green=Real, Red=Fake, Black dashed=learned boundary, "
                 "Blue/Orange dotted=fixed rule",
                 fontsize=11)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    plt.tight_layout()
    plt.savefig(PLOT_PATH, dpi=150)
    print(f"[SAVED] Decision boundary plot -> {PLOT_PATH}")
    print("="*70)


if __name__ == "__main__":
    main()
