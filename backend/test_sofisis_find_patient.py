import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SOFISIS_API_TOKEN")
BASE = (os.getenv("SOFISIS_BASE_URL", "https://sofisis.com") or "").rstrip("/")
VERIFY_SSL = os.getenv("SOFISIS_VERIFY_SSL", "true").lower() in ("1", "true", "yes", "y", "on")

# Puedes cambiar este valor para buscar otro paciente
IDENTIFICATION = "12345678999"

URL = f"{BASE}/api/v1/history_clinic/patient/?identification={IDENTIFICATION}"

headers = {
    "X-API-TOKEN": TOKEN or "",
    "Accept": "application/json",
}

print("TOKEN_START:", (TOKEN or "")[:6], "TOKEN_LEN:", len(TOKEN or ""))
print("GET:", URL)
print("VERIFY_SSL:", VERIFY_SSL)

r = requests.get(
    URL,
    headers=headers,
    timeout=30,
    verify=VERIFY_SSL
)

print("HTTP:", r.status_code)
print("RESP:", r.text[:4000])