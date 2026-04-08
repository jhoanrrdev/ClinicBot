import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ✅ Carga el .env desde la carpeta actual (backend)
load_dotenv()

TOKEN = os.getenv("SOFISIS_API_TOKEN")
print("TOKEN_START:", (TOKEN or "")[:6], "TOKEN_LEN:", len(TOKEN or ""))

BASE = (os.getenv("SOFISIS_BASE_URL", "https://sofisis.com") or "").rstrip("/")
VERIFY_SSL = os.getenv("SOFISIS_VERIFY_SSL", "true").lower() in ("1", "true", "yes", "y", "on")

URL = f"{BASE}/api/v1/schedule/appointment/"

headers = {
    "X-API-TOKEN": TOKEN or "",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

start_dt = datetime(2026, 3, 1, 15, 30, 0)
end_dt = start_dt + timedelta(minutes=30)

payload = {
    "patient_cell": "573111234567",
    "user_transaction_cell": "573111234567",
    "text": "Cita Odontologia - test min payload",
    "start_date": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
    "end_date": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
}

print("POST:", URL)
print("VERIFY_SSL:", VERIFY_SSL)
print("PAYLOAD:", payload)

r = requests.post(URL, headers=headers, json=payload, timeout=30, verify=VERIFY_SSL)

print("HTTP:", r.status_code)
print("RESP:", r.text)