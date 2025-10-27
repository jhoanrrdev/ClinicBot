# Backend (FastAPI)

## Requisitos
- Python 3.11+
- Virtualenv

## Pasos
```bash
cd backend
python -m venv .venv
# Activar venv:
#   Windows: .venv\Scripts\activate
#   Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
Rutas básicas:
- `GET /` -> "ClinicBot API – OK"
- `GET /health` -> `{"status": "ok"}`
