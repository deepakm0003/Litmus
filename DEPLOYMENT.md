# Deploying Litmus

Everything works locally today. This is what changes when it leaves your laptop,
in the order it will bite you.

---

## 1. HTTPS is not optional — the camera stops working without it

`getUserMedia` only runs in a **secure context**. Browsers make exactly one
exception: `localhost`. Deploy to plain `http://your-server.com` and **the
camera and microphone silently refuse**, which takes LiveChallenge, the live
face capture, and the whole assurance demonstration with them.

There is no workaround and no flag. You need a real certificate.

The easy paths, in order of how little work they are:

| Host | TLS | Notes |
|---|---|---|
| **Render** | automatic | Free tier sleeps after inactivity — first request takes ~50s |
| **Railway** | automatic | Simple, paid |
| **Fly.io** | automatic | Good for a persistent process |
| Your own VM | Caddy or nginx + Let's Encrypt | Most control, most work |

**Test this first, before anything else.** Open the deployed console on a phone
and press *Turn on camera*. If it fails, nothing else matters.

---

## 2. Memory, and why a restart wipes the demo

Sessions, consortium reports and challenge audio all live in Python
dictionaries. That means:

- **A restart loses everything** — TrustLine sessions, LiveChallenge sessions,
  the fraud feed
- **More than one worker breaks it** — a session minted by worker 1 is invisible
  to worker 2, so a challenge issued on one request cannot be verified on the
  next

So, for now:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1
```

**One worker.** Not a suggestion — with two, LiveChallenge fails roughly half
the time and looks like a bug.

The seeded demo numbers re-seed on every startup, so those survive restarts.
Live sessions do not.

For a pilot this moves to Redis with native TTLs. It is a contained change —
the state is already isolated in `_SESSIONS` / `_SIGNALS` dictionaries — but it
is not done, and the roadmap says so.

---

## 3. Memory footprint

Four models load at import: two face checkpoints, two voice checkpoints, the
fine-tuned CNN, plus MTCNN. Expect **~2 GB resident**.

A 512 MB free tier will be killed on startup. Budget **2 GB minimum**, and note
that first inference after a cold start takes several seconds while the weights
page in.

`models/face/faceguard_cnn.pt` is **44 MB** and must ship with the deployment —
without it the pipeline silently falls back to the public checkpoints, which
score AUC 0.652 instead of 0.934. Check it is in your build.

---

## 4. Secrets

Every one of these has a working development default, which is exactly why they
must be set in production — the defaults are in this repository.

```bash
LITMUS_TRUSTLINE_SECRET=<random 32+ bytes>      # signs call codes
LITMUS_LIVECHALLENGE_SECRET=<random 32+ bytes>  # signs challenges
LITMUS_REPORT_SECRET=<random 32+ bytes>         # signs PDF verification codes
LITMUS_CONSORTIUM_SALT=<random 32+ bytes>       # member pseudonyms
```

Generate them with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

If `LITMUS_REPORT_SECRET` stays at its default, anyone with this repository can
forge a verification code on a record. That is the whole point of the code, so
it is the one to get right.

---

## 5. Email delivery

Optional everywhere. Without credentials the record is composed and the response
says `sent: false` with a reason — it never claims a delivery it did not make.

### SMTP2GO HTTP API — use this one

```bash
LITMUS_SMTP2GO_API_KEY=api-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LITMUS_SMTP2GO_SENDER=you@a-domain-you-verified.com
```

Preferred over SMTP for deployment: it is an ordinary HTTPS request, so it
survives the outbound-port blocking that silently breaks SMTP on most managed
hosts.

**The sender must be a Verified Sender first, or every send is rejected.** In
the SMTP2GO dashboard: *Sending → Verified Senders → Add*. You can verify either

- **a single email address** — they send a confirmation link, which is the fast
  path and works with a Gmail or Outlook address you control; or
- **a whole domain** — needs DNS records, so only if you own the domain.

A university or employer address such as `@iiitd.ac.in` cannot be domain-
verified without DNS access. Verify a personal address as a single sender
instead, and send to yourself for the demonstration.

The API key is read from the environment only. It is never in source, so a copy
of this repository carries no ability to send mail as anyone. **Rotate a key the
moment it appears anywhere it should not** — a chat window, a screenshot, a
commit.

### Plain SMTP — the fallback

```bash
LITMUS_SMTP_HOST=smtp.gmail.com
LITMUS_SMTP_PORT=587
LITMUS_SMTP_USER=you@gmail.com
LITMUS_SMTP_PASSWORD=<app password>
LITMUS_SMTP_FROM=you@gmail.com
```

Gmail needs an **App Password** (Account → Security → 2-Step Verification → App
passwords), not your account password. Many hosts block outbound 587; port 465
with SSL sometimes gets through, but the HTTP API above avoids the problem
entirely.

Check which path is live at `/api/v1/report/mail-status`.

---

## 6. CORS

Currently `allow_origins=["*"]`, which is fine while the backend serves the
frontend from the same origin. If you split them, replace the wildcard with the
frontend's actual origin before anything goes public.

---

## 7. Build and serve

```bash
cd frontend/web && npm install && SINGLE=1 npm run build
cd ../../backend && uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1
```

The API serves the built bundle at `/console`, so the frontend is same-origin
and no CORS or API-discovery configuration is needed. `dist/index.html` must
exist before starting, or `/console` returns 503 with instructions.

---

## Pre-demo checklist

Run through this on the deployed URL, not locally:

- [ ] Page loads over **https://**
- [ ] Console pill reads **Live**, not *Backend offline*
- [ ] *Turn on camera* actually opens the camera
- [ ] LiveChallenge completes all three rounds
- [ ] **Download record (PDF)** produces a file
- [ ] Assurance shows the seeded numbers and reacts to `99999 00000`
- [ ] Face scoring returns in reasonable time after a cold start

If the free tier sleeps, **hit the URL five minutes before you present** so the
models are warm. A cold start in front of a jury looks like a broken product.
