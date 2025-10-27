# ClinicBot – Semana 1 (Arranque Técnico)

## 🧑‍🤝‍🧑 Roles y responsables (equipo)
- **Líder técnico:** Jhoan
- **Backend:** John
- **Frontend:** Ana Maria
- **DevOps:** (a definir)
- **QA:** (a definir)

## 🧩 Kanban (GitHub Projects)
Crea un tablero y pega aquí el enlace:
- **Enlace Kanban:** _pendiente_

### ¿Cómo crear el tablero rápido?
1. Entra al repo en GitHub → pestaña **Projects** → **New project** → **Board**.
2. Nombre: `ClinicBot – Semana 1` → Plantilla: **Team planning** (o **Kanban**).
3. Crea columnas: **Backlog**, **En progreso**, **En revisión**, **Hecho**.
4. Añade issues mínimas:
   - Estructura repo y ramas
   - Hello World Backend (staging)
   - Hello World Frontend (staging)
   - README y .env.example
   - Documento 00_Alcance_Tecnico_ClinicBot
   - Evidencias y Bitácora GFPI-F-147
5. Copia la **URL del proyecto** y pégala en este README.


> Paquete base para cumplir con los entregables de la Semana 1.
> Stack recomendado: **Backend FastAPI**, **Frontend React (Vite)**, **DB PostgreSQL (prod) / SQLite (local)**.

## 📌 Objetivo
Dejar el proyecto listo para clonar, ejecutar localmente y desplegar un **Hello World** de backend y frontend en **staging**.

## 🧱 Estructura
```
ClinicBot/
 ├── backend/
 │   ├── src/
 │   ├── tests/
 │   ├── requirements.txt
 │   ├── .env.example
 │   └── README.md
 ├── frontend/
 │   ├── src/
 │   ├── public/
 │   ├── index.html
 │   ├── package.json
 │   ├── vite.config.js
 │   └── README.md
 ├── docs/
 │   ├── 00_Alcance_Tecnico_ClinicBot.md
 │   ├── arquitectura/
 │   ├── uml/
 │   └── evidencias/
 ├── .gitignore
 ├── LICENSE
 └── README.md
```

## 🧑‍🤝‍🧑 Roles y responsables (ejemplo)
- **Líder técnico**: coordina ramas y revisiones.
- **Backend**: API FastAPI, modelos, BD.
- **Frontend**: React UI.
- **DevOps**: despliegues (Render/Railway/Vercel/Netlify).
- **QA**: pruebas y evidencias.

## 🧩 Kanban
- GitHub Projects / Trello: _(agrega el enlace aquí)_

## 🔗 URLs de staging
- Backend (Render/Railway): _(URL aquí)_
- Frontend (Vercel/Netlify): _(URL aquí)_

---

# ▶️ Ejecución local

## Backend (FastAPI)
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# variables de entorno
cp .env.example .env

# ejecutar
uvicorn src.main:app --reload
# http://localhost:8000/health
```

## Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

# 🚀 Despliegue (staging)

## Backend (Render/Railway)
- Crear servicio de **Web Service**.
- Python version: 3.11+
- Start command: `uvicorn src.main:app --host 0.0.0.0 --port 10000`
- Variables de entorno desde `.env.example`.
- PostgreSQL en prod: usa `DATABASE_URL` (driver async recomendado: `postgresql+psycopg://` o `postgresql://` según ORM).

## Frontend (Vercel/Netlify)
- Framework: Vite
- Build command: `npm run build`
- Output dir: `dist`

Agrega las **URLs de staging** en este README.

---

## ✅ Criterios de aceptación (resumen)
- Repo clonable y ejecutable.
- Ramas `main` y `develop` activas; commits claros.
- Documentación (README + 00_Alcance_Tecnico_ClinicBot.md).
- URLs públicas de backend y frontend.
- Bitácora GFPI-F-147 firmada y cargada.
```