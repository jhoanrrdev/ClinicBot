import os
import requests

token = os.getenv("SOFISIS_API_TOKEN")
url = "https://sofisis.com/api/v1/schedule/appointment/"

r = requests.options(url, headers={"X-API-TOKEN": token}, timeout=30)
print("STATUS:", r.status_code)

data = r.json()
post = data.get("actions", {}).get("POST", {})
print("\n=== CAMPOS REQUERIDOS (POST) ===")

required_fields = []
for field, meta in post.items():
    if isinstance(meta, dict) and meta.get("required") is True:
        required_fields.append((field, meta.get("type"), meta.get("label")))

for f, t, label in required_fields:
    print(f"- {f} ({t}) | {label}")

print("\n=== TOTAL REQUERIDOS ===", len(required_fields))