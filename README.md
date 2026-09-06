# Litmus

**A two-way AI trust layer for TVS Credit's lending pipeline.**
TVS Credit E.P.I.C 8.0 — IT Challenge · Problem Statement (b): Decoding Machine-Generated Trust

> Every fake has a tell. We catch it before the loan does.

---

## What this is

Two questions, one platform:

- **Inbound** — is this loan applicant a real, honest human?
- **Outbound** — is this caller, claiming to be TVS Credit, actually TVS Credit?

Every established KYC vendor (HyperVerge, Signzy, IDfy, Karza) solves the first.
None solve the second, because their contract is with the lender, not with the
borrower being scammed. That gap is where TrustLine sits.

---

## Build status — honest

| Module | What it does | Status |
|---|---|---|
| **FaceGuard** | Two-model deepfake ensemble on the V-CIP frame | **Built, live API** |
| **VoicePrint** | Two-model spectral ensemble on verification-call audio | **Built, live API** |
| **TrustLine** | HMAC challenge-response outbound call authentication | **Built, live API** |
| Identity Forensics | Document tamper detection | Architecture only |
| CallShield | Synthetic call-pattern flagging | Architecture only |
| FormPulse | Behavioural biometrics on the application form | Architecture only |

Three modules run. Three are design. The deck labels which is which on the
architecture slide — that labelling is deliberate and should not be removed.

---

## Running it

Python 3.11. All dependencies are already installed in the global environment
on the build machine; on a fresh machine:

```bash
pip install -r backend/requirements.txt
```

Start the API (models load on first import, ~15s):

```bash
cd backend
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Then open the operations console:

```
http://127.0.0.1:8000/console
```

The console is served **by the API itself**, so it is same-origin — no CORS
issues, no `file://` weirdness. If the backend is down the console falls back
to a scripted demo mode and says so in the status pill, so it stays clickable
as a prototype anywhere.

---

## Endpoints

**Inbound**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/face/detect` | FaceGuard — two models + fusion |
| POST | `/api/v1/voice/detect` | VoicePrint — two models + fusion |
| POST | `/api/v1/verify/score` | Fused Litmus Trust Score (face and/or voice) |
| GET | `/api/v1/face/models` | Model provenance + declared limitations |
| GET | `/api/v1/voice/models` | Model provenance + declared limitations |

**Outbound (TrustLine)**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/trustline/initiate` | Mint an authenticated outbound call session |
| POST | `/api/v1/trustline/verify` | Customer-side call verification |
| GET | `/api/v1/trustline/sessions` | Active / recently-verified sessions |
| GET | `/api/v1/trustline/fraud-feed` | Live fraud intelligence + campaign alerts |
| GET | `/api/v1/trustline/purposes` | Legitimate vs scam-indicator call purposes |

---

## Tests

```bash
python backend/test_trustline.py     # 36 adversarial tests, all passing
```

The TrustLine suite is adversarial by design — every test is an attack the
protocol must survive: no active session, guessed codes, replay, cross-customer
reuse, brute force, expiry, and the digital-arrest purpose short-circuit.

---

## Measured results

These are our own numbers, run before submission. They are reported in full,
including the bad ones, because a fraud product that hides its failure modes is
the thing we are warning against.

**FaceGuard**

- Individual models: 25% and 35% on the FaceForensics++ benchmark subset — each
  unreliable alone, with opposite biases.
- Ensemble: **zero silent wrong auto-approvals** across all demo-condition tests.
- Known failure: both models can share a blind spot and agree while wrong.
  Observed once, on a compressed benchmark image.

**VoicePrint**

| Test set | Result |
|---|---|
| Real speech — 20 samples, FoR dataset | 80% correctly approved |
| Synthetic — 2019-era TTS/VC, 20 samples | 35% caught |
| Synthetic — modern neural TTS (Edge Neural) | **0% caught** |

The 0% is load-bearing. It is precisely why TrustLine does not ask *"does this
voice sound real?"* but *"does this caller know a code only our server could
have minted?"* — a possession factor, not a detection guess.

---

## Disclosed bias

Both are real, measured, and stated in the deck rather than smoothed out.

- **Face** — Model 1 assigns Indian real faces an average real-score of 9.5%
  (trained on FFHQ, which under-represents South Asian faces). In the current
  ensemble this routes 100% of genuine Indian applicants to manual review. Safe,
  but not fair, and not free.
- **Voice** — both models misclassify certain female vocal profiles as synthetic,
  ~20% false-positive rate on real female speech. Ruled out file-format artefacts
  via a `.wav` conversion test; the scores did not move.

**Containment already shipped:** a spoof verdict never triggers automatic
rejection. It routes to a human. Uncertainty *never* escalates to the fraud desk
— only a confident positive identification of synthesis does. See
`_resolve_band()` in `backend/app.py`; the reasoning is documented in the
docstring because it is the whole safety argument.

**Correction on the roadmap:** fine-tune Model 1 on InDeepFake (Indian faces,
7 languages) / MLADDC (6-Indian-language audio), or weight toward Model 2 for
Indian-context inputs.

---

## Layout

```
backend/
  app.py               FastAPI — all endpoints, fusion, banding, console serving
  trustline.py         TrustLine protocol (HMAC, sessions, fraud intelligence)
  test_trustline.py    36 adversarial protocol tests
frontend/
  console.html         Trust Operations Console (served at /console)
models/
  face/                FaceGuard — two models + fusion + evaluation scripts
  voice/               VoicePrint — two models + fusion + evaluation scripts
build_deck.py          Generates Litmus_Round2_Deck.pptx
render_deck.py         Renders the deck to PNGs for review
```

---

## Models used

All four are public HuggingFace checkpoints, cited as such. We did not train
them, and the deck says so. The original engineering is the fusion layer, the
TrustLine protocol, and the decision to architect around a measured detection
ceiling.

- `prithivMLmods/Deep-Fake-Detector-Model` (face, M1)
- `dima806/deepfake_vs_real_image_detection` (face, M2)
- `MelodyMachine/Deepfake-audio-detection-V2` (voice, M1)
- `motheecreator/Deepfake-audio-detection` (voice, M2)

Two upstream GitHub repos were evaluated and abandoned — `aaronchong888/DeepFake-Detect`
(no shipped checkpoint, deprecated TF/Keras) and `yzyouzhang/AIR-ASVspoof`
(MATLAB dependency, Python 3.6 / PyTorch 1.1 EOL, 2019-era training data). Do
not revisit either.

---

## Production notes

Things that are demo-scoped and would change for a pilot:

- `_SESSIONS` / `_FRAUD_REPORTS` are in-memory dicts. Production: Redis with
  native TTL for sessions, a durable event store for fraud reports.
- `LITMUS_TRUSTLINE_SECRET` is read from the environment with a demo default.
  Production: HSM/KMS custody with scheduled rotation.
- CORS is `allow_origins=["*"]`. Lock down before anything leaves localhost.


