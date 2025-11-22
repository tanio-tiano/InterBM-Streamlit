"""Chart helpers and safe wrappers around Streamlit plotting functions."""
from typing import Optional
import streamlit as st
import pandas as pd


def safe_bar_chart(df: Optional[pd.DataFrame], x_col: str, y_col: str, titulo: Optional[str] = None):
    """Safely render a bar chart if data is valid.

    - No-op with a friendly message when df is None or empty.
    - Removes rows with empty x_col.
    - Ensures y_col is numeric and has non-zero values.
    """
    if df is None or df.empty:
        st.info("No hay datos para este gráfico.")
        return

    df = df.copy()
    if x_col not in df.columns or y_col not in df.columns:
        st.info("Columnas requeridas no presentes en los datos.")
        return

    df[x_col] = df[x_col].astype(str).str.strip()
    df = df[df[x_col] != ""]
    if df.empty:
        st.info("No hay datos válidos para este gráfico.")
        return

    if not pd.api.types.is_numeric_dtype(df[y_col]):
        st.info("No hay datos numéricos para graficar en esta métrica.")
        return

    if df[y_col].fillna(0).sum() == 0:
        st.info("Todos los valores son 0 o NaN. No se grafica nada.")
        return

    if titulo:
        st.markdown(f"#### {titulo}")

    try:
        st.bar_chart(df.set_index(x_col)[y_col], width="stretch")
    except Exception:
        # Fallback: Streamlit bar_chart might expect ints for width — ignore width if it errors
        st.bar_chart(df.set_index(x_col)[y_col])
