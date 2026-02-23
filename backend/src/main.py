import os
import json
from dotenv import load_dotenv

from fastapi import FastAPI, Query, Body, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .database import SessionLocal, engine, Base
from .models import Usuario


load_dotenv()

app = FastAPI(title="ClinicBot API", version="0.1.0")

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinicbot_verify_token")


# ===============================
# ✅ DB: crear tablas al iniciar
# ===============================
@app.on_event("startup")
def startup():
    print("📦 Creando/verificando tablas...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas listas en MySQL")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===============================
# ✅ Schemas
# ===============================
class UsuarioCreate(BaseModel):
    nombre: str
    telefono: str


# ===============================
# ✅ Health / Root
# ===============================
@app.get("/")
def root():
    return {"message": "ClinicBot API running"}

@app.get("/health")
def health():
    return {"status": "ok"}


# ===============================
# ✅ Usuarios (POST + GET)
# ===============================
@app.post("/usuarios")
def crear_usuario(data: UsuarioCreate, db: Session = Depends(get_db)):
    # evita duplicados por teléfono
    existente = db.query(Usuario).filter(Usuario.telefono == data.telefono).first()
    if existente:
        return existente  # o lanza error si prefieres

    usuario = Usuario(nombre=data.nombre, telefono=data.telefono)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario

@app.get("/usuarios")
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).order_by(Usuario.id.desc()).all()


# ===============================
# ✅ Webhook verification (GET)
# ===============================
@app.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge)
    return {"error": "Invalid verification token"}


# ===============================
# ✅ Webhook receive (POST)
# Guardamos consentimiento en BD
# ===============================
@app.post("/webhook")
async def receive_webhook(payload: dict = Body(...), db: Session = Depends(get_db)):
    print("\n==============================")
    print("📩 MENSAJE RECIBIDO")
    print(json.dumps(payload, indent=2))
    print("==============================")

    try:
        entry = payload.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "received"}

        message = messages[0]
        sender = message.get("from")
        text = message.get("text", {}).get("body", "").strip().lower()

        print(f"👤 Número: {sender}")
        print(f"💬 Texto: {text}")

        # buscar/crear usuario
        usuario = db.query(Usuario).filter(Usuario.telefono == sender).first()
        if not usuario:
            usuario = Usuario(nombre="SinNombre", telefono=sender, consentimiento=None)
            db.add(usuario)
            db.commit()
            db.refresh(usuario)

        # flujo consentimiento
        if usuario.consentimiento is None:
            if text in ["hola", "buenas", "buenos días", "buenos dias", "hey"]:
                return {
                    "reply": (
                        "👋 Bienvenido a ClinicBot.\n\n"
                        "Para continuar necesitamos tu autorización de tratamiento de datos.\n"
                        "Responde:\n"
                        "1️⃣ Acepto\n"
                        "2️⃣ No acepto"
                    )
                }

            if text in ["1", "acepto", "si", "sí"]:
                usuario.consentimiento = True
                db.commit()
                return {
                    "reply": (
                        "✅ Gracias. Tu consentimiento fue registrado.\n\n"
                        "📌 Menú:\n"
                        "1️⃣ Agendar cita\n"
                        "4️⃣ Horarios\n"
                        "5️⃣ Servicios\n\n"
                        "Responde con un número."
                    )
                }

            if text in ["2", "no acepto", "no"]:
                usuario.consentimiento = False
                db.commit()
                return {
                    "reply": (
                        "❌ Entendido. Sin tu autorización no podemos continuar.\n"
                        "Si cambias de opinión, escribe 'Hola' para empezar de nuevo."
                    )
                }

            return {
                "reply": (
                    "🤖 Para continuar necesito tu autorización.\n"
                    "Responde:\n"
                    "1️⃣ Acepto\n"
                    "2️⃣ No acepto"
                )
            }

        # si ya aceptó
        if usuario.consentimiento is True:
            if text == "4":
                return {"reply": "🕒 Horarios: Lunes a Viernes 8:00am - 6:00pm, Sábados 8:00am - 12:00m."}
            if text == "5":
                return {"reply": "🩺 Servicios: Medicina general, Odontología, Psicología."}
            if text == "1":
                return {"reply": "📅 Perfecto. ¿Para qué especialidad deseas agendar? (Ej: Odontología, Medicina general)"}

            return {
                "reply": (
                    "📌 Menú:\n"
                    "1️⃣ Agendar cita\n"
                    "4️⃣ Horarios\n"
                    "5️⃣ Servicios\n\n"
                    "Responde con un número."
                )
            }

        # si no aceptó
        return {"reply": "❌ No tienes consentimiento. Escribe 'Hola' si quieres iniciar de nuevo."}

    except Exception as e:
        print("⚠️ Error procesando mensaje:", str(e))
        raise HTTPException(status_code=500, detail="Error procesando webhook")

    return {"status": "received"}