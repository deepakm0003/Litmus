import { useEffect, useState } from 'react';
import * as api from '../../lib/api';
import { useToast } from '../Toast';
import FaceCapture from './FaceCapture';

/**
 * Assurance panel — the half of the system that can approve someone.
 *
 * Everything else in this console produces a rejection or a review. This reads
 * the same evidence in the positive direction: how strongly do we know WHO this
 * applicant is, which is the question that blocks a thin-file borrower.
 *
 * The panel is built around one demonstration. Assess a genuine applicant with
 * no liveness proof and the score sits below the bar, with the missing evidence
 * named. Add the liveness proof and the same person crosses into approvable.
 * That delta is the product, so the UI is arranged to make it visible rather
 * than buried in a payload.
 */
export default function Assurance({
  passedSession = '', applicantRef = '', applicantEmail = '', onGoToChallenge,
}) {
  const toast = useToast();

  const [face, setFace] = useState(null);
  const [caller, setCaller] = useState('');
  const [liveSession, setLiveSession] = useState(passedSession);
  const [hasBureau, setHasBureau] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [previous, setPrevious] = useState(null);
  const [error, setError] = useState(null);
  const [issuing, setIssuing] = useState(false);
  const [email, setEmail] = useState(applicantEmail);
  const [demo, setDemo] = useState([]);

  // A challenge passed on the other tab arrives here ready to use.
  useEffect(() => {
    if (passedSession) setLiveSession(passedSession);
  }, [passedSession]);

  // The reference entered at the challenge is the same applicant, so it
  // pre-fills here rather than being typed twice.
  useEffect(() => {
    if (applicantRef) setCaller((c) => c || applicantRef);
  }, [applicantRef]);

  useEffect(() => {
    if (applicantEmail) setEmail((e) => e || applicantEmail);
  }, [applicantEmail]);

  // Seeded numbers with known history, so the adverse path can be shown
  // without manufacturing the fraud first.
  useEffect(() => {
    api.demoNumbers().then((r) => r.ok && setDemo(r.data.numbers || []));
  }, []);

  async function run() {
    if (!face && !caller && !liveSession) {
      toast('Supply at least one piece of evidence.', 'warn');
      return;
    }
    setBusy(true);
    setError(null);
    const res = await api.assessAssurance({
      face,
      callerNumber: caller,
      liveSession,
      hasBureauFile: hasBureau,
    });
    setBusy(false);

    if (!res.ok) {
      setError(res.error);
      toast(res.error, 'bad');
      return;
    }
    // Keep the prior score so the jump is visible when evidence is added.
    setPrevious(result ? { score: result.assurance_score, label: result.label } : null);
    setResult(res.data);
    toast(`${res.data.label} — ${res.data.assurance_score}/100`, res.data.unlocks_thin_file ? 'ok' : 'warn');
  }

  const level = result?.assurance_level;

  return (
    <>
      <div className="notice notice-info wide">
        <b>This is not a credit score.</b> It measures how strongly the evidence supports that
        this applicant is a real, unique, present human — the question that blocks a thin file.
        Whether they can afford the loan remains the underwriter&rsquo;s decision.
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>Evidence available</h3>
          <p className="panel-sub">
            Everything is optional. A missing signal lowers assurance; it never accuses anyone.
          </p>

          <FaceCapture file={face} onPick={setFace} />

          <div className="field">
            <label>Contact number (network history)</label>
            <input
              value={caller}
              onChange={(e) => setCaller(e.target.value)}
              placeholder="enter the applicant's number — worth 15 of 100"
              inputMode="tel"
            />
          </div>

          <div className="field">
            <label>LiveChallenge session</label>
            <div className="row-actions">
              <input
                className="grow-input"
                value={liveSession}
                onChange={(e) => setLiveSession(e.target.value)}
                placeholder="none — worth 45 of 100"
                readOnly
              />
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => onGoToChallenge?.()}
                type="button"
              >
                Run one
              </button>
            </div>
          </div>

          <div className="field">
            <label>Email for the record — optional</label>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="leave blank to skip"
              inputMode="email"
              type="email"
            />
          </div>

          {demo.length > 0 && (
            <div className="demo-nums">
              <div className="demo-nums-h">Seeded numbers with known history</div>
              {demo.map((n) => (
                <button
                  key={n.number}
                  type="button"
                  className={`demo-num tier-${n.fri_tier}`}
                  onClick={() => setCaller(n.number)}
                  title={n.expect}
                >
                  <span className="mono">{n.display}</span>
                  <span className="demo-num-t">{n.fri_tier.replace('_', ' ')}</span>
                  <span className="demo-num-m">{n.reported_by} lender{n.reported_by === 1 ? '' : 's'}</span>
                </button>
              ))}
              <p className="field-hint">
                Fabricated for demonstration and patterned so they cannot be mistaken for a
                real subscriber.
              </p>
            </div>
          )}

          <p className="field-hint">
            A session only counts once it has been <b>passed</b> on the LiveChallenge tab.
            &ldquo;Run one&rdquo; takes you there; passing it sends the session back here.
          </p>

          <label className="check-row">
            <input
              type="checkbox"
              checked={hasBureau}
              onChange={(e) => setHasBureau(e.target.checked)}
            />
            <span>This applicant already has a bureau file</span>
          </label>

          <div className="row-actions">
            <button className="btn btn-primary" onClick={run} disabled={busy}>
              {busy ? <span className="spinner" /> : null} Assess identity assurance
            </button>
          </div>

          <div className="notice">
            <b>Weights follow measured reliability.</b> Liveness carries 45 because it is a
            verifiable fact with a 0.44% blind-guess probability. Face analysis carries 25
            because it is a model — a good one at 0.934 AUC, but still a model.
          </div>
        </div>

        <div className="panel">
          <h3>Assessment</h3>
          <p className="panel-sub">The evidence trail behind the decision.</p>

          {busy && (
            <div className="empty">
              <span className="spinner" /> Reading the evidence…
            </div>
          )}
          {!busy && error && <div className="notice notice-bad">{error}</div>}
          {!busy && !error && !result && (
            <div className="empty">Supply evidence and assess to see the result.</div>
          )}

          {!busy && result && (
            <>
              <div className={`asr-head asr-${level}`}>
                <div className="asr-score">
                  {result.assurance_score}
                  <span className="asr-of">/100</span>
                </div>
                <div>
                  <div className="asr-label">{result.label}</div>
                  {previous && previous.score !== result.assurance_score && (
                    <div className="asr-delta">
                      {previous.score} → {result.assurance_score}
                      <span>
                        {result.assurance_score > previous.score ? ' evidence added' : ' evidence removed'}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div className={`asr-license asr-lic-${level}`}>{result.licenses}</div>

              <div className="asr-evidence">
                {result.evidence.map((e) => (
                  <div className="asr-row" key={e.signal}>
                    <div className="asr-row-head">
                      <span className="asr-sig">{e.signal}</span>
                      <span className={`asr-out ${e.earned > 0 ? 'ok-text' : 'muted'}`}>
                        {e.outcome}
                      </span>
                      <span className="asr-pts mono">
                        +{e.earned}
                        <em>/{e.weight}</em>
                      </span>
                    </div>
                    <div className="asr-bar">
                      <i style={{ width: `${(e.earned / e.weight) * 100}%` }} />
                    </div>
                    <p className="asr-why">{e.why}</p>
                  </div>
                ))}
              </div>

              {result.adverse_findings.length > 0 && (
                <div className="notice notice-bad">
                  <b>Adverse findings.</b> {result.adverse_findings.join('; ')}.
                </div>
              )}

              <div className={`notice ${result.recovery.recoverable ? 'notice-info' : 'notice-warn'}`}>
                <b>{result.recovery.headline}.</b> {result.recovery.detail}
              </div>

              <div className="notice">
                <b>Scope.</b> {result.disclaimer}
              </div>

              <div className="row-actions">
                <button
                  className="btn btn-primary"
                  type="button"
                  disabled={issuing}
                  onClick={async () => {
                    setIssuing(true);
                    const out = await api.downloadAssuranceRecord(
                      result, applicantRef || caller, caller,
                    );
                    setIssuing(false);
                    toast(
                      out.ok ? `Record ${out.reference} issued.` : out.error,
                      out.ok ? 'ok' : 'bad',
                    );
                  }}
                >
                  {issuing ? <span className="spinner" /> : null} Download record (PDF)
                </button>
                {email.trim() && (
                  <button
                    className="btn btn-ghost"
                    type="button"
                    disabled={issuing}
                    onClick={async () => {
                      setIssuing(true);
                      const out = await api.emailRecord({
                        email: email.trim(),
                        assessment: result,
                        applicant_ref: applicantRef || caller,
                        contact: caller,
                      });
                      setIssuing(false);
                      if (!out.ok) return toast(out.error, 'bad');
                      const d = out.data.delivery;
                      toast(d.message, d.sent ? 'ok' : 'warn');
                    }}
                  >
                    Email the record
                  </button>
                )}
              </div>
              <p className="field-hint">
                Issued and signed by the server, not assembled in this browser — a record the
                verified party could produce for themselves would prove nothing. The printed
                code can be checked back against the issuing system.
              </p>
            </>
          )}
        </div>
      </div>
    </>
  );
}
