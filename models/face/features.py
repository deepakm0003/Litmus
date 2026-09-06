"""
Frequency-domain and capture-quality features for face forensics.

WHY THIS EXISTS
---------------
The shipped checkpoints are semantic classifiers, and we measured that Model 1's
score falls with face resolution on an identical face — it is partly reading
capture quality rather than synthesis. Two things follow: we need signal that
does not come from those checkpoints, and we need to give the classifier the
quality variables explicitly so it can account for them instead of confusing
them with evidence.

WHAT THE LITERATURE SAYS
------------------------
Generative upsampling leaves periodic artifacts. FFT spectra of GAN output carry
less high-frequency energy than camera output, and DCT spectra show grid-like
structure (BiHPF, WACV 2022; FrePGAN; F3-Net, which separates frequency bands via
DCT specifically for robustness on compressed video). FSBI (Image and Vision
Computing, 2025) extends self-blended-image training with discrete wavelet
transforms, reporting wavelet sub-band energy as discriminative.

None of that requires training a network, which matters here: these are cheap,
deterministic, and computable on thousands of images in minutes.

WHAT IS EXTRACTED
-----------------
  spectral    radial FFT energy profile, high/low frequency ratio, spectral
              slope — the GAN upsampling signature
  dct         block-DCT coefficient statistics, including the 8x8 grid energy
              that JPEG and generative upsampling both disturb
  wavelet     Haar sub-band energies (LH/HL/HH), implemented directly since
              PyWavelets is not installed
  quality     Laplacian variance (blur), JPEG blockiness, noise estimate,
              resolution — the confounds, supplied as features so the model can
              condition on them rather than be fooled by them
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
from PIL import Image
from scipy import fftpack

FEATURE_NAMES: List[str] = []


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 3:
        return (0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2])
    return img.astype(np.float64)


def _radial_profile(power: np.ndarray, bins: int = 24) -> np.ndarray:
    """Azimuthally averaged power spectrum — the standard GAN-fingerprint view."""
    h, w = power.shape
    cy, cx = h // 2, w // 2
    y, x = np.indices((h, w))
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    r_max = r.max()
    idx = np.clip((r / r_max * bins).astype(int), 0, bins - 1)

    profile = np.zeros(bins)
    for b in range(bins):
        m = idx == b
        profile[b] = power[m].mean() if m.any() else 0.0
    return profile


# ---------------------------------------------------------------------------
# feature blocks
# ---------------------------------------------------------------------------

def spectral_features(gray: np.ndarray) -> Dict[str, float]:
    """FFT-domain descriptors. GAN output carries less high-frequency energy."""
    g = gray - gray.mean()
    win = np.outer(np.hanning(g.shape[0]), np.hanning(g.shape[1]))
    spec = np.abs(fftpack.fftshift(fftpack.fft2(g * win)))
    power = np.log1p(spec ** 2)

    prof = _radial_profile(power)
    prof_n = prof / (prof.sum() + 1e-9)

    n = len(prof_n)
    low = prof_n[: n // 3].sum()
    mid = prof_n[n // 3: 2 * n // 3].sum()
    high = prof_n[2 * n // 3:].sum()

    # Slope of log power vs log radius — camera noise and generative upsampling
    # fall off at different rates.
    radii = np.arange(1, n + 1)
    slope = np.polyfit(np.log(radii), np.log(prof + 1e-9), 1)[0]

    out = {
        "fft_low": low,
        "fft_mid": mid,
        "fft_high": high,
        "fft_high_low_ratio": high / (low + 1e-9),
        "fft_slope": slope,
        "fft_profile_std": float(prof_n.std()),
    }
    for i in range(0, n, 3):          # coarse profile shape
        out[f"fft_r{i}"] = float(prof_n[i])
    return out


def dct_features(gray: np.ndarray) -> Dict[str, float]:
    """Block-DCT statistics — sensitive to JPEG blocking and upsampling grids."""
    h, w = gray.shape
    h8, w8 = (h // 8) * 8, (w // 8) * 8
    g = gray[:h8, :w8]
    if h8 < 8 or w8 < 8:
        return {"dct_mean": 0.0, "dct_std": 0.0, "dct_hf_ratio": 0.0, "dct_grid": 0.0}

    blocks = g.reshape(h8 // 8, 8, w8 // 8, 8).transpose(0, 2, 1, 3).reshape(-1, 8, 8)
    d = fftpack.dct(fftpack.dct(blocks, axis=1, norm="ortho"), axis=2, norm="ortho")
    a = np.abs(d)

    lo = a[:, :3, :3].mean()
    hi = a[:, 4:, 4:].mean()
    return {
        "dct_mean": float(a.mean()),
        "dct_std": float(a.std()),
        "dct_hf_ratio": float(hi / (lo + 1e-9)),
        "dct_grid": float(a[:, 0, 0].std() / (a[:, 0, 0].mean() + 1e-9)),
    }


def _haar(a: np.ndarray):
    """One level of Haar DWT. Written out because PyWavelets is unavailable."""
    h, w = a.shape
    a = a[: (h // 2) * 2, : (w // 2) * 2]
    e, o = a[:, 0::2], a[:, 1::2]
    lo, hi = (e + o) / np.sqrt(2), (e - o) / np.sqrt(2)
    ll, hl = (lo[0::2] + lo[1::2]) / np.sqrt(2), (lo[0::2] - lo[1::2]) / np.sqrt(2)
    lh, hh = (hi[0::2] + hi[1::2]) / np.sqrt(2), (hi[0::2] - hi[1::2]) / np.sqrt(2)
    return ll, lh, hl, hh


def wavelet_features(gray: np.ndarray) -> Dict[str, float]:
    """Haar sub-band energies over two levels — the FSBI-style descriptor."""
    out, cur = {}, gray
    for lvl in (1, 2):
        if min(cur.shape) < 4:
            break
        ll, lh, hl, hh = _haar(cur)
        tot = np.sum(ll ** 2) + np.sum(lh ** 2) + np.sum(hl ** 2) + np.sum(hh ** 2) + 1e-9
        out[f"dwt{lvl}_lh"] = float(np.sum(lh ** 2) / tot)
        out[f"dwt{lvl}_hl"] = float(np.sum(hl ** 2) / tot)
        out[f"dwt{lvl}_hh"] = float(np.sum(hh ** 2) / tot)
        out[f"dwt{lvl}_hh_std"] = float(hh.std())
        cur = ll
    return out


def quality_features(gray: np.ndarray, rgb: np.ndarray) -> Dict[str, float]:
    """
    The confounds, made explicit.

    Supplying resolution and compression as inputs lets the classifier learn
    "low-resolution AND low model score" means low resolution, rather than
    treating the degraded score as evidence of forgery.
    """
    lap = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
    from scipy.signal import convolve2d
    edges = convolve2d(gray, lap, mode="valid")

    # Blockiness: 8-pixel-boundary discontinuity relative to interior.
    h, w = gray.shape
    bh = np.abs(np.diff(gray, axis=0))
    bv = np.abs(np.diff(gray, axis=1))
    block_h = bh[7::8].mean() if bh.shape[0] > 8 else 0.0
    block_v = bv[:, 7::8].mean() if bv.shape[1] > 8 else 0.0

    return {
        "q_lap_var": float(edges.var()),
        "q_blockiness": float((block_h + block_v) / 2 / (bh.mean() + bv.mean() + 1e-9)),
        "q_width": float(w),
        "q_height": float(h),
        "q_pixels": float(np.log1p(w * h)),
        "q_noise": float(np.median(np.abs(edges)) / 0.6745),
        "q_sat_mean": float(rgb.std(axis=2).mean()),
        "q_luma_std": float(gray.std()),
    }


# ---------------------------------------------------------------------------
# public entry point
# ---------------------------------------------------------------------------

def extract(path_or_image, size: int = 256) -> Dict[str, float]:
    """Full feature vector for one image. Never raises on a bad file."""
    try:
        img = (Image.open(path_or_image) if isinstance(path_or_image, str)
               else path_or_image).convert("RGB")
    except Exception:
        return {}

    orig_w, orig_h = img.size
    work = img.resize((size, size), Image.LANCZOS) if img.size != (size, size) else img
    rgb = np.asarray(work, dtype=np.float64)
    gray = _gray(rgb)

    feats: Dict[str, float] = {}
    feats.update(spectral_features(gray))
    feats.update(dct_features(gray))
    feats.update(wavelet_features(gray))
    feats.update(quality_features(gray, rgb))

    # True capture size, not the resampled working size.
    feats["q_width"] = float(orig_w)
    feats["q_height"] = float(orig_h)
    feats["q_pixels"] = float(np.log1p(orig_w * orig_h))

    return {k: (0.0 if not np.isfinite(v) else float(v)) for k, v in feats.items()}
