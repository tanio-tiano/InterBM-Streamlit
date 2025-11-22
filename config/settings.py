"""Global settings for the InterBM Streamlit app.

This module centralizes constants and environment loading so other modules
can import configuration values without duplicating code.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env from project root if present
ROOT = Path(__file__).resolve().parents[1]
env_path = ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # fall back to system env
    load_dotenv()

# Google Sheet URL (project-specific)
SHEET_URL = os.getenv(
    "SHEET_URL",
    "https://docs.google.com/spreadsheets/d/1tc7me60_L-h_btVfofDnMPtVL1VVk-wSLqlFCI4SD1s/edit?usp=sharing",
)

# Scopes for Google Sheets and Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Service account credentials file (should be in project root)
CRED_FILE = os.getenv("CRED_FILE", "credenciales.json")

# Gemini model name (string used with google.generativeai)
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

# API key for Gemini (read-only here; services/gemini will configure the client)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
