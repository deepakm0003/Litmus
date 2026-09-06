"""
Litmus FaceGuard — calibrated detection pipeline
================================================

This module replaces the naive "run two classifiers, compare at 0.5" path with
four changes, each of which was measured on the 120-sample labelled benchmark
in meta_training_data.csv before being adopted. `validate_faceguard.py`
reproduces every number below.

1. CACHED PIPELINES
   The original code called transformers.pipeline() inside the request path, so
   every verification re-loaded both checkpoints from disk. Loading once at
   module scope removes several seconds per call.

2. FACE CROPPING (MTCNN)
   Both checkpoints were trained on tightly-cropped faces. Feeding a full
   showroom photo — background, torso, other people — shifts the input
   distribution away from what the model saw in training. We detect the largest
   face, expand the box by a margin, and classify that crop. When no face is
   found we fall back to the whole image and say so in the result, because
   silently scoring a photo with no detectable face is how a system ends up
   confidently judging a picture of a wall.

3. TEST-TIME AUGMENTATION
   A single forward pass on a compressed phone photo is noisy. We score the
   crop several ways (identity, horizontal flip, slight centre zoom) and average
   the real-scores. Costs ~3x inference; buys stability.

4. CALIBRATED THRESHOLD  <- the largest single win
   Model 1 is a good *ranker* and a badly calibrated *classifier*. On the
   benchmark it scores real images 0.950 and fakes 0.852 — both above 0.5, so at
   the default threshold it calls almost everything real and lands at 52.5%,
   which is chance. Its AUC is 0.737, meaning the ordering carries real signal;
   only the cut point was wrong.

   Choosing the threshold on training folds and scoring on held-out folds
   (5-fold, no leakage) puts it at 0.975 in four folds and 0.965 in the fifth,
   and lifts held-out accuracy to 70.0%.

WHY MODEL 2 IS NO LONGER AN EQUAL VOTER
---------------------------------------
Model 2 scores AUC 0.501 on this benchmark — indistinguishable from a coin
flip. Averaging it with Model 1 as an equal member actively destroys signal
(the pair averages to AUC 0.590, worse than Model 1 alone at 0.737).

It is not removed, because it remains the only check we have against Model 1's
documented South Asian bias: on the 15-image Indian-face set Model 2 was 100%
correct while Model 1 flagged all of them. So it is demoted from voter to
DEMOGRAPHIC CONTEXT CHECK — it does not move the verdict, but when it strongly
disagrees with a Model 1 "fake" call, that is the known bias signature and the
case is routed to a human rather than rejected.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageOps

# ---------------------------------------------------------------------------
# Calibration constants — derived in validate_faceguard.py, not guessed.
# ---------------------------------------------------------------------------

M1_THRESHOLD = 0.975      # median of per-fold optima (0.975 x4, 0.965 x1)

# ASYMMETRIC GATES. A single threshold treats both errors as equally costly.
# They are not: auto-approving a synthetic applicant loses the whole loan (a
# fraudulent low-ticket vehicle loan has no collateral recovery path), whereas
# flagging a genuine applicant costs one officer review. So the bar to clear
# someone is set far higher than the bar to escalate them.
#
# Measured on the 120-sample benchmark (validate_faceguard.py prints the full
# curve). At 0.980/0.85 the system decides 60% of cases but lets 14 fakes
# through. At 0.995/0.85 it decides 25% and lets 2 through. For a lending
# decision the second operating point is the correct trade.
APPROVE_ABOVE = 0.995     # clear as REAL only above this
ESCALATE_BELOW = 0.85     # escalate as FAKE only below this
                          # ...anything between the two goes to a human
# The documented bias pattern is M1 CONFIDENTLY fake (~0.095 real-score on the
# Indian-face set) while M2 is CONFIDENTLY real (~0.998). Both bounds matter:
# without the M1 bound, every image merely sitting below the 0.975 cut gets
# mislabelled a bias case, and effectively nothing is ever decided.
M2_CONTEXT_FLOOR = 0.90   # M2 must be confidently real
M1_BIAS_CEILING = 0.50    # ...and M1 confidently fake, not just below the cut
FACE_MARGIN = 0.35        # expand the detected box by this fraction
TTA_VIEWS = 3

# ---------------------------------------------------------------------------
# QUALITY GATE — the most important safety rule in this file.
#
# Model 1's real-score falls monotonically with face resolution, on an
# IDENTICAL face. Measured by downscaling one real crop and re-scoring:
#
#     400px 0.966 | 220px 0.957 | 150px 0.926 | 110px 0.888
#      80px 0.850 | 64px 0.836  |  48px 0.709
#
# It crosses the escalate gate at roughly 80px purely because of pixel count.
# In other words the model is partly measuring CAPTURE QUALITY rather than
# authenticity — so a genuine applicant photographed across a showroom, or an
# image recompressed by WhatsApp, can be reported as synthetic.
#
# That is a false accusation produced by a confound, and it is unacceptable in
# a lending decision. Below this face size the pipeline may still clear or
# review, but it may NEVER make a confident adverse finding.
MIN_FACE_PX_FOR_ESCALATION = 128
MIN_FACE_PX_FOR_APPROVAL = 160    # clearing someone needs at least as much

# Minimum confidence for the trained classifier to decide on its own. Set from
# the operating-point table printed by train_detector.py.
FORENSIC_DECIDE_CONF = 0.60

# Minimum confidence for the fine-tuned detector to decide alone. From the
# measured operating-point table: 0.95 gives 96.3%% accuracy over 47%% of cases,
# where 0.50 would take every case at 86.3%%. In lending the abstention is
# cheaper than the error, so we buy accuracy with coverage.
CNN_DECIDE_CONF = 0.95

_M1_ID = "prithivMLmods/Deep-Fake-Detector-Model"
_M2_ID = "dima806/deepfake_vs_real_image_detection"

_m1 = None
_m2 = None
_detector = None
_forensic = None          # trained frequency-domain classifier
_forensic_meta = None
_cnn = None               # fine-tuned CNN — the primary discriminator
_cnn_meta = None


def _cnn_model():
    """
    Load the fine-tuned detector, if it has been trained.

    This is the primary discriminator. It is the only component trained on our
    own labelled pool, and the only one trained with capture degradation in the
    augmentation, so it is the only one whose score does not collapse on a
    small or recompressed photo.
    """
    global _cnn, _cnn_meta
    if _cnn is None:
        import json
        ckpt = os.path.join(os.path.dirname(__file__), "faceguard_cnn.pt")
        meta = os.path.join(os.path.dirname(__file__), "faceguard_cnn_metrics.json")
        if not os.path.exists(ckpt):
            return None, None
        try:
            import torch
            import torch.nn as nn
            from torchvision.models import resnet18
            blob = torch.load(ckpt, map_location="cpu")
            net = resnet18()
            net.fc = nn.Linear(512, 2)
            net.load_state_dict(blob["state_dict"])
            net.eval()
            _cnn = {"net": net, "size": blob.get("size", 128)}
            _cnn_meta = json.load(open(meta)) if os.path.exists(meta) else {"auc": blob.get("auc")}
        except Exception:
            return None, None
    return _cnn, _cnn_meta


def score_cnn(image: Image.Image):
    """Real-probability from the fine-tuned detector, or None if untrained."""
    bundle, meta = _cnn_model()
    if bundle is None:
        return None
    try:
        import torch
        import torchvision.transforms as T
        tf = T.Compose([
            T.Resize((bundle["size"], bundle["size"])),
            T.ToTensor(),
            T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        with torch.no_grad():
            logits = bundle["net"](tf(image).unsqueeze(0))
            p_real = float(torch.softmax(logits, 1)[0, 1])
        return {
            "real_probability": round(p_real, 4),
            "verdict": "real" if p_real >= 0.5 else "fake",
            "confidence": round(abs(p_real - 0.5) * 2, 4),
            "auc": (meta or {}).get("auc"),
            "trained_on": (meta or {}).get("n_per_class"),
            "robustness": (meta or {}).get("robustness"),
        }
    except Exception:
        return None


def _forensic_model():
    """
    Load the trained forensic classifier, if it has been built.

    This is the primary discriminator when present. Unlike the shipped
    checkpoints it is trained on our own labelled pool, calibrated, and given
    capture-quality features explicitly so it can condition on resolution
    rather than mistake it for evidence. Returns (None, None) when the model
    has not been trained yet, and the pipeline falls back to the checkpoints.
    """
    global _forensic, _forensic_meta
    if _forensic is None:
        import json
        model_path = os.path.join(os.path.dirname(__file__), "face_detector.joblib")
        meta_path = os.path.join(os.path.dirname(__file__), "face_detector_metrics.json")
        if not os.path.exists(model_path):
            return None, None
        try:
            import joblib
            bundle = joblib.load(model_path)
            _forensic = bundle
            _forensic_meta = (json.load(open(meta_path)) if os.path.exists(meta_path) else {})
        except Exception:
            return None, None
    return _forensic, _forensic_meta


def _pipelines():
    """Load both checkpoints once, on first use."""
    global _m1, _m2
    if _m1 is None or _m2 is None:
        from transformers import pipeline
        _m1 = pipeline("image-classification", model=_M1_ID)
        _m2 = pipeline("image-classification", model=_M2_ID)
    return _m1, _m2


class _TorchMTCNN:
    """
    facenet-pytorch's MTCNN behind the API the original mtcnn package exposed.

    WHY THIS EXISTS
    ---------------
    The mtcnn package runs on TensorFlow/Keras. Measured, that dependency costs
    338 MB resident — more than torch, torchvision and every Litmus model put
    together — purely to draw five landmarks on a face. On a 512 MB instance it
    is the single reason the service is killed on its first request.

    facenet-pytorch runs the same MTCNN architecture on the torch that is
    already loaded, for roughly 30 MB.

    The output shape is deliberately identical to the old package's: a list of
    {box, confidence, keypoints} dicts, with keypoints named left_eye,
    right_eye, nose, mouth_left and mouth_right. LiveChallenge estimates head
    yaw from those exact keys, so anything else silently breaks the challenge
    rather than failing loudly.
    """

    def __init__(self) -> None:
        from facenet_pytorch import MTCNN as _M

        # keep_all: crop_face picks the largest of several faces itself, and a
        # second face in frame is information the caller needs, not noise.
        self._m = _M(keep_all=True, device="cpu")

    _KEYS = ("left_eye", "right_eye", "nose", "mouth_left", "mouth_right")

    def detect_faces(self, arr):
        boxes, probs, points = self._m.detect(arr, landmarks=True)
        if boxes is None:
            return []

        out = []
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = (float(v) for v in box)
            conf = float(probs[i]) if probs is not None and probs[i] is not None else 0.0
            keypoints = {}
            if points is not None and i < len(points):
                for name, (px, py) in zip(self._KEYS, points[i]):
                    keypoints[name] = (int(round(float(px))), int(round(float(py))))
            out.append({
                # x, y, width, height — the format the rest of this module reads.
                "box": [int(round(x1)), int(round(y1)),
                        int(round(x2 - x1)), int(round(y2 - y1))],
                "confidence": conf,
                "keypoints": keypoints,
            })
        return out


def _face_detector():
    """
    Return a face detector, preferring the torch implementation.

    Falls back to the TensorFlow package if facenet-pytorch is not installed,
    so an existing environment keeps working unchanged — it simply uses a great
    deal more memory.
    """
    global _detector
    if _detector is None:
        try:
            _detector = _TorchMTCNN()
        except Exception:  # noqa: BLE001 — fall back rather than lose detection
            from mtcnn import MTCNN
            _detector = MTCNN()
    return _detector


# ---------------------------------------------------------------------------
# Face cropping
# ---------------------------------------------------------------------------

def crop_face(image: Image.Image) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Crop to the largest detected face.

    Returns (image, meta). `meta['found']` is False when no face was detected,
    in which case the original image comes back unchanged — the caller must
    surface that, since a confident verdict on an image with no face is
    meaningless.
    """
    rgb = image.convert("RGB")
    try:
        faces = _face_detector().detect_faces(np.array(rgb))
    except Exception as exc:  # noqa: BLE001 — detection must never break scoring
        return rgb, {"found": False, "error": f"{type(exc).__name__}", "count": 0}

    if not faces:
        return rgb, {"found": False, "count": 0,
                     "note": "No face detected — scored the full image instead."}

    # Largest box by area: in a showroom photo the applicant is the subject.
    faces.sort(key=lambda f: f["box"][2] * f["box"][3], reverse=True)
    best = faces[0]
    x, y, w, h = best["box"]
    x, y = max(0, x), max(0, y)

    mx, my = int(w * FACE_MARGIN), int(h * FACE_MARGIN)
    left, top = max(0, x - mx), max(0, y - my)
    right, bottom = min(rgb.width, x + w + mx), min(rgb.height, y + h + my)

    return rgb.crop((left, top, right, bottom)), {
        "found": True,
        "count": len(faces),
        "confidence": round(float(best.get("confidence", 0.0)), 4),
        "box": [int(x), int(y), int(w), int(h)],
        "crop": [int(left), int(top), int(right), int(bottom)],
        "image_size": [rgb.width, rgb.height],
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _real_score(pipe, image: Image.Image) -> float:
    """Pull the 'real' class probability out of a classification pipeline."""
    out = pipe(image)
    real = fake = 0.0
    for pred in out:
        label = str(pred["label"]).lower()
        if "real" in label:
            real = float(pred["score"])
        elif "fake" in label:
            fake = float(pred["score"])
    # Some checkpoints emit only one of the two labels.
    if real == 0.0 and fake > 0.0:
        real = 1.0 - fake
    return real


def _views(image: Image.Image) -> List[Image.Image]:
    """The augmented views averaged over at test time."""
    views = [image, ImageOps.mirror(image)]
    if TTA_VIEWS >= 3:
        w, h = image.size
        inset = 0.08
        views.append(image.crop((int(w * inset), int(h * inset),
                                 int(w * (1 - inset)), int(h * (1 - inset)))))
    return views[:TTA_VIEWS]


def score_with_tta(pipe, image: Image.Image, use_tta: bool = True) -> Dict[str, Any]:
    """Average the real-score across augmented views."""
    imgs = _views(image) if use_tta else [image]
    scores = [_real_score(pipe, v) for v in imgs]
    return {
        "real_score": float(np.mean(scores)),
        "views": len(scores),
        "spread": round(float(np.max(scores) - np.min(scores)), 4) if len(scores) > 1 else 0.0,
        "per_view": [round(s, 4) for s in scores],
    }


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

def analyze(image_path: str, use_tta: bool = True, use_crop: bool = True) -> Dict[str, Any]:
    """
    Run the calibrated FaceGuard pipeline.

    The return value is deliberately stage-structured rather than a single
    verdict: the console renders each stage as it resolves, and an officer
    reviewing a flagged application can see which step produced the decision.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    m1, m2 = _pipelines()
    original = Image.open(image_path).convert("RGB")

    # --- stage 1: locate the face ------------------------------------------
    if use_crop:
        face_img, face_meta = crop_face(original)
    else:
        face_img, face_meta = original, {"found": False, "skipped": True, "count": 0}

    # --- stage 2: primary discriminator ------------------------------------
    m1_out = score_with_tta(m1, face_img, use_tta)
    m1_real = m1_out["real_score"]
    m1_verdict = "real" if m1_real >= M1_THRESHOLD else "fake"

    # --- input quality: can this image support a confident verdict at all? --
    face_px = min(face_meta["box"][2], face_meta["box"][3]) if face_meta.get("found") else 0
    too_small_to_escalate = face_meta.get("found") and face_px < MIN_FACE_PX_FOR_ESCALATION
    too_small_to_approve = face_meta.get("found") and face_px < MIN_FACE_PX_FOR_APPROVAL

    quality = {
        "face_px": int(face_px),
        "min_px_to_escalate": MIN_FACE_PX_FOR_ESCALATION,
        "min_px_to_approve": MIN_FACE_PX_FOR_APPROVAL,
        "sufficient_for_adverse_finding": bool(face_meta.get("found") and not too_small_to_escalate),
        "note": (
            "Model 1's score falls with face resolution on an identical face, so a "
            "small or heavily recompressed capture can look synthetic when it is not. "
            "Adverse findings are suppressed below the minimum."
        ),
    }

    # Which asymmetric gate, if either, does this score clear?
    clears_approve = m1_real >= APPROVE_ABOVE and not too_small_to_approve
    clears_escalate = m1_real <= ESCALATE_BELOW and not too_small_to_escalate
    in_grey_zone = not (clears_approve or clears_escalate)

    if m1_verdict == "real":
        m1_conf = min(1.0, (m1_real - M1_THRESHOLD) / max(1e-6, 1.0 - M1_THRESHOLD))
    else:
        m1_conf = min(1.0, (M1_THRESHOLD - m1_real) / max(1e-6, M1_THRESHOLD))

    # --- stage 2b: trained forensic classifier ------------------------------
    # Frequency-domain + capture-quality evidence, independent of the semantic
    # checkpoints. When available this drives the verdict, because it is the
    # only component actually calibrated on labelled data.
    cnn = score_cnn(face_img)

    forensic = None
    bundle, fmeta = _forensic_model()
    if bundle is not None:
        try:
            import features as feat_mod
            fv = feat_mod.extract(face_img)
            if fv:
                names = bundle["feature_names"]
                vec = np.array([[fv.get(k, 0.0) for k in names]])
                p_real = float(bundle["model"].predict_proba(vec)[0][1])
                forensic = {
                    "real_probability": round(p_real, 4),
                    "verdict": "real" if p_real >= 0.5 else "fake",
                    "confidence": round(abs(p_real - 0.5) * 2, 4),
                    "auc": (fmeta or {}).get("auc"),
                    "trained_on": (fmeta or {}).get("n_per_class"),
                    "role": (
                        "Trained on our own labelled pool using frequency-domain "
                        "and capture-quality features. Calibrated, and the only "
                        "component whose threshold was fitted rather than assumed."
                    ),
                }
        except Exception:
            forensic = None

    # --- stage 3: demographic context check --------------------------------
    m2_out = score_with_tta(m2, face_img, use_tta)
    m2_real = m2_out["real_score"]

    bias_flag = (
        m1_verdict == "fake"
        and m1_real <= M1_BIAS_CEILING      # M1 is confidently fake...
        and m2_real >= M2_CONTEXT_FLOOR     # ...while M2 is confidently real
    )
    context = {
        "module": "demographic context check",
        "real_score": round(m2_real, 4),
        "role": (
            "Model 2 does not vote on the verdict — it scored AUC 0.501 on our "
            "benchmark. It runs as a check against Model 1's documented South "
            "Asian bias, where it was the reliable one."
        ),
        "bias_signature_detected": bias_flag,
    }

    # --- stage 4: fuse ------------------------------------------------------
    if cnn is not None:
        p = cnn["real_probability"]
        conf = cnn["confidence"]
        auc = cnn.get("auc") or 0.0
        if conf >= CNN_DECIDE_CONF:
            verdict = cnn["verdict"]
            action = "auto-approve" if verdict == "real" else "escalate"
            explanation = (
                f"Fine-tuned detector: {p * 100:.1f}% real ({conf * 100:.0f}% "
                f"confident), held-out AUC {auc:.3f}. Trained on our own labelled "
                f"pool with capture degradation in the augmentation, so the score "
                f"holds up on small or recompressed photos."
            )
            if verdict == "fake" and too_small_to_escalate:
                verdict, action = "uncertain", "route-to-review"
                explanation = (
                    f"Fine-tuned detector reads {p * 100:.1f}% real, but the face is "
                    f"only {int(face_px)}px across. Routed to a person rather than "
                    f"escalated; ask for a closer capture."
                )
        else:
            verdict, action = "uncertain", "route-to-review"
            explanation = (
                f"Fine-tuned detector is undecided ({p * 100:.1f}% real, "
                f"{conf * 100:.0f}% confident). A person decides."
            )
    elif forensic is not None:
        p = forensic["real_probability"]
        conf = forensic["confidence"]
        if conf >= FORENSIC_DECIDE_CONF:
            verdict = forensic["verdict"]
            action = "auto-approve" if verdict == "real" else "escalate"
            explanation = (
                f"Forensic classifier: {p * 100:.1f}% real "
                f"({conf * 100:.0f}% confident). Frequency-domain and "
                f"capture-quality evidence, cross-validated at AUC "
                f"{forensic.get('auc', 0):.3f}."
            )
            # A confident adverse call still needs a usable capture.
            if verdict == "fake" and too_small_to_escalate:
                verdict, action = "uncertain", "route-to-review"
                explanation = (
                    f"Forensic classifier reads {p * 100:.1f}% real, but the face is "
                    f"only {int(face_px)}px across — too small to support an adverse "
                    f"finding. Routed to a person; ask for a closer capture."
                )
        else:
            verdict, action = "uncertain", "route-to-review"
            explanation = (
                f"Forensic classifier is undecided ({p * 100:.1f}% real, "
                f"{conf * 100:.0f}% confident — below the {FORENSIC_DECIDE_CONF * 100:.0f}% "
                f"bar). A person decides."
            )
    elif too_small_to_escalate and m1_real <= ESCALATE_BELOW:
        verdict, action = "uncertain", "route-to-review"
        explanation = (
            f"The detected face is only {int(face_px)}px across — below the "
            f"{MIN_FACE_PX_FOR_ESCALATION}px needed for an adverse finding. Model 1 "
            f"scores low ({m1_real:.4f}), but its score falls with resolution on "
            f"genuine faces too, so this reads as a capture-quality artefact rather "
            f"than evidence of synthesis. Routed to a person, not escalated. Ask for "
            f"a closer, uncompressed capture."
        )
    elif in_grey_zone:
        verdict, action = "uncertain", "route-to-review"
        reason = (
            f"the face is {int(face_px)}px across, below the "
            f"{MIN_FACE_PX_FOR_APPROVAL}px needed to clear an applicant"
            if too_small_to_approve
            else f"the score falls between the escalate gate ({ESCALATE_BELOW:.2f}) "
                 f"and the approve gate ({APPROVE_ABOVE:.3f})"
        )
        explanation = (
            f"Model 1 real-score {m1_real:.4f} — {reason}. Not confident enough to "
            f"clear, not adverse enough to escalate, so a person decides."
        )
    elif bias_flag:
        verdict, action = "uncertain", "route-to-review"
        explanation = (
            f"Model 1 says FAKE with confidence ({m1_real:.3f} real-score) but the "
            f"context check reads REAL at {m2_real * 100:.1f}%. That combination is "
            f"the signature of Model 1's documented bias against under-represented "
            f"faces, so this goes to a person rather than a rejection."
        )
    elif clears_approve:
        verdict, action = "real", "auto-approve"
        explanation = (
            f"Model 1 real-score {m1_real:.4f} clears the approve gate "
            f"({APPROVE_ABOVE:.3f}) and the context check shows no bias signature."
        )
    else:
        verdict, action = "fake", "escalate"
        explanation = (
            f"Model 1 real-score {m1_real:.4f} is below the escalate gate "
            f"({ESCALATE_BELOW:.2f}) — a confident synthetic-media finding."
        )

    if not face_meta.get("found") and not face_meta.get("skipped"):
        verdict, action = "uncertain", "route-to-review"
        explanation = (
            "No face was detected in this image, so the whole frame was scored. "
            "A verdict on an image with no detectable face is not trustworthy."
        )

    return {
        "verdict": verdict,
        "action": action,
        "explanation": explanation,
        "confidence": round(float(m1_conf), 4),
        "quality": quality,
        "stages": {
            "face_detection": face_meta,
            "primary": {
                "model": _M1_ID,
                "real_score": round(m1_real, 4),
                "threshold": M1_THRESHOLD,
                "approve_above": APPROVE_ABOVE,
                "escalate_below": ESCALATE_BELOW,
                "verdict": m1_verdict,
                "confidence": round(float(m1_conf), 4),
                "tta": m1_out,
            },
            "context": {**context, "tta": m2_out, "model": _M2_ID},
            "forensic": forensic,
            "cnn": cnn,
            # Both shipped checkpoints are reported with their measured
            # reliability attached. M1 in particular looks convincing in hand
            # testing because it calls almost everything real (mean 0.952 on
            # real images, 0.911 on fakes) — it is right on genuine photos by
            # default rather than by discrimination, so the AUC belongs next to
            # the score wherever the score is shown.
            "second_opinions": {
                "model_1": {
                    "name": _M1_ID,
                    "real_score": round(m1_real, 4),
                    "measured_auc": 0.652,
                    "caveat": "Calls ~everything real; 51.9% accuracy at its default threshold.",
                },
                "model_2": {
                    "name": _M2_ID,
                    "real_score": round(m2_real, 4),
                    "measured_auc": 0.513,
                    "caveat": "Indistinguishable from a coin flip on our data.",
                },
            },
        },
        "pipeline": {
            "face_crop": bool(face_meta.get("found")),
            "tta_views": m1_out["views"],
            "calibrated_threshold": M1_THRESHOLD,
            "approve_above": APPROVE_ABOVE,
            "escalate_below": ESCALATE_BELOW,
            "grey_zone": in_grey_zone,
            "note": (
                "Threshold calibrated by 5-fold cross-validation on a 120-sample "
                "labelled set; see validate_faceguard.py to reproduce."
            ),
        },
    }


# Backwards-compatible shim so existing callers keep working.
def run_face_detection_calibrated(image_path: str) -> Dict[str, float]:
    result = analyze(image_path)
    return {
        "real_score": result["stages"]["primary"]["real_score"],
        "verdict": result["verdict"],
    }
