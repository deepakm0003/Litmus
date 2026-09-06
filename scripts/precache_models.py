"""
Download the four public checkpoints ahead of time.

Left to the first request, transformers fetches roughly 1.9 GB over the
network while someone waits, and does it again after every restart. Running
this during the image build moves that cost to build time, where nobody is
watching.

Failure is deliberately not fatal: a HuggingFace outage during a build should
delay the first request, not break the deployment. The models still download
lazily if this did not manage to cache them.
"""

import os
import sys

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

MODELS = [
    ("image-classification", "Deep-Fake-Detector-Model"),
    ("image-classification", "deepfake_vs_real_image_detection"),
    ("audio-classification", "Deepfake-audio-detection-V2"),
    ("audio-classification", "Deepfake-audio-detection"),
]


def main() -> int:
    try:
        from transformers import pipeline
    except ImportError as exc:
        print(f"transformers unavailable, skipping pre-cache: {exc}", flush=True)
        return 0

    ok = 0
    for task, name in MODELS:
        try:
            pipeline(task, model=name)
            print(f"cached  {name}", flush=True)
            ok += 1
        except Exception as exc:  # noqa: BLE001 — a build must not die here
            print(f"skipped {name}: {type(exc).__name__}: {exc}", flush=True)

    print(f"{ok}/{len(MODELS)} checkpoints cached", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
