import os
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from config import settings

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def _load_service_account_credentials():
    """Try to obtain a service account credentials mapping.

    Priority:
      1. `st.secrets["gcp_service_account"]` (recommended for Streamlit Cloud/local .streamlit/secrets.toml)
      2. Service account JSON file pointed by `settings.CRED_FILE` on disk

    Returns a `google.oauth2.service_account.Credentials` instance.
    """
    # 1) Try Streamlit secrets
    try:
        sa_info = st.secrets.get("gcp_service_account")
        if sa_info:
            return Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    except Exception:
        # don't fail yet; try file fallback
        pass

    # 2) Fallback to credentials file on disk
    cred_path = getattr(settings, "CRED_FILE", None) or os.getenv("CRED_FILE")
    if cred_path and os.path.exists(cred_path):
        return Credentials.from_service_account_file(cred_path, scopes=SCOPES)

    # Not found: raise informative error
    raise RuntimeError(
        "No Google service account credentials found.\n"
        "Provide a `.streamlit/secrets.toml` with `[gcp_service_account]` or set `CRED_FILE` pointing to a service-account JSON file.\n"
        "Valid secrets path examples: %s, %s"
        % (
            os.path.expanduser("~/.streamlit/secrets.toml"),
            os.path.join(os.getcwd(), ".streamlit", "secrets.toml"),
        )
    )


@st.cache_resource
def get_gspread_client():
    creds = _load_service_account_credentials()
    return gspread.authorize(creds)


def get_available_sheets():
    gc = get_gspread_client()
    sh = gc.open_by_key(settings.SHEET_URL.split('/d/')[1].split('/')[0])
    return [ws.title for ws in sh.worksheets()]


def get_worksheet(name: str):
    gc = get_gspread_client()
    sh = gc.open_by_key(settings.SHEET_URL.split('/d/')[1].split('/')[0])
    return sh.worksheet(name)
