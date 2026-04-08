# test_sofisis_options_dump.py
import os, json, requests

TOKEN = os.getenv("SOFISIS_API_TOKEN")
BASE = os.getenv("SOFISIS_BASE_URL", "https://sofisis.com").rstrip("/")
URL = f"{BASE}/api/v1/schedule/appointment/"

r = requests.options(URL, headers={"X-API-TOKEN": TOKEN}, timeout=30)
print("HTTP:", r.status_code)

data = r.json()
post = (data.get("actions") or {}).get("POST") or {}
print("\n=== CAMPOS POST (resumen) ===")

def short(meta):
    if not isinstance(meta, dict):
        return {}
    return {
        "type": meta.get("type"),
        "required": meta.get("required"),
        "read_only": meta.get("read_only"),
        "label": meta.get("label"),
    }

# imprime TODO pero ordenado
for k in sorted(post.keys()):
    print(f"- {k}: {short(post[k])}")

print("\n=== CANDIDATOS (ids/relaciones) ===")
for k in sorted(post.keys()):
    meta = post[k]
    if not isinstance(meta, dict):
        continue
    t = (meta.get("type") or "").lower()
    if "integer" in t or k.endswith("_id") or "choice" in t or "field" in t:
        if any(x in k for x in ["calendar", "branch", "doctor", "patient", "owner", "user"]):
            print(f"* {k}: {short(meta)}")