"""Google Sheets service functions (gspread wrappers).

Provides cached resource functions for Streamlit to initialize and reuse
the gspread client and to fetch spreadsheets/worksheets.
"""
from typing import List
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import settings


@st.cache_resource
def get_gspread_client() -> gspread.Client:
    """Initializes and returns an authorized gspread client using a service account."""
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        settings.CRED_FILE,
        settings.SCOPES,
    )
    client = gspread.authorize(creds)
    return client


@st.cache_resource
def get_spreadsheet() -> gspread.Spreadsheet:
    client = get_gspread_client()
    ss = client.open_by_url(settings.SHEET_URL)
    return ss


@st.cache_data
def get_available_sheets() -> List[str]:
    ss = get_spreadsheet()
    return [ws.title for ws in ss.worksheets()]


@st.cache_resource
def get_worksheet(sheet_name: str) -> gspread.Worksheet:
    ss = get_spreadsheet()
    ws = ss.worksheet(sheet_name)
    return ws
