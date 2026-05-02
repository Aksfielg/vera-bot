import json, os, sys, time
from compose import compose_message
from dotenv import load_dotenv
load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')

# Only generate these specific test IDs
REMAINING = {"T22", "T23", "T24", "T25", "T26", "T27", "T28", "T29", "T30"}

def main():
    with open("embedded_testpairs.json", "r", encoding="utf-8") as f:
        pairs = json.load(f)
    
    # Filter to only remaining pairs
    todo = [p for p in pairs if p["test_id"] in REMAINING]
    print(f"Generating {len(todo)} remaining pairs...")

    # Load already completed test IDs from submission.jsonl
    done_ids = set()
    if os.path.exists("submission.jsonl"):
        with open("submission.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    done_ids.add(json.loads(line)["test_id"])
    print(f"Already done: {done_ids}")

    results = []
    failed = []

    for pair in todo:
        test_id = pair["test_id"]
        if test_id in done_ids:
            print(f"  Skipping {test_id} — already in submission.jsonl")
            continue

        category = pair["category"]
        merchant = pair["merchant"]
        trigger = pair["trigger"]
        customer = pair.get("customer")
        cat_slug = merchant.get("category_slug", "")
        trg_kind = trigger.get("kind", "unknown")
        m_name = merchant.get("identity", {}).get("name", "?")

        print(f"  Generating {test_id}: [{cat_slug}/{trg_kind}] {m_name}...", end=" ", flush=True)
        time.sleep(5)  # 5s gap = stays under 12 req/min safely

        try:
            result = compose_message(category, merchant, trigger, customer)
            if result and result.get("body"):
                results.append({
                    "test_id": test_id,
                    "merchant_id": pair["merchant_id"],
                    "trigger_id": pair["trigger_id"],
                    "customer_id": pair.get("customer_id"),
                    "category": cat_slug,
                    "trigger_kind": trg_kind,
                    "body": result["body"],
                    "cta": result.get("cta", "open_ended"),
                    "send_as": result.get("send_as", "vera"),
                    "suppression_key": result.get("suppression_key", ""),
                    "rationale": result.get("rationale", "")
                })
                print("✓")
            else:
                failed.append(test_id)
                print("✗ compose returned None")
        except Exception as e:
            failed.append(test_id)
            print(f"✗ ERROR: {e}")

    # APPEND to existing submission.jsonl
    with open("submission.jsonl", "a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n✓ Appended {len(results)} new entries to submission.jsonl")
    if failed:
        print(f"✗ Still failed: {failed}")

    # Count total lines
    with open("submission.jsonl", "r", encoding="utf-8") as f:
        total = sum(1 for line in f if line.strip())
    print(f"Total in submission.jsonl: {total}/30")

    # Re-run quality check on all 30
    print("\n=== FINAL QUALITY CHECK ===")
    with open("submission.jsonl", "r", encoding="utf-8") as f:
        all_results = [json.loads(line) for line in f if line.strip()]

    passed = 0
    for r in sorted(all_results, key=lambda x: x["test_id"]):
        body = r["body"]
        issues = []
        if len(body) < 60: issues.append("too short")
        if not any(c.isdigit() for c in body): issues.append("NO NUMBER")
        if not r.get("rationale", "").strip(): issues.append("missing rationale")
        if any(p in body.lower() for p in ["hope this finds", "i am reaching out", "dear merchant"]):
            issues.append("preamble detected")
        if r["cta"] not in ["binary_yes_stop", "open_ended", "none"]:
            issues.append(f"INVALID CTA: {r['cta']}")
        if r.get("customer_id") and r.get("send_as") != "merchant_on_behalf":
            issues.append("needs send_as=merchant_on_behalf")
        if issues:
            print(f"  ⚠  {r['test_id']} ({r['category']}/{r['trigger_kind']}): {'; '.join(issues)}")
        else:
            print(f"  ✓  {r['test_id']} ({r['category']}/{r['trigger_kind']})")
            passed += 1

    print(f"\nFINAL RESULT: {passed}/{len(all_results)} passed")
    if passed == 30:
        print("🏆 PERFECT — all 30 passed. Submit now!")

if __name__ == "__main__":
    main()
