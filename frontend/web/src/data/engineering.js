/**
 * API reference, model card and changelog.
 *
 * The model card is the important one. It is the artifact a technical buyer or
 * a regulator asks for, and it is where the measured bias is recorded in full
 * rather than summarised away.
 */

/* ------------------------------------------------------------------ API */

export const apiGroups = [
  {
    group: 'Inbound — applicant verification',
    blurb: 'Score a face capture, a voice sample, or both fused into one number.',
    endpoints: [
      {
        method: 'POST',
        path: '/api/v1/face/detect',
        summary: 'Run the two-model face ensemble on one image.',
        body: 'multipart/form-data — file: image/*',
        returns: 'verdict, confidence_band, m1_score, m2_score, explanation, action',
      },
      {
        method: 'POST',
        path: '/api/v1/voice/detect',
        summary: 'Run the two-model voice ensemble on one audio clip.',
        body: 'multipart/form-data — file: audio/wav | audio/mpeg',
        returns: 'verdict, confidence_band, m1_score, m2_score, explanation, action',
      },
      {
        method: 'POST',
        path: '/api/v1/verify/score',
        summary: 'Fuse whichever modalities are supplied into one Litmus Trust Score.',
        body: 'multipart/form-data — face: image/* (optional), voice: audio/* (optional)',
        returns: 'litmus_trust_score, confidence_band, action, modalities{}, fusion{}, disclosure',
      },
    ],
  },
  {
    group: 'Outbound — TrustLine',
    blurb: 'Mint an authenticated call, verify one from the customer side, read the fraud feed.',
    endpoints: [
      {
        method: 'POST',
        path: '/api/v1/trustline/initiate',
        summary: 'Mint a session and derive its verification phrase.',
        body: 'customer_id, customer_phone, agent_id, agent_name, purpose',
        returns: 'session_id, phrase, agent_script, customer_instruction, expires_at',
      },
      {
        method: 'POST',
        path: '/api/v1/trustline/verify',
        summary: 'Customer-side check of an inbound call claiming to be you.',
        body: 'customer_id, claimed_phrase, caller_number, claimed_purpose',
        returns: 'result, genuine, severity, message, campaign_alert, fraud_report_id',
      },
      {
        method: 'GET',
        path: '/api/v1/trustline/fraud-feed',
        summary: 'Failed verifications, newest first, with FRI and network enrichment.',
        body: '—',
        returns: 'total_reports, critical, high, active_campaigns[], reports[]',
      },
    ],
  },
  {
    group: 'Fraud intelligence',
    blurb: 'DoT Financial Fraud Risk Indicator enrichment and the TrustLine Consortium.',
    endpoints: [
      {
        method: 'GET',
        path: '/api/v1/intel/fri/check/{number}',
        summary: "One number's fraud-risk tier from DoT's Digital Intelligence Platform.",
        body: '—',
        returns: 'tier, label, rank, action, guidance, simulated, disclosure',
      },
      {
        method: 'GET',
        path: '/api/v1/intel/consortium/lookup/{number}',
        summary: 'What every member institution collectively knows about a number.',
        body: '—',
        returns: 'status, corroborated, distinct_members, reports_in_window, recommendation',
      },
      {
        method: 'POST',
        path: '/api/v1/intel/consortium/contribute',
        summary: 'Publish a fraud signal to the network. Accepts no customer identifier.',
        body: 'member_id, caller_number, severity, claimed_purpose',
        returns: 'contributed, signal_id, network_view',
      },
    ],
  },
];

/* ----------------------------------------------------------- model card */

export const modelCard = {
  updated: 'August 2026',
  intro:
    'The detector that decides a Litmus verdict is our own: a ResNet18 fine-tuned here with capture-degradation augmentation, reaching 0.934 AUC. Reference baselines run alongside it as second opinions, each reported with its measured ceiling attached — one of them barely beats a coin toss. This card records what every model does, what it gets wrong, and who it gets wrong most often.',
  models: [
    {
      module: 'FaceGuard',
      slot: 'Primary',
      id: 'Litmus ResNet18 fine-tune',
      arch: 'ResNet18',
      benchmark: '0.934 AUC · 86.3% accuracy',
      note:
        'Trained here on 10,000 images with random downscale and JPEG recompression, so it holds 0.914 AUC even at 0.3x downscale. This is the model that decides a verdict.',
    },
    {
      module: 'FaceGuard',
      slot: 'Second opinion',
      id: 'Vision Transformer baseline',
      arch: 'Vision Transformer',
      benchmark: '0.652 AUC',
      note: 'Over-flags South Asian faces. Reported alongside a verdict, never able to decide one.',
    },
    {
      module: 'FaceGuard',
      slot: 'Second opinion',
      id: 'CNN baseline',
      arch: 'CNN classifier',
      benchmark: '0.513 AUC',
      note: 'Barely above chance. Shown precisely because averaging it in would hide that.',
    },
    {
      module: 'VoicePrint',
      slot: 'Model 1',
      id: 'Wav2Vec2 fine-tune',
      arch: 'Wav2Vec2 fine-tune',
      benchmark: '90% on real speech, 0% on fakes',
      note: 'Reliable on genuine audio, effectively blind to synthesis.',
    },
    {
      module: 'VoicePrint',
      slot: 'Model 2',
      id: 'Wav2Vec2 base',
      arch: 'Wav2Vec2 base',
      benchmark: '80% real, 35% of 2019-era fakes',
      note: 'Noisier on real speech but the only one that fires on synthesis at all.',
    },
  ],
  biases: [
    {
      axis: 'Ethnicity — South Asian faces',
      finding:
        'Model 1 assigns genuine Indian faces an average real-score of 9.5% on our 15-image test set. In the current ensemble this routes effectively 100% of genuine Indian applicants to manual review.',
      impact:
        'Safe but not fair. Nobody is rejected, but the operational cost of review falls disproportionately on the exact population the deploying lender serves.',
      mitigation:
        'Containment shipped: uncertainty routes to a human, never to rejection. Correction planned: fine-tune on InDeepFake, or weight toward Model 2 for Indian-context inputs.',
    },
    {
      axis: 'Gender — female vocal profiles',
      finding:
        'Both voice models misclassify certain female voices as synthetic at roughly a 20% false-positive rate on genuine speech.',
      impact:
        'Real women are disproportionately flagged on verification calls. Ruled out file-format artefacts with a .wav conversion test — the scores did not move.',
      mitigation:
        'A spoof verdict never triggers automatic rejection. Wider demographic audit planned alongside the MLADDC fine-tune.',
    },
  ],
  accuracy: {
    heading: 'Calibration — measured, not assumed',
    intro:
      'Model 1 is a good ranker (AUC 0.737) and was a badly calibrated classifier. It scores real images 0.950 and fakes 0.852 — both above the default 0.5 cut, so at that threshold it called almost everything real and landed at 52.5%, which is chance. Recalibrating the cut point, with the threshold chosen on training folds only, lifts held-out accuracy to 70.0%.',
    rows: [
      ['Model 1 AUC (ranking quality)', '0.737', 'Real signal — the ordering is informative'],
      ['Model 2 AUC (ranking quality)', '0.501', 'Coin flip on this benchmark'],
      ['Equal-weight average AUC', '0.590', 'Averaging M2 in destroys signal'],
      ['Accuracy @ default 0.50 cut', '52.5%', 'Chance'],
      ['Accuracy @ calibrated 0.975 cut', '70.0%', '+17.5 points, cross-validated'],
    ],
    gates:
      'Approve above 0.995, escalate below 0.85, human review between. The two errors are not equally costly: auto-approving a synthetic applicant loses the whole loan, while flagging a genuine one costs an officer review. At a symmetric 0.980 cut the system decides 60% of cases but lets 14 fakes through; at these asymmetric gates it decides 25% and lets 2 through. For a lending decision that is the correct trade.',
  },
  confound: {
    heading: 'The confound we found by accident',
    body:
      'A real applicant photographed across a room was reported as synthetic. Investigating it produced the most important result in this card. Re-scoring one genuine face at decreasing resolution — the same person, the same photo, only the pixel count changing — gives 0.966 at 400px, 0.926 at 150px, 0.850 at 80px and 0.709 at 48px. The model is measuring capture quality as well as authenticity, and crosses the adverse threshold on a genuine person purely because the crop is small.',
    consequence:
      'Two things follow. First, FaceGuard now refuses to make an adverse finding when the detected face is under 128px, and will not clear one under 160px — a poor capture returns "ask for a closer photo", never "this person is fake". Second, every face in our benchmark set is 45-65px, so the accuracy figures above are themselves partly a measurement of compression rather than synthesis. We report them with that caveat attached rather than quietly enjoying the number.',
    why: 'RBI V-CIP captures are close-range and sit comfortably above the floor. The public benchmark does not, which is a reason to distrust benchmark-derived accuracy claims in this field generally — including ours.',
  },
  scopeCorrection: {
    heading: 'A claim we had to narrow',
    body:
      'Earlier material said "zero silent wrong auto-approvals". That result is real, but it was measured on demo-condition samples. On the harder FF++/DFDC-derived benchmark the same fixed 70% rule auto-decides 41 of 120 cases and is wrong on 17 of them — 41% of the calls it commits to. Both numbers are true; the scope was doing too much work. Recalibrating cut the worst error, fakes auto-approved as real, from 14 to 2. The honest version of the claim is the one stated here.',
  },
  limits: [
    'Voice detection catches 0% of modern neural TTS. Treat VoicePrint as a weak first filter, never as liveness proof.',
    'FaceGuard is a deepfake classifier on a captured frame. It is not presentation-attack detection and it does not stop virtual-camera injection, which bypasses the camera entirely.',
    'Not ISO/IEC 30107-3 certified. Level 2 is the procurement baseline for biometric onboarding, and the certification path is on the roadmap.',
    'Both models can share a blind spot and agree while wrong. Agreement raises confidence; it does not guarantee correctness.',
    'All published accuracy figures come from public benchmark data, not from any lender\'s live capture conditions.',
  ],
};

/* ------------------------------------------------------------ changelog */

export const changelog = [
  {
    version: '3.1',
    date: 'September 2026',
    tag: 'current',
    changes: [
      { type: 'added', text: 'DoT Financial Fraud Risk Indicator enrichment on every outbound verification, with live and simulated modes clearly distinguished.' },
      { type: 'added', text: 'TrustLine Consortium — cross-lender fraud signal sharing that carries the attacker number and no customer data.' },
      { type: 'added', text: 'Officer console rebuilt inside the React app; marketing site and product now share one design system.' },
      { type: 'added', text: 'Public model card documenting both measured biases in full.' },
      { type: 'added', text: 'Calibrated FaceGuard pipeline: MTCNN face cropping, test-time augmentation over three views, and a cross-validated decision threshold. Held-out accuracy 52.5% -> 70.0%.' },
      { type: 'added', text: 'Asymmetric approve/escalate gates. Fakes auto-approved as real fell from 14 to 2 on the 120-sample benchmark, at the cost of routing more cases to human review.' },
      { type: 'fixed', text: 'Model 2 was an equal voter in face scoring despite scoring AUC 0.501 — averaging it in was measurably destroying signal. It is now a demographic-bias check and does not vote.' },
      { type: 'note', text: 'Narrowed the "zero silent wrong auto-approvals" claim. It holds on demo-condition samples; on the FF++/DFDC benchmark the old rule was wrong on 41% of the cases it committed to. Recalibration is the response.' },
    ],
  },
  {
    version: '3.0',
    date: 'September 2026',
    tag: '',
    changes: [
      { type: 'added', text: 'TrustLine protocol — HMAC-SHA256 challenge-response, session-bound, single-use, 36 adversarial tests.' },
      { type: 'added', text: 'Fused Litmus Trust Score endpoint combining face and voice.' },
      { type: 'fixed', text: 'Uncertain verdicts were escalating to the fraud desk. Routing bands now resolve from verdict states, so uncertainty always reaches a human instead.' },
      { type: 'fixed', text: 'Every uncertain case returned an identical score because the sub-score was hardcoded to a constant. Now derived continuously from the model evidence.' },
    ],
  },
  {
    version: '2.0',
    date: 'August 2026',
    tag: '',
    changes: [
      { type: 'added', text: 'VoicePrint two-model ensemble with asymmetric spoof-priority fusion.' },
      { type: 'added', text: 'Disagreement-based routing for FaceGuard.' },
      { type: 'fixed', text: 'Temp-file handling broke on Windows; switched to tempfile.NamedTemporaryFile.' },
      { type: 'note', text: 'Measured 0% detection against modern neural TTS. Published rather than buried — it is why TrustLine exists.' },
    ],
  },
];
