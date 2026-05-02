import json, os, sys, time
from compose import compose_message
from dotenv import load_dotenv
load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')

def main():
    pairs_path = "embedded_testpairs.json"
    if not os.path.exists(pairs_path):
        print("ERROR: embedded_testpairs.json not found in project root!")
        return

    with open(pairs_path, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    print(f"Loaded {len(pairs)} test pairs from embedded_testpairs.json")

    results = []
    failed = []

    for pair in pairs:
        test_id   = pair["test_id"]
        category  = pair["category"]
        merchant  = pair["merchant"]
        trigger   = pair["trigger"]
        customer  = pair.get("customer")
        cat_slug  = merchant.get("category_slug", "")
        trg_kind  = trigger.get("kind", "unknown")
        m_name    = merchant.get("identity", {}).get("name", "?")

        print(f"  Generating {test_id}: [{cat_slug}/{trg_kind}] {m_name}...", end=" ", flush=True)
        time.sleep(4)  # stay under 15 req/min free tier limit

        try:
            result = compose_message(category, merchant, trigger, customer)
            if result and result.get("body"):
                results.append({
                    "test_id":         test_id,
                    "merchant_id":     pair["merchant_id"],
                    "trigger_id":      pair["trigger_id"],
                    "customer_id":     pair.get("customer_id"),
                    "category":        cat_slug,
                    "trigger_kind":    trg_kind,
                    "body":            result["body"],
                    "cta":             result.get("cta", "open_ended"),
                    "send_as":         result.get("send_as", "vera"),
                    "suppression_key": result.get("suppression_key", ""),
                    "rationale":       result.get("rationale", "")
                })
                print(f"✓")
            else:
                failed.append(test_id)
                print(f"✗ compose returned None")
        except Exception as e:
            failed.append(test_id)
            print(f"✗ ERROR: {e}")

    # Write submission.jsonl
    with open("submission.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n{'='*50}")
    print(f"✓ Written {len(results)}/30 to submission.jsonl")
    if failed:
        print(f"✗ Failed: {failed}")

    # ── Quality Check ──
    print("\n=== QUALITY CHECK (what the judge looks for) ===")
    passed = 0
    for r in results:
        body = r["body"]
        issues = []

        if len(body) < 60:
            issues.append("TOO SHORT — needs more context")
        if not any(ch.isdigit() for ch in body):
            issues.append("NO NUMBER — loses Specificity score")
        if not r.get("rationale", "").strip():
            issues.append("MISSING RATIONALE")
        if any(p in body.lower() for p in ["hope this finds", "i am reaching out", "dear merchant", "i hope you"]):
            issues.append("PREAMBLE DETECTED — loses Engagement score")
        if r["cta"] not in ["binary_yes_stop", "open_ended", "none"]:
            issues.append(f"INVALID CTA: {r['cta']}")

        # Check customer-facing send_as
        if r.get("customer_id") and r.get("send_as") != "merchant_on_behalf":
            issues.append("CUSTOMER MSG must have send_as=merchant_on_behalf")

        if issues:
            print(f"  ⚠  {r['test_id']} ({r['category']}/{r['trigger_kind']}): {'; '.join(issues)}")
        else:
            print(f"  ✓  {r['test_id']} ({r['category']}/{r['trigger_kind']})")
            passed += 1

    print(f"\nRESULT: {passed}/{len(results)} passed quality check")
    if passed == 30:
        print("🏆 PERFECT — all 30 passed. Ready to submit!")
    elif passed >= 25:
        print("✅ GOOD — review the ⚠ items above and fix if possible")
    else:
        print("⚠ NEEDS WORK — check compose.py for the failing trigger kinds")

    # Preview first 3
    print("\n=== FIRST 3 OUTPUTS PREVIEW ===")
    for r in results[:3]:
        print(f"\n[{r['test_id']}] {r['category']}/{r['trigger_kind']}")
        print(f"Body: {r['body']}")
        print(f"CTA: {r['cta']} | Send as: {r['send_as']}")
        print(f"Rationale: {r['rationale']}")

if __name__ == "__main__":
    main()
