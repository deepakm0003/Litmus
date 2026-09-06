/**
 * Backend client.
 *
 * The console is demoed live in front of people, so every call here is written
 * for the case where the backend is not running: discovery tries a short list
 * of likely origins with a hard timeout, and each request returns a tagged
 * result rather than throwing. Nothing in the UI should ever be able to hang
 * on a dead socket while a jury watches.
 */

const CANDIDATES = [
  // Same origin first — the backend serves the built bundle at /console.
  typeof window !== 'undefined' ? window.location.origin : '',
  'http://127.0.0.1:8000',
  'http://localhost:8000',
].filter((origin) => origin && !origin.startsWith('file://'));

let base = null;
let discovered = false;

function withTimeout(ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, done: () => clearTimeout(timer) };
}

/**
 * Find a reachable backend. Resolves to the base URL, or null if offline.
 *
 * A 200 is NOT enough to accept an origin. The Vite dev server answers every
 * unmatched GET with the SPA shell — including /health — so a naive res.ok
 * check happily "discovers" the dev server, and then every API call returns
 * HTML that fails to parse. We therefore require the response to be JSON that
 * actually looks like the Litmus health payload.
 */
export async function discover() {
  if (discovered) return base;
  for (const origin of CANDIDATES) {
    const t = withTimeout(1400);
    try {
      const res = await fetch(`${origin}/health`, {
        signal: t.signal,
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) continue;
      const body = await res.json(); // throws on the SPA shell — which is the point
      if (body && body.status === 'healthy' && body.models) {
        base = origin;
        break;
      }
    } catch {
      /* not our API — try the next candidate */
    } finally {
      t.done();
    }
  }
  discovered = true;
  return base;
}

export function baseUrl() {
  return base;
}

export function isLive() {
  return Boolean(base);
}

/**
 * All requests funnel through here so failures are uniform.
 * Returns { ok, data, error } — never throws.
 */
async function request(path, options = {}, timeoutMs = 120000) {
  if (!base) await discover();
  if (!base) {
    return { ok: false, error: 'Backend offline. Start it with: cd backend && python -m uvicorn app:app --port 8000' };
  }

  const t = withTimeout(timeoutMs);
  try {
    const res = await fetch(`${base}${path}`, {
      ...options,
      signal: t.signal,
      headers: { Accept: 'application/json', ...(options.headers || {}) },
    });
    const text = await res.text();

    let data = null;
    let parsed = true;
    try {
      data = JSON.parse(text);
    } catch {
      parsed = false;
    }

    if (!res.ok) {
      return {
        ok: false,
        error: (parsed && data?.detail) || `HTTP ${res.status}`,
        status: res.status,
      };
    }

    // A 200 carrying HTML means we are talking to a static/dev server, not the
    // API. Returning it as success is what previously crashed the console with
    // a blank page, so treat it as a hard failure and re-arm discovery.
    if (!parsed) {
      base = null;
      discovered = false;
      return {
        ok: false,
        error:
          'That origin returned a web page instead of API data. Start the backend on port 8000 and reload.',
      };
    }

    return { ok: true, data };
  } catch (err) {
    const offline = err.name === 'AbortError';
    return {
      ok: false,
      error: offline
        ? 'Request timed out. Model inference can take a few seconds on first run.'
        : `Could not reach the backend: ${err.message}`,
    };
  } finally {
    t.done();
  }
}

const json = (body) => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

/* ------------------------------------------------------------- inbound */

export function assessAssurance({ face, callerNumber, liveSession, hasBureauFile }) {
  const form = new FormData();
  if (face) form.append('face', face);
  if (callerNumber) form.append('caller_number', callerNumber);
  if (liveSession) form.append('livechallenge_session', liveSession);
  form.append('has_bureau_file', hasBureauFile ? 'true' : 'false');
  return request('/api/v1/assurance/assess', { method: 'POST', body: form }, 240000);
}

export const assuranceModel = () => request('/api/v1/assurance/model');

/** Absolute URL for a recorded spoken response, for an <audio> element. */
export const liveChallengeAudioUrl = (sessionId, round) =>
  `${baseUrl() || ''}/api/v1/livechallenge/audio/${encodeURIComponent(sessionId)}/${round}`;

export const initiateLiveChallenge = (applicantId, applicantRef) =>
  request('/api/v1/livechallenge/issue', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ applicant_id: applicantId, applicant_ref: applicantRef }),
  });

/**
 * Download a record. The PDF is issued and signed by the server — the browser
 * only saves it, so the document is not something the verified party produced
 * for themselves.
 */
async function savePdf(path, options) {
  if (!base) await discover();
  if (!base) return { ok: false, error: 'Backend offline — records are issued by the server.' };
  try {
    const res = await fetch(`${base}${path}`, options);
    if (!res.ok) return { ok: false, error: `Could not issue the record (HTTP ${res.status}).` };
    const blob = await res.blob();
    const ref = res.headers.get('X-Litmus-Reference') || 'litmus-record';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${ref}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    return { ok: true, reference: ref, code: res.headers.get('X-Litmus-Code') };
  } catch (err) {
    return { ok: false, error: `Could not issue the record: ${err.message}` };
  }
}

export const demoNumbers = () => request('/api/v1/demo/numbers');
export const mailStatus = () => request('/api/v1/report/mail-status');

/** Issue a record and deliver it. Email is optional throughout. */
export const emailRecord = (body) =>
  request('/api/v1/report/email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

export const downloadLiveChallengeRecord = (sessionId) =>
  savePdf(`/api/v1/report/livechallenge/${encodeURIComponent(sessionId)}`, { method: 'GET' });

export const downloadAssuranceRecord = (assessment, applicantRef, contact) =>
  savePdf('/api/v1/report/assurance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assessment, applicant_ref: applicantRef, contact }),
  });

export function verifyLiveChallenge(sessionId, blob, audioBlob) {
  const form = new FormData();
  // The endpoint takes the frame as multipart and the session as a query
  // parameter, so it is appended to the URL rather than the body.
  form.append('file', blob, 'response.jpg');
  if (audioBlob) form.append('audio', audioBlob, 'spoken.webm');
  return request(
    `/api/v1/livechallenge/verify?session_id=${encodeURIComponent(sessionId)}`,
    { method: 'POST', body: form },
    120000,
  );
}

export function analyzeFace(file) {
  const form = new FormData();
  form.append('file', file);
  return request('/api/v1/face/analyze', { method: 'POST', body: form }, 240000);
}

export function scoreEvidence({ face, voice }) {
  const form = new FormData();
  if (face) form.append('face', face);
  if (voice) form.append('voice', voice);
  // Model inference on a cold process can take a while — generous timeout.
  return request('/api/v1/verify/score', { method: 'POST', body: form }, 180000);
}

/* ------------------------------------------------------------ trustline */

export const initiateCall = (body) => request('/api/v1/trustline/initiate', json(body));
export const verifyCall = (body) => request('/api/v1/trustline/verify', json(body));
export const fraudFeed = (limit = 40) => request(`/api/v1/trustline/fraud-feed?limit=${limit}`);
export const purposes = () => request('/api/v1/trustline/purposes');

/* ---------------------------------------------------------------- intel */

export const friStatus = () => request('/api/v1/intel/fri/status');
export const friCheck = (number) => request(`/api/v1/intel/fri/check/${encodeURIComponent(number)}`);
export const consortiumStats = () => request('/api/v1/intel/consortium/stats');
export const consortiumLookup = (number) =>
  request(`/api/v1/intel/consortium/lookup/${encodeURIComponent(number)}`);
export const consortiumContribute = (body) =>
  request('/api/v1/intel/consortium/contribute', json(body));
export const consortiumMembers = () => request('/api/v1/intel/consortium/members');
