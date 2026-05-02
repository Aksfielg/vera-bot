import os, time, requests
BOT_URL = os.environ.get("BOT_URL", "http://localhost:8000")
print(f"Keep-alive pinger started for {BOT_URL}")
while True:
    try:
        r = requests.get(f"{BOT_URL}/v1/healthz", timeout=10)
        print(f"[{time.strftime('%H:%M:%S')}] healthz → {r.status_code}")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ping failed: {e}")
    time.sleep(240)
