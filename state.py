import time

class ContextStore:
    def __init__(self):
        self._store = {}
        self._suppression_keys = set()
        self._conversations = {}
        self._start_time = time.time()

    def upsert(self, scope, context_id, version, payload):
        existing = self._store.get(context_id)
        if existing is None or version > existing.get("version", -1):
            self._store[context_id] = {
                "scope": scope,
                "version": version,
                "payload": payload
            }

    def get(self, scope, context_id):
        entry = self._store.get(context_id)
        if entry and entry["scope"] == scope:
            return entry["payload"]
        
        # Fallback search by merchant_id in payload
        for _, val in self._store.items():
            if val["scope"] == scope and val.get("payload", {}).get("merchant_id") == context_id:
                return val["payload"]
                
        return None

    def get_version(self, context_id):
        entry = self._store.get(context_id)
        if entry:
            return entry["version"]
        return None

    def get_all(self, scope):
        return [val["payload"] for val in self._store.values() if val["scope"] == scope]

    def count_all(self):
        counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
        for val in self._store.values():
            scope = val["scope"]
            if scope in counts:
                counts[scope] += 1
        return counts

    def get_used_suppression_keys(self):
        return self._suppression_keys

    def mark_suppression_key(self, key):
        self._suppression_keys.add(key)

    def add_conversation(self, conv_id, merchant_id, customer_id, trigger_id):
        self._conversations[conv_id] = {
            "conv_id": conv_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "trigger_id": trigger_id,
            "message_history": [],
            "turn_count": 0,
            "state": "open"
        }

    def get_conversation(self, conv_id):
        return self._conversations.get(conv_id)

    def add_to_conversation(self, conv_id, role, message):
        conv = self._conversations.get(conv_id)
        if conv:
            conv["message_history"].append({"role": role, "message": message})
            conv["turn_count"] += 1

    def get_uptime(self):
        return time.time() - self._start_time
