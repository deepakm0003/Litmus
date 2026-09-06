# Round 2 submission checklist — due Sep 6, 2026

## Done

- [x] `Litmus_Round2_Deck.pptx` — 19 slides, corrected facts, restructured narrative
- [x] Self-scoring "96/100" slide **removed** (judges score you; you don't score yourself)
- [x] Every statistic sourced on-slide
- [x] TrustLine built — protocol, API, 36 passing adversarial tests
- [x] Fused Trust Score endpoint built (`/api/v1/verify/score`)
- [x] Operations console built and wired to the live API
- [x] Speaker notes on every slide that needs one

## Corrections made to the original proposal

| Was | Now | Why |
|---|---|---|
| "Global AI fraud losses exceeded $40bn in 2025" | RBI FY26 ₹48,021 cr · digital arrest ₹22,495 cr · NBFC ₹15–20 cr | The $40bn is a **US projection for 2027** (Deloitte), from $12.3bn in 2023. Wrong geography, year and tense. |
| "26 million+ customers" | "2.44 crore customers, 60,500 touchpoints, 190 branches" | TVS Credit's own FY26 Annual Report. Don't misquote a judge's own metric. |
| "TrustLine has no commercial equivalent" | Head-to-head vs the TRAI 1600-series mandate | TRAI mandated 1600 for NBFCs Feb–Mar 2026. Their compliance team is doing it right now. Pre-empt it or lose the innovation argument. |
| Regulatory hook = IT Amendment Rules 2026 | RBI KYC Master Directions (Nov 2025) + RBI FREE-AI (Aug 2025) | IT Rules bind *intermediaries*, not NBFCs. RBI's V-CIP liveness clause and FREE-AI's Fairness/Explainability Sutras bind TVS Credit directly. |
| FaceGuard = "passive liveness, catches injection attacks" | "Two-model deepfake ensemble on the V-CIP frame" | Liveness ≠ deepfake classification, and injection-attack detection is a different control we don't implement. Don't claim it. |
| Bias buried on page 4 | Its own slide, plus the lead-in slide 2 | It's the strongest differentiator, not a confession. |

## Before you submit — you must do these

- [ ] **Visit a dealership.** The brief explicitly says the round *"may require visiting a
      two-wheeler / used car / consumer durable retailer and understanding the current loan
      process."* Slide 4 maps the six-step journey from public research. **Confirm or correct
      it from what you actually see**, add one concrete observation and the dealership name.
      Do **not** claim a visit you didn't make — judges will probe it, and the whole deck's
      credibility rests on not overclaiming.

- [ ] **Rewrite the prose in your own voice.** Submissions are screened for AI-generated
      content. Read every slide aloud; anywhere it doesn't sound like you, change it. The
      field-visit content is the best antidote because it can't be generated.

- [ ] **Confirm the round structure.** You said this is the final round. Public info says
      Round 3 is the Grand Finale — shortlisted teams get a week to build and present a
      working prototype with a code walkthrough. If your organisers told you otherwise,
      the demo plan on slide 17 needs to become screenshots + a recorded video instead.

- [ ] **Record a 60-second backup video** of the demo (real selfie → disagreement → TTS clip
      fools VoicePrint → TrustLine catches it anyway). Never demo live without a fallback.

- [ ] **Take fresh screenshots** of the console with your own face/voice samples. The ones in
      `shots/` were generated during the build.

## Demo-day runbook

```bash
cd backend
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/console`. Confirm the status pill reads **LIVE**, not DEMO MODE.

**Sequence (the order matters):**

1. **Inbound tab** — upload a real selfie. Models disagree. Point at the two bars: *"Model 1
   says fake at 88%, Model 2 says real at 99%. That's the South Asian bias we measured. It
   routes to a human — it does not reject."*
2. **Play a modern neural TTS clip** through VoicePrint. It passes as real. Say so out loud:
   *"Our own voice detection catches zero percent of modern TTS. We measured it."*
3. **TrustLine tab** — same scenario. The caller can't produce the code. Blocked instantly.
   *"That's why we don't ask whether the voice sounds real."*
4. **Try to break it** — hit the attack buttons. Replay, cross-customer, brute force.
5. **Fraud Desk tab** — the campaign alert is now populated. *"Every scam attempt just
   generated labelled training data for us, at zero cost."*

**Step 2 into step 3 is the single highest-impact thirty seconds.** Everyone else will show
you something working. You show something failing, then show why that was survivable by design.

## Likely judge questions

**"Isn't the biased model a weakness?"**
Every team here has this bias in their models. We're the only one who measured it, published
it, and architected containment around it. That's what RBI's FREE-AI Fairness Sutra asks for.

**"TRAI already mandated the 1600-series — isn't this solved?"**
Slide 11. 1600 authenticates the *number*. It doesn't authenticate the *human*, doesn't cover
WhatsApp calls, and doesn't survive CLI spoofing. And once 2.44 crore customers are trained
that "1600 = genuinely TVS," that trust signal becomes worth stealing.

**"Why not just buy HyperVerge?"**
Slide 15. For inbound — you should. We don't pretend to beat them. For outbound, no vendor's
business model covers it: their contract is with TVS Credit, not with the customer being
scammed.

**"You only built three of six modules."**
Deliberate. Two shallow demos of six half-built things is less credible than three that run.
The architecture slide labels exactly which is which.

**"Did you train these models?"**
No, and the deck says so. Four public HuggingFace checkpoints, cited. What we built is the
fusion layer, the TrustLine protocol, and the decision to design around a measured ceiling.
