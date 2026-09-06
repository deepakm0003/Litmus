"""
Litmus — speech presence detection
==================================

THE GAP THIS CLOSES
-------------------
LiveChallenge told the applicant to say a word, then passed the round whether or
not they said anything. The word was recorded for human review and never
checked, so silence sailed through. A control that instructs you to do something
and then does not care whether you did it is not a control — it teaches the
person being verified that half the instruction is theatre.

WHAT IS AND IS NOT CHECKED
--------------------------
This measures whether SPEECH WAS PRESENT. It does not attempt to recognise the
word, and it never will here:

  * Our voice models catch 0% of modern neural TTS, so a voice match would
    prove nothing about who was speaking.
  * Speech recognition running in the applicant's browser is under the
    attacker's control — a client reporting "yes, they said it" is the
    attacker's own testimony, not evidence.

So the audio is decoded on the server and measured for the acoustic signature of
someone speaking. The recording is still retained for a human to listen to, and
that reviewer remains the only party who judges WHAT was said.

WHY IT IS MEASURED SERVER-SIDE
------------------------------
The browser could compute a level and post it, and that would be trivially
forged. The raw audio is decoded here, from the bytes actually uploaded.

HOW SPEECH IS DISTINGUISHED FROM SILENCE
----------------------------------------
Three properties together, because any one alone is easy to fool:

  1. Energy above a noise floor across enough of the recording. Silence and a
     muted microphone fail this immediately.
  2. Variation in that energy. Speech rises and falls between syllables; a
     steady hum, a fan, or a held tone does not, and would otherwise pass a
     naive loudness test.
  3. Enough duration of actual voiced activity, so a cough or a single click
     does not count as a spoken word.
"""

from __future__ import annotations

import io
import math
from typing import Any, Dict, List

# Thresholds are conservative: the cost of failing a genuine speaker is an
# annoying retry, but they are set from the acoustics of a phone at arm's length
# in a noisy room, not a studio.
NOISE_FLOOR = 0.012          # RMS below this is treated as silence
MIN_ACTIVE_RATIO = 0.08      # at least this share of frames must carry energy
MIN_VOICED_SECONDS = 0.25    # total voiced time required
MIN_VARIATION = 0.004        # std-dev of frame energy — flat tones fail this
FRAME_MS = 20


def _decode(data: bytes) -> tuple[List[float], int]:
    """
    Decode compressed audio to mono samples.

    Returns ([], 0) when the bytes cannot be decoded, which the caller must
    treat as "no usable audio" rather than as silence — an unreadable upload and
    a silent one are different failures.
    """
    try:
        import av  # PyAV decodes WebM/Opus in-process, no subprocess needed
        import numpy as np

        container = av.open(io.BytesIO(data))
        stream = next((s for s in container.streams if s.type == "audio"), None)
        if stream is None:
            return [], 0

        rate = int(stream.codec_context.sample_rate or 48000)
        chunks: List["np.ndarray"] = []
        for frame in container.decode(stream):
            arr = frame.to_ndarray()
            if arr.ndim > 1:            # average channels down to mono
                arr = arr.mean(axis=0)
            chunks.append(arr.astype("float64").ravel())
        container.close()

        if not chunks:
            return [], rate
        samples = np.concatenate(chunks)

        # Integer formats arrive unnormalised; scale to roughly [-1, 1].
        peak = float(max(abs(samples.max()), abs(samples.min()))) if samples.size else 0.0
        if peak > 1.5:
            samples = samples / 32768.0
        return samples.tolist(), rate
    except Exception:
        return [], 0


def analyse(data: bytes) -> Dict[str, Any]:
    """
    Decide whether this recording contains someone speaking.

    Never raises. Every failure mode is reported as a distinct reason so the
    applicant can be told something actionable rather than just "rejected".
    """
    if not data:
        return {
            "speech_detected": False,
            "reason": "no_audio",
            "message": (
                "No audio was submitted with this response. The challenge asks the "
                "applicant to speak, so a recording is required — check that the "
                "microphone is permitted."
            ),
            "decoded": False,
        }

    samples, rate = _decode(data)
    if not samples or not rate:
        return {
            "speech_detected": False,
            "reason": "undecodable",
            "message": (
                "The audio could not be decoded on the server. It was not treated "
                "as silence; it simply could not be read."
            ),
            "decoded": False,
            "bytes": len(data),
        }

    frame_len = max(1, int(rate * FRAME_MS / 1000))
    energies: List[float] = []
    for i in range(0, len(samples) - frame_len + 1, frame_len):
        window = samples[i:i + frame_len]
        acc = 0.0
        for v in window:
            acc += v * v
        energies.append(math.sqrt(acc / frame_len))

    if not energies:
        return {
            "speech_detected": False,
            "reason": "too_short",
            "message": "The recording was too short to assess.",
            "decoded": True,
        }

    duration = len(samples) / rate
    active = [e for e in energies if e > NOISE_FLOOR]
    active_ratio = len(active) / len(energies)
    voiced_seconds = len(active) * FRAME_MS / 1000.0

    mean_e = sum(energies) / len(energies)
    variation = math.sqrt(sum((e - mean_e) ** 2 for e in energies) / len(energies))
    peak = max(energies)

    metrics = {
        "duration_seconds": round(duration, 2),
        "voiced_seconds": round(voiced_seconds, 2),
        "active_ratio": round(active_ratio, 3),
        "peak_level": round(peak, 4),
        "level_variation": round(variation, 4),
        "decoded": True,
        "bytes": len(data),
    }

    if peak <= NOISE_FLOOR:
        return {**metrics, "speech_detected": False, "reason": "silence",
                "message": ("The recording contains no sound above the noise floor. "
                            "Nothing was said, or the microphone captured nothing.")}

    if active_ratio < MIN_ACTIVE_RATIO or voiced_seconds < MIN_VOICED_SECONDS:
        return {**metrics, "speech_detected": False, "reason": "too_quiet",
                "message": (f"Only {voiced_seconds:.2f}s of audible activity was found. "
                            f"The word may not have been spoken, or was too quiet.")}

    if variation < MIN_VARIATION:
        return {**metrics, "speech_detected": False, "reason": "no_modulation",
                "message": ("The audio carries a steady level with none of the rise and "
                            "fall of speech — consistent with background noise or a held "
                            "tone rather than someone talking.")}

    return {**metrics, "speech_detected": True, "reason": "speech",
            "message": (f"Speech detected — {voiced_seconds:.2f}s of voiced activity across "
                        f"a {duration:.2f}s recording. The content of what was said is not "
                        f"assessed here and remains for human review.")}
