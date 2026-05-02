import json, os, sys, time
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("VERA-BOT COMPLETE VERIFICATION")
print("=" * 60)

# TEST 1: Groq API
print("\n[TEST 1] Groq API...")
try:
    from groq import Groq
    c = Groq(api_key=os.environ['GROQ_API_KEY'])
    r = c.chat.completions.create(
        messages=[{"role": "user", "content": "Say hello in 5 words"}],
        model="llama-3.3-70b-versatile"
    )
    print(f"  PASS: {r.choices[0].message.content.strip()}")
except Exception as e:
    print(f"  FAIL: {e}")

# TEST 2: compose() generates real dynamic messages
print("\n[TEST 2] Dynamic message generation (3 different merchants)...")
try:
    with open("embedded_testpairs.json", "r", encoding="utf-8") as f:
        pairs = json.load(f)
    from compose import compose_message
    for idx in [0, 8, 20]:
        pair = pairs[idx]
        result = compose_message(
            pair["category"], pair["merchant"],
            pair["trigger"], pair.get("customer")
        )
        is_fallback = "Fallback" in result.get("rationale", "")
        status = "FALLBACK" if is_fallback else "AI-GENERATED"
        print(f"  {pair['test_id']} [{status}] {pair['merchant']['identity']['name']}")
        print(f"    Body: {result['body'][:90]}...")
        print(f"    CTA: {result['cta']} | send_as: {result['send_as']}")
except Exception as e:
    print(f"  FAIL: {e}")

# TEST 3: submission.jsonl quality
print("\n[TEST 3] submission.jsonl quality check...")
try:
    with open("submission.jsonl", "r", encoding="utf-8") as f:
        entries = [json.loads(l) for l in f if l.strip()]
    print(f"  Total entries: {len(entries)}/30")
    passed = 0
    for r in entries:
        body = r["body"]
        issues = []
        if len(body) < 60: issues.append("TOO SHORT")
        if not any(c.isdigit() for c in body): issues.append("NO NUMBER")
        if r["cta"] not in ["binary_yes_stop","open_ended","none"]: issues.append(f"BAD CTA:{r['cta']}")
        if r.get("customer_id") and r.get("send_as") != "merchant_on_behalf": issues.append("WRONG SEND_AS")
        if "â€" in body or "â€™" in body: issues.append("ENCODING ERROR")
        if issues:
            print(f"  WARN {r['test_id']} ({r['trigger_kind']}): {issues}")
        else:
            passed += 1
    print(f"  RESULT: {passed}/30 passed {'PERFECT!' if passed==30 else 'NEEDS FIX'}")
except Exception as e:
    print(f"  FAIL: {e}")

# TEST 4: Server endpoints
print("\n[TEST 4] Live server endpoints...")
try:
    import requests
    # healthz
    r = requests.get("http://localhost:8000/v1/healthz", timeout=5)
    data = r.json()
    ctx = data.get("contexts_loaded", {})
    print(f"  healthz: status={data['status']} contexts={ctx}")
    if ctx.get("merchant", 0) == 0:
        print("  WARNING: No contexts loaded! Run: python load_dataset.py")

    # tick
    r = requests.post("http://localhost:8000/v1/tick",
        json={"now": "2026-05-01T10:00:00Z",
              "available_triggers": ["trg_001_research_digest_dentists", "trg_004_perf_dip_bharat"]},
        timeout=35)
    actions = r.json().get("actions", [])
    print(f"  tick: returned {len(actions)} actions")
    for a in actions:
        print(f"    merchant={a.get('merchant_id','?')} send_as={a.get('send_as','?')}")
        print(f"    body: {a.get('body','')[:80]}...")

    # reply
    if actions:
        conv_id = actions[0].get("conversation_id")
        merchant_id = actions[0].get("merchant_id")
        r2 = requests.post("http://localhost:8000/v1/reply",
            json={"conversation_id": conv_id, "merchant_id": merchant_id,
                  "from_role": "merchant", "message": "yes please go ahead", "turn_number": 1},
            timeout=35)
        reply_data = r2.json()
        print(f"  reply: action={reply_data.get('action')} body={str(reply_data.get('body',''))[:60]}...")
    else:
        print("  reply: skipped (no actions from tick)")

except requests.exceptions.ConnectionError:
    print("  FAIL: Server not running! Start with: python main.py")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)