import os
import requests
from dotenv import load_dotenv

load_dotenv()


class SofisisAPI:
    def __init__(self):
        self.base_url = os.getenv("SOFISIS_BASE_URL", "https://sofisis.com").rstrip("/")
        self.token = os.getenv("SOFISIS_API_TOKEN", "").strip()
        self.verify_ssl = os.getenv("SOFISIS_VERIFY_SSL", "true").lower() == "true"

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-TOKEN": self.token,
        }

    # ======================================================
    # REQUEST BASE
    # ======================================================

    def _get(self, endpoint, params=None):
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        print("🌐 GET:", url, "PARAMS:", params)

        r = requests.get(
            url,
            headers=self.headers,
            params=params,
            verify=self.verify_ssl,
            timeout=30
        )

        try:
            data = r.json()
        except Exception:
            data = r.text

        print("✅ GET STATUS:", r.status_code)
        print("✅ GET DATA:", data)
        return r.status_code, data

    def _post(self, endpoint, payload=None):
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        print("🌐 POST:", url)
        print("📦 PAYLOAD:", payload)

        r = requests.post(
            url,
            headers=self.headers,
            json=payload or {},
            verify=self.verify_ssl,
            timeout=30
        )

        try:
            data = r.json()
        except Exception:
            data = r.text

        print("✅ POST STATUS:", r.status_code)
        print("✅ POST DATA:", data)
        return r.status_code, data

    def _patch(self, endpoint, payload=None):
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        print("🌐 PATCH:", url)
        print("📦 PAYLOAD:", payload)

        r = requests.patch(
            url,
            headers=self.headers,
            json=payload or {},
            verify=self.verify_ssl,
            timeout=30
        )

        try:
            data = r.json()
        except Exception:
            data = r.text

        print("✅ PATCH STATUS:", r.status_code)
        print("✅ PATCH DATA:", data)
        return r.status_code, data

    def _put(self, endpoint, payload=None):
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        print("🌐 PUT:", url)
        print("📦 PAYLOAD:", payload)

        r = requests.put(
            url,
            headers=self.headers,
            json=payload or {},
            verify=self.verify_ssl,
            timeout=30
        )

        try:
            data = r.json()
        except Exception:
            data = r.text

        print("✅ PUT STATUS:", r.status_code)
        print("✅ PUT DATA:", data)
        return r.status_code, data

    def _delete(self, endpoint):
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        print("🌐 DELETE:", url)

        r = requests.delete(
            url,
            headers=self.headers,
            verify=self.verify_ssl,
            timeout=30
        )

        try:
            data = r.json()
        except Exception:
            data = r.text

        print("✅ DELETE STATUS:", r.status_code)
        print("✅ DELETE DATA:", data)
        return r.status_code, data

    # ======================================================
    # PACIENTES
    # ======================================================

    def find_patient_by_identification(self, identification: str):
        identification = str(identification).strip()

        status, data = self._get(
            "history_clinic/patient/",
            params={
                "identification": identification,
                "_page_size": 10,
            }
        )
        if status == 200:
            if isinstance(data, dict) and data.get("results"):
                return status, data
            if isinstance(data, list) and len(data) > 0:
                return status, data

        return self._get(
            "history_clinic/patient/",
            params={
                "identification__icontains": identification,
                "_page_size": 10,
            }
        )

    def create_patient(
        self,
        first_name: str,
        last_name: str,
        identification: str,
        email: str,
        cell: str,
        phone: str = "",
        address: str = "",
        city: str = "",
        state: str = "",
    ):
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "identification": str(identification).strip(),
            "email": email,
            "cell": cell,
            "phone": phone or cell,
            "address": address,
            "city": city,
            "state": state,
            "is_customer": True,
            "observation": "Paciente creado desde ClinicBot",
        }
        return self._post("history_clinic/patient/", payload)

    def find_or_create_patient(
        self,
        first_name: str,
        last_name: str,
        identification: str,
        email: str,
        cell: str,
        phone: str = "",
        address: str = "",
        city: str = "",
        state: str = "",
    ):
        identification = str(identification).strip()

        status, data = self.find_patient_by_identification(identification)

        if status == 200:
            if isinstance(data, dict) and "results" in data and len(data["results"]) > 0:
                return {"action": "found", "patient": data["results"][0], "source": "search_results"}
            if isinstance(data, list) and len(data) > 0:
                return {"action": "found", "patient": data[0], "source": "search_list"}

        status_create, created = self.create_patient(
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

        if status_create in [200, 201]:
            return {"action": "created", "patient": created, "source": "created"}

        status_retry, retry_data = self.find_patient_by_identification(identification)
        if status_retry == 200:
            if isinstance(retry_data, dict) and "results" in retry_data and len(retry_data["results"]) > 0:
                return {"action": "found", "patient": retry_data["results"][0], "source": "retry_search"}
            if isinstance(retry_data, list) and len(retry_data) > 0:
                return {"action": "found", "patient": retry_data[0], "source": "retry_search"}

        return {
            "action": "error",
            "status": status_create,
            "response": created
        }

    # ======================================================
    # AGENDAS
    # ======================================================

    def list_calendars(self, page_size=20):
        params = {"_page_size": page_size}
        return self._get("schedule/calendar/", params=params)

    # ======================================================
    # USUARIOS / PROFESIONALES
    # ======================================================

    def get_user(self, user_id: int):
        return self._get(f"base_model_s/user/{user_id}/")

    # ======================================================
    # CITAS
    # ======================================================

    def list_appointments(self, params=None):
        final_params = {"_page_size": 200}
        if params:
            final_params.update(params)
        return self._get("schedule/appointment/", params=final_params)

    def get_appointment(self, appointment_id: int):
        return self._get(f"schedule/appointment/{appointment_id}/")

    def create_appointment(
        self,
        calendar_id: int,
        patient_id: int,
        patient_cell: str,
        user_transaction_cell: str,
        doctor_owner_calendar_cell: str,
        calendar_user_full_name: str,
        calendar_user_sex: str,
        calendar_branch_name: str,
        text: str,
        start_date: str,
        end_date: str,
    ):
        payload = {
            "calendar": calendar_id,
            "customer": patient_id,
            "patient_cell": patient_cell,
            "user_transaction_cell": user_transaction_cell,
            "doctor_owner_calendar_cell": doctor_owner_calendar_cell,
            "calendar__user__full_name": calendar_user_full_name,
            "calendar__user__sex": calendar_user_sex,
            "calendar__branch__name": calendar_branch_name,
            "text": text,
            "start_date": start_date,
            "end_date": end_date,
        }
        return self._post("schedule/appointment/", payload)

    def update_appointment_full(
        self,
        appointment_id: int,
        calendar_id: int,
        patient_id: int,
        patient_cell: str,
        user_transaction_cell: str,
        doctor_owner_calendar_cell: str,
        calendar_user_full_name: str,
        calendar_user_sex: str,
        calendar_branch_name: str,
        text: str,
        start_date: str,
        end_date: str,
    ):
        payload = {
            "calendar": calendar_id,
            "customer": patient_id,
            "patient_cell": patient_cell,
            "user_transaction_cell": user_transaction_cell,
            "doctor_owner_calendar_cell": doctor_owner_calendar_cell,
            "calendar__user__full_name": calendar_user_full_name,
            "calendar__user__sex": calendar_user_sex,
            "calendar__branch__name": calendar_branch_name,
            "text": text,
            "start_date": start_date,
            "end_date": end_date,
        }
        status, data = self._put(f"schedule/appointment/{appointment_id}/", payload)

        # Some Sofisis deployments reject PUT updates for appointment reschedules
        # even when the same payload succeeds on create. Retry with PATCH so the
        # bot can keep working without user intervention.
        if status >= 400 and isinstance(data, dict):
            start_errors = data.get("start_date")
            end_errors = data.get("end_date")
            if start_errors or end_errors:
                print("Retrying appointment update with PATCH due to date field validation on PUT")
                return self._patch(f"schedule/appointment/{appointment_id}/", payload)

        return status, data

    def cancel_appointment(self, appointment_id: int):
        return self._delete(f"schedule/appointment/{appointment_id}/")
