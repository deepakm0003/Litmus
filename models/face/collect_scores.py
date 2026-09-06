"""
Score Kaggle face images with both models and save [m1_score, m2_score, label] CSV.
Run this once after the Kaggle download; train_meta_model.py reads the CSV.
"""

import os, sys, csv, time, traceback
import numpy as np

# Detect kaggle dataset folder structure automatically
KAGGLE_ROOT = os.path.join(os.path.dirname(__file__), "kaggle_data")
SCORES_CSV   = os.path.join(os.path.dirname(__file__), "meta_training_data.csv")
MAX_PER_CLASS = 60   # 60 real + 60 fake = 120 samples; enough for a robust LR

sys.path.insert(0, os.path.dirname(__file__))
from test_face   import run_face_detection
from test_face_model2 import run_face_detection_model2


def find_real_fake_dirs(root):
    """
    Walk root and return (real_dir, fake_dir).
    Matches any folder whose lowercase name CONTAINS 'real' or 'fake' —
    handles 'Real faces', 'Fake faces', 'REAL', 'fake' etc.
    """
    for dirpath, dirnames, _ in os.walk(root):
        real_match = next((d for d in dirnames if 'real' in d.lower()), None)
        fake_match = next((d for d in dirnames if 'fake' in d.lower()), None)
        if real_match and fake_match:
            real_dir = os.path.join(dirpath, real_match)
            fake_dir = os.path.join(dirpath, fake_match)
            exts = {".jpg", ".jpeg", ".png"}
            if any(os.path.splitext(f)[1].lower() in exts
                   for f in os.listdir(real_dir)):
                return real_dir, fake_dir
    return None, None


def collect(image_dir, label, max_n, writer, done_count):
    """Score up to max_n images from image_dir, write rows, return count scored."""
    exts = {".jpg", ".jpeg", ".png"}
    files = [f for f in os.listdir(image_dir)
             if os.path.splitext(f)[1].lower() in exts][:max_n]

    scored = 0
    for i, fname in enumerate(files, 1):
        fpath = os.path.join(image_dir, fname)
        try:
            r1 = run_face_detection(fpath)
            r2 = run_face_detection_model2(fpath)
            writer.writerow({
                "filename":     fname,
                "true_label":   label,
                "m1_real_score": round(r1["real_score"], 6),
                "m2_real_score": round(r2["real_score"], 6),
            })
            scored += 1
            tag = "REAL" if label == 1 else "FAKE"
            m1v = r1["verdict"].upper()[:1]
            m2v = r2["verdict"].upper()[:1]
            print(f"  [{done_count+scored:3d}] {tag} {fname[:30]:30s}  "
                  f"M1={r1['real_score']:.3f}({m1v})  M2={r2['real_score']:.3f}({m2v})")
        except Exception:
            print(f"  [ERR] {fname}: {traceback.format_exc(limit=1).strip()}")
    return scored


def main():
    print("="*70)
    print("FACE SCORE COLLECTION — Kaggle dataset")
    print("="*70)

    if not os.path.isdir(KAGGLE_ROOT):
        print(f"[ERROR] Kaggle data folder not found: {KAGGLE_ROOT}")
        sys.exit(1)

    real_dir, fake_dir = find_real_fake_dirs(KAGGLE_ROOT)
    if real_dir is None:
        print("[ERROR] Could not locate real/ and fake/ sub-folders inside:")
        for root, dirs, _ in os.walk(KAGGLE_ROOT):
            print(f"  {root}/  subdirs={dirs[:6]}")
        sys.exit(1)

    print(f"real dir : {real_dir}")
    print(f"fake dir : {fake_dir}")
    print(f"Max per class: {MAX_PER_CLASS}")
    print(f"Output CSV: {SCORES_CSV}")
    print("="*70)

    t0 = time.time()
    with open(SCORES_CSV, "w", newline="") as f:
        fields = ["filename", "true_label", "m1_real_score", "m2_real_score"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        print(f"\n[REAL] Scoring up to {MAX_PER_CLASS} real images...")
        n_real = collect(real_dir, 1, MAX_PER_CLASS, writer, 0)

        print(f"\n[FAKE] Scoring up to {MAX_PER_CLASS} fake images...")
        n_fake = collect(fake_dir, 0, MAX_PER_CLASS, writer, n_real)

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"[DONE] {n_real} real + {n_fake} fake = {n_real+n_fake} samples")
    print(f"       Elapsed: {elapsed/60:.1f} min")
    print(f"       CSV saved: {SCORES_CSV}")
    print("="*70)


if __name__ == "__main__":
    main()
