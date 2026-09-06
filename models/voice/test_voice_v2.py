"""
Voice Detection Model 2 — motheecreator/Deepfake-audio-detection
Same return format as test_voice.py (run_voice_detection).
"""

import os
from pathlib import Path
import librosa
from transformers import pipeline

# Ensure ffmpeg is on PATH
_FFMPEG_BIN = (
    r"C:\Users\deepa\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.1-full_build\bin"
)
# Windows-only convenience. On Linux (and any deployment host) ffmpeg is
# on PATH already, so this block is skipped rather than prepending a
# directory that does not exist there.
if os.name == "nt" and _FFMPEG_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")

# Load model once at module level
_detector2 = None

def _get_detector():
    global _detector2
    if _detector2 is None:
        print("[M2] Loading motheecreator/Deepfake-audio-detection ...")
        _detector2 = pipeline(
            "audio-classification",
            model="motheecreator/Deepfake-audio-detection"
        )
        print("[M2] Model loaded.")
    return _detector2


def run_voice_detection_v2(audio_path: str) -> dict:
    """
    Args:
        audio_path: path to audio file (.wav / .mp3 / .m4a / etc.)
    Returns:
        {"real_score": float, "verdict": "real" | "spoof"}
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    detector = _get_detector()

    # Load as numpy array — avoids ffmpeg path issues same as M1
    audio, sr = librosa.load(audio_path, sr=16000, mono=True)

    result = detector({"array": audio, "sampling_rate": 16000})
    print(f"  [M2 DEBUG] {result}")

    real_score = 0.0
    spoof_score = 0.0
    for pred in result:
        label = pred["label"].lower()
        score = pred["score"]
        if any(k in label for k in ("real", "bonafide", "genuine")):
            real_score = score
        elif any(k in label for k in ("fake", "spoof", "generated", "synthetic")):
            spoof_score = score

    verdict = "real" if real_score > spoof_score else "spoof"
    return {"real_score": real_score, "verdict": verdict}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test_voice_v2.py <audio_path>")
        sys.exit(1)
    r = run_voice_detection_v2(sys.argv[1])
    print(f"Verdict: {r['verdict'].upper()}  |  real_score: {r['real_score']:.4f}")
