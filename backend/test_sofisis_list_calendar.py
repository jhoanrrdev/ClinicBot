import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

TOKEN = os.getenv("SOFISIS_API_TOKEN")
BASE = (os.getenv("SOFISIS_BASE_URL", "https://sofisis.com") or "").rstrip("/")
VERIFY_SSL = os.getenv("SOFISIS_VERIFY_SSL", "true").lower() in ("1", "true", "yes", "y", "on")

url = f"{BASE}/api/v1/schedule/calendar/?_page_size=5"

headers = {
    "X-API-TOKEN": TOKEN or "",
    "Accept": "application/json",
}

r = requests.get(url, headers=headers, timeout=30, verify=VERIFY_SSL)

print("HTTP:", r.status_code)
try:
    data = r.json()
    print(json.dumps(data, indent=2, ensure_ascii=False)[:5000])
except Exception:
    print(r.text[:5000])