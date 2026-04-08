import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SOFISIS_API_TOKEN")
BASE = (os.getenv("SOFISIS_BASE_URL", "https://sofisis.com") or "").rstrip("/")
VERIFY_SSL = os.getenv("SOFISIS_VERIFY_SSL", "true").lower() in ("1", "true", "yes", "y", "on")

URL = f"{BASE}/api/v1/history_clinic/patient/"

headers = {
    "X-API-TOKEN": TOKEN or "",
    "Accept": "application/json",
}

print("TOKEN_START:", (TOKEN or "")[:6], "TOKEN_LEN:", len(TOKEN or ""))
print("URL:", URL)

r = requests.options(URL, headers=headers, timeout=30, verify=VERIFY_SSL)

print("HTTP:", r.status_code)

try:
    data = r.json()
    print("JSON_KEYS:", list(data.keys()))
    post_fields = data.get("actions", {}).get("POST", {})
    print("\n=== CAMPOS POST ===")
    for k, v in post_fields.items():
        if isinstance(v, dict):
            print(
                f"- {k}: type={v.get('type')} "
                f"required={v.get('required')} "
                f"read_only={v.get('read_only')} "
                f"label={v.get('label')}"
            )
        else:
            print(f"- {k}: {v}")
except Exception:
    print("RESP_TEXT:", r.text[:4000])