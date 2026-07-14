"""
FastAPI Entry Point
"""
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load version2/.env before any LLM clients are constructed
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv()

from src.api.routes.chat import router as chat_router

app = FastAPI(
    title="AI Co-worker Simulation Engine",
    description="Engine API for Gucci Group Case Study",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "ok", "message": "AI Co-worker Engine is running"}
