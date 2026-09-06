# How to present Litmus

You are not presenting a deepfake detector. Every other team will do that, and
they will all claim 95%+ accuracy.

**You are presenting one argument:** detection alone does not work, you proved it
on your own system, and you built the layer that survives that.

Everything below serves that one sentence. If you remember nothing else on
stage, remember that you are the person in the room who measured honestly.

---

## Before you walk in

- [ ] Deployed URL open in a tab, **loaded and warm** — hit it 5 minutes before
- [ ] Second tab: the backup URL, in case the first one dies
- [ ] Backup demo video downloaded **locally**, not streaming
- [ ] Phone on the same network, camera permission already granted
- [ ] One face scan already run, so the models are in memory
- [ ] `99999 00000` and `55555 44444` memorised — the two demo numbers
- [ ] Laptop charged, notifications off, browser zoom at 100%

**Run one full LiveChallenge yourself before the judges arrive.** A cold start in
front of a jury looks like a broken product.

---

# PART 1 — Opening (60 seconds)

### Who you are (15s)

> "I'm Deepak Meena, fourth year B.Tech Computer Science at IIIT Delhi. I built
> this solo.
>
> I picked problem statement (b) — decoding machine-generated trust."

### Open with the failure, not the pitch (45s)

> "Before I tell you what I built, let me tell you what I measured.
>
> I took four off-the-shelf deepfake detection models — the same class of model
> this industry sells to banks. Against real speech they scored 80%. Against
> 2019-era synthetic speech, 35%. Against modern neural text-to-speech — the kind
> anyone can generate free today — **zero percent.** Both models. Confidently
> wrong. Every single time.
>
> So any team that shows you a detection accuracy number today is selling you
> something. I built Litmus for detectors that fail."

**Do not rush this. Pause after "zero percent."** That pause is your whole pitch.

---

# PART 2 — The product page (2 minutes)

Walk the page top to bottom. Do not read it — point, and say the line underneath.

### The hero

> "Two directions of trust in a lending relationship. The industry guards one.
>
> **Inbound** — is the applicant a real human? Every KYC vendor solves this.
> HyperVerge, Signzy, IDfy. They are good at it and I will not pretend I beat
> them.
>
> **Outbound** — is the call telling a customer they are approved actually from
> the lender? **Almost nobody guards this.** Not because it is hard, but because
> a KYC vendor's contract is with the lender, not with the customer being
> scammed. There is no business model. That is the gap I built into."

Anchor it: **Rs 22,495 crore** lost in India to caller-impersonation "digital
arrest" scams during 2025.

### "We tested four models before building anything"

> "This is the section I would delete if I were trying to win on accuracy.
>
> 80% on real speech. 35% on old fakes. **Zero on modern TTS.** These are my own
> numbers, on my own system, and they are the reason the architecture looks the
> way it does."

### The two directions

> "Inbound: two independently-biased models score every frame. When they
> disagree, that gap is *information*, not an error to average away. Disagreement
> routes to a human — it never rejects.
>
> Outbound: the arrow is reversed. An OTP makes the customer prove themselves to
> you, which is exactly what scams exploit. TrustLine makes you prove yourself to
> the customer."

### TrustLine — the inversion

Point at the code on screen: **SAFFRON-BEACON-47**

> "Two words and two digits, not six digits. Chosen because digits collide when
> they are misheard on a noisy showroom call, in any language. Session-bound,
> single-use, ten-minute expiry, HMAC-SHA256.
>
> The rule becomes: **we will always tell you the code, we will never ask you for
> it.** That is a rule that stays safe even when the customer forgets it."

### Six modules — three live

> "Three say **Built · Live**. Three say **Architecture**. I am telling you which
> is which, because two shallow demos of six half-built things convince nobody.
> Three that work in front of you do."

### The model card

> "My detector is a ResNet18 I fine-tuned on 10,000 images with
> capture-degradation augmentation — random downscaling and JPEG recompression —
> because a real onboarding photo is a compressed phone snap, not a clean dataset
> image. **0.934 AUC, 86.3% accuracy**, and it holds 0.914 even at a third of the
> resolution.
>
> The two baselines underneath it score 0.652 and 0.513. **The second one is
> barely better than a coin toss.** I show it precisely because averaging it into
> a verdict would hide that.
>
> And here — one of those baselines over-flags South Asian faces. I measured it,
> published it, and contained it: uncertainty routes to a human, never to a
> rejection."

### Regulatory fit

> "Three live Indian instruments, not speculation.
>
> **RBI KYC Master Directions, November 2025** — V-CIP must carry liveness and
> spoof detection with a high degree of accuracy, regularly upgraded. That is
> FaceGuard, with an evaluation record behind it.
>
> **RBI FREE-AI, August 2025** — fairness, transparency, accountability for
> high-risk financial AI. Bias measured and published; uncertainty always routed
> to a human.
>
> **TRAI 1600-series** — it authenticates the *number*. TrustLine authenticates
> the *human on the line*, and survives caller-ID spoofing by construction."

### Transition

> "That is the claim. Let me show you it running."

---

# PART 3 — The console demo (3 minutes)

**Order matters. Lead with LiveChallenge — it is the strongest thing you have.**

### 3.1 LiveChallenge (75s) — the centrepiece

Open the LiveChallenge tab. Enter a number. Issue a challenge.

> "The server has just issued a challenge. **I do not know what it will ask.**"

Complete the round — turn your head, say the word.

> "Injection attacks rose roughly ninefold in 2024, driven by a 28-fold spike in
> virtual-camera exploits. The attacker feeds generated video straight into the
> verification software, so the camera is never involved and passive liveness
> never sees an attack at all. No amount of pixel analysis fixes that, because
> the pixels are perfect.
>
> So I stopped asking 'does this face look real' and started asking **'can this
> face do something it could not have prepared for.'**"

Complete all three rounds.

> "Three rounds, each derived only after the previous response. Five head poses
> per round, plus a spoken word checked server-side for actual speech — staying
> silent fails the round.
>
> Blind-guess probability is 0.80%. I measured it: **2 sessions in 300** cleared
> with a fixed pre-generated response.
>
> And head pose is computed geometrically from facial landmarks. There is no
> classifier — so there is nothing to be biased, and nothing to drift."

### 3.2 The record (30s)

Click **Download record (PDF)**. Open it.

> "The server issues and signs this — the browser only saves it. Every record
> carries an HMAC verification code, so the document is not something the
> verified party produced for themselves. Anyone can check it later against the
> server."

### 3.3 Assurance (45s) — the part that makes it a lending product

Switch to Assurance. Enter **`99999 00000`**.

> "Everything so far rejects. This *approves*.
>
> Between 70 and 85% of first-time borrowers get rejected at the bureau check —
> not because they are bad credit, but because they are invisible to it. Litmus
> recovers the ones who were rejected only because we could not verify who they
> were.
>
> Verified at 80 and above, provisional at 55, insufficient below. And it says
> plainly on the page: **this is not a credit score.** It answers 'is this a real
> person', not 'will they repay'."

Then enter **`55555 44444`**.

> "Clean on the government fraud register — but two other lenders have already
> flagged it. **No single lender could see that.** That is the consortium."

### 3.4 TrustLine (30s)

Place a call. Show the phrase. Verify it. Then hit the attack buttons.

> "Replay it — blocked. Another customer's code — blocked. Guess it — locks after
> three attempts. **36 out of 36 adversarial tests passing.**
>
> A perfect voice clone still cannot produce it, because it is a possession
> factor, not a detection guess. That is why the zero percent I opened with does
> not sink this system."

Show the fraud desk.

> "And every failed attempt just became intelligence — the number, the script,
> the timing. **The attacker generated that data for us, for free.** An inbound
> KYC vendor can never see this; it happens on calls they are not part of."

---

# PART 4 — Close (30 seconds)

> "Three modules built and running behind a live API. Three are architecture
> only, and I label which is which.
>
> I fine-tuned the detector that decides verdicts — 0.934 AUC, and the checkpoint
> ships in the repository. The baselines beside it are public models I
> benchmarked and beat, and I show their scores next to mine so you can see the
> difference.
>
> But the real answer is not the model. The system never asks a detector to be
> right forever. It asks for proof a clone cannot produce.
>
> **Every fake has a tell. Litmus reads it — on the way in, and on the way out.**"

---

## If the demo breaks

Say this, calmly, and switch to the backup video:

> "That is live inference — let me show you the recorded run."

**Record that video before you go.** Never demo without one. Do not apologise
twice, do not debug on stage, do not narrate the error.

If the camera fails, the cause is almost always a non-HTTPS URL. Switch tabs.

---

## The questions you will get

**"Did you train these models?"**
> "I fine-tuned the primary detector myself — that is the 0.934 AUC checkpoint,
> trained on 10,000 images with degradation augmentation, and it ships in the
> repo. The two baselines are public checkpoints I benchmarked and beat. I show
> their scores next to mine so you can see the difference."

**"Isn't the biased model a weakness?"**
> "Every model in this room has that bias. I am the only one who measured it and
> told you. RBI's FREE-AI framework asks for exactly that — measure it, disclose
> it, keep a human in the loop. And it never decides a verdict; it is reported
> beside one."

**"TRAI already mandated the 1600-series. Isn't this solved?"**
> "1600 authenticates the *number*. It does not authenticate the *human*, does
> not cover WhatsApp calls, and does not survive caller-ID spoofing. And there is
> a sharper problem: once crores of customers learn that 1600 means genuine, that
> trust signal becomes worth stealing. TrustLine is a shared secret, so it
> survives spoofing by construction. It sits above the mandate, not beside it."

**"Why not just buy HyperVerge?"**
> "For inbound — you should. I am not claiming to beat them. For outbound there
> is nothing to buy. Their contract is with the lender, not the borrower."

**"You only built three of six modules."**
> "Deliberately. Two shallow demos of six half-built things is less credible than
> three that actually run in front of you."

**"What happens at scale?"**
> "Sessions are in-memory today, which means one worker. For a pilot that moves
> to Redis with native TTLs — the state is already isolated behind two
> dictionaries, so it is a contained change. It is on the roadmap and the
> deployment notes say so."

---

## Things not to do

- **Don't apologise for the 0%.** It is your strongest asset. Deliver it as a
  finding, not a confession.
- **Don't say "I think" or "I tried to".** You measured. Say "I measured".
- **Don't read the slides.** They are the evidence; you are the argument.
- **Don't oversell the three unbuilt modules.** One sentence each, move on.
- **Don't claim the baselines are yours.** Saying what is yours and what is not
  buys more credibility than it costs — and the honest version is stronger,
  because your number beats theirs.
- **Don't debug live.** Switch to the video and keep talking.

---

## The thing to hold onto

You are not competing on model accuracy. You would lose that — everyone can
download the same checkpoints.

You are competing on **engineering judgement**: you measured, you found the
ceiling, you published it, and you designed a system that stays safe when the
model is wrong. That is what a senior engineer at TVS Credit would do, and it is
what the jury means when they say critical thinking carries greater weightage.
