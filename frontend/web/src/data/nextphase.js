/**
 * Phase 2 — what gets built next.
 *
 * The organising idea: we measured that detection does not work well enough to
 * decide alone (our own best model is 0.934 AUC, and the public checkpoints are
 * near chance). TrustLine already removed that dependency on the outbound side
 * by asking for proof instead of judging appearance. Phase 2 does the same on
 * the inbound side, and extends the consortium from attackers to rings.
 *
 * Every claim below is tied to a public source; nothing is invented traction.
 */

export const thesis = {
  eyebrow: 'Phase 2',
  heading: 'Stop detecting. Start demanding proof.',
  body:
    'Our own fine-tuned detector reaches 0.934 AUC — good, and still not good enough to decide a loan alone. TrustLine already showed the way out on the outbound side: it never asks whether a voice sounds real, it asks for a code a clone was never issued. Phase 2 applies that same inversion to the inbound side and to fraud that spans institutions. The goal is a pipeline where neither direction depends on a detector being right.',
};

export const phase2 = [
  {
    id: 'livechallenge',
    tag: 'Built · live API',
    name: 'LiveChallenge',
    line: 'TrustLine, pointed inward.',
    problem:
      'Injection attacks rose roughly 9x in 2024, driven by a 28x spike in virtual-camera exploits. They feed a generated video straight into the verification software, so the camera is never involved and passive liveness never sees a presentation attack at all. No amount of pixel analysis fixes this, because the pixels are perfect.',
    idea:
      'Stop asking "does this face look real?" and start asking "can this face do something it could not have prepared for?" At verification time the server issues a random physical challenge — turn to a stated angle, hold a randomly-coloured card across half your face, mouth a randomly generated word — and checks that the response matches the challenge that was issued.',
    why: [
      'A pre-recorded or pre-generated stream cannot answer a challenge chosen after it was made. Injection attacks fail by construction, not by detection.',
      'Real-time face-swap degrades badly under exactly these conditions. The literature is consistent that occlusion, extreme head pose and objects crossing the face are where these models break.',
      'It is verifiable rather than probabilistic. The check is "did the response match the issued challenge", which an officer can audit — not a confidence score.',
      'We measured it: a fixed pre-generated response cleared 2 sessions in 300, against a theoretical floor of 0.80%. Head pose is derived from landmark geometry, so there is no model to be biased or to drift. An occlusion check was tried and removed — a head turn produces the same landmark asymmetry as a hand over the cheek, so it failed genuine applicants, and the round count was raised instead.',
    ],
    status: 'Built. 23 adversarial tests passing, live on the API.',
    built: true,
    evidence: [
      ['Challenge space', '5 head poses per round'],
      ['Rounds required', '3, each derived only after the previous response'],
      ['Blind-guess probability', '0.80% (measured: 2 of 300 prepared responses cleared a session)'],
      ['Head pose', 'Measured geometrically from MTCNN landmarks — no classifier'],
      ['Session TTL', '120 seconds'],
    ],
    source: 'Injection-attack figures: industry reporting, 2024–26. Occlusion/pose weakness: ACM TOMM and ICCV 2025 literature.',
  },
  {
    id: 'ringgraph',
    tag: 'Network effect',
    name: 'RingGraph',
    line: 'Catch the ring, not the application.',
    problem:
      '75% of auto lenders report rising fraud, and the driver is organised rings rather than lone applicants. They build synthetic profiles in volume, test them against lender systems, and hit several institutions inside the same window before busting out. Each lender sees one plausible application; nobody sees the pattern.',
    idea:
      'Extend the TrustLine Consortium from outbound attackers to inbound rings. Members contribute hashed, bucketed weak signals — device fingerprint, address cluster, employer string, bank-account prefix, dealer code — never raw customer data. A ring shows up as an improbably dense cluster across institutions that no single member could have seen.',
    why: [
      'The same privacy property as TrustLine: the contribution API accepts no identifier that can be reversed to a person, so the guarantee is structural rather than promised.',
      'Value compounds with membership. One lender sees its slice; ten lenders see the ring assembling.',
      'It catches the profile-building phase, which is weeks before the bust-out and the only point where intervention is cheap.',
    ],
    status: 'Consortium plumbing already exists for outbound. This reuses it.',
    source: 'Auto-lender fraud survey and bust-out sequence description, Auto Finance News.',
  },
  {
    id: 'assettrace',
    tag: 'After disbursal',
    name: 'AssetTrace',
    line: 'The fraud that happens after the loan clears.',
    problem:
      'A Bijnor racket resold loan-funded tractors on forged papers — around ₹53 lakh, uncovered only when finance companies compared complaints. Every control we have runs before disbursal. Nothing watches the asset afterwards, which is where vehicle finance actually bleeds.',
    idea:
      'Periodic asset re-verification: a geotagged photo of the vehicle and its plate at set intervals, checked for tampering, duplication across loan accounts, and inconsistency with the registered chassis. The same forensic stack, pointed at the collateral rather than the customer.',
    why: [
      'Two-wheeler and tractor lending is collateral-backed, and a resold asset is a total loss with no recovery path.',
      'Duplicate-asset detection across accounts finds the organised version, where one vehicle backs several loans.',
      'It reuses Identity Forensics rather than needing a new model.',
    ],
    status: 'Architecture only. Depends on a field-collection flow that does not exist yet.',
    source: 'Bijnor tractor-loan resale case, April 2026.',
  },
  {
    id: 'formpulse',
    tag: 'Emerging',
    name: 'FormPulse',
    line: 'When the applicant is a script.',
    problem:
      'The whole fraud lifecycle — identity fabrication, document submission, underwriting gaming, disbursement — can now run remotely and be automated end to end. Agentic tooling means the entity filling the form need not be a person at all, and nothing in a document check notices that.',
    idea:
      'Behavioural biometrics on the application itself: keystroke cadence, field-revisit order, paste patterns, time-to-first-keystroke, and how the form is navigated. Humans hesitate, correct themselves and tab backwards. Scripts do not.',
    why: [
      'It is orthogonal to every other signal here — it needs no face, no voice and no document.',
      'It costs nothing at capture time; the evidence is a by-product of the applicant filling the form.',
      'Bot-filled applications arrive in volume, so one detection protects against a batch.',
    ],
    status: 'Architecture only.',
    source: 'Digital lending fraud lifecycle analysis, 2026.',
  },
];

export const symmetry = {
  heading: 'What the architecture looks like when Phase 2 lands',
  rows: [
    {
      direction: 'Inbound — is this applicant real?',
      today: 'FaceGuard · fine-tuned detector at 0.934 AUC, uncertainty routed to a person',
      next: 'LiveChallenge · BUILT — a physical challenge the applicant could not have prepared for',
      shift: 'probabilistic → verifiable',
    },
    {
      direction: 'Outbound — is this caller really us?',
      today: 'TrustLine · HMAC challenge-response, live',
      next: 'Already verifiable — this is the model Phase 2 copies',
      shift: 'already done',
    },
    {
      direction: 'Across institutions',
      today: 'Consortium · shared attacker numbers, live',
      next: 'RingGraph · shared hashed weak signals to surface rings',
      shift: 'incident → campaign',
    },
    {
      direction: 'After disbursal',
      today: 'Nothing watches the asset',
      next: 'AssetTrace · periodic collateral re-verification',
      shift: 'blind → monitored',
    },
  ],
};
