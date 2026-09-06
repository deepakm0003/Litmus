import { useCallback, useEffect, useRef, useState } from 'react';
import * as api from '../../lib/api';
import { useToast } from '../Toast';

/**
 * LiveChallenge panel — where the applicant actually answers the challenge.
 *
 * The protocol was live on the API before this existed, but there was no way to
 * respond to a challenge from the console: you could issue one and never pass
 * it. That made the most important demonstration in the product impossible to
 * show, so this closes it.
 *
 * Camera capture uses getUserMedia, which needs a secure context. Localhost
 * qualifies, so it works when the backend serves this page. Anywhere it does
 * not — a published static copy, a blocked permission — the panel falls back to
 * a file upload rather than simply breaking, because a demo that cannot fall
 * back is a demo that fails in the room.
 */
export default function LiveChallengePanel({ onPassed }) {
  const toast = useToast();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileRef = useRef(null);
  const streamRef = useRef(null);

  const [session, setSession] = useState(null);
  const [challenge, setChallenge] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [camera, setCamera] = useState('idle'); // idle | on | denied
  const [history, setHistory] = useState([]);
  const [recording, setRecording] = useState(false);
  const [countdown, setCountdown] = useState(null);
  const [ref, setRef] = useState('');
  const [issuing, setIssuing] = useState(false);
  const [email, setEmail] = useState('');
  const [audioUrl, setAudioUrl] = useState(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const audioBlobRef = useRef(null);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCamera('idle');
  }, []);

  useEffect(() => stopCamera, [stopCamera]);

  async function startCamera() {
    try {
      // Audio is requested alongside video so the spoken word can actually be
      // captured. If the mic is refused we still proceed — the word is review
      // evidence, never a pass condition, so losing it must not block anyone.
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: true,
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setCamera('on');
    } catch {
      setCamera('denied');
      toast('Camera unavailable — use the photo upload instead.', 'warn');
    }
  }

  function startRecording() {
    const stream = streamRef.current;
    if (!stream || stream.getAudioTracks().length === 0) {
      toast('No microphone available \u2014 the word will not be recorded.', 'warn');
      return;
    }
    try {
      chunksRef.current = [];
      const rec = new MediaRecorder(new MediaStream(stream.getAudioTracks()));
      rec.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data); };
      rec.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        audioBlobRef.current = blob;
        setAudioUrl(URL.createObjectURL(blob));
      };
      rec.start();
      recorderRef.current = rec;
      setRecording(true);
    } catch {
      toast('Recording is not supported in this browser.', 'warn');
    }
  }

  function stopRecording() {
    if (recorderRef.current && recorderRef.current.state === 'recording') {
      recorderRef.current.stop();
    }
    recorderRef.current = null;
    setRecording(false);
  }

  async function issue() {
    if (!ref.trim()) {
      toast('Enter the applicant reference first — it identifies the record.', 'warn');
      return;
    }
    setBusy(true);
    const res = await api.initiateLiveChallenge(ref.trim(), ref.trim());
    setBusy(false);
    if (!res.ok) return toast(res.error, 'bad');
    setSession(res.data.session_id);
    setChallenge(res.data);
    setResult(null);
    setHistory([]);
    setAudioUrl(null);
    audioBlobRef.current = null;
    toast(`Round 1 of ${res.data.rounds_required} issued.`, 'info');
    if (camera === 'idle') startCamera();
  }

  /** Grab the current video frame as a JPEG blob. */
  function grabFrame() {
    return new Promise((resolve) => {
      const v = videoRef.current;
      const c = canvasRef.current;
      if (!v || !c) return resolve(null);
      c.width = v.videoWidth || 640;
      c.height = v.videoHeight || 480;
      c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
      c.toBlob((b) => resolve(b), 'image/jpeg', 0.92);
    });
  }

  /**
   * Run one round hands-free: start recording, count down so the applicant can
   * turn and speak, then capture automatically. This exists because the
   * applicant cannot see the screen while their head is turned away.
   */
  async function runRound() {
    if (!session || camera !== 'on') return;
    startRecording();
    for (let n = 3; n > 0; n -= 1) {
      setCountdown(n);
      // eslint-disable-next-line no-await-in-loop
      await new Promise((r) => setTimeout(r, 1000));
    }
    setCountdown('capturing');
    const frame = await grabFrame();
    setCountdown(null);
    await submit(frame);
  }

  async function submit(blob) {
    if (!session || !blob) return;
    stopRecording();
    // Let the recorder flush its final chunk before the blob is read.
    await new Promise((r) => setTimeout(r, 220));

    setBusy(true);
    const res = await api.verifyLiveChallenge(session, blob, audioBlobRef.current);
    setBusy(false);
    if (!res.ok) return toast(res.error, 'bad');

    const d = res.data;
    setResult(d);
    setHistory((h) => [...h, d]);

    if (d.result === 'ROUND_PASSED') {
      setChallenge((c) => ({
        ...c,
        challenge: d.next_challenge,
        instruction: d.next_instruction,
        round: (d.rounds_passed ?? 0) + 1,
      }));
      audioBlobRef.current = null;
      setAudioUrl(null);
      toast(`Round ${d.rounds_passed} passed. New challenge issued.`, 'ok');
    } else if (d.passed) {
      toast('Challenge passed — identity presence established.', 'ok');
      stopCamera();
    } else {
      toast(d.result.replace(/_/g, ' '), 'bad');
    }
  }

  const instruction = result?.next_instruction || challenge?.instruction;
  const roundNow = result?.rounds_passed != null
    ? result.rounds_passed + 1
    : challenge?.round ?? 1;

  return (
    <>
      <div className="notice notice-info wide">
        <b>Why this beats an injection attack.</b> The challenge below is generated
        <em> after</em> this session opened. A pre-recorded or AI-generated video stream was
        fixed before it existed, so it cannot contain the answer. The attack fails by
        construction — no detector has to be right.
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>The challenge</h3>
          <div className="field">
            <label>Applicant reference</label>
            <input
              value={ref}
              onChange={(e) => setRef(e.target.value)}
              placeholder="mobile number or application id"
              inputMode="tel"
              disabled={Boolean(session)}
            />
            <p className="field-hint">
              Identifies the applicant on the issued record, and carries through to the
              assurance assessment. Locked once a challenge is running.
            </p>
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
            <p className="field-hint">
              Not required. Verification completes with or without it, and the record stays
              downloadable either way.
            </p>
          </div>

          <p className="panel-sub">
            {challenge
              ? `Round ${roundNow} of ${challenge.rounds_required ?? 2}. Blind-guess probability across the whole session: ${((challenge.blind_guess_probability ?? 0.0044) * 100).toFixed(2)}%.`
              : 'Issue a challenge to begin.'}
          </p>

          {challenge && (
            <div className="lc-dots" aria-label={`Round ${roundNow} of ${challenge.rounds_required ?? 3}`}>
              {Array.from({ length: challenge.rounds_required ?? 3 }).map((_, i) => (
                <span
                  key={i}
                  className={`lc-dot ${i < (result?.rounds_passed ?? 0) ? 'done' : ''} ${
                    i === roundNow - 1 && !result?.passed ? 'now' : ''
                  }`}
                />
              ))}
              <span className="lc-dots-label">
                {result?.passed
                  ? 'all rounds complete'
                  : `round ${roundNow} of ${challenge.rounds_required ?? 3}`}
              </span>
            </div>
          )}

          {instruction ? (
            <div className={`lc-instruction ${result?.result === 'ROUND_PASSED' ? 'fresh' : ''}`}>
              {instruction}
            </div>
          ) : (
            <div className="empty">No challenge outstanding.</div>
          )}

          {result?.result === 'ROUND_PASSED' && (
            <div className="lc-advance">
              Round {result.rounds_passed} passed. A <b>new</b> challenge is shown above — it was
              generated just now, so it could not have been prepared during the last round.
            </div>
          )}

          <div className="row-actions">
            <button className="btn btn-primary" onClick={issue} disabled={busy}>
              {busy ? <span className="spinner" /> : null}
              {session ? 'Issue a new challenge' : 'Issue challenge'}
            </button>
            {camera === 'idle' && (
              <button className="btn btn-ghost" onClick={startCamera} type="button">
                Turn on camera
              </button>
            )}
          </div>

          {history.length > 0 && (
            <div className="lc-history">
              {history.map((h, i) => (
                <div key={`${h.result}-${i}`} className={`lc-hrow ${h.passed || h.result === 'ROUND_PASSED' ? 'ok' : 'bad'}`}>
                  <span className="lc-hn">{i + 1}</span>
                  <span className="lc-hr">{h.result.replace(/_/g, ' ')}</span>
                  {h.checks?.head_turn && (
                    <span className="lc-hd mono">
                      demanded {h.checks.head_turn.demanded} · measured{' '}
                      {h.checks.head_turn.measured_degrees}&deg;
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="notice">
            <b>What is measured.</b> Head yaw is computed from facial landmark geometry — the
            nose&rsquo;s offset from the eye midpoint over interocular distance. No classifier is
            involved, so there is nothing to be biased and an officer can audit the arithmetic.
          </div>
        </div>

        <div className="panel">
          <h3>Your response</h3>
          <p className="panel-sub">
            Press start, then turn and speak. It captures on its own after three seconds — you
            do not need to reach for the screen while your head is turned.
          </p>

          <div className="lc-stage">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className={`lc-video ${camera === 'on' ? '' : 'hidden'}`}
            />
            {countdown !== null && (
              <div className="lc-count">
                <div className="lc-count-n">
                  {countdown === 'capturing' ? '📸' : countdown}
                </div>
                <div className="lc-count-t">
                  {countdown === 'capturing'
                    ? 'Captured'
                    : 'Turn your head AND say the word out loud'}
                </div>
              </div>
            )}
            {camera !== 'on' && (
              <div className="lc-placeholder">
                {camera === 'denied'
                  ? 'Camera unavailable. Upload a photo of yourself performing the instruction instead.'
                  : 'Camera off.'}
              </div>
            )}
          </div>
          <canvas ref={canvasRef} className="hidden" />

          <div className="row-actions">
            <button
              className="btn btn-primary"
              disabled={busy || !session || camera !== 'on' || countdown !== null || result?.passed}
              onClick={runRound}
            >
              {busy ? <span className="spinner" /> : null}
              {countdown !== null ? 'Hold still…' : `Start round ${roundNow}`}
            </button>
            <button
              className="btn btn-ghost"
              disabled={busy || !session}
              onClick={() => fileRef.current?.click()}
              type="button"
            >
              Upload a photo instead
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) submit(f);
              }}
            />
          </div>

          {audioUrl && (
            <div className="lc-audio">
              <div className="lc-audio-head">
                <b>Spoken response recorded</b>
                <span>demanded: {challenge?.challenge?.say_word || challenge?.say_word}</span>
              </div>
              <audio controls src={audioUrl} className="lc-player" />
              <p className="lc-audio-note">
                Attached to the case for human review, and never machine-scored. Our voice
                models catch 0% of modern neural TTS, and speech recognition running in the
                applicant&rsquo;s own browser would be the attacker&rsquo;s testimony rather than
                evidence. A reviewer hearing the wrong word, a synthetic cadence, or someone
                prompting off-camera learns what no classifier here could.
              </p>
            </div>
          )}

          {result && (
            <div className={`verdict-card ${result.passed || result.result === 'ROUND_PASSED' ? 'ok' : 'bad'}`}>
              <div className="verdict-title">{result.result.replace(/_/g, ' ')}</div>
              <div className="rm">{result.message}</div>
            </div>
          )}

          {result?.checks?.spoken_word && !result.checks.spoken_word.speech_detected && (
            <div className="notice notice-bad">
              <b>Nothing was heard.</b> {result.checks.spoken_word.analysis?.message}{' '}
              The head pose is only half the challenge — the word has to be spoken aloud
              during the countdown.
            </div>
          )}

          {result?.checks && (
            <div className="forensic-rows">
              <div className="frow">
                <span className="fk">Head turn</span>
                <span className="fv">
                  demanded {result.checks.head_turn.demanded} (
                  {result.checks.head_turn.target_degrees}&deg;) · measured{' '}
                  {result.checks.head_turn.measured_degrees}&deg; ·{' '}
                  <b className={result.checks.head_turn.passed ? 'ok-text' : 'bad-text'}>
                    {result.checks.head_turn.passed ? 'match' : 'no match'}
                  </b>
                </span>
              </div>
              <div className="frow">
                <span className="fk">Spoken word</span>
                <span className="fv">
                  demanded {result.checks.spoken_word.demanded} ·{' '}
                  <b className={result.checks.spoken_word.speech_detected ? 'ok-text' : 'bad-text'}>
                    {result.checks.spoken_word.speech_detected ? 'speech detected' : 'no speech detected'}
                  </b>
                  {result.checks.spoken_word.analysis?.voiced_seconds != null && (
                    <> · {result.checks.spoken_word.analysis.voiced_seconds}s voiced</>
                  )}
                </span>
              </div>
            </div>
          )}

          {result?.passed && (
            <div className="lc-done">
              <div className="lc-done-mark">&#10003;</div>
              <div>
                <div className="lc-done-title">Challenge passed</div>
                <p className="lc-done-body">
                  All {challenge?.rounds_required ?? 3} rounds matched, each one issued only
                  after the previous answer arrived. Physical presence is established without
                  any detector having to be right.
                </p>
                <code className="lc-done-sid">{session}</code>
                <div className="row-actions">
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={() => onPassed?.(session, ref.trim(), email.trim())}
                  >
                    Use this in Assurance <span className="arw">&#8594;</span>
                  </button>
                  <button
                    className="btn btn-ghost"
                    type="button"
                    disabled={issuing}
                    onClick={async () => {
                      setIssuing(true);
                      const out = await api.downloadLiveChallengeRecord(session);
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
                          livechallenge_session: session,
                        });
                        setIssuing(false);
                        if (!out.ok) return toast(out.error, 'bad');
                        const d = out.data.delivery;
                        toast(d.sent ? d.message : d.message, d.sent ? 'ok' : 'warn');
                      }}
                    >
                      Email the record
                    </button>
                  )}
                </div>
                <p className="lc-done-hint">
                  Worth 45 of 100 there — enough to move a thin-file applicant from
                  &ldquo;not established&rdquo; to approvable.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
