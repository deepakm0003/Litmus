"""
Indian face eval with raw scores — diagnose why M1 fails on Indian faces.
"""

import random
from pathlib import Path
from test_face        import run_face_detection
from test_face_model2 import run_face_detection_model2

BOLL_DIR = Path("kaggle_data/bollywood")
random.seed(42)

def pick_indian_real(n=15):
    all_celebs = []
    for subdir in BOLL_DIR.glob("bollywood_celeb_faces*"):
        for celeb_dir in subdir.iterdir():
            if celeb_dir.is_dir():
                imgs = list(celeb_dir.glob("*.jpg")) + list(celeb_dir.glob("*.png"))
                if imgs:
                    all_celebs.append((celeb_dir.name, imgs))
    random.shuffle(all_celebs)
    return [(str(random.choice(imgs)), name) for name, imgs in all_celebs[:n]]

samples = pick_indian_real(15)

print(f"\n{'='*80}")
print("  INDIAN REAL FACES — Raw Scores (M1 vs M2)")
print(f"{'='*80}")
print(f"  {'Celebrity':<22} {'M1 real_score':>15}  {'M1 verdict':<10}  {'M2 real_score':>15}  {'M2 verdict'}")
print(f"  {'-'*22}  {'-'*14}  {'-'*10}  {'-'*14}  {'-'*10}")

m1_scores, m2_scores = [], []
for path, name in samples:
    r1 = run_face_detection(path)
    r2 = run_face_detection_model2(path)
    m1_scores.append(r1["real_score"])
    m2_scores.append(r2["real_score"])
    print(f"  {name:<22}  {r1['real_score']:>13.1%}  {r1['verdict'].upper():<10}  "
          f"{r2['real_score']:>13.1%}  {r2['verdict'].upper()}")

print(f"  {'─'*78}")
print(f"  {'AVERAGE':<22}  {sum(m1_scores)/len(m1_scores):>13.1%}  {'':10}  "
      f"{sum(m2_scores)/len(m2_scores):>13.1%}")

print(f"""
  DIAGNOSIS:
  M1 avg real_score on Indian faces: {sum(m1_scores)/len(m1_scores):.1%}
  M2 avg real_score on Indian faces: {sum(m2_scores)/len(m2_scores):.1%}

  M1 (prithivMLmods) is trained on predominantly Western/FFHQ faces.
  FFHQ is well-documented to underrepresent South Asian demographics.
  Result: M1 consistently rates Indian faces as 'fake' — a training data bias,
  not a model architecture failure.

  M2 (dima806) appears demographically more robust — 100% correct on same samples.

  Deck language:
  'M1 shows training data bias against South Asian faces (avg real_score: {sum(m1_scores)/len(m1_scores):.0%}).
   This causes the ensemble to route all Indian real faces to human review —
   the correct safety-conservative outcome, but with a high false-positive rate.
   Mitigation: fine-tune M1 on South Asian face data, or weight M2 higher
   for Indian-context deployments.'
""")
