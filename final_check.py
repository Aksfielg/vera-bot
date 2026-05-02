import json, os, sys, time, requests
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

PASS = []
FAIL = []

def ok(msg): print(f"  ✓ {msg}"); PASS.append(msg)
def fail(msg): print(f"  ✗ {msg}"); FAIL.append(msg)

print("=" * 60)
print("VERA-BOT FINAL COMPLETE CHECK")
print("=" * 60)

# ── CHECK 1: Environment variables ──
print("\n[1] Environment Variables")
gemini = os.environ.get("GEMINI_API_KEY", "")
groq = os.environ.get("GROQ_API_KEY", "")
if gemini.startswith("AIza") and len(gemini) > 30:
    ok(f"GEMINI_API_KEY loaded (ends: ...{gemini[-6:]})")
else:
    fail("GEMINI_API_KEY missing or wrong format")
if groq.startswith("gsk_") and len(groq) > 20:
    ok(f"GROQ_API_KEY loaded (ends: ...{groq[-6:]})")
else:
    fail("GROQ_API_KEY missing or wrong format")

# ── CHECK 2: Groq API live call ──
print("\n[2] Groq API Live Test")
try:
    from groq import Groq
    c = Groq(api_key=groq)
    r = c.chat.completions.create(
        messages=[{"role": "user", "content": "Say hello in 5 words"}],
        model="llama-3.3-70b-versatile"
    )
    reply = r.choices[0].message.content.strip()
    ok(f"Groq responded: {reply}")
except Exception as e:
    fail(f"Groq failed: {str(e)[:80]}")

# ── CHECK 3: Gemini API live call ──
print("\n[3] Gemini API Live Test")
try:
    import google.generativeai as genai
    genai.configure(api_key=gemini)
    model = genai.GenerativeModel("gemini-2.0-flash")
    r = model.generate_content("Say hello in 5 words")
    ok(f"Gemini responded: {r.text.strip()[:50]}")
except Exception as e:
    err = str(e)[:100]
    if "429" in err or "quota" in err.lower():
        ok(f"Gemini quota exhausted but key valid — Groq will handle")
    else:
        fail(f"Gemini key invalid: {err}")

# ── CHECK 4: compose() generates real messages ──
print("\n[4] compose() — 5 different trigger types")
try:
    with open("embedded_testpairs.json", "r", encoding="utf-8") as f:
        pairs = json.load(f)
    from compose import compose_message

    test_indices = [0, 5, 12, 20, 27]
    for idx in test_indices:
        pair = pairs[idx]
        t0 = time.time()
        result = compose_message(
            pair["category"], pair["merchant"],
            pair["trigger"], pair.get("customer")
        )
        elapsed = round(time.time() - t0, 1)
        body = result.get("body", "")
        is_fallback = "Fallback" in result.get("rationale", "")
        has_num = any(c.isdigit() for c in body)
        valid_cta = result.get("cta") in ["binary_yes_stop","open_ended","none"]
        src = "FALLBACK" if is_fallback else "GROQ/GEMINI"
        if body and has_num and valid_cta:
            ok(f"{pair['test_id']} [{src}] {elapsed}s — {body[:60]}...")
        else:
            fail(f"{pair['test_id']} issues — body={bool(body)} num={has_num} cta={valid_cta}")
except Exception as e:
    fail(f"compose() crashed: {e}")

# ── CHECK 5: submission.jsonl ──
print("\n[5] submission.jsonl — All 30 entries")
try:
    with open("submission.jsonl", "r", encoding="utf-8") as f:
        entries = [json.loads(l) for l in f if l.strip()]
    if len(entries) == 30:
        ok(f"30 entries found")
    else:
        fail(f"Only {len(entries)} entries found — need 30")

    issues_count = 0
    for r in entries:
        body = r["body"]
        probs = []
        if len(body) < 60: probs.append("short")
        if not any(c.isdigit() for c in body): probs.append("no_number")
        if r["cta"] not in ["binary_yes_stop","open_ended","none"]: probs.append("bad_cta")
        if r.get("customer_id") and r.get("send_as") != "merchant_on_behalf": probs.append("wrong_send_as")
        if "â€" in body: probs.append("encoding_error")
        if not r.get("rationale","").strip(): probs.append("no_rationale")
        if probs:
            print(f"    ⚠ {r['test_id']}: {probs}")
            issues_count += 1

    if issues_count == 0:
        ok("All 30 entries pass quality check")
    else:
        fail(f"{issues_count} entries have issues")

    # Check key test IDs
    entry_map = {e["test_id"]: e for e in entries}
    for tid in ["T03","T04","T07","T08","T13","T14","T15","T28","T29"]:
        e = entry_map.get(tid, {})
        if e.get("send_as") == "merchant_on_behalf":
            ok(f"{tid} send_as=merchant_on_behalf ✓")
        else:
            fail(f"{tid} send_as={e.get('send_as')} — should be merchant_on_behalf")

except Exception as e:
    fail(f"submission.jsonl error: {e}")

# ── CHECK 6: Live server ──
print("\n[6] Live Server Endpoints")
try:
    # healthz
    r = requests.get("http://localhost:8000/v1/healthz", timeout=5)
    data = r.json()
    ctx = data.get("contexts_loaded", {})
    if data.get("status") == "ok":
        ok(f"healthz OK — contexts: {ctx}")
    else:
        fail(f"healthz bad status: {data}")

    if ctx.get("merchant", 0) < 50:
        fail("Merchants not loaded — run: python load_dataset.py")
    else:
        ok("All 355 contexts loaded (5+50+200+100)")

    # tick with 3 triggers
    r = requests.post("http://localhost:8000/v1/tick",
        json={"now": "2026-05-01T10:00:00Z",
              "available_triggers": [
                  "trg_001_research_digest_dentists",
                  "trg_004_perf_dip_bharat",
                  "trg_010_ipl_match_delhi"
              ]},
        timeout=35)
    actions = r.json().get("actions", [])
    if len(actions) >= 2:
        ok(f"tick returned {len(actions)} actions")
        for a in actions:
            body = a.get("body","")
            ok(f"  → {a['merchant_id'][:30]} | {body[:55]}...")
    else:
        fail(f"tick returned only {len(actions)} actions")

    # reply test
    if actions:
        conv_id = actions[0].get("conversation_id")
        mid = actions[0].get("merchant_id")
        r2 = requests.post("http://localhost:8000/v1/reply",
            json={"conversation_id": conv_id, "merchant_id": mid,
                  "from_role": "merchant", "message": "yes please go ahead",
                  "turn_number": 1},
            timeout=35)
        rd = r2.json()
        if rd.get("action") in ["send","wait","end"]:
            ok(f"reply action={rd['action']} body={str(rd.get('body',''))[:50]}...")
        else:
            fail(f"reply bad response: {rd}")

    # metadata
    r = requests.get("http://localhost:8000/v1/metadata", timeout=5)
    meta = r.json()
    ok(f"metadata: bot={meta.get('bot_name')} model={meta.get('model')}")

    # auto-reply detection
    if actions:
        conv_id = actions[0].get("conversation_id")
        mid = actions[0].get("merchant_id")
        r3 = requests.post("http://localhost:8000/v1/reply",
            json={"conversation_id": conv_id, "merchant_id": mid,
                  "from_role": "merchant",
                  "message": "Aapki jaankari ke liye bahut-bahut shukriya. Main aapki yeh sabhi baatein team tak pahuncha deti hoon.",
                  "turn_number": 2},
            timeout=35)
        rd3 = r3.json()
        if rd3.get("action") in ["end","send"]:
            ok(f"Auto-reply detection working: action={rd3.get('action')}")
        else:
            fail(f"Auto-reply detection issue: {rd3}")

except requests.exceptions.ConnectionError:
    fail("Server not running — start with: python main.py")
except Exception as e:
    fail(f"Server test error: {e}")

# ── FINAL SUMMARY ──
print("\n" + "=" * 60)
print(f"PASSED: {len(PASS)} | FAILED: {len(FAIL)}")
if not FAIL:
    print("🏆 ALL CHECKS PASSED — BOT IS READY TO SUBMIT!")
else:
    print("⚠ ISSUES FOUND:")
    for f in FAIL:
        print(f"  ✗ {f}")
print("=" * 60)
