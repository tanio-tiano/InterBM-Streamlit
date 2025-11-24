import google.generativeai as genai
from config import settings
import streamlit as st

api_key = settings.GOOGLE_API_KEY

if not api_key:
    st.error("GOOGLE_API_KEY no definido (es None o vacío). Revisa tus Secrets.")
else:
    genai.configure(api_key=api_key)

def get_gemini_model():
    return genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
