"""
Litmus LiveChallenge — inbound verification that does not depend on detection
=============================================================================

THE SAME INVERSION, POINTED INWARD
----------------------------------
TrustLine removed our dependence on voice detection by refusing to ask "does
this voice sound real?" and asking instead for a code a clone was never issued.
LiveChallenge does that for video KYC.

The problem it solves is injection attacks. Those feed generated video straight
into the verification software, so the camera is never involved. Passive
liveness cannot see them — there is no presentation artifact to find, because
nothing was ever presented to a sensor. The pixels are perfect. Analysing them
harder does not help.

So we stop analysing pixels for authenticity and start asking a question the
attacker could not have prepared an answer to.

THE PROTOCOL
------------
  1. At verification time the server mints a session and derives a RANDOM
     physical challenge from it — a head turn to one of five stated
     positions, plus a spoken word.
  2. The applicant performs it. The client submits the response frames.
  3. The server measures whether the response matches the challenge it issued.

WHY THIS DEFEATS INJECTION
--------------------------
A pre-recorded or pre-generated stream is fixed before the challenge exists.
It cannot contain a response to a challenge chosen afterwards. The attack fails
by construction rather than by detection — the same property that makes
TrustLine work.

To beat it, an attacker needs *real-time* generation that correctly renders
extreme head pose on demand, three times, each pose unknown until the
previous one was answered. Extreme yaw is precisely where real-time
face-swap degrades.

An occlusion check (hold a hand over one cheek) was tried and removed. It
inferred the hand from landmark asymmetry, but a head turn produces the same
asymmetry, so genuine applicants failed it. A check that rejects honest
people is worse than no check, and the round count was raised instead.

WHAT IS MEASURED, AND WHAT IS NOT
---------------------------------
Head pose and occlusion are measured geometrically from facial landmarks — not
by a classifier, and not by a confidence score. The check is "does the measured
yaw match the yaw that was demanded", which an officer can audit and a court
could follow.

THE SPOKEN WORD — WHAT IS CHECKED, AND WHAT IS NOT
---------------------------------------------------
The audio is decoded on the server and checked for the acoustic signature of
someone speaking: energy above a noise floor, spread across enough of the
recording, with the rise and fall that separates speech from a steady hum.
Silence fails the round. Saying nothing used to pass, which made half the
instruction theatre.

What is NOT checked is WHICH word was said.

The word is captured as audio and attached to the session, then replayed for
whoever reviews the case. It is deliberately NOT machine-verified, for two
reasons that are worth stating rather than hiding.

First, our own voice models catch 0% of modern neural TTS, so a voice match
would prove nothing. Second, any speech recognition running in the applicant's
browser is under the attacker's control — a client that reports "yes, they said
the word" is not evidence, it is the attacker's own testimony.

So the split is: the server proves someone spoke, and a human decides whether
they said the right thing. A reviewer hearing the wrong word, a synthesised
cadence, or a prompt being read aloud by someone off-camera learns something
no classifier here could tell them.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

_SECRET: bytes = os.environ.get(
    "LITMUS_LIVECHALLENGE_SECRET", "litmus-demo-livechallenge-secret"
).encode()

SESSION_TTL_SECONDS = 120        # a live capture, not a form — keep it short
MAX_ATTEMPTS = 3

# Geometric tolerances, in degrees of estimated yaw.
YAW_TARGETS = {
    "far-left": -40.0,
    "left": -22.0,
    "centre": 0.0,
    "right": 22.0,
    "far-right": 40.0,
}
YAW_TOLERANCE = 11.0             # tightened so adjacent targets stay distinct

# ROUNDS. One head-pose challenge has 5 possible answers, so a fixed
# pre-generated response clears it 1 time in 5 by luck — nowhere near good
# enough for a control that gates a loan.
#
# Requiring N independent rounds raises the bar to 5^-N. Three rounds puts a
# blind guess at 0.8%, and each round's challenge is derived only after the
# previous response arrives, so an attacker cannot prepare round 2 while
# round 1 is in flight either.
ROUNDS_REQUIRED = 3

# Whether a round requires audible speech. On by default: a challenge that
# instructs the applicant to speak and then ignores whether they did teaches
# them the instruction is optional, and an attacker learns the same thing.
REQUIRE_SPEECH = os.environ.get("LITMUS_REQUIRE_SPEECH", "1") != "0"

# Words chosen to be pronounceable by a Hindi/English bilingual speaker and
# phonetically distinct from one another over a low-bitrate call.
_WORDS = [
    "MONSOON", "TIGER", "SAFFRON", "COPPER", "LANTERN", "MARIGOLD",
    "PEACOCK", "HARBOUR", "JASMINE", "THUNDER", "EMERALD", "COMPASS",
]


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

@dataclass
class ChallengeSession:
    session_id: str
    applicant_id: str
    yaw_direction: str
    word: str
    issued_at: float
    expires_at: float
    attempts: int = 0
    status: str = "issued"          # issued | passed | failed | expired | locked
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    applicant_ref: str = ""         # operator-supplied reference for the record
    round_index: int = 1            # which round is currently outstanding
    rounds_passed: int = 0
    # Audio responses per round, kept for human review. Demo-scoped in memory;
    # production would put these in object storage with a retention policy,
    # since a voice recording is personal data under the DPDP Act.
    audio: Dict[int, bytes] = field(default_factory=dict)
    # Speech-presence analysis per round, computed when the audio arrives.
    speech: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    def expired(self, now: Optional[float] = None) -> bool:
        return (now or time.time()) > self.expires_at

    def public(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "applicant_id": self.applicant_id,
            "applicant_ref": self.applicant_ref,
            "challenge": {
                "turn_head": self.yaw_direction,
                "target_yaw_degrees": YAW_TARGETS[self.yaw_direction],
                "tolerance_degrees": YAW_TOLERANCE,
                "say_word": self.word,
            },
            "instruction": (
                f"Turn your head to the {self.yaw_direction.upper()} and say "
                f"the word \"{self.word}\" out loud."
            ),
            "round": self.round_index,
            "rounds_required": ROUNDS_REQUIRED,
            "rounds_passed": self.rounds_passed,
            "blind_guess_probability": round(guess_probability(), 5),
            "issued_at": _iso(self.issued_at),
            "expires_at": _iso(self.expires_at),
            "seconds_remaining": max(0, int(self.expires_at - time.time())),
            "status": self.status,
            "attempts": self.attempts,
            "audio_rounds": sorted(self.audio.keys()),
        }


_SESSIONS: Dict[str, ChallengeSession] = {}


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Challenge derivation
# ---------------------------------------------------------------------------

def _derive(applicant_id: str, session_id: str) -> Tuple[str, str, str, str]:
    """
    Derive the challenge from the session under a server secret.

    Deterministic given the session, so the server can re-derive it without
    storing it, and unpredictable to anyone without the secret — which is the
    property that makes a pre-generated response impossible.
    """
    digest = hmac.new(_SECRET, f"{applicant_id}|{session_id}".encode(),
                      hashlib.sha256).digest()
    keys = list(YAW_TARGETS)
    yaw = keys[digest[0] % len(keys)]
    word = _WORDS[digest[2] % len(_WORDS)]
    return yaw, word


def _derive_round(applicant_id: str, session_id: str, rnd: int):
    """Round N's challenge. Derived per round so round 2 is unknowable during round 1."""
    return _derive(applicant_id, f"{session_id}#r{rnd}")


def guess_probability(rounds: int = None) -> float:
    """Probability a fixed pre-generated response clears the whole session."""
    n = rounds if rounds is not None else ROUNDS_REQUIRED
    per_round = 1.0 / len(YAW_TARGETS)
    return per_round ** n


def issue(applicant_id: str, applicant_ref: str = "") -> Dict[str, Any]:
    """Mint a challenge. Must be called at verification time, never earlier."""
    now = time.time()
    session_id = f"lc_{secrets.token_hex(6)}"
    yaw, word = _derive_round(applicant_id, session_id, 1)

    session = ChallengeSession(
        session_id=session_id,
        applicant_id=applicant_id,
        yaw_direction=yaw,
        word=word,
        issued_at=now,
        expires_at=now + SESSION_TTL_SECONDS,
        applicant_ref=applicant_ref or applicant_id,
    )
    _SESSIONS[session_id] = session
    return session.public()


# ---------------------------------------------------------------------------
# Geometry — measured, not classified
# ---------------------------------------------------------------------------

def estimate_yaw(landmarks: Dict[str, Any]) -> Optional[float]:
    """
    Estimate head yaw in degrees from five facial landmarks.

    Uses the nose's horizontal offset from the eye midpoint, normalised by
    inter-ocular distance. Positive is a turn to the subject's right as the
    camera sees it. This is deliberately a geometric measurement rather than a
    learned regressor: the result is auditable, has no training distribution to
    drift from, and cannot be biased against a demographic.
    """
    try:
        le = np.array(landmarks["left_eye"], dtype=float)
        re = np.array(landmarks["right_eye"], dtype=float)
        nose = np.array(landmarks["nose"], dtype=float)
    except (KeyError, TypeError, ValueError):
        return None

    eye_mid = (le + re) / 2.0
    interocular = float(np.linalg.norm(re - le))
    if interocular < 1e-6:
        return None

    offset = float(nose[0] - eye_mid[0]) / interocular
    # ~0.5 normalised offset corresponds to roughly 45 degrees in practice.
    return float(np.clip(offset * 90.0, -90.0, 90.0))


def measure_occlusion(landmarks: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    Infer which side of the face is obscured. NO LONGER PART OF THE PROTOCOL.

    Retained as a review aid only. It was removed from verification because a
    head turn produces the same landmark asymmetry as a hand over the cheek,
    so it failed genuine applicants.

    MTCNN still returns five landmarks under partial occlusion but its
    confidence drops and the covered side's points bunch toward the visible
    side. We report the asymmetry rather than a verdict, and the caller decides.
    """
    try:
        le = np.array(landmarks["left_eye"], dtype=float)
        re = np.array(landmarks["right_eye"], dtype=float)
        ml = np.array(landmarks["mouth_left"], dtype=float)
        mr = np.array(landmarks["mouth_right"], dtype=float)
    except (KeyError, TypeError, ValueError):
        return {"side": "unknown", "asymmetry": None, "detector_confidence": confidence}

    left_span = float(np.linalg.norm(le - ml))
    right_span = float(np.linalg.norm(re - mr))
    total = left_span + right_span
    if total < 1e-6:
        return {"side": "unknown", "asymmetry": None, "detector_confidence": confidence}

    asym = (left_span - right_span) / total
    if confidence < 0.97 and abs(asym) > 0.10:
        side = "left_cheek" if asym < 0 else "right_cheek"
    else:
        side = "none"

    return {
        "side": side,
        "asymmetry": round(asym, 4),
        "detector_confidence": round(float(confidence), 4),
    }


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def attach_audio(session_id: str, round_index: int, data: bytes) -> bool:
    """
    Store the spoken response and measure whether it contains speech.

    Analysis happens here, on the bytes actually uploaded, rather than trusting
    anything the browser reports about them.
    """
    session = _SESSIONS.get(session_id)
    if not session:
        return False
    session.audio[round_index] = data or b""
    try:
        import audio_check
        session.speech[round_index] = audio_check.analyse(data or b"")
    except Exception as exc:  # noqa: BLE001 — never break a verification on this
        session.speech[round_index] = {
            "speech_detected": False,
            "reason": "analysis_failed",
            "message": f"Speech analysis unavailable ({type(exc).__name__}).",
        }
    return True


def get_speech(session_id: str, round_index: int) -> Optional[Dict[str, Any]]:
    session = _SESSIONS.get(session_id)
    return session.speech.get(round_index) if session else None


def get_audio(session_id: str, round_index: int) -> Optional[bytes]:
    session = _SESSIONS.get(session_id)
    return session.audio.get(round_index) if session else None


def verify(session_id: str, landmarks: Dict[str, Any],
           detector_confidence: float = 1.0) -> Dict[str, Any]:
    """
    Check a response against the challenge that was issued.

    Returns a structured result. Every branch states what was demanded and what
    was measured, because "the response did not match" is a claim an applicant
    is entitled to see the working for.
    """
    session = _SESSIONS.get(session_id)
    if not session:
        return {
            "result": "NO_SUCH_SESSION",
            "passed": False,
            "message": (
                "No challenge was issued with that id. A response cannot be "
                "accepted for a challenge this server never set."
            ),
        }

    if session.status in ("passed", "failed", "locked"):
        return {
            "result": "ALREADY_RESOLVED",
            "passed": False,
            "message": f"This challenge is already {session.status}. Issue a new one.",
        }

    if session.expired():
        session.status = "expired"
        return {
            "result": "EXPIRED",
            "passed": False,
            "message": (
                f"The challenge expired after {SESSION_TTL_SECONDS}s. This window is "
                f"deliberately short — a long one gives an attacker time to generate "
                f"a matching response."
            ),
        }

    session.attempts += 1
    if session.attempts > MAX_ATTEMPTS:
        session.status = "locked"
        return {
            "result": "LOCKED",
            "passed": False,
            "message": f"Locked after {MAX_ATTEMPTS} attempts.",
        }

    measured_yaw = estimate_yaw(landmarks)
    if measured_yaw is None:
        return {
            "result": "NO_LANDMARKS",
            "passed": False,
            "message": "No usable facial landmarks in the response frame.",
        }

    target = YAW_TARGETS[session.yaw_direction]
    yaw_error = abs(measured_yaw - target)
    yaw_ok = yaw_error <= YAW_TOLERANCE

    # Speech presence. Absent analysis means no audio reached the server at
    # all, which is itself a failure to follow the instruction.
    speech = session.speech.get(session.round_index) or {
        "speech_detected": False,
        "reason": "no_audio",
        "message": (
            "No audio was submitted with this response. The challenge asks the "
            "applicant to speak — check that the microphone is permitted."
        ),
    }
    speech_ok = bool(speech.get("speech_detected")) or not REQUIRE_SPEECH


    checks = {
        "head_turn": {
            "demanded": session.yaw_direction,
            "target_degrees": target,
            "measured_degrees": round(measured_yaw, 1),
            "error_degrees": round(yaw_error, 1),
            "tolerance_degrees": YAW_TOLERANCE,
            "passed": bool(yaw_ok),
        },
        "spoken_word": {
            "demanded": session.word,
            "required": REQUIRE_SPEECH,
            "speech_detected": bool(speech.get("speech_detected")),
            "passed": speech_ok,
            "analysis": speech,
            "word_verified": False,
            "audio_captured": bool(session.audio.get(session.round_index)),
            "audio_url": (
                f"/api/v1/livechallenge/audio/{session.session_id}/{session.round_index}"
                if session.round_index in session.audio else None
            ),
            "note": (
                "The server checks that speech was PRESENT, decoded from the audio "
                "actually uploaded. It does not check WHICH word was said: our voice "
                "models catch 0% of modern neural TTS, and speech recognition in the "
                "applicant's own browser would be the attacker's testimony rather "
                "than evidence. The recording is retained for a human to judge the "
                "content."
            ),
        },
    }

    round_ok = bool(yaw_ok and speech_ok)
    session.evidence.append({"at": _iso(time.time()), "round": session.round_index,
                             "checks": checks})

    if round_ok and session.rounds_passed + 1 < ROUNDS_REQUIRED:
        # Advance. The next round's challenge is derived only now, so it could
        # not have been anticipated while this one was being answered.
        session.rounds_passed += 1
        session.round_index += 1
        session.attempts = 0
        session.yaw_direction, session.word = _derive_round(
            session.applicant_id, session.session_id, session.round_index)
        return {
            "result": "ROUND_PASSED",
            "passed": False,
            "rounds_passed": session.rounds_passed,
            "rounds_required": ROUNDS_REQUIRED,
            "message": (
                f"Round {session.rounds_passed} of {ROUNDS_REQUIRED} matched. "
                f"A new challenge has been issued for round {session.round_index} — "
                f"it was generated just now, so it could not have been prepared "
                f"during the previous round."
            ),
            "checks": checks,
            "next_challenge": session.public()["challenge"],
            "next_instruction": session.public()["instruction"],
        }

    passed = round_ok
    session.status = "passed" if passed else "issued"
    if passed:
        session.rounds_passed += 1

    if passed:
        return {
            "result": "CHALLENGE_PASSED",
            "passed": True,
            "rounds_passed": session.rounds_passed,
            "blind_guess_probability": round(guess_probability(), 5),
            "message": (
                f"The response matches the challenge issued {int(time.time() - session.issued_at)}s "
                f"ago. Because the challenge was generated after this session opened, "
                f"a pre-recorded or pre-generated stream could not have contained it. "
                f"All {ROUNDS_REQUIRED} rounds matched; a blind guess clears that "
                f"about {guess_probability() * 100:.2f}% of the time."
            ),
            "checks": checks,
            "why_this_matters": (
                "This is a verifiable check, not a confidence score. It does not "
                "depend on any deepfake detector being correct."
            ),
        }

    failed = [k for k, v in checks.items() if v.get("passed") is False]
    if not speech_ok:
        detail = speech.get("message", "No speech was detected.")
        return {
            "result": "CHALLENGE_FAILED",
            "passed": False,
            "message": (
                f"{detail} The head pose "
                f"{'matched' if yaw_ok else 'did not match'}, but the challenge also "
                f"requires the word to be spoken aloud. "
                f"{max(0, MAX_ATTEMPTS - session.attempts)} attempt(s) remain."
            ),
            "checks": checks,
            "attempts_remaining": max(0, MAX_ATTEMPTS - session.attempts),
        }
    return {
        "result": "CHALLENGE_FAILED",
        "passed": False,
        "message": (
            f"The response does not match what was demanded ({', '.join(failed)}). "
            f"This may be a genuine applicant who misunderstood — "
            f"{MAX_ATTEMPTS - session.attempts} attempt(s) remain before lockout."
        ),
        "checks": checks,
        "attempts_remaining": max(0, MAX_ATTEMPTS - session.attempts),
    }


def get_evidence(session_id: str) -> list:
    """Per-round check results, in order, for the evidence record."""
    session = _SESSIONS.get(session_id)
    return list(session.evidence) if session else []


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    s = _SESSIONS.get(session_id)
    if not s:
        return None
    if s.status == "issued" and s.expired():
        s.status = "expired"
    return s.public()


def reset_state() -> None:
    _SESSIONS.clear()
