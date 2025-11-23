import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(creds)


def get_available_sheets():
    gc = get_gspread_client()
    sh = gc.open_by_key("1tc7me60_L-h_btVfofDnMPtVL1VVk-wSLqlFCI4SD1s")  # tu ID
    return [ws.title for ws in sh.worksheets()]


def get_worksheet(name: str):
    gc = get_gspread_client()
    sh = gc.open_by_key("1tc7me60_L-h_btVfofDnMPtVL1VVk-wSLqlFCI4SD1s")
    return sh.worksheet(name)
