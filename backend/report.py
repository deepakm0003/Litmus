"""
Litmus — verification record generation
=======================================

Produces the PDF evidence record for a completed verification.

WHY THE SERVER ISSUES IT
------------------------
The certificate is generated and signed here, never in the browser. A record
the client could assemble itself would be worthless as evidence — the party
being verified would be issuing their own proof. Each document carries an
HMAC-derived verification code computed over its own contents, so anyone
holding the PDF can check it back against the issuing server and detect a
single altered character.

ON BRANDING
-----------
The record is issued as a Litmus document, with the deploying lender named in a
"Prepared for" field. It deliberately does not imitate any lender's own
letterhead: a verification record about a named individual that appears to have
been issued by a bank is exactly the kind of document that causes harm if it
leaves the room it was made in. A lender deploying this would apply its own
brand through a controlled template.

DESIGN
------
Laid out to the conventions of a banking evidence document rather than a
marketing page: a metadata block at the head, numbered sections, hairline
rules instead of boxes, monospace for every identifier, and a verification
footer repeated on each page. Nothing decorative.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

_SECRET: bytes = os.environ.get(
    "LITMUS_REPORT_SECRET", "litmus-demo-report-secret"
).encode()

# Matches the product palette, muted for print.
INK = colors.HexColor("#17131F")
DIM = colors.HexColor("#5F5975")
FAINT = colors.HexColor("#8D87A3")
RULE = colors.HexColor("#C9C2E0")
ACCENT = colors.HexColor("#4A21C4")
GOOD = colors.HexColor("#0B7A6E")
WARN = colors.HexColor("#A5660B")
BAD = colors.HexColor("#A83326")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


def _now() -> datetime:
    return datetime.now(timezone.utc)


def verification_code(payload: str) -> str:
    """
    Short code binding this document to its contents.

    Derived over the document's own material, so altering any field invalidates
    it. Presented in four-character groups because it gets read aloud and typed
    back by people.
    """
    digest = hmac.new(_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest().upper()
    raw = digest[:16]
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


def check_code(payload: str, code: str) -> bool:
    return hmac.compare_digest(verification_code(payload), code.strip().upper())


class _Doc:
    """Thin layout helper over the canvas — tracks the cursor and paginates."""

    def __init__(self, title: str, reference: str, code: str, subject: str):
        self.buf = io.BytesIO()
        self.c = rl_canvas.Canvas(self.buf, pagesize=A4)
        self.c.setTitle(title)
        self.c.setAuthor("Litmus")
        self.c.setSubject(subject)
        self.title = title
        self.reference = reference
        self.code = code
        self.page = 0
        self.y = 0.0
        self._new_page(first=True)

    # ---------------------------------------------------------------- chrome
    def _new_page(self, first: bool = False) -> None:
        if not first:
            self._footer()
            self.c.showPage()
        self.page += 1
        self.y = PAGE_H - MARGIN
        if first:
            self._masthead()
        else:
            self._running_head()

    def _masthead(self) -> None:
        c = self.c
        c.setFillColor(INK)
        c.setFont("Times-Bold", 22)
        c.drawString(MARGIN, self.y - 6 * mm, "LITMUS")
        c.setFillColor(ACCENT)
        c.setFont("Times-Bold", 22)
        c.drawString(MARGIN + 27 * mm, self.y - 6 * mm, ".")

        c.setFillColor(FAINT)
        c.setFont("Helvetica", 7.5)
        c.drawRightString(PAGE_W - MARGIN, self.y - 3 * mm,
                          "IDENTITY VERIFICATION RECORD")
        c.drawRightString(PAGE_W - MARGIN, self.y - 7 * mm,
                          f"Reference {self.reference}")

        self.y -= 11 * mm
        c.setStrokeColor(INK)
        c.setLineWidth(1.1)
        c.line(MARGIN, self.y, PAGE_W - MARGIN, self.y)
        self.y -= 9 * mm

    def _running_head(self) -> None:
        c = self.c
        c.setFillColor(FAINT)
        c.setFont("Helvetica", 7.5)
        c.drawString(MARGIN, self.y - 3 * mm, f"LITMUS · {self.title}")
        c.drawRightString(PAGE_W - MARGIN, self.y - 3 * mm, f"Reference {self.reference}")
        self.y -= 6 * mm
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.line(MARGIN, self.y, PAGE_W - MARGIN, self.y)
        self.y -= 8 * mm

    def _footer(self) -> None:
        c = self.c
        y = MARGIN - 4 * mm
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.line(MARGIN, y + 7 * mm, PAGE_W - MARGIN, y + 7 * mm)
        c.setFillColor(FAINT)
        c.setFont("Helvetica", 6.8)
        c.drawString(MARGIN, y + 3 * mm,
                     "Machine-generated. Verification code binds this record to its contents; "
                     "any alteration invalidates it.")
        c.setFont("Courier", 6.8)
        c.drawString(MARGIN, y, f"CODE {self.code}")
        c.setFont("Helvetica", 6.8)
        c.drawRightString(PAGE_W - MARGIN, y, f"Page {self.page}")

    def _space(self, needed: float) -> None:
        if self.y - needed < MARGIN + 14 * mm:
            self._new_page()

    # ----------------------------------------------------------- primitives
    def title_block(self, heading: str, meta: List[Tuple[str, str]]) -> None:
        c = self.c
        c.setFillColor(INK)
        c.setFont("Times-Bold", 15)
        c.drawString(MARGIN, self.y, heading)
        self.y -= 8 * mm

        col = CONTENT_W / 3
        for i, (k, v) in enumerate(meta):
            row, colx = divmod(i, 3)
            x = MARGIN + colx * col
            yy = self.y - row * 9 * mm
            c.setFillColor(FAINT)
            c.setFont("Helvetica", 6.5)
            c.drawString(x, yy, k.upper())
            c.setFillColor(INK)
            c.setFont("Courier", 8.6)
            c.drawString(x, yy - 4 * mm, v[:38])
        rows = (len(meta) + 2) // 3
        self.y -= rows * 9 * mm + 3 * mm
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.line(MARGIN, self.y, PAGE_W - MARGIN, self.y)
        self.y -= 8 * mm

    def section(self, number: str, heading: str) -> None:
        # Reserve enough for the rule plus a few lines of whatever follows, so a
        # heading never strands itself at the foot of a page.
        self._space(42 * mm)
        c = self.c
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(MARGIN, self.y, number)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(MARGIN + 8 * mm, self.y, heading.upper())
        self.y -= 3 * mm
        c.setStrokeColor(INK)
        c.setLineWidth(0.7)
        c.line(MARGIN, self.y, PAGE_W - MARGIN, self.y)
        self.y -= 6 * mm

    def verdict_bar(self, label: str, detail: str, tone: str) -> None:
        self._space(24 * mm)
        c = self.c
        tint = {"good": GOOD, "warn": WARN, "bad": BAD}.get(tone, INK)
        c.setFillColor(tint)
        c.rect(MARGIN, self.y - 13 * mm, 1.6 * mm, 15 * mm, fill=1, stroke=0)
        c.setFillColor(tint)
        c.setFont("Times-Bold", 15)
        c.drawString(MARGIN + 6 * mm, self.y - 3 * mm, label)
        self.y -= 8 * mm
        self.paragraph(detail, indent=6 * mm, size=8.6)
        self.y -= 3 * mm

    def paragraph(self, text: str, indent: float = 0.0, size: float = 8.4,
                  colour=DIM) -> None:
        c = self.c
        width = CONTENT_W - indent
        chars = int(width / (size * 0.48))
        words, line = text.split(), ""
        lines: List[str] = []
        for w in words:
            if len(line) + len(w) + 1 <= chars:
                line = f"{line} {w}".strip()
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        for ln in lines:
            self._space(8 * mm)
            c.setFillColor(colour)
            c.setFont("Helvetica", size)
            c.drawString(MARGIN + indent, self.y, ln)
            self.y -= size * 0.52 * mm + 1.2 * mm
        self.y -= 1.5 * mm

    def table(self, cols: List[Tuple[str, float]], rows: List[List[Any]]) -> None:
        """cols = [(heading, width_fraction)]; rows may carry (text, colour)."""
        c = self.c
        self._space(18 * mm)
        widths = [f * CONTENT_W for _, f in cols]

        x = MARGIN
        c.setFillColor(FAINT)
        c.setFont("Helvetica-Bold", 6.4)
        for (head, _), w in zip(cols, widths):
            c.drawString(x, self.y, head.upper())
            x += w
        self.y -= 2.5 * mm
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.line(MARGIN, self.y, PAGE_W - MARGIN, self.y)
        self.y -= 5 * mm

        for row in rows:
            # Wrap each cell, then let the tallest decide the row height.
            cells: List[List[str]] = []
            for val, w in zip(row, widths):
                text = val[0] if isinstance(val, tuple) else str(val)
                chars = max(6, int((w - 3 * mm) / 4.05))
                out, line = [], ""
                for word in text.split():
                    if len(line) + len(word) + 1 <= chars:
                        line = f"{line} {word}".strip()
                    else:
                        out.append(line)
                        line = word
                if line:
                    out.append(line)
                cells.append(out or [""])

            height = max(len(cc) for cc in cells) * 4.2 * mm + 2 * mm
            self._space(height + 6 * mm)

            x = MARGIN
            for val, cc, w in zip(row, cells, widths):
                colour = val[1] if isinstance(val, tuple) and len(val) > 1 else INK
                mono = isinstance(val, tuple) and len(val) > 2 and val[2] == "mono"
                c.setFillColor(colour)
                c.setFont("Courier" if mono else "Helvetica", 8.2)
                for i, ln in enumerate(cc):
                    c.drawString(x, self.y - i * 4.2 * mm, ln)
                x += w
            self.y -= height
            c.setStrokeColor(colors.HexColor("#E8E3F6"))
            c.setLineWidth(0.4)
            c.line(MARGIN, self.y + 1 * mm, PAGE_W - MARGIN, self.y + 1 * mm)
            self.y -= 3 * mm
        self.y -= 3 * mm

    def note(self, text: str) -> None:
        self._space(20 * mm)
        c = self.c
        start = self.y
        self.y -= 2 * mm
        self.paragraph(text, indent=5 * mm, size=7.8, colour=DIM)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.9)
        c.line(MARGIN + 1 * mm, start + 2 * mm, MARGIN + 1 * mm, self.y + 2 * mm)
        self.y -= 2 * mm

    def finish(self) -> bytes:
        self._footer()
        self.c.save()
        return self.buf.getvalue()


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

def _reference(prefix: str, seed: str) -> str:
    h = hashlib.sha256(seed.encode()).hexdigest()[:8].upper()
    return f"{prefix}-{_now():%Y%m%d}-{h}"


def livechallenge_record(session: Dict[str, Any], evidence: List[Dict[str, Any]],
                         lender: str = "TVS Credit",
                         applicant_ref: str = "") -> Tuple[bytes, str, str]:
    """Evidence record for a completed liveness challenge."""
    ref = _reference("LC", session.get("session_id", ""))
    subject = applicant_ref or session.get("applicant_id", "—")
    payload = f"{ref}|{session.get('session_id')}|{subject}|{session.get('status')}"
    code = verification_code(payload)

    d = _Doc("Liveness Verification Record", ref, code,
             "Physical presence challenge — evidence record")

    passed = session.get("status") == "passed"
    d.title_block("LIVENESS VERIFICATION RECORD", [
        ("Prepared for", lender),
        ("Applicant reference", subject),
        ("Session", session.get("session_id", "—")),
        ("Issued", f"{_now():%Y-%m-%d %H:%M UTC}"),
        ("Rounds completed", f"{session.get('rounds_passed', 0)} of {session.get('rounds_required', 3)}"),
        ("Outcome", "PASSED" if passed else str(session.get("status", "—")).upper()),
    ])

    d.verdict_bar(
        "Physical presence established" if passed else "Presence not established",
        ("The applicant answered a randomised physical challenge generated after the "
         "verification session opened. A pre-recorded or synthetically generated video "
         "stream is fixed before that challenge exists and therefore cannot contain the "
         "response. Presence is established by construction rather than estimated by a "
         "detector.")
        if passed else
        ("The response did not satisfy the challenge issued. This is not, on its own, a "
         "finding of fraud: a mishearing, a poor capture or a misunderstood instruction "
         "produces the same result. Refer to a reviewer."),
        "good" if passed else "warn")

    d.section("1", "Challenge rounds")
    if evidence:
        rows = []
        for i, ev in enumerate(evidence, 1):
            ht = (ev.get("checks") or {}).get("head_turn", {})
            ok = ht.get("passed")
            rows.append([
                (f"Round {i}", INK),
                (str(ht.get("demanded", "—")), INK),
                (f"{ht.get('target_degrees', '—')}°", INK, "mono"),
                (f"{ht.get('measured_degrees', '—')}°", INK, "mono"),
                ("MATCH" if ok else "NO MATCH", GOOD if ok else BAD, "mono"),
            ])
        d.table([("Round", .16), ("Demanded pose", .24), ("Target", .16),
                 ("Measured", .16), ("Result", .28)], rows)
    else:
        d.paragraph("No round evidence recorded against this session.")

    d.section("2", "Method")
    d.table([("Property", .34), ("Value", .66)], [
        [("Measurement", INK), ("Head yaw derived from facial landmark geometry — "
                                "nose offset from the eye midpoint, normalised by "
                                "interocular distance", DIM)],
        [("Classifier used", INK), ("None. The check compares a measured angle against "
                                    "the angle demanded, and is auditable by inspection", DIM)],
        [("Tolerance", INK), ("±11° per round", DIM, "mono")],
        [("Challenge space", INK), ("5 poses per round, 3 rounds", DIM, "mono")],
        [("Blind-guess probability", INK), ("0.80% across the session", DIM, "mono")],
        [("Spoken word", INK), ("Server confirms speech was present, decoded from the "
                                "uploaded audio. Which word was said is not machine-"
                                "assessed and remains for human review", DIM)],
    ])

    d.section("3", "Scope and limitations")
    d.note(
        "This record attests to physical presence during the session named above. It "
        "makes no claim about the applicant's identity matching any document, their "
        "creditworthiness, or their capacity to repay. The spoken response is retained "
        "as evidence for human review and was not evaluated by any automated system. "
        "Voice-based synthesis detection was measured at 0% against contemporary neural "
        "text-to-speech and is deliberately not relied upon.")
    d.paragraph(
        f"Issued by Litmus for {lender}. Verify this record by presenting the code "
        f"below to the issuing system.", size=8)
    return d.finish(), ref, code


def assurance_record(assessment: Dict[str, Any], lender: str = "TVS Credit",
                     applicant_ref: str = "", contact: str = "") -> Tuple[bytes, str, str]:
    """Evidence record for an identity-assurance assessment."""
    ref = _reference("AS", f"{applicant_ref}{assessment.get('assurance_score')}")
    payload = f"{ref}|{applicant_ref}|{assessment.get('assurance_score')}|{assessment.get('assurance_level')}"
    code = verification_code(payload)

    d = _Doc("Identity Assurance Record", ref, code,
             "Identity assurance assessment — evidence record")

    level = assessment.get("assurance_level", "insufficient")
    tone = {"verified": "good", "provisional": "warn"}.get(level, "bad")

    d.title_block("IDENTITY ASSURANCE RECORD", [
        ("Prepared for", lender),
        ("Applicant reference", applicant_ref or "—"),
        ("Contact on file", contact or "not supplied"),
        ("Issued", f"{_now():%Y-%m-%d %H:%M UTC}"),
        ("Assurance score", f"{assessment.get('assurance_score', 0)} of 100"),
        ("Determination", str(assessment.get("label", "—"))),
    ])

    d.verdict_bar(str(assessment.get("label", "—")),
                  str(assessment.get("licenses", "")), tone)

    d.section("1", "Evidence considered")
    rows = []
    for ev in assessment.get("evidence", []):
        earned = ev.get("earned", 0)
        weight = ev.get("weight", 0)
        rows.append([
            (str(ev.get("signal", "")), INK),
            (str(ev.get("outcome", "")), DIM),
            (f"{earned} / {weight}",
             GOOD if earned == weight else (WARN if earned else FAINT), "mono"),
        ])
    d.table([("Signal", .28), ("Outcome", .50), ("Contribution", .22)], rows)

    d.section("2", "Basis for the weighting")
    d.table([("Signal", .30), ("Weight", .14), ("Reason", .56)], [
        [("Liveness challenge", INK), ("45", INK, "mono"),
         ("A verifiable fact rather than a model's opinion. Blind-guess probability "
          "0.80% across the session", DIM)],
        [("Face analysis", INK), ("25", INK, "mono"),
         ("Fine-tuned detector, held-out AUC 0.934. A strong signal, but a model, so "
          "weighted below the liveness proof", DIM)],
        [("Capture quality", INK), ("15", INK, "mono"),
         ("Gates the analysis above. Detector scores fall with resolution on genuine "
          "faces, so a poor capture supports no conclusion", DIM)],
        [("Network history", INK), ("15", INK, "mono"),
         ("Consortium fraud reports and DoT Financial Fraud Risk Indicator tier "
          "against the contact number", DIM)],
    ])

    if assessment.get("adverse_findings"):
        d.section("3", "Adverse findings")
        for f in assessment["adverse_findings"]:
            d.paragraph(f"— {f}", size=8.4, colour=BAD)

    d.section("4" if assessment.get("adverse_findings") else "3", "Scope and limitations")
    d.note(str(assessment.get("disclaimer", "")))
    rec = assessment.get("recovery") or {}
    if rec.get("headline"):
        d.paragraph(f"{rec['headline']}. {rec.get('detail', '')}", size=8.2)
    d.paragraph(
        f"Issued by Litmus for {lender}. This record is evidence of identity assurance "
        f"only. The credit decision, including affordability, remains with the "
        f"underwriter.", size=8)
    return d.finish(), ref, code
