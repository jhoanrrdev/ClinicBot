import os
import requests
from dotenv import load_dotenv

load_dotenv()


class SofisisPatientClient:
    def __init__(self):
        self.token = os.getenv("SOFISIS_API_TOKEN")
        self.base = (os.getenv("SOFISIS_BASE_URL", "https://sofisis.com") or "").rstrip("/")
        self.verify_ssl = os.getenv("SOFISIS_VERIFY_SSL", "true").lower() in ("1", "true", "yes", "y", "on")

        self.headers = {
            "X-API-TOKEN": self.token or "",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def find_by_identification(self, identification: str):
        url = f"{self.base}/api/v1/history_clinic/patient/?identification={identification}"
        r = requests.get(url, headers=self.headers, timeout=30, verify=self.verify_ssl)

        try:
            data = r.json()
        except Exception:
            return {"ok": False, "status_code": r.status_code, "raw": r.text}

        return {"ok": True, "status_code": r.status_code, "data": data}

    def create_patient(
        self,
        first_name: str,
        identification: str,
        email: str,
        last_name: str = "",
        cell: str = "",
        phone: str = "",
        address: str = "",
        city: str = "",
        state: str = "",
        observation: str = "Paciente creado desde ClinicBot",
    ):
        url = f"{self.base}/api/v1/history_clinic/patient/"

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "identification": identification,
            "email": email,
            "cell": cell,
            "phone": phone,
            "address": address,
            "city": city,
            "state": state,
            "is_customer": True,
            "observation": observation,
        }

        r = requests.post(
            url,
            headers=self.headers,
            json=payload,
            timeout=30,
            verify=self.verify_ssl
        )

        try:
            data = r.json()
        except Exception:
            return {"ok": False, "status_code": r.status_code, "raw": r.text}

        return {"ok": r.status_code in (200, 201), "status_code": r.status_code, "data": data}

    def find_or_create_patient(
        self,
        first_name: str,
        identification: str,
        email: str,
        last_name: str = "",
        cell: str = "",
        phone: str = "",
        address: str = "",
        city: str = "",
        state: str = "",
    ):
        found = self.find_by_identification(identification)

        if found["ok"]:
            data = found["data"]

            # Puede venir como lista, dict paginado, o dict simple
            if isinstance(data, list) and len(data) > 0:
                return {
                    "action": "found",
                    "patient": data[0],
                    "source": "search_list"
                }

            if isinstance(data, dict):
                if "results" in data and isinstance(data["results"], list) and len(data["results"]) > 0:
                    return {
                        "action": "found",
                        "patient": data["results"][0],
                        "source": "search_results"
                    }

                # Si devuelve paciente directo
                if data.get("id"):
                    return {
                        "action": "found",
                        "patient": data,
                        "source": "search_direct"
                    }

        created = self.create_patient(
            first_name=first_name,
            last_name=last_name,
            identification=identification,
            email=email,
            cell=cell,
            phone=phone,
            address=address,
            city=city,
            state=state,
        )

        if created["ok"]:
            return {
                "action": "created",
                "patient": created["data"],
                "source": "create"
            }

        return {
            "action": "error",
            "error": created
        }