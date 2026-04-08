import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SOFISIS_API_TOKEN")
BASE = os.getenv("SOFISIS_BASE_URL", "https://sofisis.com").rstrip("/")
URL = f"{BASE}/api/v1/schedule/appointment/"

headers = {
    "X-API-TOKEN": TOKEN,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

payload = {
    "patient_cell": "573111234567",
    "user_transaction_cell": "573111234567",
    "doctor_owner_calendar_cell": "573101234567",

    # ✅ OJO: Sofisis los pide con doble __
    "calendar__user__full_name": "Doctor Demo",
    "calendar__user__sex": "M",
    "calendar__branch__name": "Sede Principal",

    "text": "Cita Odontologia - Jhoan",
    "start_date": "2026-02-27T15:00:00",
    "end_date": "2026-02-27T15:30:00",
}

r = requests.post(URL, headers=headers, json=payload, timeout=30)
print("HTTP:", r.status_code)
print("RESP:", r.text)