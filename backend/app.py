"""
Litmus Backend API - FaceGuard + VoicePrint with Ensemble Fusion
FastAPI backend for deepfake detection with disagreement-based routing
"""

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sys
import os
import tempfile
from typing import Dict, Any
from PIL import Image
import io

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
#
# Load .env before importing anything else from this package. The signing
# secrets are read at MODULE IMPORT time into module-level constants
# (trustline, livechallenge, report, consortium), so loading the file after
# those imports would silently leave every one of them on its demo default —
# the failure would be invisible until someone forged a verification code.
#
# python-dotenv is optional: on a real deployment the variables come from the
# host's own environment and no .env file exists. Real environment variables
# always win; the file never overwrites them.
try:
    from dotenv import load_dotenv

    load_dotenv(
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        override=False,
    )
except ImportError:  # pragma: no cover — the file path is simply not used
    pass

# Add models paths to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'models', 'face'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'models', 'voice'))

from test_face import run_face_detection
from test_face_model2 import run_face_detection_model2
from fuse_face_verdict import fuse_face_verdict
import faceguard

from test_voice import run_voice_detection
from test_voice_v2 import run_voice_detection_v2
from fuse_voice_verdict import fuse_voice_verdict

import fri
import consortium
import livechallenge
import assurance
import report
import mailer
import demo_data
from trustline import (
    initiate_call_session,
    verify_phrase,
    get_fraud_feed,
    get_session,
    list_active_sessions,
    LEGITIMATE_PURPOSES,
    SCAM_INDICATOR_PURPOSES,
)

app = FastAPI(
    title="Litmus API — FaceGuard + VoicePrint + TrustLine",
    version="3.0.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
#
# Two deployment shapes are supported:
#
#   same-origin   the API serves the built console at /console, so the browser
#                 never makes a cross-origin request and CORS is irrelevant.
#   split         the console is hosted separately (Vercel) and calls this API
#                 across origins, which is where the settings below matter.
#
# LITMUS_ALLOWED_ORIGINS is a comma-separated allowlist, e.g.
#   https://litmus.vercel.app,https://litmus-git-main-you.vercel.app
#
# Left unset it falls back to "*", which keeps local development and the
# same-origin deployment working. Note that "*" cannot be combined with
# credentialed requests per the CORS spec, so allow_credentials is enabled only
# when a real allowlist is configured.
_origins_env = os.environ.get("LITMUS_ALLOWED_ORIGINS", "").strip()
_allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()] or ["*"]
_allow_credentials = _allowed_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    # Without this the browser hides these from cross-origin JavaScript, and the
    # downloaded record silently loses its reference number and verification
    # code — the two things that make the document checkable.
    expose_headers=["X-Litmus-Reference", "X-Litmus-Code"],
)


class FaceDetectionResponse(BaseModel):
    """Response model for face detection endpoint"""
    verdict: str  # 'real' | 'fake' | 'uncertain'
    confidence_band: str  # 'high' | 'review'
    m1_score: float  # Model 1 real score
    m2_score: float  # Model 2 real score
    explanation: str
    action: str  # 'auto-approve' | 'route-to-review'
    
    # Individual model details for transparency
    model1_verdict: str
    model2_verdict: str
    model1_confidence: float
    model2_confidence: float
    agreement: bool


class VoiceDetectionResponse(BaseModel):
    """Response model for voice detection endpoint"""
    verdict: str          # 'real' | 'spoof' | 'uncertain'
    confidence_band: str  # 'high' | 'review'
    m1_score: float       # M1 real_score
    m2_score: float       # M2 real_score
    explanation: str
    action: str           # 'auto-approve' | 'route-to-review'

    model1_verdict: str
    model2_verdict: str
    model1_confidence: float
    model2_confidence: float
    agreement: bool


@app.on_event("startup")
async def _seed_demo_history() -> None:
    """
    Populate the seeded fraud history so the demonstration numbers have a past.

    Idempotent, and every seeded record is fabricated — see demo_data.py.
    """
    try:
        result = demo_data.seed(consortium)
        print(f"  seeded {result['seeded_signals']} demo fraud signals "
              f"across {result['numbers']} numbers")
    except Exception as exc:  # noqa: BLE001 — never block startup on demo data
        print(f"  demo seeding skipped: {exc}")


@app.get("/api/v1/demo/numbers")
async def demo_numbers() -> Dict[str, Any]:
    """The seeded numbers and what each one demonstrates."""
    return demo_data.catalogue()


@app.get("/console", response_class=HTMLResponse)
async def console():
    """
    Serve the Trust Operations Console from the API itself.

    Same-origin by construction, so the live demo never trips over CORS or a
    file:// origin — which is exactly the class of failure you do not want in
    front of a jury.
    """
    # The console now lives inside the React app (frontend/web) as a hash
    # route, so we serve the built single-file bundle and let the client
    # router land on /#/console.
    dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "web", "dist", "index.html")
    if not os.path.exists(dist):
        raise HTTPException(
            status_code=503,
            detail=(
                "Frontend bundle not built. Run: "
                "cd frontend/web && npm install && SINGLE=1 npm run build"
            ),
        )
    with open(dist, "r", encoding="utf-8") as fh:
        return HTMLResponse(fh.read())


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Litmus API — FaceGuard + VoicePrint + TrustLine",
        "status": "online",
        "version": "3.0.0",
        "endpoints": {
            "inbound": {
                "face_detection":  "/api/v1/face/detect",
                "voice_detection": "/api/v1/voice/detect",
                "fused_trust_score": "/api/v1/verify/score",
            },
            "outbound": {
                "initiate_call": "/api/v1/trustline/initiate",
                "verify_call":   "/api/v1/trustline/verify",
                "sessions":      "/api/v1/trustline/sessions",
                "fraud_feed":    "/api/v1/trustline/fraud-feed",
                "purposes":      "/api/v1/trustline/purposes",
            },
            "health": "/health",
        },
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "models": {
            "face_model1": "Vision Transformer baseline (second opinion)",
            "face_model2": "CNN baseline (second opinion)",
            "voice_model1": "Wav2Vec2 fine-tune",
            "voice_model2": "Wav2Vec2 base",
        },
        "fusion": "disagreement-based routing with confidence threshold"
    }


@app.post("/api/v1/face/detect", response_model=FaceDetectionResponse)
async def detect_face_deepfake(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Detect if an uploaded face image is real or AI-generated/deepfake.
    
    Uses ensemble of two models with disagreement-based routing:
    - When models agree with high confidence: auto-approve
    - When models disagree or low confidence: route to human review
    
    Args:
        file: Uploaded image file (JPG, PNG)
        
    Returns:
        FaceDetectionResponse with fused verdict and routing decision
    """
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Expected image/*"
        )
    
    try:
        # Read image bytes
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # Save temporarily for model inference (cross-platform temp dir)
        suffix = os.path.splitext(file.filename or "upload")[1] or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(image_bytes)
            temp_path = tmp.name
        
        # Run both models
        model1_result = run_face_detection(temp_path)
        model2_result = run_face_detection_model2(temp_path)
        
        # Fuse verdicts with confidence-aware routing
        fused_result = fuse_face_verdict(model1_result, model2_result)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Map to response format
        return FaceDetectionResponse(
            verdict=fused_result['final_verdict'],
            confidence_band='high' if fused_result['confidence'] == 'high' else 'review',
            m1_score=model1_result['real_score'],
            m2_score=model2_result['real_score'],
            explanation=fused_result['explanation'],
            action=fused_result['action'],
            model1_verdict=fused_result['model1_verdict'],
            model2_verdict=fused_result['model2_verdict'],
            model1_confidence=fused_result['model1_confidence'],
            model2_confidence=fused_result['model2_confidence'],
            agreement=fused_result['agreement']
        )
        
    except Exception as e:
        # Clean up on error
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing image: {str(e)}"
        )


@app.post("/api/v1/face/analyze")
async def face_analyze(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Calibrated FaceGuard pipeline, returned stage by stage.

    Differs from /face/detect in four ways, each measured before adoption:
    MTCNN face cropping, test-time augmentation, a cross-validated decision
    threshold, and asymmetric approve/escalate gates. Model 2 no longer votes —
    it runs as a check against Model 1's documented demographic bias.

    The stage structure exists so the console can render the analysis as it
    resolves, and so a reviewer can see which step produced the decision.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"Expected an image, got {file.content_type}")

    data = await file.read()
    try:
        Image.open(io.BytesIO(data)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail=f"'{file.filename}' is not a decodable image.")

    suffix = os.path.splitext(file.filename or "u.jpg")[1] or ".jpg"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        return faceguard.analyze(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.get("/api/v1/face/models")
async def get_model_info():
    """
    Get information about the models used in the ensemble.
    """
    return {
        "ensemble": {
            "model1": {
                "name": "Vision Transformer baseline",
                "type": "Vision Transformer",
                "source": "HuggingFace"
            },
            "model2": {
                "name": "CNN baseline",
                "type": "CNN-based detector",
                "source": "HuggingFace"
            }
        },
        "fusion_strategy": {
            "type": "disagreement-based routing",
            "confidence_threshold": 0.70,
            "routing_logic": "Both models agree + both confident → auto-approve, else → human review"
        },
        "known_limitations": [
            "Agreement doesn't guarantee correctness - both models can share the same blind spot",
            "Heavily compressed or preprocessed images may trigger false positives",
            "Performance on modern face-swap tools (2024+) requires ongoing validation"
        ]
    }


@app.post("/api/v1/voice/detect", response_model=VoiceDetectionResponse)
async def detect_voice_deepfake(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Detect if an uploaded audio clip is real or AI-generated/voice-cloned.

    Uses ensemble of two models with asymmetric fusion:
    - Both models say real with high confidence → auto-approve
    - Either model says spoof → route to human review
    - Both say real but confidence low → route to human review

    Known limitations:
    - Catches ~35% of 2019-era TTS/VC synthesis (FoR dataset)
    - Catches ~0% of modern neural TTS (ElevenLabs/Edge-TTS quality)
    - Shows false positives on some female vocal profiles (~20% FP rate)
    - By design: human review is the safety net, models flag risk

    Args:
        file: Uploaded audio file (.wav preferred; .mp3 accepted)

    Returns:
        VoiceDetectionResponse with fused verdict and routing decision
    """
    allowed_types = ("audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3",
                     "audio/mp4", "audio/x-m4a", "audio/flac", "application/octet-stream")
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Expected audio/wav or audio/mpeg"
        )

    temp_path = None
    try:
        audio_bytes = await file.read()

        # Write to cross-platform temp file (.wav preferred by both models)
        suffix = os.path.splitext(file.filename or "upload")[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        # Run both models
        model1_result = run_voice_detection(temp_path)
        model2_result = run_voice_detection_v2(temp_path)

        # Fuse with asymmetric voice logic
        fused_result = fuse_voice_verdict(model1_result, model2_result)

        return VoiceDetectionResponse(
            verdict=fused_result["final_verdict"],
            confidence_band="high" if fused_result["confidence"] == "high" else "review",
            m1_score=model1_result["real_score"],
            m2_score=model2_result["real_score"],
            explanation=fused_result["explanation"],
            action=fused_result["action"],
            model1_verdict=fused_result["model1_verdict"],
            model2_verdict=fused_result["model2_verdict"],
            model1_confidence=fused_result["model1_confidence"],
            model2_confidence=fused_result["model2_confidence"],
            agreement=fused_result["agreement"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing audio: {str(e)}"
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.get("/api/v1/voice/models")
async def get_voice_model_info():
    """Get information about the voice ensemble models."""
    return {
        "ensemble": {
            "model1": {
                "name": "Wav2Vec2 fine-tune",
                "type": "Wav2Vec2-based audio classifier",
                "source": "HuggingFace",
                "real_accuracy": "90%",
                "fake_detection": "0%",
            },
            "model2": {
                "name": "Wav2Vec2 base",
                "type": "Wav2Vec2 base",
                "source": "HuggingFace",
                "real_accuracy": "80%",
                "fake_detection": "35%",
            },
        },
        "fusion_strategy": {
            "type": "asymmetric spoof-priority routing",
            "confidence_threshold": 0.70,
            "routing_logic": (
                "Both REAL + both confident → auto-approve; "
                "either SPOOF → route-to-review; "
                "low confidence → route-to-review"
            ),
        },
        "validated_on": {
            "real_voice": "FoR dataset originals (20 samples) — 80% correct",
            "fake_FoR_era": "FoR dataset synthetics (20 samples) — 35% detected",
            "fake_modern_TTS": "Edge-TTS / ElevenLabs — 0% detected",
        },
        "known_limitations": [
            "Cannot detect modern neural TTS (ElevenLabs, Edge-TTS, etc.)",
            "False positive rate ~20% on certain female vocal profiles",
            "Models are a first-pass risk filter — human review is the safety net",
            "Architecture compensates via challenge-response code (TrustLine), "
            "not biometric accuracy alone",
        ],
    }


# ===========================================================================
# TrustLine — outbound call authentication
# ===========================================================================

class InitiateCallRequest(BaseModel):
    """Agent-side: start an authenticated outbound call."""
    customer_id: str
    customer_phone: str
    agent_id: str
    agent_name: str
    purpose: str
    channel: str = "app_push"


class VerifyPhraseRequest(BaseModel):
    """Customer-side: check whether an incoming call is genuinely TVS Credit."""
    customer_id: str
    claimed_phrase: str = ""
    caller_number: str | None = None
    claimed_purpose: str | None = None


@app.post("/api/v1/trustline/initiate")
async def trustline_initiate(req: InitiateCallRequest) -> Dict[str, Any]:
    """
    Mint an authenticated outbound call session.

    Called the moment a TVS Credit agent or voicebot dials a customer. Returns
    the verification phrase for the agent's CRM screen; the same phrase is
    pushed to the customer out-of-band.
    """
    try:
        return initiate_call_session(
            customer_id=req.customer_id,
            customer_phone=req.customer_phone,
            agent_id=req.agent_id,
            agent_name=req.agent_name,
            purpose=req.purpose,
            channel=req.channel,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/trustline/verify")
async def trustline_verify(req: VerifyPhraseRequest) -> Dict[str, Any]:
    """
    Customer-side verification.

    Someone called claiming to be TVS Credit. The customer types the code they
    were given. Returns GENUINE, NO_ACTIVE_SESSION, PHRASE_MISMATCH, or
    SCAM_CONFIRMED — and files a fraud report on every negative outcome.
    """
    return verify_phrase(
        customer_id=req.customer_id,
        claimed_phrase=req.claimed_phrase,
        caller_number=req.caller_number,
        claimed_purpose=req.claimed_purpose,
    )


@app.get("/api/v1/trustline/sessions")
async def trustline_sessions() -> Dict[str, Any]:
    """Active and recently-verified outbound call sessions, for the console."""
    return {"sessions": list_active_sessions()}


@app.get("/api/v1/trustline/session/{session_id}")
async def trustline_session(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"No session {session_id}")
    return session


@app.get("/api/v1/trustline/fraud-feed")
async def trustline_fraud_feed(limit: int = 50) -> Dict[str, Any]:
    """
    Live fraud intelligence generated by the attackers themselves.

    Every failed verification is a scammer revealing an active campaign. This
    feed is the piece an inbound-only KYC vendor structurally cannot produce.
    """
    return get_fraud_feed(limit=limit)


@app.get("/api/v1/trustline/purposes")
async def trustline_purposes() -> Dict[str, Any]:
    """Call purposes TVS Credit does and does not make — drives the customer UI."""
    return {
        "legitimate": LEGITIMATE_PURPOSES,
        "scam_indicators": SCAM_INDICATOR_PURPOSES,
    }


# ===========================================================================
# Fused Litmus Trust Score
# ===========================================================================

BAND_RANGES = {"high": (75.0, 100.0), "medium": (45.0, 74.0), "low": (0.0, 44.0)}


def _evidence_score(s1: float, s2: float, verdict: str, confidence: str,
                    c1: float, c2: float, positive: str, negative: str) -> float:
    """
    Turn two model scores into one 0-100 evidence score.

    The uncertain branch matters more than the confident ones, because with a
    biased Model 1 it is the branch most inputs actually land in. It must stay
    CONTINUOUS: an earlier version returned a flat 50 for every uncertain case,
    which made six visually different faces — model outputs ranging from 0.007
    to 0.999 — all score identically. That is not conservatism, it is discarding
    the evidence, and it makes a working system look hardcoded.

    So uncertainty is scored on the mean of the two real-scores. The routing
    decision is still made by _resolve_band() from the verdict states, so
    safety is unchanged — but the number now orders the review queue by how
    real the evidence actually looks, which is what an officer working through
    that queue needs.
    """
    if verdict == positive and confidence == "high":
        return 100.0 * min(c1, c2)
    if verdict == negative:
        return 100.0 * (1.0 - min(c1, c2))
    return 100.0 * (s1 + s2) / 2.0


def _resolve_band(modalities: Dict[str, Any]) -> tuple:
    """
    Decide the routing band from the VERDICT STATES, not from score arithmetic.

    This ordering matters and is the whole safety argument of the system:

      low     — a modality positively identified synthesis with high confidence.
                Only this escalates to the fraud desk.
      medium  — models disagreed, or one was unconfident. The system does not
                know. Routes to a human.
      high    — every modality agreed 'real' with high confidence.

    Critically, UNCERTAINTY NEVER ESCALATES. Litmus's own measured bias is that
    Model 1 systematically over-flags South Asian faces, so disagreement is the
    expected state for a legitimate Indian applicant. Letting arithmetic push
    that into the fraud-desk band would turn a disclosed model bias into a
    discriminatory outcome. Disagreement means "ask a person", full stop —
    which is also what RBI's FREE-AI fairness and accountability principles
    require of a high-risk automated decision.
    """
    fake_verdicts = {"fake", "spoof"}

    confident_synthetic = any(
        m["verdict"] in fake_verdicts
        and m.get("action") in ("auto-approve", "escalate", "escalate-to-fraud-desk")
        for m in modalities.values()
    )
    if confident_synthetic:
        return "low", "escalate-to-fraud-desk", (
            "Both models positively identified synthetic media with high "
            "confidence. Escalate to the fraud desk; do not disburse."
        )

    needs_review = any(m["action"] != "auto-approve" for m in modalities.values())
    if needs_review:
        return "medium", "route-to-review", (
            "The ensemble could not reach confident agreement. Route to a branch "
            "officer for manual review. This is not an adverse finding against "
            "the applicant."
        )

    return "high", "auto-approve", "Proceed with standard onboarding."


@app.post("/api/v1/verify/score")
async def fused_trust_score(
    face: UploadFile = File(None),
    voice: UploadFile = File(None),
) -> Dict[str, Any]:
    """
    Fuse whichever modalities were supplied into one Litmus Trust Score.

    Scoring is deliberately conservative and asymmetric. Each modality
    contributes a 0-100 sub-score; the fused score is the weighted mean, then
    penalised for uncertainty. A single modality routing to review is enough
    to pull the whole application out of the auto-approve band — the system
    never averages away a red flag.

    Weights reflect measured reliability, not intuition. FaceGuard carries
    more weight because its ensemble produced zero silent wrong auto-approvals
    on demo-condition samples; VoicePrint carries less because its own
    measured ceiling against modern neural TTS is 0%.
    """
    if face is None and voice is None:
        raise HTTPException(
            status_code=400,
            detail="Supply at least one of 'face' or 'voice'.",
        )

    modalities: Dict[str, Any] = {}
    temp_paths: list = []

    try:
        # --- Face leg ------------------------------------------------------
        if face is not None:
            face_bytes = await face.read()

            # Verify it actually decodes before spending model time on it, and
            # fail as a 400 rather than a 500 — a bad upload is the caller's
            # error, not a server fault. (A truncated download or a saved HTML
            # error page arriving as ".jpg" is the common real-world case.)
            try:
                Image.open(io.BytesIO(face_bytes)).verify()
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"'{face.filename}' is not a decodable image. Check the "
                        f"file downloaded correctly and is not an HTML error page."
                    ),
                )

            suffix = os.path.splitext(face.filename or "f.jpg")[1] or ".jpg"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(face_bytes)
                temp_paths.append(tmp.name)

            # Calibrated pipeline: MTCNN crop -> TTA -> asymmetric gates.
            # Deliberately NOT the old equal-weight fusion of both models —
            # Model 2 scores AUC 0.501 on our benchmark, so averaging it in
            # measurably destroys signal (pair AUC 0.590 vs 0.737 for Model 1
            # alone). It now runs as a bias check, not as a second vote.
            fa = faceguard.analyze(temp_paths[-1])
            prim = fa["stages"]["primary"]
            ctx = fa["stages"]["context"]
            m1_real = prim["real_score"]

            if fa["verdict"] == "real":
                sub = 100.0 * m1_real
            elif fa["verdict"] == "fake":
                sub = 100.0 * m1_real          # a low real-score IS the low sub-score
            else:
                sub = 100.0 * m1_real          # continuous either way; the band
                                               # is decided from the verdict state

            modalities["face"] = {
                "module": "FaceGuard",
                "sub_score": round(sub, 1),
                "verdict": fa["verdict"],
                "action": "auto-approve" if fa["action"] == "auto-approve" else "route-to-review",
                "explanation": fa["explanation"],
                "m1_real_score": round(m1_real, 4),
                "m2_real_score": round(ctx["real_score"], 4),
                "models_agree": not ctx["bias_signature_detected"],
                "disagreement": round(abs(m1_real - ctx["real_score"]), 4),
                "calibrated": True,
                "face_detected": bool(fa["stages"]["face_detection"].get("found")),
                "gates": {
                    "approve_above": prim["approve_above"],
                    "escalate_below": prim["escalate_below"],
                },
                "caveat": (
                    "Model 2 is a demographic-bias check, not a second vote — it "
                    "scored AUC 0.501 on our benchmark."
                ),
            }

        # --- Voice leg -----------------------------------------------------
        if voice is not None:
            voice_bytes = await voice.read()
            suffix = os.path.splitext(voice.filename or "v.wav")[1] or ".wav"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(voice_bytes)
                temp_paths.append(tmp.name)

            v1 = run_voice_detection(temp_paths[-1])
            v2 = run_voice_detection_v2(temp_paths[-1])
            vf = fuse_voice_verdict(v1, v2)

            sub = _evidence_score(
                v1["real_score"], v2["real_score"],
                vf["final_verdict"], vf["confidence"],
                vf["model1_confidence"], vf["model2_confidence"],
                positive="real", negative="spoof",
            )

            modalities["voice"] = {
                "module": "VoicePrint",
                "sub_score": round(sub, 1),
                "verdict": vf["final_verdict"],
                "action": vf["action"],
                "explanation": vf["explanation"],
                "m1_real_score": round(v1["real_score"], 4),
                "m2_real_score": round(v2["real_score"], 4),
                "models_agree": vf["agreement"],
                "disagreement": round(abs(v1["real_score"] - v2["real_score"]), 4),
                "caveat": (
                    "Measured 0% detection against modern neural TTS. This "
                    "sub-score is a weak signal by design and must not be "
                    "read as a liveness guarantee."
                ),
            }

        # --- Fuse ----------------------------------------------------------
        weights = {"face": 0.65, "voice": 0.35}
        present = [k for k in ("face", "voice") if k in modalities]
        total_w = sum(weights[k] for k in present)
        raw = sum(modalities[k]["sub_score"] * weights[k] for k in present) / total_w

        # The band is decided by verdict state; the score is then expressed
        # INSIDE that band. Number and decision can therefore never contradict
        # each other on screen — an officer never sees "82/100, escalate".
        band, action, guidance = _resolve_band(modalities)
        lo, hi = BAND_RANGES[band]
        score = round(lo + (hi - lo) * (max(0.0, min(100.0, raw)) / 100.0), 1)

        routed_to_review = [
            k for k in present if modalities[k]["action"] != "auto-approve"
        ]

        return {
            "litmus_trust_score": score,
            "confidence_band": band,
            "action": action,
            "guidance": guidance,
            "modalities_evaluated": present,
            "modalities": modalities,
            "fusion": {
                "raw_weighted_score": round(raw, 1),
                "band_range": [lo, hi],
                "weights_applied": {k: weights[k] for k in present},
                "routed_to_review": routed_to_review,
                "rule": (
                    "Routing band is resolved from verdict states, then the "
                    "weighted sub-score is expressed within that band. Weights "
                    "reflect measured per-modality reliability, not assumed "
                    "parity. Uncertainty routes to a human and never escalates."
                ),
            },
            "disclosure": (
                "This score is a routing aid, not an adjudication. No applicant "
                "is rejected on a model verdict alone — low scores route to a "
                "human, per RBI FREE-AI principles of fairness and accountability."
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring error: {e}")
    finally:
        for p in temp_paths:
            if os.path.exists(p):
                os.remove(p)


# ===========================================================================
# Assurance — reading the same evidence in the positive direction
# ===========================================================================

@app.post("/api/v1/assurance/assess")
async def assurance_assess(
    # Form fields rather than a Pydantic body: FastAPI cannot mix a JSON body
    # model with a multipart file upload in one request, and the face capture
    # has to travel with the rest of the evidence.
    livechallenge_session: str = Form(None),
    caller_number: str = Form(None),
    has_bureau_file: bool = Form(False),
    face: UploadFile = File(None),
) -> Dict[str, Any]:
    """
    Produce an identity-assurance level from whatever verification evidence exists.

    This is NOT a credit score and the response says so explicitly. It answers
    "how strongly do we know who this is", which is the question that blocks a
    thin-file applicant — as distinct from "will they repay", which the
    underwriter still owns.
    """
    face_result = None
    if face is not None:
        data = await face.read()
        try:
            Image.open(io.BytesIO(data)).verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Face capture is not a decodable image.")
        suffix = os.path.splitext(face.filename or "f.jpg")[1] or ".jpg"
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            face_result = faceguard.analyze(tmp_path)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    live = None
    if livechallenge_session:
        sess = livechallenge.get_session(livechallenge_session)
        if sess:
            # A challenge that has been ISSUED but not yet attempted is absent
            # evidence, not failed evidence. Reporting it as failed would file
            # an adverse finding against an applicant who simply has not been
            # asked yet — the exact confusion this module is built to avoid.
            status = sess.get("status")
            if status == "passed":
                live = {"passed": True, "session": sess}
            elif status in ("failed", "locked", "expired"):
                live = {"passed": False, "session": sess}
            else:
                live = None   # "issued" — outstanding, not answered

    net = None
    if caller_number:
        net = consortium.lookup(caller_number)
        net["fri"] = fri.check_number(caller_number).to_dict()

    return assurance.assess(
        liveness=live,
        face=face_result,
        network=net,
        has_bureau_file=has_bureau_file,
    )


@app.get("/api/v1/assurance/model")
async def assurance_model() -> Dict[str, Any]:
    """The weights and levels, so the scoring is inspectable rather than opaque."""
    return {
        "weights": {
            "liveness": assurance.W_LIVENESS,
            "face": assurance.W_FACE,
            "capture": assurance.W_CAPTURE,
            "network": assurance.W_NETWORK,
        },
        "levels": assurance.LEVELS,
        "principle": (
            "Weights are ordered by measured reliability. LiveChallenge is a "
            "verifiable fact with a 0.44% blind-guess probability, so it carries "
            "the most. FaceGuard is a model at 0.934 AUC, so it carries less."
        ),
    }


# ===========================================================================
# LiveChallenge — inbound verification that does not depend on detection
# ===========================================================================

class IssueChallengeRequest(BaseModel):
    applicant_id: str
    # Operator-supplied reference (an application number, a phone number).
    # It appears on the evidence record and follows the applicant through
    # to the assurance assessment.
    applicant_ref: str | None = None


@app.post("/api/v1/livechallenge/issue")
async def livechallenge_issue(req: IssueChallengeRequest) -> Dict[str, Any]:
    """
    Mint a random physical challenge for a video-KYC session.

    Must be called at verification time. The challenge is derived from the
    session under a server secret, so it cannot exist — and therefore cannot be
    answered — before the applicant is actually on the call.
    """
    return livechallenge.issue(req.applicant_id, req.applicant_ref or "")


@app.post("/api/v1/livechallenge/verify")
async def livechallenge_verify(
    session_id: str,
    file: UploadFile = File(...),
    audio: UploadFile = File(None),
) -> Dict[str, Any]:
    """
    Check a response frame against the issued challenge.

    Runs MTCNN on the frame, measures head yaw and cheek occlusion
    geometrically from the landmarks, and compares against what was demanded.
    No classifier is involved in the decision.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"Expected an image, got {file.content_type}")

    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Not a decodable image.")

    try:
        import numpy as _np
        faces = faceguard._face_detector().detect_faces(_np.array(img))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Face detection failed: {e}")

    if not faces:
        return {
            "result": "NO_FACE",
            "passed": False,
            "message": "No face found in the response frame.",
        }

    # Attach the spoken response before verifying, so the result can report
    # whether audio was captured for this round. It is never scored.
    if audio is not None:
        sess = livechallenge.get_session(session_id)
        if sess:
            livechallenge.attach_audio(session_id, sess.get("round", 1), await audio.read())

    faces.sort(key=lambda f: f["box"][2] * f["box"][3], reverse=True)
    best = faces[0]
    return livechallenge.verify(
        session_id=session_id,
        landmarks=best.get("keypoints", {}),
        detector_confidence=float(best.get("confidence", 1.0)),
    )


@app.get("/api/v1/report/livechallenge/{session_id}")
async def report_livechallenge(session_id: str, lender: str = "TVS Credit"):
    """
    Issue the PDF evidence record for a liveness session.

    Generated server-side and signed. A record the browser could assemble would
    be the verified party issuing their own proof, which is worth nothing.
    """
    from fastapi.responses import Response
    sess = livechallenge.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="No such challenge session")

    pdf, ref, code = report.livechallenge_record(
        session=sess,
        evidence=livechallenge.get_evidence(session_id),
        lender=lender,
        applicant_ref=sess.get("applicant_ref", ""),
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{ref}.pdf"',
            "X-Litmus-Reference": ref,
            "X-Litmus-Code": code,
        },
    )


class AssuranceReportRequest(BaseModel):
    assessment: Dict[str, Any]
    applicant_ref: str | None = None
    contact: str | None = None
    lender: str = "TVS Credit"


@app.post("/api/v1/report/assurance")
async def report_assurance(req: AssuranceReportRequest):
    """Issue the PDF evidence record for an assurance assessment."""
    from fastapi.responses import Response
    if not req.assessment or "assurance_score" not in req.assessment:
        raise HTTPException(status_code=400, detail="An assessment is required.")

    pdf, ref, code = report.assurance_record(
        assessment=req.assessment,
        lender=req.lender,
        applicant_ref=req.applicant_ref or "",
        contact=req.contact or "",
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{ref}.pdf"',
            "X-Litmus-Reference": ref,
            "X-Litmus-Code": code,
        },
    )


class EmailRecordRequest(BaseModel):
    email: str
    lender: str = "TVS Credit"
    # Exactly one of these identifies what to send.
    livechallenge_session: str | None = None
    assessment: Dict[str, Any] | None = None
    applicant_ref: str | None = None
    contact: str | None = None


@app.post("/api/v1/report/email")
async def report_email(req: EmailRecordRequest) -> Dict[str, Any]:
    """
    Issue a record and deliver it to an address.

    The email is optional throughout the product: a verification is complete
    with or without one, and the PDF is downloadable regardless. When SMTP is
    unconfigured the response says the record was NOT sent rather than implying
    it arrived.
    """
    if not mailer.valid_address(req.email):
        raise HTTPException(status_code=400, detail=f"'{req.email}' is not a valid address.")

    if req.livechallenge_session:
        sess = livechallenge.get_session(req.livechallenge_session)
        if not sess:
            raise HTTPException(status_code=404, detail="No such challenge session")
        pdf, ref, code = report.livechallenge_record(
            session=sess,
            evidence=livechallenge.get_evidence(req.livechallenge_session),
            lender=req.lender,
            applicant_ref=sess.get("applicant_ref", ""),
        )
        passed = sess.get("status") == "passed"
        headline = ("Physical presence was established for this session."
                    if passed else "Presence was not established for this session.")
        detail = (
            f"The applicant completed {sess.get('rounds_passed', 0)} of "
            f"{sess.get('rounds_required', 3)} randomised challenge rounds. Each round was "
            f"generated after the previous response arrived, so a pre-recorded or "
            f"synthetically generated stream could not have contained the answers."
        )
        kind = "liveness"
    elif req.assessment:
        pdf, ref, code = report.assurance_record(
            assessment=req.assessment,
            lender=req.lender,
            applicant_ref=req.applicant_ref or "",
            contact=req.contact or "",
        )
        headline = str(req.assessment.get("label", "Identity assurance assessment"))
        detail = str(req.assessment.get("licenses", ""))
        kind = "assurance"
    else:
        raise HTTPException(
            status_code=400,
            detail="Supply either livechallenge_session or assessment.")

    outcome = mailer.send_record(
        to_address=req.email, pdf_bytes=pdf, filename=f"{ref}.pdf",
        kind=kind, reference=ref, code=code,
        headline=headline, detail=detail, lender=req.lender,
    )
    return {"reference": ref, "verification_code": code, "delivery": outcome}


@app.get("/api/v1/report/mail-status")
async def report_mail_status() -> Dict[str, Any]:
    """Whether delivery is configured, so the console can say so up front."""
    return mailer.status()


@app.get("/api/v1/report/verify")
async def report_verify(payload: str, code: str) -> Dict[str, Any]:
    """
    Check a code printed on a record against its stated contents.

    This is what makes the printed code meaningful: the document can be proved
    against the issuing server rather than merely looking official.
    """
    ok = report.check_code(payload, code)
    return {
        "valid": ok,
        "message": (
            "The code matches these contents. The record was issued by this server "
            "and has not been altered."
            if ok else
            "The code does not match. Either the record was altered, or it was not "
            "issued by this server."
        ),
    }


@app.get("/api/v1/livechallenge/audio/{session_id}/{round_index}")
async def livechallenge_audio(session_id: str, round_index: int):
    """
    Replay the spoken response for one round.

    This exists so a reviewer can hear what the applicant actually said. It is
    evidence for a person, not an input to any automated decision.
    """
    from fastapi.responses import Response
    data = livechallenge.get_audio(session_id, round_index)
    if not data:
        raise HTTPException(status_code=404, detail="No audio recorded for that round")
    return Response(content=data, media_type="audio/webm")


@app.get("/api/v1/livechallenge/session/{session_id}")
async def livechallenge_session(session_id: str) -> Dict[str, Any]:
    s = livechallenge.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="No such challenge session")
    return s


@app.get("/api/v1/livechallenge/info")
async def livechallenge_info() -> Dict[str, Any]:
    """Protocol parameters, including the measured blind-guess probability."""
    return {
        "poses": list(livechallenge.YAW_TARGETS),
        "occlusions": [o[0] for o in livechallenge._OCCLUSIONS],
        "rounds_required": livechallenge.ROUNDS_REQUIRED,
        "combinations_per_round": len(livechallenge.YAW_TARGETS) * len(livechallenge._OCCLUSIONS),
        "blind_guess_probability": livechallenge.guess_probability(),
        "ttl_seconds": livechallenge.SESSION_TTL_SECONDS,
        "yaw_tolerance_degrees": livechallenge.YAW_TOLERANCE,
        "principle": (
            "A pre-recorded or pre-generated stream is fixed before the challenge "
            "exists, so it cannot contain a response to it. The attack fails by "
            "construction rather than by detection."
        ),
    }


# ===========================================================================
# Fraud intelligence — DoT FRI + TrustLine Consortium
# ===========================================================================

@app.get("/api/v1/intel/fri/status")
async def fri_status() -> Dict[str, Any]:
    """Which mode the FRI client is in. Surfaced so nobody mistakes simulated
    output for a live government risk classification."""
    return fri.status()


@app.get("/api/v1/intel/fri/check/{number}")
async def fri_check(number: str) -> Dict[str, Any]:
    """Risk tier for one caller number, per DoT's Financial Fraud Risk Indicator."""
    return fri.check_number(number).to_dict()


@app.get("/api/v1/intel/consortium/stats")
async def consortium_stats() -> Dict[str, Any]:
    """Network-wide view: members, corroborated campaigns, coverage multiple."""
    return consortium.network_stats()


@app.get("/api/v1/intel/consortium/lookup/{number}")
async def consortium_lookup(number: str) -> Dict[str, Any]:
    """What every member institution collectively knows about one number."""
    return consortium.lookup(number)


class ContributeRequest(BaseModel):
    member_id: str
    caller_number: str
    severity: str = "high"
    claimed_purpose: str | None = None


@app.post("/api/v1/intel/consortium/contribute")
async def consortium_contribute(req: ContributeRequest) -> Dict[str, Any]:
    """
    Publish a fraud signal to the consortium.

    Note the absence of a customer field: the API cannot leak customer identity
    because it never accepts it. Members share the attacker, never the victim.
    """
    try:
        return consortium.contribute(
            member_id=req.member_id,
            caller_number=req.caller_number,
            severity=req.severity,
            claimed_purpose=req.claimed_purpose,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/intel/consortium/members")
async def consortium_members() -> Dict[str, Any]:
    return {"members": consortium.members()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
