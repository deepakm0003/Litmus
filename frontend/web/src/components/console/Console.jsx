import { useCallback, useEffect, useRef, useState } from 'react';
import * as api from '../../lib/api';
import { useToast } from '../Toast';
import ForensicScan from './ForensicScan';
import Assurance from './Assurance';
import LiveChallengePanel from './LiveChallengePanel';
import {
  sampleFraudFeed,
  sampleConsortiumStats,
  sampleFriStatus,
  sampleLookup,
} from '../../data/sampleIntel';

/**
 * Trust Operations Console.
 *
 * Four tabs matching how the work actually splits: score an applicant, run an
 * authenticated outbound call, work the fraud desk, and read the network view.
 *
 * Every panel below is wired to the live backend. There is no mock data path —
 * if the API is down the UI says so plainly rather than showing invented
 * numbers, because a console that fabricates a fraud verdict is worse than one
 * that admits it is offline.
 */
export default function Console() {
  const [tab, setTab] = useState('inbound');
  const [live, setLive] = useState(null); // null = still checking
  const [alerts, setAlerts] = useState(0);
  // A LiveChallenge that passes hands its session to the Assurance tab, so the
  // score jump can be demonstrated without copying an id by hand.
  const [passedSession, setPassedSession] = useState('');
  const [applicantRef, setApplicantRef] = useState('');
  const [applicantEmail, setApplicantEmail] = useState('');

  useEffect(() => {
    api.discover().then((base) => setLive(Boolean(base)));
  }, []);

  const tabs = [
    { id: 'inbound', label: 'Applicant verification' },
    { id: 'livechallenge', label: 'LiveChallenge' },
    { id: 'assurance', label: 'Assurance' },
    { id: 'trustline', label: 'TrustLine' },
    { id: 'fraud', label: 'Fraud desk', badge: alerts || null },
    { id: 'network', label: 'Consortium' },
  ];

  return (
    <div className="console">
      <div className="console-bar">
        <div className="wrap console-bar-row">
          <div>
            <div className="console-title">Trust Operations Console</div>
            <div className="console-sub">
              Live verification, outbound authentication and fraud intelligence
            </div>
          </div>
          <ConnectionPill live={live} />
        </div>
      </div>

      <div className="console-tabs">
        <div className="wrap console-tabs-row">
          {tabs.map((t) => (
            <button
              key={t.id}
              className={`ctab ${tab === t.id ? 'on' : ''}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
              {t.badge ? <span className="ctab-badge">{t.badge}</span> : null}
            </button>
          ))}
        </div>
      </div>

      <div className="wrap console-body">
        {live === false && <OfflineNotice />}
        {tab === 'inbound' && <InboundPanel />}
        {tab === 'livechallenge' && (
          <LiveChallengePanel
            onPassed={(sid, ref, mail) => {
              setPassedSession(sid);
              if (ref) setApplicantRef(ref);
              if (mail) setApplicantEmail(mail);
              setTab('assurance');
            }}
          />
        )}
        {tab === 'assurance' && (
          <Assurance
            passedSession={passedSession}
            applicantRef={applicantRef}
            applicantEmail={applicantEmail}
            onGoToChallenge={() => setTab('livechallenge')}
          />
        )}
        {tab === 'trustline' && <TrustLinePanel onAlert={() => setAlerts((n) => n + 1)} />}
        {tab === 'fraud' && <FraudDesk />}
        {tab === 'network' && <ConsortiumPanel />}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- chrome */

function ConnectionPill({ live }) {
  if (live === null) {
    return (
      <span className="conn checking">
        <span className="spinner" /> checking backend…
      </span>
    );
  }
  return live ? (
    <span className="conn live">
      <span className="pip" /> Live · {api.baseUrl()?.replace(/^https?:\/\//, '')}
    </span>
  ) : (
    <span className="conn down">
      <span className="pip" /> Backend offline
    </span>
  );
}

function OfflineNotice() {
  return (
    <div className="notice notice-warn">
      <b>Backend not reachable — showing sample data.</b> The fraud desk and consortium tabs
      below show illustrative records so you can see what they do. Applicant
      verification has no fallback and will not score an upload: inventing a fraud verdict
      about a real person’s face is the one thing this product exists to argue against.
      <code className="code-line">cd backend &amp;&amp; python -m uvicorn app:app --port 8000</code>
    </div>
  );
}

/** Unmistakable marker wherever illustrative data is on screen. */
function SampleTag() {
  return <span className="sample-tag">Sample</span>;
}

function Empty({ children }) {
  return <div className="empty">{children}</div>;
}

/* ------------------------------------------------------ inbound panel */

function InboundPanel() {
  const toast = useToast();
  const [face, setFace] = useState(null);
  const [voice, setVoice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [forensic, setForensic] = useState(null);
  const [error, setError] = useState(null);

  async function run() {
    if (!face && !voice) {
      toast('Select a face image or a voice sample first.', 'warn');
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    setForensic(null);

    // When a face is supplied, run the calibrated pipeline too so the scan view
    // can show the real detection box and per-stage evidence.
    const [scoreRes, faceRes] = await Promise.all([
      api.scoreEvidence({ face, voice }),
      face ? api.analyzeFace(face) : Promise.resolve(null),
    ]);

    setBusy(false);
    if (faceRes?.ok) setForensic(faceRes.data);

    if (scoreRes.ok) {
      setResult(scoreRes.data);
      toast(`Scored ${scoreRes.data.litmus_trust_score} — ${scoreRes.data.action.replace(/-/g, ' ')}`, 'ok');
    } else {
      setError(scoreRes.error);
      toast(scoreRes.error, 'bad');
    }
  }

  function reset() {
    setFace(null);
    setVoice(null);
    setResult(null);
    setForensic(null);
    setError(null);
  }

  return (
    <div className="grid-2">
      <div className="panel">
        <h3>Applicant evidence</h3>
        <p className="panel-sub">A V-CIP frame, a verification-call clip, or both.</p>

        <FilePick label="Face capture" accept="image/*" file={face} onPick={setFace} hint="JPG or PNG" />
        <FilePick label="Voice sample" accept="audio/*" file={voice} onPick={setVoice} hint="WAV or MP3" />

        <div className="row-actions">
          <button className="btn btn-primary" onClick={run} disabled={busy}>
            {busy ? (
              <>
                <span className="spinner" /> Running both models…
              </>
            ) : (
              'Run Litmus Trust Score'
            )}
          </button>
          <button className="btn btn-ghost" onClick={reset} disabled={busy}>
            Clear
          </button>
        </div>

        <div className="notice">
          <b>What this runs.</b> Two independent models per modality, fused by disagreement-based
          routing. Weights are 0.65 face / 0.35 voice, set from measured reliability rather than
          assumed parity.
        </div>
      </div>

      <div className="panel">
        <h3>Forensic analysis</h3>
        <p className="panel-sub">
          Face located, cropped, scored across three augmented views, then gated.
        </p>

        <ForensicScan file={face} result={forensic} running={busy} error={error} />

        {forensic && <ForensicVerdict data={forensic} />}
        {!busy && !error && !result && !face && (
          <Empty>Submit evidence to score an applicant.</Empty>
        )}
        {!busy && result && <ScoreResult data={result} />}
      </div>
    </div>
  );
}

function FilePick({ label, accept, file, onPick, hint }) {
  const ref = useRef(null);
  return (
    <div className="field">
      <label>{label}</label>
      <button
        className={`dropzone ${file ? 'has' : ''}`}
        onClick={() => ref.current?.click()}
        type="button"
      >
        {file ? `${file.name} · ${(file.size / 1024).toFixed(0)} KB` : `Choose a file — ${hint}`}
      </button>
      <input
        ref={ref}
        type="file"
        accept={accept}
        hidden
        onChange={(e) => onPick(e.target.files?.[0] ?? null)}
      />
    </div>
  );
}

function ScoreResult({ data }) {
  const band = data.confidence_band;
  return (
    <>
      <div className="score-head">
        <Dial value={data.litmus_trust_score} band={band} />
        <div>
          <span className={`band band-${band}`}>
            {band} · {data.action.replace(/-/g, ' ')}
          </span>
          <p className="score-guidance">{data.guidance}</p>
          <p className="score-meta">
            Evaluated {data.modalities_evaluated.join(' + ')} · raw{' '}
            {data.fusion.raw_weighted_score} · band {data.fusion.band_range[0]}–
            {data.fusion.band_range[1]}
          </p>
        </div>
      </div>

      {Object.entries(data.modalities).map(([key, m]) => (
        <div className="modality" key={key}>
          <div className="modality-head">
            <b>{m.module}</b>
            <span className="muted">
              evidence <span className="mono">{m.sub_score}</span> · spread{' '}
              <span className="mono">
                {m.disagreement != null ? `${(m.disagreement * 100).toFixed(1)}%` : '—'}
              </span>{' '}
              ·{' '}
              <span className={m.models_agree ? 'ok-text' : 'warn-text'}>
                {m.calibrated
                  ? m.models_agree
                    ? 'no bias signature'
                    : 'bias signature'
                  : m.models_agree
                    ? 'models agree'
                    : 'models disagree'}
              </span>
            </span>
          </div>
          <ModelBar label="Model 1" value={m.m1_real_score} />
          <ModelBar label="Model 2" value={m.m2_real_score} />
          <div className="notice">{m.explanation}</div>
          {m.caveat && <div className="notice notice-warn">{m.caveat}</div>}
        </div>
      ))}

      <div className="notice notice-info">
        <b>Disclosure.</b> {data.disclosure}
      </div>
    </>
  );
}

function ForensicVerdict({ data }) {
  const p = data.stages.primary;
  const c = data.stages.context;
  const gz = data.pipeline.grey_zone;

  return (
    <div className="forensic">
      <div className={`forensic-verdict fv-${data.action.replace(/-/g, '')}`}>
        <span className="fv-label">{data.verdict}</span>
        <span className="fv-action">{data.action.replace(/-/g, ' ')}</span>
      </div>
      <p className="forensic-why">{data.explanation}</p>

      <div className="gate-viz">
        <div className="gate-track">
          <span className="gate-zone gate-esc" style={{ width: `${p.escalate_below * 100}%` }} />
          <span
            className="gate-zone gate-grey"
            style={{ width: `${(p.approve_above - p.escalate_below) * 100}%` }}
          />
          <span className="gate-zone gate-ok" style={{ width: `${(1 - p.approve_above) * 100}%` }} />
          <span className="gate-marker" style={{ left: `${p.real_score * 100}%` }}>
            <span className="gate-val">{p.real_score.toFixed(3)}</span>
          </span>
        </div>
        <div className="gate-legend">
          <span>escalate &le; {p.escalate_below}</span>
          <span className={gz ? 'gate-here' : ''}>human review</span>
          <span>approve &ge; {p.approve_above}</span>
        </div>
      </div>

      {data.quality && data.quality.face_px > 0 && (
        <div className={`notice ${data.quality.sufficient_for_adverse_finding ? '' : 'notice-warn'}`}>
          <b>Capture quality: {data.quality.face_px}px face.</b>{' '}
          {data.quality.sufficient_for_adverse_finding
            ? `Above the ${data.quality.min_px_to_escalate}px floor, so a verdict is supportable.`
            : `Below the ${data.quality.min_px_to_escalate}px floor. Model 1's score drops with resolution on genuine faces too, so an adverse finding here would be a capture artefact, not evidence. Suppressed — ask for a closer, uncompressed photo.`}
        </div>
      )}

      {data.stages.forensic && (
        <div className="notice notice-info">
          <b>
            Forensic classifier: {(data.stages.forensic.real_probability * 100).toFixed(1)}% real
            {data.stages.forensic.auc
              ? ` (AUC ${data.stages.forensic.auc.toFixed(3)})`
              : ''}.
          </b>{' '}
          {data.stages.forensic.role}
        </div>
      )}

      <div className="forensic-rows">
        {data.stages.forensic && (
          <div className="frow">
            <span className="fk">Forensic model</span>
            <span className="fv">
              {(data.stages.forensic.real_probability * 100).toFixed(1)}% real ·{' '}
              {(data.stages.forensic.confidence * 100).toFixed(0)}% confident
            </span>
          </div>
        )}
        <div className="frow">
          <span className="fk">Capture</span>
          <span className="fv">
            {data.quality?.face_px ?? '—'}px face ·{' '}
            {data.quality?.sufficient_for_adverse_finding ? 'sufficient' : 'below floor'}
          </span>
        </div>
        <div className="frow">
          <span className="fk">Primary model</span>
          <span className="fv">
            {p.real_score.toFixed(4)} real · {p.tta.views} views · spread{' '}
            {(p.tta.spread * 100).toFixed(1)}%
          </span>
        </div>
        <div className="frow">
          <span className="fk">Context check</span>
          <span className="fv">
            {c.real_score.toFixed(4)} ·{' '}
            {c.bias_signature_detected ? (
              <b className="warn-text">bias signature detected</b>
            ) : (
              'no bias signature'
            )}
          </span>
        </div>
      </div>

      <div className="notice">
        <b>Model 2 does not vote.</b> {c.role}
      </div>
    </div>
  );
}

function ModelBar({ label, value }) {
  const pct = (value * 100).toFixed(1);
  const tone = value >= 0.5 ? 'ok' : 'bad';
  return (
    <div className="mbar-row">
      <span className="mbar-label">{label}</span>
      <span className="mbar-track">
        <i className={`mbar-fill ${tone}`} style={{ width: `${pct}%` }} />
      </span>
      <span className={`mbar-val ${tone}-text`}>{pct}% real</span>
    </div>
  );
}

function Dial({ value, band }) {
  const r = 52;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - value / 100);
  return (
    <div className={`dial dial-${band}`}>
      <svg width="132" height="132" viewBox="0 0 132 132">
        <circle cx="66" cy="66" r={r} className="dial-track" />
        <circle
          cx="66"
          cy="66"
          r={r}
          className="dial-value"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 66 66)"
        />
      </svg>
      <div className="dial-center">
        <div className="dial-num">{value}</div>
        <div className="dial-of">/ 100</div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------- trustline panel */

const ATTACKS = [
  { id: 'none', label: "Scammer calls when you aren't calling" },
  { id: 'guess', label: 'Scammer guesses the code' },
  { id: 'replay', label: 'Replay an already-used code' },
  { id: 'campaign', label: 'Simulate a campaign (5 victims)', danger: true },
];

function TrustLinePanel({ onAlert }) {
  const toast = useToast();
  const [form, setForm] = useState({
    customer_id: 'TVSC_884213',
    customer_phone: '9840012345',
    agent_name: 'Priya Raghavan',
    purpose: 'emi_reminder',
  });
  const [session, setSession] = useState(null);
  const [entered, setEntered] = useState('');
  const [caller, setCaller] = useState('');
  const [claimed, setClaimed] = useState('');
  const [verdict, setVerdict] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function initiate() {
    setBusy(true);
    const res = await api.initiateCall({ ...form, agent_id: 'AGT_2291' });
    setBusy(false);
    if (!res.ok) return toast(res.error, 'bad');
    setSession(res.data);
    setVerdict(null);
    setEntered('');
    toast('Authenticated call placed. Code pushed to the customer.', 'ok');
  }

  async function verify(phraseOverride, customerOverride, purposeOverride) {
    setBusy(true);
    const res = await api.verifyCall({
      customer_id: customerOverride ?? form.customer_id,
      claimed_phrase: phraseOverride ?? entered,
      caller_number: caller,
      claimed_purpose: purposeOverride ?? (claimed || null),
    });
    setBusy(false);
    if (!res.ok) return toast(res.error, 'bad');
    setVerdict(res.data);
    if (!res.data.genuine) onAlert?.();
    toast(res.data.result.replace(/_/g, ' '), res.data.genuine ? 'ok' : 'bad');
    return res.data;
  }

  async function runAttack(id) {
    setBusy(true);
    let out = null;
    if (id === 'none') {
      out = await api.verifyCall({
        customer_id: 'TVSC_NOT_BEING_CALLED',
        claimed_phrase: 'TIGER-STONE-42',
        caller_number: caller,
        claimed_purpose: 'loan_approval',
      });
    } else if (id === 'guess') {
      out = await api.verifyCall({
        customer_id: form.customer_id,
        claimed_phrase: 'MANGO-CLOUD-11',
        caller_number: caller,
      });
    } else if (id === 'replay') {
      if (!session) {
        setBusy(false);
        return toast('Place a call and verify it once first.', 'warn');
      }
      await api.verifyCall({
        customer_id: form.customer_id,
        claimed_phrase: session.phrase,
        caller_number: '1600123456',
      });
      out = await api.verifyCall({
        customer_id: form.customer_id,
        claimed_phrase: session.phrase,
        caller_number: caller,
      });
    } else if (id === 'campaign') {
      for (let i = 0; i < 5; i += 1) {
        // eslint-disable-next-line no-await-in-loop
        await api.verifyCall({
          customer_id: `TVSC_VICTIM_${i}`,
          claimed_phrase: 'TIGER-STONE-01',
          caller_number: caller,
          claimed_purpose: 'loan_approval',
        });
      }
      out = await api.verifyCall({
        customer_id: 'TVSC_VICTIM_9',
        claimed_phrase: 'TIGER-STONE-01',
        caller_number: caller,
        claimed_purpose: 'loan_approval',
      });
    }
    setBusy(false);
    if (out?.ok) {
      setVerdict(out.data);
      onAlert?.();
      toast(`Attack blocked — ${out.data.result.replace(/_/g, ' ')}`, 'ok');
    } else if (out) {
      toast(out.error, 'bad');
    }
  }

  return (
    <>
      <div className="notice notice-info wide">
        <b>The inversion.</b> An OTP makes the customer prove identity to the institution — which
        is what every voice scam exploits. TrustLine reverses it. You will always tell the customer
        the code; you will never ask them for it.
      </div>

      <div className="grid-2">
        <div className="panel panel-agent">
          <div className="panel-tag">Agent console</div>
          <div className="field">
            <label>Customer ID</label>
            <input value={form.customer_id} onChange={set('customer_id')} />
          </div>
          <div className="field">
            <label>Customer phone</label>
            <input value={form.customer_phone} onChange={set('customer_phone')} />
          </div>
          <div className="field">
            <label>Agent</label>
            <input value={form.agent_name} onChange={set('agent_name')} />
          </div>
          <div className="field">
            <label>Call purpose</label>
            <select value={form.purpose} onChange={set('purpose')}>
              <option value="emi_reminder">EMI payment reminder</option>
              <option value="loan_approval">Loan application status</option>
              <option value="document_request">Pending document collection</option>
              <option value="collections">Overdue payment discussion</option>
              <option value="noc_dispatch">NOC dispatch</option>
              <option value="kyc_reverification">Periodic KYC re-verification</option>
              <option value="service_callback">Service callback</option>
            </select>
          </div>
          <button className="btn btn-primary" onClick={initiate} disabled={busy}>
            {busy ? <span className="spinner" /> : null} Place authenticated call
          </button>

          {session && (
            <>
              <div className="phrase-box">{session.phrase}</div>
              <p className="muted center-text">
                Session live · expires in {session.ttl_seconds / 60} min · pushed to{' '}
                {session.customer_phone}
              </p>
              <div className="script">
                <div className="script-label">Agent reads this aloud</div>
                {session.agent_script}
              </div>
            </>
          )}
        </div>

        <div className="panel panel-customer">
          <div className="panel-tag">Customer app</div>

          {session ? (
            <div className="push-note">
              <div className="push-head">
                <span>TVS CREDIT · TRUSTLINE</span>
                <span>just now</span>
              </div>
              <div>
                An agent is calling about <b>{session.purpose_label}</b>. They must tell you this
                code:
              </div>
              <div className="push-code">{session.phrase}</div>
            </div>
          ) : (
            <Empty>No incoming call.</Empty>
          )}

          <div className="field">
            <label>Code the caller gave you</label>
            <input
              value={entered}
              onChange={(e) => setEntered(e.target.value)}
              placeholder="e.g. SAFFRON-BEACON-47"
            />
          </div>
          <div className="field">
            <label>Caller’s number</label>
            <input
              value={caller}
              onChange={(e) => setCaller(e.target.value)}
              placeholder="the number that called you"
              inputMode="tel"
            />
          </div>
          <div className="field">
            <label>What did they ask for?</label>
            <select value={claimed} onChange={(e) => setClaimed(e.target.value)}>
              <option value="">— nothing unusual —</option>
              <option value="otp_request">They asked for my OTP</option>
              <option value="remote_access">They asked me to install AnyDesk</option>
              <option value="upi_pin">They asked for my UPI PIN</option>
              <option value="penalty_payment">They demanded a payment</option>
              <option value="digital_arrest">They threatened police action</option>
              <option value="loan_processing_fee">They demanded a processing fee</option>
            </select>
          </div>
          <button className="btn btn-primary" onClick={() => verify()} disabled={busy}>
            Verify this call
          </button>

          {verdict && <VerdictCard data={verdict} />}
        </div>
      </div>

      <div className="panel">
        <h3>Try to break it</h3>
        <p className="panel-sub">Each button runs a real attack against the live protocol.</p>
        <div className="row-actions wrap-actions">
          {ATTACKS.map((a) => (
            <button
              key={a.id}
              className={`btn ${a.danger ? 'btn-danger' : 'btn-ghost'}`}
              onClick={() => runAttack(a.id)}
              disabled={busy}
            >
              {a.label}
            </button>
          ))}
        </div>
      </div>
    </>
  );
}

function VerdictCard({ data }) {
  const ok = data.genuine;
  return (
    <>
      <div className={`verdict-card ${ok ? 'ok' : 'bad'}`}>
        <div className="verdict-title">{data.result.replace(/_/g, ' ')}</div>
        <div>{data.message}</div>
      </div>
      {data.campaign_alert && (
        <div className="notice notice-bad">
          <b>Campaign alert.</b> {data.campaign_alert.failed_verifications} failed verifications
          from <span className="mono">{data.campaign_alert.caller_number}</span> across{' '}
          {data.campaign_alert.distinct_customers_targeted} customers in the last hour.
        </div>
      )}
      {data.reminder && (
        <div className="notice">
          <b>Still applies.</b> {data.reminder}
        </div>
      )}
    </>
  );
}

/* --------------------------------------------------------- fraud desk */

function FraudDesk() {
  const [feed, setFeed] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    const res = await api.fraudFeed(40);
    setLoading(false);
    if (res.ok && Array.isArray(res.data?.reports)) {
      setFeed(res.data);
      setError(null);
    } else {
      // Offline: show the illustrative feed rather than a dead tab. Clearly
      // marked everywhere it appears.
      setFeed(sampleFraudFeed);
      setError(null);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="empty">
        <span className="spinner" /> Loading the fraud feed…
      </div>
    );
  }
  if (error) return <div className="notice notice-bad">{error}</div>;
  // Never return null here — an empty tab reads as a broken tab.
  if (!feed) return <Empty>No fraud data available.</Empty>;

  return (
    <>
      <div className="grid-3">
        <Stat n={feed.critical} label="Critical reports" tone="bad" />
        <Stat n={feed.high} label="High severity" tone="warn" />
        <Stat n={feed.active_campaigns.length} label="Active campaigns" tone="ok" />
      </div>

      <div className="panel">
        <h3>Active campaigns {feed.sample && <SampleTag />}</h3>
        <p className="panel-sub">Clustered by caller number over a one-hour window.</p>
        {feed.active_campaigns.length === 0 ? (
          <Empty>No campaigns detected yet. Run an attack on the TrustLine tab.</Empty>
        ) : (
          feed.active_campaigns.map((c) => (
            <div className="campaign" key={c.caller_number}>
              <div className="campaign-num">{c.caller_number}</div>
              <div className="muted">
                {c.failed_verifications} failed verifications in the last hour · recommend telecom
                block, proactive customer warning, and an I4C / DoT FRI filing
              </div>
            </div>
          ))
        )}
        <div className="notice">
          <b>Why this is the asset no KYC vendor can sell you.</b> Every failed verification is a
          scammer identifying themselves in real time. An inbound-only vendor never sees this,
          because it happens on calls they are not part of.
        </div>
      </div>

      <div className="panel">
        <div className="panel-head-row">
          <div>
            <h3>Verification failures {feed.sample && <SampleTag />}</h3>
            <p className="panel-sub">Newest first, enriched with DoT FRI and network context.</p>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={load}>
            Refresh
          </button>
        </div>

        {feed.reports.length === 0 ? (
          <Empty>Nothing reported yet.</Empty>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Severity</th>
                  <th>Caller</th>
                  <th>FRI tier</th>
                  <th>Network</th>
                  <th>Why it failed</th>
                </tr>
              </thead>
              <tbody>
                {feed.reports.map((r) => (
                  <tr key={r.report_id}>
                    <td className="mono nowrap">{(r.reported_at || '').split('T')[1] || '—'}</td>
                    <td>
                      <span className={`sev sev-${r.severity}`}>{r.severity}</span>
                    </td>
                    <td className="mono">{r.caller_number || '—'}</td>
                    <td>
                      {r.fri ? (
                        <span className={`fri fri-${r.fri.tier}`}>
                          {r.fri.label}
                          {r.fri.simulated ? <em> (sim)</em> : null}
                        </span>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      {r.network ? (
                        <span className={r.network.corroborated ? 'bad-text' : 'muted'}>
                          {r.network.distinct_members} member
                          {r.network.distinct_members === 1 ? '' : 's'}
                        </span>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>{r.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

function Stat({ n, label, tone }) {
  return (
    <div className={`cstat cstat-${tone}`}>
      <div className="cstat-n">{n}</div>
      <div className="cstat-l">{label}</div>
    </div>
  );
}

/* -------------------------------------------------------- consortium */

function ConsortiumPanel() {
  const toast = useToast();
  const [stats, setStats] = useState(null);
  const [fri, setFri] = useState(null);
  const [lookup, setLookup] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const [s, f] = await Promise.all([api.consortiumStats(), api.friStatus()]);
    // Offline: illustrative network view rather than an empty tab.
    // Shape-check as well as ok-check: a malformed payload must fall back
    // rather than reach a .map() and take the page down.
    setStats(s.ok && Array.isArray(s.data?.members) ? s.data : sampleConsortiumStats);
    setFri(f.ok && f.data?.mode ? f.data : sampleFriStatus);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function check() {
    if (!lookup.trim()) return toast('Enter a number to look up.', 'warn');
    const [net, tier] = await Promise.all([
      api.consortiumLookup(lookup.trim()),
      api.friCheck(lookup.trim()),
    ]);
    if (net.ok && tier.ok) {
      setResult({ network: net.data, fri: tier.data });
    } else {
      setResult(sampleLookup(lookup.trim()));
      toast('Backend offline — showing a sample lookup.', 'warn');
    }
  }

  if (loading) {
    return (
      <div className="empty">
        <span className="spinner" /> Loading network view…
      </div>
    );
  }

  return (
    <>
      <div className="notice notice-info wide">
        <b>Why a consortium.</b> The same call centre dials a TVS Credit customer at 11:00, a Bajaj
        customer at 11:04 and a Shriram customer at 11:09. Today each lender learns that number
        independently. Shared, the first customer at any member to check a code protects customers
        at every member. Records carry the attacker’s number and never any customer data.
      </div>

      {fri && (
        <div className={`notice ${fri.configured ? 'notice-info' : 'notice-warn'}`}>
          <b>DoT FRI: {fri.mode} mode.</b> {fri.note}
        </div>
      )}

      {stats && (
        <>
          <div className="grid-3">
            <Stat n={stats.member_count} label="Member institutions" tone="ok" />
            <Stat n={stats.network_confirmed_campaigns} label="Network-confirmed campaigns" tone="bad" />
            <Stat n={stats.total_signals} label="Signals contributed" tone="warn" />
          </div>

          <div className="panel">
            <h3>Members {stats.sample && <SampleTag />}</h3>
            <p className="panel-sub">
              Attribution is pseudonymous, so a member proves it contributed without publishing its
              fraud volumes to competitors.
            </p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Institution</th>
                    <th>Pseudonym</th>
                    <th>Contributions</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.members.map((m) => (
                    <tr key={m.pseudonym}>
                      <td>{m.name}</td>
                      <td className="mono">{m.pseudonym}</td>
                      <td className="mono">{m.contributions}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      <div className="panel">
        <h3>Look up a number</h3>
        <p className="panel-sub">Combined network history and DoT fraud-risk tier.</p>
        <div className="row-actions">
          <input
            className="grow-input"
            value={lookup}
            onChange={(e) => setLookup(e.target.value)}
            placeholder="9198765432"
          />
          <button className="btn btn-primary" onClick={check}>
            Check
          </button>
        </div>

        {result && (
          <div className="lookup-result">
            <div className={`notice ${result.network.corroborated ? 'notice-bad' : 'notice-info'}`}>
              <b>Network: {result.network.status.replace(/_/g, ' ')}.</b>{' '}
              {result.network.recommendation}
            </div>
            <div className={`notice fri-notice fri-${result.fri.tier}`}>
              <b>DoT FRI: {result.fri.label}.</b> {result.fri.meaning} {result.fri.guidance}
              <div className="muted small">{result.fri.disclosure}</div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
