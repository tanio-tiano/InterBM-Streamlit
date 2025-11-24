"""
Services for reading Google Sheets.
Supports:
- Local mode: load credentials from credenciales.json
- Cloud mode: load credentials from st.secrets["gcp_service_account"]
"""

import json
import os
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from functools import lru_cache

# ID de la planilla (puedes moverlo a settings.py si quieres)
SHEET_ID = "1tc7me60_L-h_btVfofDnMPtVL1VVk-wSLqlFCI4SD1s"


# ----------------------------------------------------------
# 1. Detectar si estamos en Streamlit Cloud o en Local
# ----------------------------------------------------------
def running_in_cloud() -> bool:
    """Streamlit Cloud define este env var interno."""
    return os.environ.get("STREAMLIT_RUNTIME", "") != ""


# ----------------------------------------------------------
# 2. Obtener credenciales
# ----------------------------------------------------------
def load_credentials():
    """
    En Local: lee credenciales.json
    En Cloud: usa st.secrets["gcp_service_account"]
    """
    if running_in_cloud():
        if "gcp_service_account" not in st.secrets:
            raise ValueError("No se encontró gcp_service_account en secrets de Streamlit Cloud.")
        info = st.secrets["gcp_service_account"]
        return Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])

    # LOCAL
    cred_path = os.path.join(os.path.dirname(__file__), "..", "credenciales.json")
    cred_path = os.path.abspath(cred_path)

    if not os.path.exists(cred_path):
        raise FileNotFoundError(
            f"No se encontró el archivo local de credenciales: {cred_path}\n"
            "Crea credenciales.json en la raíz del proyecto."
        )

    with open(cred_path, "r", encoding="utf-8") as f:
        info = json.load(f)

    return Credentials.from_s_
