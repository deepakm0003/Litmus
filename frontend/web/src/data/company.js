/**
 * Company, market and commercial content.
 *
 * Every figure here is either a cited public number or a clearly-labelled
 * assumption. Nothing is presented as traction we do not have — the product is
 * pre-pilot, and the pages say so.
 */

/* ------------------------------------------------------------------ market */

export const market = {
  headline: 'The attack surface grew faster than the defence budget.',
  cards: [
    {
      value: '₹48,021cr',
      label: 'Bank fraud reported in FY26',
      note: 'Up 46.4% from ₹32,803cr in FY25.',
      source: 'RBI Annual Report FY26',
    },
    {
      value: '₹22,495cr',
      label: 'Lost to "digital arrest" impersonation in 2025',
      note: '241,537 cases recorded between 2022 and 2025.',
      source: 'I4C / MHA',
    },
    {
      value: '₹15–20cr',
      label: 'Single-NBFC loss to AI-generated credentials',
      note: 'Fraudulent onboarding through breached video KYC.',
      source: 'Reported 2025–26',
    },
    {
      value: '2.44cr',
      label: 'Customers at one NBFC alone',
      note: '60,500 touchpoints, 190 branches — the scale a scam campaign targets.',
      source: 'TVS Credit Annual Report FY26',
    },
  ],
};

export const wedge = {
  heading: 'The wedge: nobody owns the outbound half.',
  body: [
    'Inbound identity verification is a solved, competitive market. HyperVerge, Signzy, IDfy and Perfios KARZA all sell it, all do it well, and all compete on the same axes — accuracy, latency, document coverage. We do not enter there and do not claim to beat them.',
    'The outbound half has no incumbent, and the reason is structural rather than technical. A KYC vendor\'s contract is with the lender. Protecting the lender\'s customers from people impersonating that lender creates no billable event for them, so no vendor has built it. The gap persists because of incentives, not difficulty.',
    'That is the wedge. TrustLine enters through the half nobody sells, and the fraud intelligence it generates compounds into a defensible network the longer it runs.',
  ],
};

/* --------------------------------------------------------------- business */

export const pricing = {
  note: 'Indicative pricing for a pilot-stage product. Not a live commercial offer — the numbers exist to show the shape of the model, not to be quoted.',
  plans: [
    {
      name: 'Pilot',
      price: 'No fee',
      period: '90 days',
      tagline: 'One product line, one branch cluster.',
      cta: 'Scope a pilot',
      featured: false,
      features: [
        'FaceGuard + VoicePrint on a sampled share of V-CIP sessions',
        'TrustLine on one outbound campaign',
        'Officer console for up to 10 reviewers',
        'A written evaluation report — including where we failed',
        'No consortium membership',
      ],
    },
    {
      name: 'Production',
      price: '₹1.40',
      period: 'per verification',
      tagline: 'Full pipeline, volume-tiered, billed monthly.',
      cta: 'Talk to us',
      featured: true,
      features: [
        'All three live modules across every channel',
        'Fused Litmus Trust Score with full model-level explainability',
        'DoT FRI enrichment on every outbound verification',
        'TrustLine Consortium membership included',
        'Model card, bias audit, and quarterly re-evaluation',
        '99.5% uptime target, sub-400ms p95 on the scoring path',
      ],
    },
    {
      name: 'Consortium',
      price: 'Shared',
      period: 'annual',
      tagline: 'For an industry body hosting the network.',
      cta: 'Discuss hosting',
      featured: false,
      features: [
        'Hosts the shared fraud feed for member institutions',
        'Pseudonymous member attribution',
        'Attacker-only records — no customer data crosses members',
        'Aggregate campaign reporting to I4C / DoT',
        'Per-member coverage analytics',
      ],
    },
  ],
  faq: [
    {
      q: 'Why per-verification rather than per-seat?',
      a: 'Fraud risk scales with transaction volume, not with headcount. A lender running 40,000 disbursals a month carries more exposure than one running 4,000 with the same number of officers, and the price should track the exposure.',
    },
    {
      q: 'What happens when the model routes something to review?',
      a: 'It still bills as a verification. We deliberately do not price review events differently — charging more when the model is uncertain would create an incentive to make it uncertain more often.',
    },
    {
      q: 'Is consortium membership really included?',
      a: 'Yes, and that is a deliberate commercial choice. The network is worth more to every member as it grows, so putting it behind a separate line item would work against the product.',
    },
  ],
};

export const roadmap = [
  {
    phase: 'Shipped',
    when: 'Now',
    status: 'done',
    items: [
      'FaceGuard, VoicePrint and TrustLine live on a working API',
      'Disagreement-based fusion with human-in-the-loop routing',
      'Measured bias published rather than smoothed out',
      'DoT FRI enrichment and consortium signal-sharing',
    ],
  },
  {
    phase: 'Next',
    when: '1–2 quarters',
    status: 'active',
    items: [
      'Fine-tune Model 1 on InDeepFake to shrink the manual-review bucket',
      'Injection-attack detection — the gap FaceGuard does not currently cover',
      'ISO/IEC 30107-3 Level 2 PAD certification path',
      'Redis-backed sessions and HSM key custody for TrustLine',
    ],
  },
  {
    phase: 'Later',
    when: '3–4 quarters',
    status: 'planned',
    items: [
      'Identity Forensics and FormPulse from architecture into production',
      'Live consortium with three or more member institutions',
      'Hindi and regional-language voice evaluation set',
      'Continuous re-evaluation harness against new generators',
    ],
  },
];

export const team = {
  note: 'Litmus is early. Presenting a large team would be the first dishonest thing on this site.',
  people: [
    {
      name: 'Deepak Meena',
      role: 'Founder — engineering',
      detail:
        'B.Tech Computer Science, IIIT Delhi. Built the model ensembles, the fusion layer, the TrustLine protocol and this site.',
    },
  ],
  hiring: [
    'ML engineer — multilingual audio anti-spoofing',
    'Security engineer — protocol and key custody',
    'Design partner — an NBFC willing to run a 90-day pilot',
  ],
};

/* ---------------------------------------------------------- how it's built */

export const principles = [
  {
    title: 'Publish the failures',
    body: 'Our voice ensemble catches 0% of modern neural TTS. That number is on the homepage, in the API response, and in the model card. A fraud vendor that hides its failure modes is selling the problem back to you.',
  },
  {
    title: 'Uncertainty is not guilt',
    body: 'A model that cannot decide routes to a person. It never rejects. Because our first face model over-flags South Asian faces, disagreement is the expected state for a legitimate Indian applicant — treating that as suspicion would turn a known bias into a discriminatory outcome.',
  },
  {
    title: 'Design for the model being wrong',
    body: 'TrustLine does not ask whether a voice sounds real, because we measured that we cannot tell. It asks for a code a clone was never issued. The architecture assumes the detector fails.',
  },
  {
    title: 'Share the attacker, never the customer',
    body: 'Consortium records contain the caller number and nothing else. The contribution API does not accept a customer identifier, so it cannot leak one. The privacy guarantee is the function signature.',
  },
];
