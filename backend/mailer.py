"""
Litmus — delivering the verification record by email
====================================================

WHY EMAIL AND NOT SMS
---------------------
The demonstration runs on fabricated phone numbers, so a text message would
have nowhere real to go. Email is addressed to a mailbox the operator supplies,
so the record can actually arrive and be read.

DELIVERY PATHS
--------------
Two, tried in order:

  1. SMTP2GO's HTTP API, when LITMUS_SMTP2GO_API_KEY is set. Preferred for
     deployment because it is an ordinary HTTPS request — many hosts block
     outbound SMTP ports entirely, and this sidesteps that whole class of
     failure.
  2. Plain SMTP, when LITMUS_SMTP_HOST and credentials are set.

Neither key is ever read from source. Both come from the environment, so a
repository copy carries no ability to send mail as anyone.

CONFIGURED AND UNCONFIGURED
---------------------------
Sending needs SMTP credentials. When they are absent the message is composed in
full and reported as NOT SENT, with the reason. It is never reported as sent.

That distinction matters more than it looks: a verification record that a system
claims to have delivered, and did not, is worse than one it never offered —
somebody downstream will assume the applicant received their evidence.

    LITMUS_SMTP_HOST      smtp.gmail.com
    LITMUS_SMTP_PORT      587
    LITMUS_SMTP_USER      you@example.com
    LITMUS_SMTP_PASSWORD  an app password, never your account password
    LITMUS_SMTP_FROM      optional; defaults to the user
"""

from __future__ import annotations

import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any, Dict, Optional

SMTP_HOST = os.environ.get("LITMUS_SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("LITMUS_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("LITMUS_SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("LITMUS_SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("LITMUS_SMTP_FROM", SMTP_USER)
SMTP_TIMEOUT = float(os.environ.get("LITMUS_SMTP_TIMEOUT", "12"))

# SMTP2GO HTTP API. The sender address must be a Verified Sender on the account
# or the API rejects the send — that verification is done in their dashboard,
# not here.
SMTP2GO_API_KEY = os.environ.get("LITMUS_SMTP2GO_API_KEY", "")
SMTP2GO_ENDPOINT = os.environ.get(
    "LITMUS_SMTP2GO_ENDPOINT", "https://api.smtp2go.com/v3/email/send")
SMTP2GO_SENDER = os.environ.get("LITMUS_SMTP2GO_SENDER", SMTP_FROM)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def api_configured() -> bool:
    return bool(SMTP2GO_API_KEY and SMTP2GO_SENDER)


def smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def is_configured() -> bool:
    return api_configured() or smtp_configured()


def valid_address(address: str) -> bool:
    return bool(address and _EMAIL_RE.match(address.strip()))


def status() -> Dict[str, Any]:
    if api_configured():
        transport, detail = "smtp2go-api", SMTP2GO_ENDPOINT
    elif smtp_configured():
        transport, detail = "smtp", f"{SMTP_HOST}:{SMTP_PORT}"
    else:
        transport, detail = None, None

    return {
        "configured": is_configured(),
        "mode": "live" if is_configured() else "not configured",
        "transport": transport,
        "endpoint": detail,
        "from": (SMTP2GO_SENDER if api_configured() else SMTP_FROM) or None,
        "note": (
            f"Records will be delivered via {transport}. The sender address must be a "
            f"Verified Sender on the account, or the provider rejects the send."
            if is_configured() else
            "No delivery credentials are set, so records are composed but not sent. "
            "Set LITMUS_SMTP2GO_API_KEY and LITMUS_SMTP2GO_SENDER, or the "
            "LITMUS_SMTP_* variables. The record remains downloadable either way."
        ),
    }


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

def _body(kind: str, reference: str, code: str, headline: str,
          detail: str, lender: str) -> tuple[str, str]:
    """Plain text and HTML. Both are sent; the client picks."""
    title = ("Liveness Verification Record" if kind == "liveness"
             else "Identity Assurance Record")

    text = f"""{title}
{'=' * len(title)}

Reference        {reference}
Verification code {code}
Prepared for     {lender}

{headline}

{detail}

The full record is attached as a PDF. The verification code above is derived
from the document's own contents, so altering any field invalidates it — the
issuing system can confirm the code against the record at any time.

This record attests to identity verification only. It is not a credit
assessment and makes no claim about ability or willingness to repay.

Issued by Litmus.
"""

    html = f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f7f5ff;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:#f7f5ff;padding:32px 16px;">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="max-width:560px;background:#ffffff;border:1px solid #e6dffb;border-radius:14px;
              font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">

  <tr><td style="padding:26px 30px 18px;border-bottom:2px solid #17131f;">
    <div style="font:700 21px Georgia,serif;color:#17131f;letter-spacing:-.01em;">
      LITMUS<span style="color:#6231e0;">.</span>
    </div>
    <div style="margin-top:3px;font-size:10px;letter-spacing:.13em;color:#8d87a3;
                text-transform:uppercase;">Identity verification record</div>
  </td></tr>

  <tr><td style="padding:26px 30px 6px;">
    <div style="font:600 19px Georgia,serif;color:#17131f;">{title}</div>
    <p style="margin:14px 0 0;font-size:14px;line-height:1.62;color:#5f5975;">{headline}</p>
  </td></tr>

  <tr><td style="padding:18px 30px 6px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:#f7f5ff;border-radius:10px;">
      <tr>
        <td style="padding:14px 16px;font-size:11px;color:#8d87a3;
                   text-transform:uppercase;letter-spacing:.08em;">Reference</td>
        <td style="padding:14px 16px;font:600 13px ui-monospace,Consolas,monospace;
                   color:#17131f;text-align:right;">{reference}</td>
      </tr>
      <tr>
        <td style="padding:0 16px 14px;font-size:11px;color:#8d87a3;
                   text-transform:uppercase;letter-spacing:.08em;">Verification code</td>
        <td style="padding:0 16px 14px;font:600 13px ui-monospace,Consolas,monospace;
                   color:#6231e0;text-align:right;">{code}</td>
      </tr>
      <tr>
        <td style="padding:0 16px 14px;font-size:11px;color:#8d87a3;
                   text-transform:uppercase;letter-spacing:.08em;">Prepared for</td>
        <td style="padding:0 16px 14px;font-size:13px;color:#17131f;text-align:right;">{lender}</td>
      </tr>
    </table>
  </td></tr>

  <tr><td style="padding:14px 30px 0;">
    <p style="margin:0;font-size:13.5px;line-height:1.65;color:#5f5975;">{detail}</p>
  </td></tr>

  <tr><td style="padding:20px 30px 6px;">
    <div style="border-left:3px solid #6231e0;background:#ede7ff;border-radius:0 8px 8px 0;
                padding:13px 16px;font-size:12.5px;line-height:1.6;color:#5f5975;">
      The full record is attached as a PDF. The verification code is derived from the
      document&rsquo;s own contents, so altering any field invalidates it.
    </div>
  </td></tr>

  <tr><td style="padding:20px 30px 28px;border-top:1px solid #e6dffb;margin-top:10px;">
    <p style="margin:14px 0 0;font-size:11.5px;line-height:1.6;color:#8d87a3;">
      This record attests to identity verification only. It is not a credit assessment and
      makes no claim about ability or willingness to repay. Issued by Litmus.
    </p>
  </td></tr>

</table></td></tr></table></body></html>"""
    return text, html


def _send_via_api(to_address: str, subject: str, text: str, html: str,
                  pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Deliver through SMTP2GO's HTTP API.

    Chosen over SMTP wherever it is available: it is a normal HTTPS call, so it
    survives the outbound-port blocking that silently breaks SMTP on most
    managed hosts.
    """
    import base64
    import json as _json
    import urllib.error
    import urllib.request

    payload = {
        "sender": SMTP2GO_SENDER,
        "to": [to_address.strip()],
        "subject": subject,
        "text_body": text,
        "html_body": html,
        "attachments": [{
            "filename": filename,
            "fileblob": base64.b64encode(pdf_bytes).decode("ascii"),
            "mimetype": "application/pdf",
        }],
    }
    req = urllib.request.Request(
        SMTP2GO_ENDPOINT,
        data=_json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Smtp2go-Api-Key": SMTP2GO_API_KEY,
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=SMTP_TIMEOUT) as resp:
            body = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = _json.loads(exc.read().decode("utf-8"))
        except Exception:
            body = {"error": f"HTTP {exc.code}"}
        return {"sent": False, "reason": "api_error",
                "message": f"Delivery rejected by the provider: {body}"}
    except Exception as exc:  # noqa: BLE001
        return {"sent": False, "reason": "api_unreachable",
                "message": f"Could not reach the mail provider: {type(exc).__name__}."}

    data = body.get("data") or {}
    succeeded = int(data.get("succeeded", 0) or 0)
    if succeeded >= 1:
        return {"sent": True, "to": to_address.strip(), "subject": subject,
                "attachment": filename, "transport": "smtp2go-api",
                "provider_id": data.get("email_id"),
                "message": f"Record delivered to {to_address.strip()}."}

    # The most common cause by far, so name it rather than echoing raw JSON.
    failures = data.get("failures") or body.get("errors") or data
    hint = ""
    if "sender" in str(failures).lower() or "verified" in str(failures).lower():
        hint = (" The sender address must be added as a Verified Sender in the "
                "SMTP2GO dashboard before it can send.")
    return {"sent": False, "reason": "api_rejected",
            "message": f"The provider accepted the request but sent nothing: {failures}.{hint}"}


def send_record(
    to_address: str,
    pdf_bytes: bytes,
    filename: str,
    kind: str,
    reference: str,
    code: str,
    headline: str,
    detail: str,
    lender: str = "TVS Credit",
) -> Dict[str, Any]:
    """
    Deliver a record. Never raises; always reports what actually happened.
    """
    if not valid_address(to_address):
        return {"sent": False, "reason": "invalid_address",
                "message": f"'{to_address}' is not a valid email address."}

    subject = (
        f"Liveness verification record {reference}" if kind == "liveness"
        else f"Identity assurance record {reference}"
    )
    text, html = _body(kind, reference, code, headline, detail, lender)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM or "litmus@localhost"
    msg["To"] = to_address.strip()
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                       filename=filename)

    if api_configured():
        outcome = _send_via_api(to_address, subject, text, html, pdf_bytes, filename)
        if outcome.get("sent") or not smtp_configured():
            return outcome
        # The API refused but SMTP is also configured, so try it rather than
        # giving up. The usual cause is a sender address the API provider will
        # not relay for — a @gmail.com sender, say, whose DMARC record forbids
        # third-party servers. Google's own SMTP has no such problem with it.
        fallback = _send_via_smtp(msg)
        fallback["note"] = (
            f"The API path was refused ({outcome.get('reason')}), so delivery fell "
            f"back to SMTP."
        )
        return fallback

    if not is_configured():
        return {
            "sent": False,
            "reason": "not_configured",
            "message": (
                "Email delivery is not configured, so the record was composed but "
                "not sent. The PDF is still downloadable from the console."
            ),
            "would_send_to": to_address.strip(),
            "subject": subject,
            "attachment": filename,
            "attachment_bytes": len(pdf_bytes),
        }

    return _send_via_smtp(msg)


def _send_via_smtp(msg: EmailMessage) -> Dict[str, Any]:
    """Deliver over plain SMTP. Split out so the API path can fall back to it."""
    to_address = msg["To"]
    subject = msg["Subject"]
    try:
        context = ssl.create_default_context()
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT,
                                  context=context) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        return {
            "sent": True,
            "to": to_address.strip(),
            "subject": subject,
            "attachment": filename,
            "message": f"Record {reference} delivered to {to_address.strip()}.",
        }
    except Exception as exc:  # noqa: BLE001 — report, never crash the verification
        return {
            "sent": False,
            "reason": "smtp_error",
            "message": f"Delivery failed: {type(exc).__name__}. The PDF is still downloadable.",
        }
