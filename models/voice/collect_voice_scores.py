"""
Score Kaggle voice clips with the voice model and save [score, label] CSV.
Handles two dataset layouts:
  split  — real/ and fake/ sibling directories
  paired — per-speaker folders containing original.m4a (real) + synthetic*.mp3 (fake)
"""

import os, sys, csv, time, traceback

KAGGLE_ROOT   = os.path.join(os.path.dirname(__file__), "kaggle_data")
SCORES_CSV    = os.path.join(os.path.dirname(__file__), "voice_meta_training_data.csv")
MAX_PER_CLASS = 60

sys.path.insert(0, os.path.dirname(__file__))
from test_voice import run_voice_detection

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


# ─── structure detection ──────────────────────────────────────────────────────

def find_structure(root):
    """
    Returns ("split", real_dir, fake_dir) or ("paired", root, None).
    """
    # 1. Look for real/ + fake/ siblings anywhere in the tree
    for dirpath, dirnames, _ in os.walk(root):
        low = {d.lower(): d for d in dirnames}
        if "real" in low and "fake" in low:
            rd = os.path.join(dirpath, low["real"])
            fd = os.path.join(dirpath, low["fake"])
            if any(os.path.splitext(f)[1].lower() in AUDIO_EXTS for f in os.listdir(rd)):
                return "split", rd, fd

    # 2. Per-speaker folders with original + synthetic files
    for dirpath, _, files in os.walk(root):
        fl = [f.lower() for f in files]
        if any("original" in f for f in fl) and any("synthetic" in f for f in fl):
            return "paired", root, None

    return "unknown", None, None


# ─── collectors ───────────────────────────────────────────────────────────────

def score_file(fpath, label, writer, idx):
    fname = os.path.basename(fpath)
    try:
        r = run_voice_detection(fpath)
        writer.writerow({"filename": fname, "true_label": label,
                         "real_score": round(r["real_score"], 6)})
        tag = "REAL" if label == 1 else "FAKE"
        v   = r["verdict"].upper()[:1]
        print(f"  [{idx:3d}] {tag} {fname[:40]:40s}  score={r['real_score']:.3f}({v})")
        return True
    except Exception:
        print(f"  [ERR] {fname}: {traceback.format_exc(limit=1).strip()}")
        return False


def collect_split(real_dir, fake_dir, max_n, writer):
    files_r = [f for f in os.listdir(real_dir)
               if os.path.splitext(f)[1].lower() in AUDIO_EXTS][:max_n]
    files_f = [f for f in os.listdir(fake_dir)
               if os.path.splitext(f)[1].lower() in AUDIO_EXTS][:max_n]

    n_real = sum(score_file(os.path.join(real_dir, f), 1, writer, i+1)
                 for i, f in enumerate(files_r))
    n_fake = sum(score_file(os.path.join(fake_dir, f), 0, writer, n_real+i+1)
                 for i, f in enumerate(files_f))
    return n_real, n_fake


def collect_paired(root, max_real, max_fake, writer):
    n_real = n_fake = 0
    for dirpath, _, files in os.walk(root):
        low = {f.lower(): f for f in files}
        orig   = next((f for fl, f in low.items() if "original" in fl), None)
        synths = [f for fl, f in low.items()
                  if "synthetic" in fl and os.path.splitext(fl)[1] in AUDIO_EXTS]

        if orig and n_real < max_real:
            if score_file(os.path.join(dirpath, orig), 1, writer, n_real+n_fake+1):
                n_real += 1

        for syn in synths[:1]:
            if n_fake >= max_fake:
                break
            if score_file(os.path.join(dirpath, syn), 0, writer, n_real+n_fake+1):
                n_fake += 1

    return n_real, n_fake


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print("="*70)
    print("VOICE SCORE COLLECTION — Kaggle dataset")
    print("="*70)

    if not os.path.isdir(KAGGLE_ROOT):
        print(f"[ERROR] Kaggle data folder not found: {KAGGLE_ROOT}")
        sys.exit(1)

    structure, real_dir, fake_dir = find_structure(KAGGLE_ROOT)

    if structure == "unknown":
        print("[ERROR] Could not detect dataset structure. Tree:")
        for root, dirs, _ in os.walk(KAGGLE_ROOT):
            if root.count(os.sep) - KAGGLE_ROOT.count(os.sep) < 4:
                print(f"  {root}/  {dirs[:6]}")
        sys.exit(1)

    print(f"Structure detected : {structure}")
    print(f"Max per class      : {MAX_PER_CLASS}")
    print(f"Output CSV         : {SCORES_CSV}")
    print("="*70)

    t0 = time.time()
    with open(SCORES_CSV, "w", newline="") as f:
        fields = ["filename", "true_label", "real_score"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        if structure == "paired":
            print("\n[PAIRED] real=original.m4a  fake=synthetic*.mp3  per speaker folder")
            n_real, n_fake = collect_paired(KAGGLE_ROOT, MAX_PER_CLASS, MAX_PER_CLASS, writer)
        else:
            print(f"\n[REAL] {real_dir}")
            print(f"[FAKE] {fake_dir}")
            n_real, n_fake = collect_split(real_dir, fake_dir, MAX_PER_CLASS, writer)

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"[DONE]  {n_real} real + {n_fake} fake = {n_real+n_fake} total samples")
    print(f"        Elapsed : {elapsed/60:.1f} min")
    print(f"        CSV     : {SCORES_CSV}")
    print("="*70)


if __name__ == "__main__":
    main()
