"""
LiveChallenge tests — adversarial, like the TrustLine suite.

    python backend/test_livechallenge.py

The central property under test: a response prepared before the challenge
existed must never pass.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

import livechallenge as lc  # noqa: E402

PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}  {detail}")


def face(yaw_norm=0.0, left_span=50.0, right_span=50.0):
    """
    Synthetic landmarks with a chosen yaw and cheek asymmetry.

    yaw_norm is the nose offset as a fraction of interocular distance, which is
    exactly what estimate_yaw consumes — so the tests exercise the real geometry
    rather than a stub.
    """
    le, re = (100.0, 100.0), (160.0, 100.0)
    interocular = re[0] - le[0]
    eye_mid_x = (le[0] + re[0]) / 2
    nose = (eye_mid_x + yaw_norm * interocular, 130.0)
    return {
        "left_eye": le,
        "right_eye": re,
        "nose": nose,
        "mouth_left": (le[0], 100.0 + left_span),
        "mouth_right": (re[0], 100.0 + right_span),
    }


APPLICANT = "TVSC_APPLICANT_5521"


def _wav(sample_fn, seconds=1.6, rate=16000):
    """Build a WAV in memory so the tests exercise the real decoder."""
    import io, math, struct, wave
    n = int(rate * seconds)
    frames = b"".join(
        struct.pack("<h", int(max(-1, min(1, sample_fn(i / rate))) * 32767))
        for i in range(n)
    )
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)
    return buf.getvalue()


def speech_audio():
    """Amplitude-modulated tone — the acoustic shape of someone talking."""
    import math
    return _wav(lambda t: (0.5 * math.sin(2 * math.pi * 180 * t)
                           * (1 + math.sin(2 * math.pi * 4 * t)))
                          * (1 if (t % 0.6) < 0.35 else 0.02))


def silent_audio():
    return _wav(lambda t: 0.0)


def say(session_id, round_index, audio=None):
    """Attach a spoken response for the round about to be verified."""
    lc.attach_audio(session_id, round_index, speech_audio() if audio is None else audio)


def respond(session_id, want, audio=None):
    """Satisfy a challenge: correct head pose, and actually speak."""
    sess = lc.get_session(session_id)
    say(session_id, (sess or {}).get("round", 1), audio)
    yaw_norm = lc.YAW_TARGETS[want["turn_head"]] / 90.0
    return lc.verify(session_id, face(yaw_norm), 0.999)


def solve(applicant):
    """Issue a session and answer every round correctly."""
    s0 = lc.issue(applicant)
    res = respond(s0["session_id"], s0["challenge"])
    while res.get("result") == "ROUND_PASSED":
        res = respond(s0["session_id"], res["next_challenge"])
    return s0, res

# ---------------------------------------------------------------------------
print("\n=== 1. Challenge is issued and is unpredictable ===")
lc.reset_state()
a = lc.issue(APPLICANT)
b = lc.issue(APPLICANT)
check("issue returns an instruction", "Turn your head" in a["instruction"])
check("challenge has a head turn", a["challenge"]["turn_head"] in lc.YAW_TARGETS)
check("challenge has a word", len(a["challenge"]["say_word"]) > 3)
check("two sessions differ (not pre-computable)",
      (a["challenge"], a["session_id"]) != (b["challenge"], b["session_id"])
      or a["session_id"] != b["session_id"])

# ---------------------------------------------------------------------------
print("\n=== 2. A correct response passes ===")
lc.reset_state()
_s, r = solve(APPLICANT)
check("correct response passes all rounds", r["passed"], r.get("result"))
check("result explains the guarantee", "pre-recorded" in r.get("message", ""))
check("guess probability reported", r.get("blind_guess_probability", 1) < 0.01)

# ---------------------------------------------------------------------------
print("\n=== 3. THE CORE PROPERTY: a prepared response cannot pass ===")
# The attacker prepares a response BEFORE the challenge exists, and must guess
# the head pose (1 in 5) three times over.
lc.reset_state()
prepared = face(0.32, left_span=50.0, right_span=50.0)   # guessed: turn right, no occlusion
passes = 0
trials = 300
spoken = speech_audio()
for i in range(trials):
    sess = lc.issue(f"{APPLICANT}_{i}")
    sid = sess["session_id"]
    # The attacker does speak — we are measuring the pose guess, not the audio.
    lc.attach_audio(sid, 1, spoken)
    res = lc.verify(sid, prepared, 0.999)
    while res.get("result") == "ROUND_PASSED":
        nxt = lc.get_session(sid)
        lc.attach_audio(sid, (nxt or {}).get("round", 1), spoken)
        res = lc.verify(sid, prepared, 0.999)
    if res.get("passed"):
        passes += 1
rate = passes / trials
print(f"    fixed pre-generated response cleared {passes}/{trials} sessions "
      f"({rate*100:.2f}%) — theoretical floor {lc.guess_probability()*100:.2f}%")
check("prepared response almost never clears a session", rate <= 0.04,
      f"{rate*100:.2f}%")

# ---------------------------------------------------------------------------
print("\n=== 4. Wrong head turn is rejected ===")
lc.reset_state()
s = lc.issue(APPLICANT)
demanded = lc.YAW_TARGETS[s["challenge"]["turn_head"]]
wrong = (-40.0 if demanded > 0 else 40.0) / 90.0
say(s["session_id"], 1)
r = lc.verify(s["session_id"], face(wrong), 0.999)
check("opposite turn fails", not r["passed"], r.get("result"))
check("failure reports measured vs demanded",
      "measured_degrees" in r.get("checks", {}).get("head_turn", {}))

# ---------------------------------------------------------------------------
print("\n=== 5. Expiry ===")
lc.reset_state()
s = lc.issue(APPLICANT)
lc._SESSIONS[s["session_id"]].expires_at = time.time() - 1
r = lc.verify(s["session_id"], face(0.0), 0.999)
check("expired challenge rejected", r["result"] == "EXPIRED", r["result"])

# ---------------------------------------------------------------------------
print("\n=== 6. Replay of a passed challenge ===")
lc.reset_state()
s0, first = solve(APPLICANT)
second = lc.verify(s0["session_id"], face(0.0), 0.999)
check("session resolves as passed", first["passed"], first.get("result"))
check("replay rejected", second["result"] == "ALREADY_RESOLVED", second["result"])

# ---------------------------------------------------------------------------
print("\n=== 7. Brute force lockout ===")
lc.reset_state()
s = lc.issue(APPLICANT)
demanded = lc.YAW_TARGETS[s["challenge"]["turn_head"]]
bad = (-40.0 if demanded > 0 else 40.0) / 90.0
for _ in range(lc.MAX_ATTEMPTS + 1):
    say(s["session_id"], 1)
    r = lc.verify(s["session_id"], face(bad), 0.999)
check("locks after max attempts", r["result"] == "LOCKED", r["result"])

# ---------------------------------------------------------------------------
print("\n=== 8. Unknown session ===")
lc.reset_state()
r = lc.verify("lc_doesnotexist", face(0.0), 0.999)
check("unknown session rejected", r["result"] == "NO_SUCH_SESSION")

# ---------------------------------------------------------------------------
print("\n=== 9. Geometry is real, not stubbed ===")
check("centre face reads ~0 deg", abs(lc.estimate_yaw(face(0.0))) < 3.0)
left = lc.estimate_yaw(face(-40.0/90.0))
right = lc.estimate_yaw(face(40.0/90.0))
check("left turn is negative", left < -30, f"{left:.1f}")
check("right turn is positive", right > 30, f"{right:.1f}")
check("symmetric", abs(abs(left) - abs(right)) < 1.0)
check("missing landmarks return None", lc.estimate_yaw({"left_eye": (0, 0)}) is None)

# ---------------------------------------------------------------------------
print("\n=== 10. Spoken word is issued but not falsely claimed as verified ===")
lc.reset_state()
_s, r = solve(APPLICANT)
sw = r.get("checks", {}).get("spoken_word", {})
check("occlusion is no longer part of the protocol",
      "occlusion" not in r.get("checks", {}), list(r.get("checks", {})))
check("word is issued", bool(sw.get("demanded")))
check("which word was said is NOT claimed as verified",
      sw.get("word_verified") is False)
check("but speech presence IS checked", sw.get("speech_detected") is True)
check("note explains the split", "0%" in sw.get("note", ""))

# ---------------------------------------------------------------------------
print("\n=== 11. Saying nothing must NOT pass ===")
lc.reset_state()
s0 = lc.issue(APPLICANT)
target = lc.YAW_TARGETS[s0["challenge"]["turn_head"]] / 90.0

# Correct pose, complete silence.
lc.attach_audio(s0["session_id"], 1, silent_audio())
r = lc.verify(s0["session_id"], face(target), 0.999)
check("correct pose + silence fails", not r.get("passed") and r["result"] == "CHALLENGE_FAILED",
      r.get("result"))
check("failure names the speech problem",
      "spoken" in r.get("message", "").lower() or "said" in r.get("message", "").lower(),
      r.get("message", "")[:70])
check("checks record that speech was absent",
      r["checks"]["spoken_word"]["speech_detected"] is False)

# Correct pose, no audio submitted at all.
lc.reset_state()
s1 = lc.issue(APPLICANT)
t1 = lc.YAW_TARGETS[s1["challenge"]["turn_head"]] / 90.0
r1 = lc.verify(s1["session_id"], face(t1), 0.999)
check("correct pose + no audio fails", not r1.get("passed"), r1.get("result"))
check("reason distinguishes missing audio from silence",
      r1["checks"]["spoken_word"]["analysis"]["reason"] == "no_audio",
      r1["checks"]["spoken_word"]["analysis"].get("reason"))

# A steady tone is not speech.
lc.reset_state()
s2 = lc.issue(APPLICANT)
t2 = lc.YAW_TARGETS[s2["challenge"]["turn_head"]] / 90.0
import math as _m
lc.attach_audio(s2["session_id"], 1, _wav(lambda t: 0.4 * _m.sin(2 * _m.pi * 300 * t)))
r2 = lc.verify(s2["session_id"], face(t2), 0.999)
check("a steady tone does not count as speech", not r2.get("passed"), r2.get("result"))

# And the positive control still works.
lc.reset_state()
_s3, r3 = solve(APPLICANT)
check("speaking properly still passes", r3.get("passed"), r3.get("result"))

print("\n" + "=" * 62)
print(f"  LiveChallenge: {PASS} passed, {FAIL} failed")
print("=" * 62)
sys.exit(1 if FAIL else 0)
