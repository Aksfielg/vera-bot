import json, os, requests, time

BASE_URL = os.environ.get("BOT_URL", "http://localhost:8000")

def load_all():
    bundle_path = "dataset_bundle.json"
    if not os.path.exists(bundle_path):
        print("WARNING: dataset_bundle.json not found. Bot will start empty.")
        return {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}

    with open(bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    loaded = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
    
    scope_map = [
        ("category", bundle.get("categories", {}).items(), lambda k, v: k),
        ("merchant", bundle.get("merchants", {}).items(), lambda k, v: k),
        ("customer", bundle.get("customers", {}).items(), lambda k, v: k),
        ("trigger",  bundle.get("triggers",  {}).items(), lambda k, v: k),
    ]

    for scope, items, get_id in scope_map:
        for context_id, payload in items:
            try:
                body = {
                    "scope": scope,
                    "context_id": context_id,
                    "version": 1,
                    "payload": payload,
                    "delivered_at": "2026-04-29T10:00:00Z"
                }
                resp = requests.post(f"{BASE_URL}/v1/context", json=body, timeout=10)
                if resp.status_code in (200, 409):
                    loaded[scope] += 1
            except Exception as e:
                print(f"Error loading {scope} {context_id}: {e}")
        print(f"  Loaded {loaded[scope]} {scope} contexts")

    return loaded

if __name__ == "__main__":
    print("Loading dataset into bot...")
    result = load_all()
    print("Done:", result)
