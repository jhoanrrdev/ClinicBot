import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SOFISIS_API_TOKEN")
BASE = (os.getenv("SOFISIS_BASE_URL", "https://sofisis.com") or "").rstrip("/")
VERIFY_SSL = os.getenv("SOFISIS_VERIFY_SSL", "true").lower() in ("1", "true", "yes", "y", "on")

URL = f"{BASE}/api/v1/history_clinic/patient/"

print("TOKEN_START:", (TOKEN or "")[:6], "TOKEN_LEN:", len(TOKEN or ""))

headers = {
    "X-API-TOKEN": TOKEN or "",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

payload = {
    "first_name": "Jhoan",
    "last_name": "Prueba",
    "identification": "12345678999",
    "email": "jhoan.prueba.clinicbot+1@gmail.com",
    "cell": "573111234567",
    "phone": "573111234567",
    "address": "Bello, Antioquia",
    "city": "Bello",
    "state": "Antioquia",
    "is_customer": True,
    "observation": "Paciente creado desde ClinicBot"
}

print("POST:", URL)
print("VERIFY_SSL:", VERIFY_SSL)
print("PAYLOAD:", payload)

r = requests.post(
    URL,
    headers=headers,
    json=payload,
    timeout=30,
    verify=VERIFY_SSL
)

print("HTTP:", r.status_code)
print("RESP:", r.text)