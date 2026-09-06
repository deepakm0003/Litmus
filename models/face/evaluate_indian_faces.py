"""
Section 3.3 — Indian/South-Asian demographic evaluation
Tests ensemble on:
  - 15 real Indian celebrity faces (Bollywood dataset, diverse celebrities + genders)
  - 15 AI-generated faces (140k StyleGAN fakes — demographically agnostic)

Purpose: Check whether the model has demographic bias on Indian faces.
Expected baseline from 140k eval: ~85-90% real accuracy, ~80%+ fake detection.
If Indian real accuracy drops significantly → document bias, don't hide it.
"""

import os, random
from pathlib import Path
from test_face        import run_face_detection
from test_face_model2 import run_face_detection_model2
from fuse_face_verdict import fuse_face_verdict

BOLL_DIR  = Path("kaggle_data/bollywood")
FAKE_DIR  = Path("kaggle_data/Fake faces")
N_SAMPLES = 15

random.seed(42)  # reproducible sample

# ── sample collection ─────────────────────────────────────────────────────────

def pick_indian_real(n=15):
    """Pick n real faces spread across celebrities and genders."""
    all_celebs = []
    for subdir in BOLL_DIR.glob("bollywood_celeb_faces*"):
        for celeb_dir in subdir.iterdir():
            if celeb_dir.is_dir():
                imgs = list(celeb_dir.glob("*.jpg")) + list(celeb_dir.glob("*.png"))
                if imgs:
                    all_celebs.append((celeb_dir.name, imgs))

    # Pick one image per celeb, up to n
    random.shuffle(all_celebs)
    selected = []
    for celeb_name, imgs in all_celebs[:n]:
        img = random.choice(imgs)
        selected.append((str(img), celeb_name))
    return selected


def pick_fake(n=15):
    """Pick n StyleGAN fake faces from 140k dataset."""
    fakes = list(FAKE_DIR.glob("*.png")) + list(FAKE_DIR.glob("*.jpg"))
    return [(str(f), "StyleGAN") for f in random.sample(fakes, min(n, len(fakes)))]


# ── evaluation ────────────────────────────────────────────────────────────────

def evaluate(path, ground_truth):
    r1 = run_face_detection(path)
    r2 = run_face_detection_model2(path)
    fused = fuse_face_verdict(r1, r2)

    if ground_truth == "real":
        correct = (fused["action"] == "auto-approve")
    else:
        correct = (fused["action"] == "route-to-review")

    return {
        "path":    path,
        "gt":      ground_truth,
        "m1_v":    r1["verdict"],  "m1_sc": r1["real_score"],
        "m2_v":    r2["verdict"],  "m2_sc": r2["real_score"],
        "fused":   fused["final_verdict"],
        "action":  fused["action"],
        "correct": correct,
    }


def print_table(rows, title):
    print(f"\n{'='*100}")
    print(f"  {title}")
    print(f"{'='*100}")
    print(f"  {'Label/File':<32} {'GT':<6} {'M1':<7} {'M2':<7} {'Fused':<10} {'Action':<20} OK")
    print(f"  {'-'*32}  {'-'*5}  {'-'*6} {'-'*6} {'-'*9} {'-'*19} --")

    for r in rows:
        label = Path(r["path"]).parent.name  # celeb name or "Fake faces"
        ok   = "✓" if r["correct"] else "✗"
        act  = "→ REVIEW" if "review" in r["action"] else "✓ APPROVE"
        print(f"  {label:<32} {r['gt']:<6} "
              f"{r['m1_v'].upper():<7} {r['m2_v'].upper():<7} "
              f"{r['fused'].upper():<10} {act:<20} {ok}")

    n  = len(rows)
    ok = sum(1 for r in rows if r["correct"])
    print(f"  {'─'*98}")
    print(f"  Correct: {ok}/{n}  ({ok/n*100:.0f}%)")

    # Single model breakdown
    m1_ok = sum(1 for r in rows if r["m1_v"] == r["gt"])
    m2_ok = sum(1 for r in rows if r["m2_v"] == r["gt"])
    print(f"  M1 standalone: {m1_ok}/{n} ({m1_ok/n*100:.0f}%)   "
          f"M2 standalone: {m2_ok}/{n} ({m2_ok/n*100:.0f}%)")
    return ok, n


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Selecting samples...")
    indian_real = pick_indian_real(N_SAMPLES)
    ai_fakes    = pick_fake(N_SAMPLES)

    print(f"  Indian real: {len(indian_real)} samples from {len(set(c for _,c in indian_real))} celebrities")
    print(f"  StyleGAN fake: {len(ai_fakes)} samples")

    print("\n>>> Evaluating Indian real faces...")
    real_rows = []
    for path, celeb in indian_real:
        print(f"  {celeb}")
        real_rows.append(evaluate(path, "real"))

    print("\n>>> Evaluating AI-generated fakes...")
    fake_rows = []
    for path, _ in ai_fakes:
        fake_rows.append(evaluate(path, "fake"))

    r_ok, r_n = print_table(real_rows, "INDIAN REAL FACES — Bollywood celebrities")
    f_ok, f_n = print_table(fake_rows, "AI FAKES — StyleGAN (140k dataset)")

    # ── comparison vs global baseline ────────────────────────────────────────
    print(f"\n{'='*70}")
    print("  DEMOGRAPHIC COMPARISON")
    print(f"{'='*70}")
    print(f"  {'Group':<35} {'Real acc':>9}  {'Fake acc':>9}")
    print(f"  {'-'*35}  {'-'*9}  {'-'*9}")
    print(f"  {'Global 140k baseline (prior eval)':<35} {'~85%':>9}  {'~80%':>9}")
    print(f"  {'Indian faces (this eval)':<35} {r_ok/r_n*100:>8.0f}%  {f_ok/f_n*100:>8.0f}%")
    print(f"{'='*70}")

    real_acc = r_ok/r_n*100
    if real_acc >= 75:
        print(f"\n  ✓ No significant demographic bias on Indian real faces ({real_acc:.0f}%)")
        print(f"    Write in deck: 'Model performs consistently across South Asian faces'")
    elif real_acc >= 55:
        print(f"\n  ⚠ Modest accuracy gap on Indian faces ({real_acc:.0f}% vs ~85% global)")
        print(f"    Write in deck: 'Slight accuracy reduction on South Asian faces ({real_acc:.0f}%)'")
        print(f"    'Noted for future fine-tuning on demographically diverse training data'")
    else:
        print(f"\n  ✗ Significant bias on Indian faces ({real_acc:.0f}%)")
        print(f"    Do NOT claim demographic fairness — document the gap honestly")
        print(f"    Write in deck: 'Model shows demographic bias on South Asian faces'")
        print(f"    'Current accuracy {real_acc:.0f}% vs global {85}% — requires further training'")
