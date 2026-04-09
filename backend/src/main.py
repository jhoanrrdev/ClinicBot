import os
import json
import re
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Query, Body, Form
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .database import SessionLocal, engine, Base
from . import models
from src.integrations.sofisis_api import SofisisAPI

load_dotenv()

app = FastAPI(title="ClinicBot API", version="0.7.2")

# ======================================================
# CONFIG
# ======================================================

SESSION_TIMEOUT_SECONDS = 60
SLOT_INTERVAL_MINUTES = 30
WORK_START_HOUR = 8
WORK_END_HOUR = 18


# ======================================================
# DATABASE INIT
# ======================================================

@app.on_event("startup")
def startup():
    print("📦 Creando/verificando tablas...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas listas en MySQL")
    print("DATABASE_URL:", os.getenv("DATABASE_URL"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======================================================
# ESQUEMAS
# ======================================================

class UsuarioCreate(BaseModel):
    nombre: str
    telefono: str


# ======================================================
# HEALTH
# ======================================================

@app.get("/")
def root():
    return {"message": "ClinicBot API running"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ======================================================
# USUARIOS
# ======================================================

@app.post("/usuarios")
def crear_usuario(data: UsuarioCreate, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.telefono == data.telefono).first()
    if not usuario:
        usuario = models.Usuario(
            nombre=data.nombre,
            telefono=data.telefono,
            consentimiento=None
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)

    return usuario


@app.get("/usuarios")
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(models.Usuario).all()


# ======================================================
# META VERIFY WEBHOOK
# ======================================================

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinicbot_verify_token")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "").strip()
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "").strip()


@app.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge)
    return {"error": "Invalid verification token"}


def send_meta_text_message(to: str, text: str):
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print("META send skipped: missing META_ACCESS_TOKEN or META_PHONE_NUMBER_ID")
        return None

    url = f"https://graph.facebook.com/v22.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    try:
        data = response.json()
    except Exception:
        data = response.text

    print("META SEND STATUS:", response.status_code)
    print("META SEND DATA:", data)
    return response.status_code, data


# ======================================================
# SESIONES
# ======================================================

SESSIONS = {}


def new_session():
    now = time.time()
    return {
        "consent": None,
        "state": "START",
        "last_activity": now,
        "booking_completed_at": None,

        "available_calendars": [],
        "selected_calendar_id": None,
        "selected_calendar_label": None,
        "selected_calendar_user_id": None,
        "selected_calendar_branch_name": None,

        "identification": "",
        "first_name": "",
        "last_name": "",
        "email": "",

        "sofisis_patient_id": None,
        "sofisis_patient_label": None,

        "future_appointments": [],
        "selected_existing_appointment": None,

        "appointment_date": "",
        "appointment_time": "",
        "available_slots": [],
    }


def get_or_create_session(sender: str):
    if sender not in SESSIONS:
        SESSIONS[sender] = new_session()

    session = SESSIONS[sender]
    now = time.time()

    completed_at = session.get("booking_completed_at")
    if completed_at and (now - completed_at) >= SESSION_TIMEOUT_SECONDS:
        SESSIONS[sender] = new_session()
        session = SESSIONS[sender]

    session["last_activity"] = now
    return session


def mark_booking_completed(session: dict):
    session["booking_completed_at"] = time.time()
    session["state"] = "MENU"


# ======================================================
# HELPERS
# ======================================================

def menu_text():
    return (
        "📌 Menú:\n"
        "1️⃣ Agendar cita\n"
        "2️⃣ Consultar mis citas\n"
        "3️⃣ Servicios\n"
        "4️⃣ Horarios\n\n"
        "Responde con un número."
    )


def is_valid_email(email: str) -> bool:
    email = email.strip()
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(pattern, email) is not None


def normalize_sex_value(value):
    if isinstance(value, dict):
        return value.get("id") or ""
    if isinstance(value, str):
        return value.strip()
    return ""


def parse_datetime_safe(value):
    if not value:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            pass

    return None


def format_datetime_human(value):
    dt = parse_datetime_safe(value)
    if not dt:
        return str(value)

    return dt.strftime("%Y-%m-%d %H:%M")


def build_start_end_datetime(date_value: str, time_value: str, duration_minutes: int = 30):
    start_dt = datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return (
        start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        end_dt.strftime("%Y-%m-%d %H:%M:%S"),
    )


def extract_patient_from_result(data):
    if isinstance(data, dict):
        if "results" in data and isinstance(data["results"], list) and len(data["results"]) > 0:
            return data["results"][0]
        if data.get("id"):
            return data

    if isinstance(data, list) and len(data) > 0:
        return data[0]

    return None


# ======================================================
# HELPERS SOFISIS
# ======================================================

def ensure_patient_in_sofisis(
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
    client = SofisisAPI()
    return client.find_or_create_patient(
        first_name=first_name,
        last_name=last_name,
        identification=identification,
        email=email,
        cell=cell,
        phone=phone or cell,
        address=address,
        city=city,
        state=state,
    )


def find_patient_in_sofisis_by_identification(identification: str):
    client = SofisisAPI()
    status, data = client.find_patient_by_identification(identification)

    if status != 200:
        return None

    return extract_patient_from_result(data)


def get_available_calendars():
    client = SofisisAPI()
    status, data = client.list_calendars(page_size=20)

    if status != 200:
        return []

    if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
        return data["results"]

    if isinstance(data, list):
        return data

    return []


def get_agenda_owner_user(user_id: int):
    client = SofisisAPI()
    return client.get_user(user_id)


def create_appointment_in_sofisis(
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
    client = SofisisAPI()
    return client.create_appointment(
        calendar_id=calendar_id,
        patient_id=patient_id,
        patient_cell=patient_cell,
        user_transaction_cell=user_transaction_cell,
        doctor_owner_calendar_cell=doctor_owner_calendar_cell,
        calendar_user_full_name=calendar_user_full_name,
        calendar_user_sex=calendar_user_sex,
        calendar_branch_name=calendar_branch_name,
        text=text,
        start_date=start_date,
        end_date=end_date,
    )


def cancel_appointment_in_sofisis(appointment_id: int):
    client = SofisisAPI()
    return client.cancel_appointment(appointment_id)


def update_appointment_in_sofisis(
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
    client = SofisisAPI()
    return client.update_appointment_full(
        appointment_id=appointment_id,
        calendar_id=calendar_id,
        patient_id=patient_id,
        patient_cell=patient_cell,
        user_transaction_cell=user_transaction_cell,
        doctor_owner_calendar_cell=doctor_owner_calendar_cell,
        calendar_user_full_name=calendar_user_full_name,
        calendar_user_sex=calendar_user_sex,
        calendar_branch_name=calendar_branch_name,
        text=text,
        start_date=start_date,
        end_date=end_date,
    )


def list_future_appointments_by_patient(patient_id: int):
    client = SofisisAPI()
    status, data = client.list_appointments()

    if status != 200:
        return []

    items = []
    if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
        items = data["results"]
    elif isinstance(data, list):
        items = data

    now = datetime.now()
    future = []

    for appt in items:
        customer = appt.get("customer")
        customer_id = None

        if isinstance(customer, dict):
            customer_id = customer.get("id")
        elif isinstance(customer, int):
            customer_id = customer

        if customer_id != patient_id:
            continue

        start_dt = parse_datetime_safe(appt.get("start_date"))
        if start_dt and start_dt >= now:
            future.append(appt)

    future.sort(key=lambda x: parse_datetime_safe(x.get("start_date")) or datetime.max)
    return future


def list_appointments_by_calendar_and_date(calendar_id: int, date_str: str):
    client = SofisisAPI()
    status, data = client.list_appointments()

    if status != 200:
        return []

    items = []
    if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
        items = data["results"]
    elif isinstance(data, list):
        items = data

    result = []

    for appt in items:
        cal = appt.get("calendar")
        cal_id = None

        if isinstance(cal, dict):
            cal_id = cal.get("id")
        elif isinstance(cal, int):
            cal_id = cal

        if cal_id != calendar_id:
            continue

        start_dt = parse_datetime_safe(appt.get("start_date"))
        if start_dt and start_dt.strftime("%Y-%m-%d") == date_str:
            result.append(appt)

    return result


def build_available_slots(calendar_id: int, date_str: str, interval_minutes: int = 30):
    occupied = list_appointments_by_calendar_and_date(calendar_id, date_str)

    occupied_times = set()
    for appt in occupied:
        start_dt = parse_datetime_safe(appt.get("start_date"))
        if start_dt:
            occupied_times.add(start_dt.strftime("%H:%M"))

    slots = []
    current = datetime.strptime(f"{date_str} {WORK_START_HOUR:02d}:00", "%Y-%m-%d %H:%M")
    end_limit = datetime.strptime(f"{date_str} {WORK_END_HOUR:02d}:00", "%Y-%m-%d %H:%M")

    while current < end_limit:
        slot = current.strftime("%H:%M")
        if slot not in occupied_times:
            slots.append(slot)
        current += timedelta(minutes=interval_minutes)

    return slots


def format_appointments_list(appointments):
    if not appointments:
        return "No encontré citas futuras."

    msg = "📅 Estas son tus citas futuras:\n\n"
    for i, appt in enumerate(appointments, start=1):
        calendar = appt.get("calendar")
        calendar_label = calendar.get("label") if isinstance(calendar, dict) else "Agenda"
        msg += f"{i}️⃣ {format_datetime_human(appt.get('start_date'))} - {calendar_label}\n"
    return msg.strip()


# ======================================================
# FLUJO
# ======================================================

def process_message(sender: str, text: str, db: Session):
    text_original = text.strip()
    text_lower = text_original.lower()

    session = get_or_create_session(sender)

    usuario = db.query(models.Usuario).filter(models.Usuario.telefono == sender).first()
    if not usuario:
        usuario = models.Usuario(
            nombre="SinNombre",
            telefono=sender,
            consentimiento=None
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)

    # --------------------------------------------------
    # CONSENTIMIENTO
    # --------------------------------------------------
    if session["consent"] is None:
        if "hola" in text_lower or session["state"] == "START":
            session["state"] = "CONSENT"
            return (
                "👋 Bienvenido a ClinicBot.\n\n"
                "Para continuar necesitamos tu autorización de tratamiento de datos.\n"
                "Responde:\n"
                "1️⃣ Acepto\n"
                "2️⃣ No acepto"
            )

        elif text_lower in ["1", "acepto", "si", "sí"]:
            session["consent"] = True
            session["state"] = "MENU"
            usuario.consentimiento = True
            db.commit()
            return "✅ Gracias. Tu consentimiento fue registrado.\n\n" + menu_text()

        elif text_lower in ["2", "no acepto", "no"]:
            session["consent"] = False
            session["state"] = "END"
            usuario.consentimiento = False
            db.commit()
            return "❌ Sin tu autorización no podemos continuar.\nSi cambias de opinión escribe 'Hola'."

        else:
            return (
                "🤖 Necesito tu autorización.\n"
                "Responde:\n"
                "1️⃣ Acepto\n"
                "2️⃣ No acepto"
            )

    # --------------------------------------------------
    # MENÚ
    # --------------------------------------------------
    if session["state"] == "MENU":
        if text_lower == "1":
            calendars = get_available_calendars()
            if not calendars:
                return "⚠️ No encontré agendas disponibles en Sofisis en este momento.\n\n" + menu_text()

            session["available_calendars"] = calendars
            session["state"] = "BOOKING_CALENDAR_SELECT"

            msg = "📅 Estas son las agendas disponibles:\n\n"
            for i, cal in enumerate(calendars[:10], start=1):
                label = cal.get("label") or cal.get("name") or f"Agenda {i}"
                msg += f"{i}️⃣ {label}\n"
            msg += "\nResponde con el número de la agenda que deseas."
            return msg

        if text_lower == "2":
            session["state"] = "CONSULT_APPOINTMENTS_IDENTIFICATION"
            return "🔎 Para consultar tus citas, envíame tu *número de identificación*."

        if text_lower == "3":
            return "🩺 Servicios: Medicina general, Odontología, Psicología."

        if text_lower == "4":
            return "🕒 Horarios: Lunes a Viernes 8:00am - 6:00pm."

        return menu_text()

    # --------------------------------------------------
    # CONSULTAR CITAS
    # --------------------------------------------------
    if session["state"] == "CONSULT_APPOINTMENTS_IDENTIFICATION":
        identification = text_original.strip()

        patient = find_patient_in_sofisis_by_identification(identification)
        if not patient:
            session["state"] = "MENU"
            return "⚠️ No encontré un paciente con esa identificación en Sofisis.\n\n" + menu_text()

        session["identification"] = identification
        session["sofisis_patient_id"] = patient.get("id")
        session["sofisis_patient_label"] = patient.get("label")

        future_appts = list_future_appointments_by_patient(patient.get("id"))
        session["future_appointments"] = future_appts

        if not future_appts:
            session["state"] = "MENU"
            return "ℹ️ No encontré citas futuras registradas.\n\n" + menu_text()

        session["state"] = "CONSULT_APPOINTMENTS_ACTION"

        return (
            f"✅ Ya encontré tu paciente en Sofisis.\n"
            f"👤 {patient.get('full_name', patient.get('label', 'Paciente'))}\n"
            f"🆔 ID Sofisis: {patient.get('id')}\n\n"
            f"{format_appointments_list(future_appts)}\n\n"
            "¿Qué deseas hacer?\n"
            "1️⃣ Reprogramar una cita\n"
            "2️⃣ Cancelar una cita\n"
            "3️⃣ Volver al menú"
        )

    if session["state"] == "CONSULT_APPOINTMENTS_ACTION":
        if text_lower == "1":
            appts = session.get("future_appointments", [])
            if not appts:
                session["state"] = "MENU"
                return "ℹ️ No encontré citas para reprogramar.\n\n" + menu_text()

            session["state"] = "SELECT_APPOINTMENT_TO_RESCHEDULE"
            msg = "Selecciona la cita que deseas reprogramar:\n\n"
            for i, appt in enumerate(appts, start=1):
                calendar = appt.get("calendar")
                calendar_label = calendar.get("label") if isinstance(calendar, dict) else "Agenda"
                msg += f"{i}️⃣ {format_datetime_human(appt.get('start_date'))} - {calendar_label}\n"
            return msg

        if text_lower == "2":
            appts = session.get("future_appointments", [])
            if not appts:
                session["state"] = "MENU"
                return "ℹ️ No encontré citas para cancelar.\n\n" + menu_text()

            session["state"] = "SELECT_APPOINTMENT_TO_CANCEL"
            msg = "Selecciona la cita que deseas cancelar:\n\n"
            for i, appt in enumerate(appts, start=1):
                calendar = appt.get("calendar")
                calendar_label = calendar.get("label") if isinstance(calendar, dict) else "Agenda"
                msg += f"{i}️⃣ {format_datetime_human(appt.get('start_date'))} - {calendar_label}\n"
            return msg

        if text_lower == "3":
            session["state"] = "MENU"
            return menu_text()

        return (
            "¿Qué deseas hacer?\n"
            "1️⃣ Reprogramar una cita\n"
            "2️⃣ Cancelar una cita\n"
            "3️⃣ Volver al menú"
        )

    if session["state"] == "SELECT_APPOINTMENT_TO_CANCEL":
        if not text_lower.isdigit():
            return "Por favor responde con el número de la cita que deseas cancelar."

        index = int(text_lower) - 1
        appts = session.get("future_appointments", [])

        if index < 0 or index >= len(appts):
            return "Ese número no corresponde a una cita válida."

        appt = appts[index]
        appointment_id = appt.get("id")

        status_cancel, data_cancel = cancel_appointment_in_sofisis(appointment_id)

        session["state"] = "MENU"

        if status_cancel in [200, 202]:
            mark_booking_completed(session)
            return "✅ Tu cita fue cancelada.\n\n" + menu_text()

        return f"⚠️ No pude cancelar la cita.\nDetalle: {data_cancel}\n\n{menu_text()}"

    if session["state"] == "SELECT_APPOINTMENT_TO_RESCHEDULE":
        if not text_lower.isdigit():
            return "Por favor responde con el número de la cita que deseas reprogramar."

        index = int(text_lower) - 1
        appts = session.get("future_appointments", [])

        if index < 0 or index >= len(appts):
            return "Ese número no corresponde a una cita válida."

        selected = appts[index]
        session["selected_existing_appointment"] = selected
        session["state"] = "BOOKING_CALENDAR_SELECT"

        calendars = get_available_calendars()
        if not calendars:
            session["state"] = "MENU"
            return "⚠️ No encontré agendas disponibles en Sofisis.\n\n" + menu_text()

        session["available_calendars"] = calendars

        msg = "📅 Selecciona la agenda para reprogramar:\n\n"
        for i, cal in enumerate(calendars[:10], start=1):
            label = cal.get("label") or cal.get("name") or f"Agenda {i}"
            msg += f"{i}️⃣ {label}\n"

        return msg

    # --------------------------------------------------
    # AGENDAR / REPROGRAMAR: SELECCIONAR AGENDA
    # --------------------------------------------------
    if session["state"] == "BOOKING_CALENDAR_SELECT":
        if not text_lower.isdigit():
            return "Por favor responde con el número de la agenda que deseas elegir."

        index = int(text_lower) - 1
        calendars = session.get("available_calendars", [])

        if index < 0 or index >= len(calendars):
            return "Ese número no corresponde a una agenda válida."

        selected = calendars[index]

        session["selected_calendar_id"] = selected.get("id")
        session["selected_calendar_label"] = selected.get("label") or selected.get("name") or "Agenda"
        session["selected_calendar_user_id"] = (selected.get("user") or {}).get("id")
        session["selected_calendar_branch_name"] = (selected.get("branch") or {}).get("label", "")

        if session.get("selected_existing_appointment"):
            session["state"] = "BOOKING_DATE"
            return (
                f"✅ Agenda seleccionada: {session['selected_calendar_label']}\n\n"
                "Ahora envíame la nueva *fecha de la cita* en formato:\n"
                "YYYY-MM-DD"
            )

        session["state"] = "BOOKING_IDENTIFICATION"
        return (
            f"✅ Agenda seleccionada: {session['selected_calendar_label']}\n\n"
            "Ahora envíame tu *número de identificación*."
        )

    # --------------------------------------------------
    # AGENDAR: IDENTIFICACIÓN
    # --------------------------------------------------
    if session["state"] == "BOOKING_IDENTIFICATION":
        identification = text_original.strip()
        session["identification"] = identification

        try:
            patient = find_patient_in_sofisis_by_identification(identification)

            if patient:
                session["sofisis_patient_id"] = patient.get("id")
                session["sofisis_patient_label"] = patient.get("label")
                session["first_name"] = patient.get("first_name", "")
                session["last_name"] = patient.get("last_name", "")
                session["email"] = patient.get("email", "")

                future_appts = list_future_appointments_by_patient(patient.get("id"))
                session["future_appointments"] = future_appts

                if future_appts:
                    session["state"] = "BOOKING_EXISTING_APPOINTMENT_DECISION"
                    return (
                        f"✅ Ya encontré tu paciente en Sofisis.\n"
                        f"👤 {patient.get('full_name', patient.get('label', 'Paciente'))}\n"
                        f"🆔 ID Sofisis: {patient.get('id')}\n\n"
                        f"{format_appointments_list(future_appts)}\n\n"
                        "Ya tienes una cita futura.\n"
                        "¿Qué deseas hacer?\n"
                        "1️⃣ Reprogramar mi cita actual\n"
                        "2️⃣ Cancelar mi cita actual\n"
                        "3️⃣ Volver al menú"
                    )

                session["state"] = "BOOKING_DATE"
                return (
                    f"✅ Ya encontré tu paciente en Sofisis.\n"
                    f"👤 {patient.get('full_name', patient.get('label', 'Paciente'))}\n"
                    f"🆔 ID Sofisis: {patient.get('id')}\n\n"
                    "Ahora envíame la *fecha de la cita* en formato:\n"
                    "YYYY-MM-DD"
                )

            session["state"] = "BOOKING_FIRST_NAME"
            return (
                "ℹ️ No encontré un paciente con esa identificación en Sofisis.\n\n"
                "Vamos a registrarte.\n"
                "Ahora dime tu *nombre*."
            )

        except Exception as e:
            session["state"] = "MENU"
            return f"⚠️ Ocurrió un error al consultar el paciente en Sofisis.\nDetalle: {str(e)}\n\n{menu_text()}"

    if session["state"] == "BOOKING_EXISTING_APPOINTMENT_DECISION":
        appts = session.get("future_appointments", [])

        if text_lower == "1":
            if not appts:
                session["state"] = "MENU"
                return "ℹ️ No encontré citas para reprogramar.\n\n" + menu_text()

            session["selected_existing_appointment"] = appts[0]
            session["state"] = "BOOKING_DATE"
            return "Perfecto 👍 Vamos a reprogramar tu cita.\n\nAhora envíame la nueva *fecha* en formato YYYY-MM-DD."

        if text_lower == "2":
            if not appts:
                session["state"] = "MENU"
                return "ℹ️ No encontré citas para cancelar.\n\n" + menu_text()

            appointment_id = appts[0].get("id")
            status_cancel, data_cancel = cancel_appointment_in_sofisis(appointment_id)

            session["state"] = "MENU"
            if status_cancel in [200, 202]:
                mark_booking_completed(session)
                return "✅ Tu cita fue cancelada.\n\n" + menu_text()

            return f"⚠️ No pude cancelar la cita.\nDetalle: {data_cancel}\n\n{menu_text()}"

        if text_lower == "3":
            session["state"] = "MENU"
            return menu_text()

        return (
            "Ya tienes una cita futura.\n"
            "¿Qué deseas hacer?\n"
            "1️⃣ Reprogramar mi cita actual\n"
            "2️⃣ Cancelar mi cita actual\n"
            "3️⃣ Volver al menú"
        )

    # --------------------------------------------------
    # REGISTRO PACIENTE NUEVO
    # --------------------------------------------------
    if session["state"] == "BOOKING_FIRST_NAME":
        session["first_name"] = text_original
        session["state"] = "BOOKING_LAST_NAME"
        return "Perfecto 👍 Ahora dime tu *apellido*."

    if session["state"] == "BOOKING_LAST_NAME":
        session["last_name"] = text_original
        session["state"] = "BOOKING_EMAIL"
        return "Ahora envíame tu *correo electrónico*."

    if session["state"] == "BOOKING_EMAIL":
        if not is_valid_email(text_original):
            return "⚠️ El correo no parece válido.\nEnvíalo así, por ejemplo:\nnombre@gmail.com"

        session["email"] = text_original

        try:
            patient_result = ensure_patient_in_sofisis(
                first_name=session.get("first_name", ""),
                last_name=session.get("last_name", ""),
                identification=session.get("identification", ""),
                email=session.get("email", ""),
                cell=sender,
                phone=sender,
                address="",
                city="",
                state="",
            )

            if patient_result.get("action") in ["found", "created"]:
                patient = patient_result.get("patient", {})
                session["sofisis_patient_id"] = patient.get("id")
                session["sofisis_patient_label"] = patient.get("label")
                session["state"] = "BOOKING_DATE"

                return (
                    f"✅ Paciente listo en Sofisis.\n"
                    f"👤 {patient.get('full_name', patient.get('label', 'Paciente'))}\n"
                    f"🆔 ID Sofisis: {patient.get('id')}\n\n"
                    "Ahora envíame la *fecha de la cita* en formato:\n"
                    "YYYY-MM-DD"
                )

            session["state"] = "MENU"
            return f"⚠️ No pude crear o encontrar el paciente en Sofisis.\nDetalle: {patient_result}\n\n{menu_text()}"

        except Exception as e:
            session["state"] = "MENU"
            return f"⚠️ Ocurrió un error al conectarme con Sofisis.\nDetalle: {str(e)}\n\n{menu_text()}"

    # --------------------------------------------------
    # FECHA -> HORARIOS
    # --------------------------------------------------
    if session["state"] == "BOOKING_DATE":
        try:
            datetime.strptime(text_original, "%Y-%m-%d")
            session["appointment_date"] = text_original

            calendar_id = session.get("selected_calendar_id")
            if not calendar_id:
                session["state"] = "MENU"
                return "⚠️ No encontré la agenda seleccionada.\n\n" + menu_text()

            slots = build_available_slots(calendar_id, text_original, SLOT_INTERVAL_MINUTES)

            if not slots:
                return "⚠️ No encontré horarios disponibles para esa fecha.\nPor favor envíame otra fecha en formato YYYY-MM-DD."

            session["available_slots"] = slots
            session["state"] = "BOOKING_TIME_SELECT"

            msg = f"🕒 Horarios disponibles para {text_original}:\n\n"
            for i, slot in enumerate(slots[:12], start=1):
                msg += f"{i}️⃣ {slot}\n"
            msg += "\nResponde con el número del horario que deseas."
            return msg

        except ValueError:
            return "⚠️ La fecha no tiene formato válido. Usa YYYY-MM-DD, por ejemplo 2026-03-10."

    # --------------------------------------------------
    # SELECCIONAR HORARIO
    # --------------------------------------------------
    if session["state"] == "BOOKING_TIME_SELECT":
        if not text_lower.isdigit():
            return "Por favor responde con el número del horario que deseas."

        index = int(text_lower) - 1
        slots = session.get("available_slots", [])

        if index < 0 or index >= len(slots):
            return "Ese número no corresponde a un horario válido."

        selected_time = slots[index]
        session["appointment_time"] = selected_time

        try:
            date_value = session.get("appointment_date")
            time_value = session.get("appointment_time")
            patient_id = session.get("sofisis_patient_id")
            patient_cell = sender
            calendar_id = session.get("selected_calendar_id")
            calendar_user_id = session.get("selected_calendar_user_id")
            calendar_branch_name = session.get("selected_calendar_branch_name", "")
            calendar_label = session.get("selected_calendar_label", "Agenda")

            if not patient_id:
                session["state"] = "MENU"
                return "⚠️ No encontré el paciente en Sofisis.\n\n" + menu_text()

            if not calendar_id:
                session["state"] = "MENU"
                return "⚠️ No encontré la agenda seleccionada.\n\n" + menu_text()

            if not calendar_user_id:
                session["state"] = "MENU"
                return "⚠️ No encontré el profesional de la agenda.\n\n" + menu_text()

            fresh_slots = build_available_slots(calendar_id, date_value, SLOT_INTERVAL_MINUTES)
            if time_value not in fresh_slots:
                session["state"] = "BOOKING_DATE"
                return (
                    "⚠️ Ese horario acaba de ocuparse.\n"
                    "Por favor envíame nuevamente la fecha para cargar horarios actualizados."
                )

            status_user, user_data = get_agenda_owner_user(calendar_user_id)
            if status_user != 200:
                session["state"] = "MENU"
                return f"⚠️ No pude obtener los datos del profesional.\nDetalle: {user_data}\n\n{menu_text()}"

            doctor_cell = user_data.get("cell") or user_data.get("phone") or ""
            doctor_name = user_data.get("full_name") or user_data.get("label") or ""
            doctor_sex = normalize_sex_value(user_data.get("sex"))

            if not doctor_cell:
                session["state"] = "MENU"
                return "⚠️ El profesional no tiene celular configurado en Sofisis.\n\n" + menu_text()

            start_date, end_date = build_start_end_datetime(date_value, time_value, duration_minutes=30)

            # REPROGRAMAR
            existing_appt = session.get("selected_existing_appointment")
            if existing_appt:
                appointment_id = existing_appt.get("id")

                print("DEBUG REPROGRAMAR")
                print("appointment_id:", appointment_id)
                print("calendar_id:", calendar_id)
                print("patient_id:", patient_id)
                print("start_date:", start_date)
                print("end_date:", end_date)

                status_upd, upd_data = update_appointment_in_sofisis(
                    appointment_id=appointment_id,
                    calendar_id=calendar_id,
                    patient_id=patient_id,
                    patient_cell=patient_cell,
                    user_transaction_cell=patient_cell,
                    doctor_owner_calendar_cell=doctor_cell,
                    calendar_user_full_name=doctor_name,
                    calendar_user_sex=doctor_sex,
                    calendar_branch_name=calendar_branch_name,
                    text=f"Reprogramada desde ClinicBot - {session.get('identification', '').strip()}",
                    start_date=start_date,
                    end_date=end_date,
                )

                session["state"] = "MENU"

                if status_upd in [200, 202]:
                    mark_booking_completed(session)
                    return (
                        "✅ ¡Tu cita fue reprogramada en Sofisis!\n\n"
                        f"👤 Paciente: {session.get('sofisis_patient_label')}\n"
                        f"📅 Fecha: {date_value}\n"
                        f"⏰ Hora: {time_value}\n"
                        f"👨‍⚕️ Profesional: {doctor_name}\n"
                        f"🏥 Agenda: {calendar_label}\n"
                        f"🏢 Sucursal: {calendar_branch_name}\n\n"
                        f"{menu_text()}"
                    )

                return f"⚠️ No se pudo reprogramar la cita.\nDetalle: {upd_data}\n\n{menu_text()}"

            # CREAR NUEVA
            status_appt, appointment_data = create_appointment_in_sofisis(
                calendar_id=calendar_id,
                patient_id=patient_id,
                patient_cell=patient_cell,
                user_transaction_cell=patient_cell,
                doctor_owner_calendar_cell=doctor_cell,
                calendar_user_full_name=doctor_name,
                calendar_user_sex=doctor_sex,
                calendar_branch_name=calendar_branch_name,
                text=f"ClinicBot - {session.get('identification', '').strip()}",
                start_date=start_date,
                end_date=end_date,
            )

            print("📌 RESPUESTA CITA SOFISIS")
            print("STATUS:", status_appt)
            print("DATA:", appointment_data)

            session["state"] = "MENU"

            if status_appt in (200, 201) and isinstance(appointment_data, dict) and appointment_data.get("id"):
                mark_booking_completed(session)
                return (
                    "✅ ¡Cita creada en Sofisis!\n\n"
                    f"👤 Paciente: {session.get('sofisis_patient_label')}\n"
                    f"📅 Fecha: {date_value}\n"
                    f"⏰ Hora: {time_value}\n"
                    f"👨‍⚕️ Profesional: {doctor_name}\n"
                    f"🏥 Agenda: {calendar_label}\n"
                    f"🏢 Sucursal: {calendar_branch_name}\n"
                    f"🆔 Cita ID: {appointment_data.get('id')}\n\n"
                    "ℹ️ Esta sesión se reiniciará automáticamente después de 1 minuto de inactividad.\n\n"
                    f"{menu_text()}"
                )

            return f"⚠️ No se pudo crear la cita.\nHTTP: {status_appt}\nDetalle: {appointment_data}\n\n{menu_text()}"

        except Exception as e:
            session["state"] = "MENU"
            return f"⚠️ Ocurrió un error al intentar agendar en Sofisis.\nDetalle: {str(e)}\n\n{menu_text()}"

    return "🤖 Escribe 'Hola' para iniciar."


# ======================================================
# WEBHOOK META
# ======================================================

@app.post("/webhook")
async def receive_webhook(payload: dict = Body(...), db: Session = Depends(get_db)):
    print("📩 MENSAJE RECIBIDO (Meta/Swagger)")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        entry = payload.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "no messages"}

        message = messages[0]
        sender = message.get("from")
        text = message.get("text", {}).get("body", "")

        if not sender or not text:
            return {"status": "ignored", "reason": "unsupported message payload"}

        reply = process_message(sender, text, db)
        send_result = send_meta_text_message(sender, reply)

        return {
            "status": "received",
            "reply": reply,
            "session": SESSIONS.get(sender),
            "meta_send": send_result
        }

    except Exception as e:
        print("⚠️ Error:", str(e))
        return {"error": str(e)}


# ======================================================
# WEBHOOK TWILIO
# ======================================================

@app.post("/twilio/webhook")
async def twilio_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: Session = Depends(get_db)
):
    print("📲 MENSAJE RECIBIDO (Twilio)")
    print("From:", From)
    print("Body:", Body)

    sender = From.replace("whatsapp:", "").replace("+", "").strip()
    text = Body.strip()
    print("Normalized sender:", sender)
    print("Normalized text:", text)

    reply = process_message(sender, text, db)
    print("Bot reply:", reply)

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>{reply}</Message>
</Response>"""
    print("TwiML response:", twiml)

    return Response(content=twiml, media_type="application/xml")
