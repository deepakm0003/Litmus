# How to present Litmus

You are not presenting a deepfake detector. Every other team will do that, and
they will all claim 95%+ accuracy.

**You are presenting one argument:** detection alone does not work, we proved it
on our own system, and we built the layer that survives that.

Everything below serves that one sentence. If you only remember one thing on
stage, remember that you are the person in the room who measured honestly.

---

## The 5-minute version

### 0:00 — Open with the number, not the pitch (30s)

> "Before I tell you what we built, let me tell you what we measured.
>
> We took four off-the-shelf deepfake detection models — the same class of model
> this industry sells to banks. Against real speech, they got 80%. Against
> 2019-era synthetic speech, 35%. Against modern neural text-to-speech — the kind
> anyone can generate free today — **zero percent.** Both models, confidently
> wrong, every time.
>
> So my conclusion is this: any team that shows you a detection accuracy number
> today is selling you something. We built Litmus for detectors that fail."

**Do not rush this.** Pause after "zero percent." That pause is your whole pitch.

### 0:30 — What Litmus is (45s)

Two questions, one platform.

> "Inbound — is this loan applicant a real human? Every KYC vendor solves this:
> HyperVerge, Signzy, IDfy. They're good at it and I'm not going to pretend I beat them.
>
> Outbound — is this caller, claiming to be TVS Credit, actually TVS Credit?
> **Nobody solves this.** Not because it's hard, but because a KYC vendor's
> contract is with TVS Credit, not with the customer being scammed. There's no
> business model. That's the gap I built into."

Anchor it: **₹22,495 crore** lost to digital-arrest impersonation scams in 2025.

### 1:15 — Live demo, inbound (60s)

Open the console. Upload a real selfie.

> "Model 1 says fake, 88% confident. Model 2 says real, 99% confident. They
> disagree completely.
>
> Model 1 was trained on FFHQ, which barely contains South Asian faces. On our
> 15-face Indian test set it gave real faces an average real-score of nine and a
> half percent. **It is biased against exactly the customer base TVS Credit
> serves.** I'm telling you that because I measured it, not because you asked.
>
> Watch what the system does with that. It does not reject. It routes to a human,
> and the score sits at 61 — in the review band, not the fraud band. Uncertainty
> never escalates. That's a hard rule in the code."

Upload a second image. **The score changes** — point at it.

> "Different evidence, different score. The number orders the review queue, so an
> officer knows which case to open first."

### 2:15 — The pivot (45s) — *this is the highest-value minute*

Play a modern neural TTS clip through VoicePrint. It passes as real.

> "There it is. Our own voice model, fooled, live, in front of you. I could have
> not shown you this."

Switch to the TrustLine tab immediately.

> "So we stopped asking the question we can't answer. TrustLine doesn't ask 'does
> this voice sound real'. It asks: **does this caller know a code that only TVS
> Credit's server could have generated?**
>
> An OTP makes the customer prove themselves to the bank — which is exactly what
> every scam exploits. 'Sir, aapka OTP bataiye.' We inverted it. TVS Credit proves
> itself to the customer. **TVS will always tell you the code. TVS will never ask
> for it.** That's a rule that's safe even when the customer breaks it."

Place a call. Show the phrase. Verify it. Then hit the attack buttons.

> "Replay it — blocked. Another customer's code — blocked. Guess it — locks after
> three tries. A perfect voice clone still cannot produce it, because it's a
> possession factor, not a detection guess."

### 3:00 — Fraud desk (30s)

> "And every failed attempt just did something for us."

Show the campaign alert.

> "Six failures from one number in an hour. That's a live scam campaign, and the
> scammers generated that data themselves, for free. An inbound KYC vendor can
> never see this — it happens on calls they're not part of. This asset accrues to
> TVS Credit and compounds."

### 3:30 — Close (30s)

> "Three modules built and running behind a live API. Three are architecture only,
> and my deck labels which is which.
>
> I didn't train these models — they're public checkpoints and I cite them. What I
> built is the fusion layer, the TrustLine protocol, and the decision to design
> around a measured ceiling instead of an assumed accuracy.
>
> Every fake has a tell. Litmus catches it — on the way in, and on the way out."

---

## If the demo breaks

Say this, calmly, and switch to your backup video:

> "That's live inference on my laptop — let me show you the recorded run."

**Record that video before you go.** Never demo without one.

---

## The four questions you will get

**"Isn't your biased model a weakness?"**
> "Every model in this room has that bias. I'm the only one who measured it and
> told you. And RBI's FREE-AI framework — the Fairness and Accountability Sutras
> — asks for exactly that: measure it, disclose it, keep a human in the loop."

**"TRAI already mandated the 1600-series. Isn't this solved?"**
> "1600 authenticates the *number*. It doesn't authenticate the *human*, doesn't
> cover WhatsApp calls, and doesn't survive caller-ID spoofing. And here's the
> sharper problem: once 2.44 crore customers learn that 1600 means genuinely TVS,
> that trust signal becomes worth stealing. TrustLine is a shared secret, so it
> survives spoofing by construction. It sits above the mandate, not beside it."

**"Why not just buy HyperVerge?"**
> "For inbound — you should. I'm not claiming to beat them. For outbound, there's
> nothing to buy. Their contract is with the lender, not the borrower."

**"You only built three of six modules."**
> "Deliberately. Two shallow demos of six half-built things is less credible than
> three that actually run in front of you."

---

## Things not to do

- **Don't apologise for the 0%.** It's your strongest asset. Deliver it as a
  finding, not a confession.
- **Don't say "I think" or "we tried to".** You measured. Say "we measured".
- **Don't read the slides.** They're the evidence; you're the argument.
- **Don't oversell the four unbuilt modules.** One sentence each, move on.
- **Don't hide that the models are public checkpoints.** Saying it out loud buys
  more credibility than it costs.

---

## The thing to hold onto

You are not competing on model accuracy. You would lose that — everyone has the
same HuggingFace checkpoints.

You are competing on **engineering judgement**: you measured, found the ceiling,
and designed a system that stays safe when the model is wrong. That is what a
senior engineer at TVS Credit would do, and it is what the jury is actually
looking for when they say "critical thinking will be given greater weightage."
