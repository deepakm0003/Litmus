/**
 * Sample intelligence data — used ONLY when the backend is unreachable.
 *
 * WHY THIS EXISTS
 * ---------------
 * The fraud desk and consortium tabs load their data on mount. When this build
 * is served as a static page (the published artifact, or an opened file), there
 * is no backend to reach, so those two tabs previously rendered an error and
 * nothing else — they looked broken rather than offline.
 *
 * WHERE THE LINE IS
 * -----------------
 * Sample data is acceptable for an illustrative feed. It is NOT acceptable for
 * a verdict about a real person, so the applicant-verification tab still has no
 * fallback: upload a face with the backend down and it reports the failure
 * rather than inventing a score. Fabricating a fraud judgement on someone's
 * actual photograph is the one thing this product exists to argue against.
 *
 * Everything below is flagged `sample: true` and every surface that renders it
 * shows a SAMPLE marker. It must never be mistakable for live data.
 */

export const SAMPLE_NOTE =
  'The backend is not reachable from this page, so these panels show illustrative ' +
  'records rather than live results. Run the API locally and reload for real output.';

export const sampleFraudFeed = {
  sample: true,
  total_reports: 9,
  critical: 7,
  high: 2,
  active_campaigns: [
    { caller_number: '9198765432', failed_verifications: 6 },
    { caller_number: '9007712845', failed_verifications: 3 },
  ],
  reports: [
    {
      report_id: 'fr_sample_01',
      reported_at: '2026-09-04T11:42:18+00:00',
      customer_id: 'TVSC_884213',
      caller_number: '9198765432',
      severity: 'critical',
      reason:
        'Customer received a call claiming to be TVS Credit, but no TVS Credit outbound session exists for this customer.',
      fri: { tier: 'very_high', label: 'Very High', simulated: true },
      network: { distinct_members: 3, corroborated: true },
    },
    {
      report_id: 'fr_sample_02',
      reported_at: '2026-09-04T11:39:04+00:00',
      customer_id: 'TVSC_772110',
      caller_number: '9198765432',
      severity: 'critical',
      reason:
        "Caller's stated purpose is one TVS Credit never calls about: Caller asked for an OTP.",
      fri: { tier: 'very_high', label: 'Very High', simulated: true },
      network: { distinct_members: 3, corroborated: true },
    },
    {
      report_id: 'fr_sample_03',
      reported_at: '2026-09-04T11:31:55+00:00',
      customer_id: 'TVSC_450981',
      caller_number: '9007712845',
      severity: 'critical',
      reason:
        'Caller claimed legal action / police / "digital arrest" — a purpose TVS Credit never calls about.',
      fri: { tier: 'high', label: 'High', simulated: true },
      network: { distinct_members: 2, corroborated: true },
    },
    {
      report_id: 'fr_sample_04',
      reported_at: '2026-09-04T11:18:37+00:00',
      customer_id: 'TVSC_884213',
      caller_number: '9812004417',
      severity: 'high',
      reason:
        'A genuine TVS Credit call is in progress, but the code the caller provided does not match.',
      fri: { tier: 'clean', label: 'No association', simulated: true },
      network: { distinct_members: 1, corroborated: false },
    },
    {
      report_id: 'fr_sample_05',
      reported_at: '2026-09-04T10:57:12+00:00',
      customer_id: 'TVSC_339276',
      caller_number: '9007712845',
      severity: 'critical',
      reason:
        'Customer received a call claiming to be TVS Credit, but no TVS Credit outbound session exists for this customer.',
      fri: { tier: 'high', label: 'High', simulated: true },
      network: { distinct_members: 2, corroborated: true },
    },
  ],
};

export const sampleConsortiumStats = {
  sample: true,
  member_count: 4,
  total_signals: 9,
  numbers_tracked: 3,
  network_confirmed_campaigns: 2,
  corroboration_threshold: 2,
  window_hours: 6,
  coverage_multiple: 3.0,
  coverage_note:
    'Numbers visible to the whole network divided by numbers a single member would have seen alone.',
  campaigns: [
    { caller_number: '9198765432', distinct_members: 3, reports: 6 },
    { caller_number: '9007712845', distinct_members: 2, reports: 3 },
  ],
  members: [
    { name: 'TVS Credit', pseudonym: '0d50d6622e61', contributions: 5 },
    { name: 'Member Lender B', pseudonym: '1963eda732cc', contributions: 2 },
    { name: 'Member Lender C', pseudonym: 'fb51d1e020de', contributions: 2 },
    { name: 'Member Lender D', pseudonym: '1cf194b2bdd9', contributions: 0 },
  ],
};

export const sampleFriStatus = {
  sample: true,
  configured: false,
  mode: 'simulated',
  note:
    'Live FRI access requires an onboarded DoT Digital Intelligence Platform account. ' +
    'Without credentials Litmus runs a deterministic local heuristic and flags every ' +
    'result as simulated.',
};

/** Deterministic stand-in for a single number lookup while offline. */
export function sampleLookup(number) {
  const digits = String(number).replace(/\D/g, '').slice(-10);
  const known = {
    9198765432: { tier: 'very_high', label: 'Very High', members: 3 },
    9007712845: { tier: 'high', label: 'High', members: 2 },
  };
  const hit = known[digits];

  return {
    network: {
      sample: true,
      caller_number: digits,
      status: hit ? 'network_confirmed' : 'unknown',
      corroborated: Boolean(hit),
      distinct_members: hit ? hit.members : 0,
      reports_in_window: hit ? hit.members * 2 : 0,
      recommendation: hit
        ? `${hit.members} independent member institutions reported this number within 6h. Block at the telecom partner, warn customers proactively, and file to I4C / DoT FRI.`
        : 'No network history for this number.',
    },
    fri: {
      sample: true,
      tier: hit ? hit.tier : 'clean',
      label: hit ? hit.label : 'No association',
      meaning: hit
        ? 'Number is associated with reported financial fraud.'
        : 'No fraud association currently recorded against this number.',
      guidance: hit
        ? 'Escalate to the fraud desk ahead of the standard review queue.'
        : 'No external signal. This does NOT mean the caller is genuine — a fresh SIM has no history yet.',
      simulated: true,
      disclosure: 'SAMPLE — offline illustrative record, not a government risk classification.',
    },
  };
}
