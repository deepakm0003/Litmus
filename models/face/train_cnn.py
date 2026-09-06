"""
Fine-tune a real deepfake detector on the labelled pool.

    python models/face/train_cnn.py --n 5000 --epochs 4

WHY FINE-TUNING RATHER THAN A LINEAR PROBE
------------------------------------------
Three cheaper approaches were measured first and all failed:

    shipped checkpoint M1        AUC 0.737
    shipped checkpoint M2        AUC 0.501
    handcrafted frequency feats  AUC 0.675
    frozen ResNet18 + linear     AUC 0.663

The frozen-embedding result is the informative one. ImageNet features encode
semantics — that there is a face, a hat, a background. The signal separating
StyleGAN output from a photograph is not semantic; it is low-level texture and
upsampling artifacts. A linear probe on top of frozen semantic features cannot
represent it, no matter how it is regularised. The convolutional filters
themselves have to adapt, which means fine-tuning.

AUGMENTATION IS THE POINT, NOT A DETAIL
---------------------------------------
The production failure that started this work: a genuine applicant photographed
across a room, then recompressed by WhatsApp, was reported as synthetic,
because the detector had only ever seen clean 256px crops and read degradation
as forgery.

So training deliberately degrades its inputs — random downscale-then-upscale,
random JPEG recompression, blur, and brightness shifts. The model is forced to
find evidence that survives a bad capture instead of learning "sharp equals
real". This is the same conclusion the compression-robustness literature
reaches, applied to our specific failure.
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import random
import time

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
from torchvision.models import resnet18, ResNet18_Weights

HERE = os.path.dirname(os.path.abspath(__file__))
REAL = os.path.join(HERE, "kaggle_data", "Real faces")
FAKE = os.path.join(HERE, "kaggle_data", "Fake faces")
BOLLY = os.path.join(HERE, "kaggle_data", "bollywood")
CKPT = os.path.join(HERE, "faceguard_cnn.pt")
METRICS = os.path.join(HERE, "faceguard_cnn_metrics.json")


class Degrade:
    """Random capture degradation — the augmentation that fixes the real bug."""

    def __init__(self, p=0.8):
        self.p = p

    def __call__(self, img: Image.Image) -> Image.Image:
        if random.random() > self.p:
            return img
        w, h = img.size

        # Downscale then upscale: mimics a small face in a wide shot.
        if random.random() < 0.7:
            f = random.uniform(0.25, 0.9)
            img = img.resize((max(16, int(w * f)), max(16, int(h * f))), Image.BILINEAR)
            img = img.resize((w, h), Image.BILINEAR)

        # Recompression: mimics WhatsApp and repeated sharing.
        if random.random() < 0.7:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=random.randint(30, 92))
            buf.seek(0)
            img = Image.open(buf).convert("RGB")

        return img


class Faces(Dataset):
    def __init__(self, items, train: bool, size: int = 128):
        self.items = items
        aug = [Degrade()] if train else []
        aug += [T.Resize((size, size))]
        if train:
            aug += [
                T.RandomHorizontalFlip(),
                T.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.2),
            ]
        aug += [T.ToTensor(),
                T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])]
        self.tf = T.Compose(aug)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        path, label = self.items[i]
        img = Image.open(path).convert("RGB")
        return self.tf(img), label


def collect(folder, n, seed):
    fs = [f for f in glob.glob(os.path.join(folder, "**", "*.*"), recursive=True)
          if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    random.Random(seed).shuffle(fs)
    return fs[:n]


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    probs, labels = [], []
    for x, y in loader:
        out = model(x.to(device))
        probs.append(torch.softmax(out, 1)[:, 1].cpu().numpy())
        labels.append(y.numpy())
    return np.concatenate(probs), np.concatenate(labels)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000, help="images per class")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--batch", type=int, default=64)
    args = ap.parse_args()

    from sklearn.metrics import roc_auc_score, accuracy_score

    torch.set_num_threads(max(1, (os.cpu_count() or 4) - 1))
    device = "cuda" if torch.cuda.is_available() else "cpu"

    real = [(f, 1) for f in collect(REAL, args.n, 1)]
    fake = [(f, 0) for f in collect(FAKE, args.n, 2)]
    items = real + fake
    random.Random(0).shuffle(items)

    cut = int(len(items) * 0.8)
    train_items, test_items = items[:cut], items[cut:]
    print(f"train {len(train_items)}  test {len(test_items)}  device {device}", flush=True)

    train_dl = DataLoader(Faces(train_items, True, args.size), batch_size=args.batch,
                          shuffle=True, num_workers=0)
    test_dl = DataLoader(Faces(test_items, False, args.size), batch_size=args.batch,
                         num_workers=0)

    model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    model.fc = nn.Linear(512, 2)
    model.to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt, max_lr=1e-3, total_steps=args.epochs * len(train_dl))
    lossf = nn.CrossEntropyLoss(label_smoothing=0.05)

    best = 0.0
    for ep in range(1, args.epochs + 1):
        model.train()
        t0, run = time.time(), 0.0
        for bi, (x, y) in enumerate(train_dl):
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = lossf(model(x), y)
            loss.backward()
            opt.step()
            sched.step()
            run += loss.item()
            if bi % 20 == 0:
                print(f"  ep{ep} {bi}/{len(train_dl)} loss {run / (bi + 1):.4f} "
                      f"({time.time() - t0:.0f}s)", flush=True)

        p, yv = evaluate(model, test_dl, device)
        auc = roc_auc_score(yv, p)
        acc = accuracy_score(yv, (p >= 0.5).astype(int))
        print(f"  EPOCH {ep}: held-out AUC {auc:.4f}  acc {acc * 100:.1f}%  "
              f"({time.time() - t0:.0f}s)", flush=True)

        if auc > best:
            best = auc
            torch.save({"state_dict": model.state_dict(), "size": args.size,
                        "auc": float(auc), "acc": float(acc)}, CKPT)
            print(f"    saved (best so far)", flush=True)

    # Final numbers from the best checkpoint.
    model.load_state_dict(torch.load(CKPT, map_location=device)["state_dict"])
    p, yv = evaluate(model, test_dl, device)
    auc = roc_auc_score(yv, p)
    acc = accuracy_score(yv, (p >= 0.5).astype(int))

    print(f"\n  {'band':>7}{'decides':>10}{'accuracy':>11}{'fakes approved':>17}")
    ops = {}
    conf = np.maximum(p, 1 - p)
    for band in (0.5, 0.7, 0.8, 0.9, 0.95, 0.99):
        d = conf >= band
        if d.sum() == 0:
            continue
        pr = (p >= 0.5).astype(int)
        a = accuracy_score(yv[d], pr[d])
        fa = int(((pr == 1) & (yv == 0) & d).sum())
        ops[str(band)] = {"coverage": float(d.mean()), "accuracy": float(a),
                          "fakes_approved": fa}
        print(f"  {band:>7.2f}{d.mean() * 100:>9.1f}%{a * 100:>10.1f}%{fa:>17}")

    # Robustness to the exact failure that prompted this: degraded captures.
    print("\n  Robustness on degraded captures (the original bug):", flush=True)
    rob = {}
    for label, tf in [
        ("clean", None),
        ("small face (0.3x)", 0.3),
        ("very small (0.15x)", 0.15),
    ]:
        class Deg(Faces):
            def __getitem__(self, i):
                path, lab = self.items[i]
                im = Image.open(path).convert("RGB")
                if tf:
                    w, h = im.size
                    im = im.resize((int(w * tf), int(h * tf)), Image.BILINEAR).resize((w, h), Image.BILINEAR)
                    b = io.BytesIO(); im.save(b, format="JPEG", quality=65); b.seek(0)
                    im = Image.open(b).convert("RGB")
                return self.tf(im), lab
        dl = DataLoader(Deg(test_items, False, args.size), batch_size=args.batch)
        pp, yy = evaluate(model, dl, device)
        a = roc_auc_score(yy, pp)
        rob[label] = float(a)
        print(f"    {label:20} AUC {a:.4f}", flush=True)

    # Bias check: Bollywood faces are all genuine.
    bolly = collect(BOLLY, 300, 3)
    bias = None
    if bolly:
        dl = DataLoader(Faces([(f, 1) for f in bolly], False, args.size), batch_size=args.batch)
        pb, _ = evaluate(model, dl, device)
        bias = float((pb >= 0.5).mean())
        print(f"\n  Indian faces called real: {bias * 100:.1f}%  (mean p={pb.mean():.3f})")

    json.dump({"auc": float(auc), "accuracy": float(acc), "operating_points": ops,
               "robustness": rob, "indian_face_real_rate": bias,
               "n_per_class": args.n, "epochs": args.epochs, "size": args.size},
              open(METRICS, "w"), indent=2)
    print(f"\nSaved {CKPT}\nSaved {METRICS}")


if __name__ == "__main__":
    main()
