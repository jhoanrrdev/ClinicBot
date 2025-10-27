from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

def get_cors_origins():
    raw = os.getenv("CORS_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()] or ["*"]

app = FastAPI(title="ClinicBot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "ClinicBot API – OK"}

@app.get("/health")
def health():
    return {"status": "ok"}
