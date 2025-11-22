"""Wrapper to configure and provide a Gemini model instance.

This module configures the `google.generativeai` client with the API key
from `config.settings` and exposes a helper to obtain a model instance.
"""
import os
import streamlit as st
import google.generativeai as genai

from config import settings


# Configure the client at import time (safe: idempotent)
if not settings.GOOGLE_API_KEY:
    # We don't stop execution here; upper layers (app) will report errors.
    st.warning("GOOGLE_API_KEY no definido en el entorno. Algunas funcionalidades LLM fallarán.")
else:
    genai.configure(api_key=settings.GOOGLE_API_KEY)


def get_gemini_model():
    """Return a Gemini GenerativeModel configured with the chosen model name.

    Callers can use the returned object and invoke `.generate_content(prompt)`
    or similar methods.
    """
    return genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
