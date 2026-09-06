"""
TrustLine test suite — adversarial, not happy-path.

Every test here is a scam attempt that TrustLine must survive. Run with:
    python backend/test_trustline.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from trustline import (  # noqa: E402
    initiate_call_session,
    verify_phrase,
    derive_phrase,
    get_fraud_feed,
    list_active_sessions,
    reset_state,
    _SESSIONS,
    SESSION_TTL_SECONDS,
    MAX_VERIFY_ATTEMPTS,
)

PASS, FAIL = 0, 0


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}  {detail}")


CUSTOMER = "TVSC_884213"
PHONE = "9840012345"
AGENT = "AGT_2291"
AGENT_NAME = "Priya Raghavan"


# ---------------------------------------------------------------------------
print("\n=== 1. Genuine call: agent proves identity to customer ===")
reset_state()

call = initiate_call_session(
    customer_id=CUSTOMER, customer_phone=PHONE,
    agent_id=AGENT, agent_name=AGENT_NAME, purpose="emi_reminder",
)
print(f"  Phrase issued to agent + pushed to customer: {call['phrase']}")

check("phrase is word-word-digits format",
      call["phrase"].count("-") == 2 and call["phrase"].split("-")[2].isdigit(),
      call["phrase"])
check("customer phone is masked in response",
      call["customer_phone"].endswith("2345") and "*" in call["customer_phone"],
      call["customer_phone"])
check("agent gets a spoken script", "TrustLine code" in call["agent_script"])

res = verify_phrase(CUSTOMER, call["phrase"], caller_number="1600123456")
check("correct phrase verifies GENUINE", res["result"] == "GENUINE", res["result"])
check("genuine result is safe to proceed",
      res["recommended_action"] == "safe_to_proceed")
check("genuine result still warns about OTP", "OTP" in res.get("reminder", ""))


# ---------------------------------------------------------------------------
print("\n=== 2. Scammer calls when TVS Credit is NOT calling ===")
reset_state()

res = verify_phrase(
    customer_id=CUSTOMER,
    claimed_phrase="TIGER-STONE-42",
    caller_number="9123456789",
    claimed_purpose="loan_approval",
)
check("no active session is caught", res["result"] == "NO_ACTIVE_SESSION", res["result"])
check("severity is critical", res["severity"] == "critical")
check("customer told to hang up", res["recommended_action"] == "hang_up_and_report")
check("fraud report filed", "fraud_report_id" in res)


# ---------------------------------------------------------------------------
print("\n=== 3. Scammer rides a real call window with a guessed code ===")
reset_state()

call = initiate_call_session(
    customer_id=CUSTOMER, customer_phone=PHONE,
    agent_id=AGENT, agent_name=AGENT_NAME, purpose="collections",
)
res = verify_phrase(CUSTOMER, "MANGO-CLOUD-11", caller_number="9123456789")
check("wrong code during a live session is rejected",
      res["result"] == "PHRASE_MISMATCH", res["result"])
check("mismatch severity is high", res["severity"] == "high")


# ---------------------------------------------------------------------------
print("\n=== 4. Brute force: 3 attempts then lock ===")
reset_state()

call = initiate_call_session(
    customer_id=CUSTOMER, customer_phone=PHONE,
    agent_id=AGENT, agent_name=AGENT_NAME, purpose="emi_reminder",
)
for i in range(MAX_VERIFY_ATTEMPTS + 1):
    verify_phrase(CUSTOMER, f"WRONG-GUESS-{i:02d}", caller_number="9123456789")

session = list(_SESSIONS.values())[0]
check("session locks after max attempts", session.status == "locked", session.status)

after_lock = verify_phrase(CUSTOMER, call["phrase"], caller_number="9123456789")
check("correct code no longer works once locked",
      after_lock["result"] != "GENUINE", after_lock["result"])


# ---------------------------------------------------------------------------
print("\n=== 5. Replay: a verified phrase cannot be reused ===")
reset_state()

call = initiate_call_session(
    customer_id=CUSTOMER, customer_phone=PHONE,
    agent_id=AGENT, agent_name=AGENT_NAME, purpose="document_request",
)
first = verify_phrase(CUSTOMER, call["phrase"])
second = verify_phrase(CUSTOMER, call["phrase"])
check("first use verifies", first["result"] == "GENUINE")
check("replay of same phrase fails",
      second["result"] == "NO_ACTIVE_SESSION", second["result"])


# ---------------------------------------------------------------------------
print("\n=== 6. Cross-customer: phrase from customer A fails for customer B ===")
reset_state()

call_a = initiate_call_session(
    customer_id="TVSC_AAA", customer_phone="9800000001",
    agent_id=AGENT, agent_name=AGENT_NAME, purpose="emi_reminder",
)
initiate_call_session(
    customer_id="TVSC_BBB", customer_phone="9800000002",
    agent_id=AGENT, agent_name=AGENT_NAME, purpose="emi_reminder",
)
res = verify_phrase("TVSC_BBB", call_a["phrase"])
check("A's phrase does not verify for B",
      res["result"] == "PHRASE_MISMATCH", res["result"])


# ---------------------------------------------------------------------------
print("\n=== 7. Expiry ===")
reset_state()

call = initiate_call_session(
    customer_id=CUSTOMER, customer_phone=PHONE,
    agent_id=AGENT, agent_name=AGENT_NAME, purpose="emi_reminder",
)
session = list(_SESSIONS.values())[0]
session.expires_at = time.time() - 1     # force expiry

res = verify_phrase(CUSTOMER, call["phrase"])
check("expired session does not verify",
      res["result"] == "NO_ACTIVE_SESSION", res["result"])


# ---------------------------------------------------------------------------
print("\n=== 8. Scam-purpose short circuit (the digital-arrest pattern) ===")
reset_state()

# Scammer has somehow got a real code, but asks for an OTP. Code check must
# not rescue the call — the purpose alone is decisive.
call = initiate_call_session(
    customer_id=CUSTOMER, customer_phone=PHONE,
    agent_id=AGENT, agent_name=AGENT_NAME, purpose="emi_reminder",
)
res = verify_phrase(
    CUSTOMER, call["phrase"],
    caller_number="9123456789", claimed_purpose="otp_request",
)
check("OTP request is SCAM_CONFIRMED regardless of a valid code",
      res["result"] == "SCAM_CONFIRMED", res["result"])

for bad in ("remote_access", "digital_arrest", "upi_pin", "loan_processing_fee"):
    r = verify_phrase(CUSTOMER, "X", caller_number="9123456789", claimed_purpose=bad)
    check(f"scam purpose '{bad}' confirmed", r["result"] == "SCAM_CONFIRMED", r["result"])


# ---------------------------------------------------------------------------
print("\n=== 9. Normalisation: customer mistypes what they heard ===")
reset_state()

call = initiate_call_session(
    customer_id=CUSTOMER, customer_phone=PHONE,
    agent_id=AGENT, agent_name=AGENT_NAME, purpose="emi_reminder",
)
phrase = call["phrase"]

for variant, label in [
    (phrase.lower(), "lowercase"),
    (phrase.replace("-", " "), "spaces instead of hyphens"),
    (f"  {phrase}  ", "leading/trailing whitespace"),
    (phrase.replace("-", "  "), "double spaces"),
]:
    reset_state()
    c = initiate_call_session(
        customer_id=CUSTOMER, customer_phone=PHONE,
        agent_id=AGENT, agent_name=AGENT_NAME, purpose="emi_reminder",
    )
    v = variant.replace(phrase, c["phrase"]) if phrase in variant else None
    # regenerate the variant against the fresh phrase
    p = c["phrase"]
    v = {
        "lowercase": p.lower(),
        "spaces instead of hyphens": p.replace("-", " "),
        "leading/trailing whitespace": f"  {p}  ",
        "double spaces": p.replace("-", "  "),
    }[label]
    r = verify_phrase(CUSTOMER, v)
    check(f"accepts {label}", r["result"] == "GENUINE", f"{v} -> {r['result']}")


# ---------------------------------------------------------------------------
print("\n=== 10. Campaign detection: scammers generate the fraud feed ===")
reset_state()

SCAM_NUMBER = "9198765432"
for i in range(5):
    verify_phrase(
        customer_id=f"TVSC_VICTIM_{i}",
        claimed_phrase="TIGER-STONE-01",
        caller_number=SCAM_NUMBER,
        claimed_purpose="loan_approval",
    )

feed = get_fraud_feed()
check("all 5 failures recorded", feed["total_reports"] == 5, feed["total_reports"])
check("campaign detected on the scam number",
      any(c["caller_number"] == SCAM_NUMBER for c in feed["active_campaigns"]),
      feed["active_campaigns"])

last = verify_phrase(
    customer_id="TVSC_VICTIM_9", claimed_phrase="X",
    caller_number=SCAM_NUMBER, claimed_purpose="loan_approval",
)
alert = last.get("campaign_alert")
check("campaign alert returned inline", alert is not None and alert["campaign_detected"])
check("alert counts distinct victims",
      alert and alert["distinct_customers_targeted"] >= 5,
      alert)


# ---------------------------------------------------------------------------
print("\n=== 11. Determinism and key-binding of phrase derivation ===")

p1 = derive_phrase("C1", "A1", "S1", "emi_reminder")
p2 = derive_phrase("C1", "A1", "S1", "emi_reminder")
check("derivation is deterministic", p1 == p2, f"{p1} vs {p2}")

check("different customer -> different phrase",
      derive_phrase("C2", "A1", "S1", "emi_reminder") != p1)
check("different session -> different phrase",
      derive_phrase("C1", "A1", "S2", "emi_reminder") != p1)
check("different purpose -> different phrase",
      derive_phrase("C1", "A1", "S1", "collections") != p1)


# ---------------------------------------------------------------------------
print("\n=== 12. Invalid purpose is rejected at initiation ===")
reset_state()
try:
    initiate_call_session(
        customer_id=CUSTOMER, customer_phone=PHONE,
        agent_id=AGENT, agent_name=AGENT_NAME, purpose="sell_them_crypto",
    )
    check("unknown purpose rejected", False, "no exception raised")
except ValueError:
    check("unknown purpose rejected", True)


# ---------------------------------------------------------------------------
print("\n" + "=" * 62)
print(f"  TrustLine: {PASS} passed, {FAIL} failed")
print("=" * 62)
sys.exit(1 if FAIL else 0)
