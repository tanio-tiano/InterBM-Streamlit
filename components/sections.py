"""UI section components for the InterBM dashboard.

Each function receives `df` and `kpis` and is responsible for rendering
its section of the dashboard using Streamlit components and helpers.
"""
from typing import Any
import streamlit as st
import pandas as pd

from components.charts import safe_bar_chart


def render_estado_financiero(df: pd.DataFrame, kpis: dict) -> None:
    st.markdown("## 🧾 Estado financiero del mes")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total ingresos", f"${kpis['total_ingresos']:,.0f}")
    col2.metric("Total gastos", f"${kpis['total_gastos']:,.0f}")
    col3.metric("Balance neto", f"${kpis['balance_neto']:,.0f}")


def render_estructura_gasto(df: pd.DataFrame, kpis: dict) -> None:
    st.markdown("## 🧩 Estructura del gasto por tipo de gasto")
    gasto_tipo = kpis.get("gasto_por_tipo")
    if gasto_tipo is not None:
        gasto_tipo_df = gasto_tipo.reset_index()
        gasto_tipo_df.columns = ["tipo_gasto", "monto_gasto"]
        col_a, col_b = st.columns(2)
        with col_a:
            st.dataframe(gasto_tipo_df, width="stretch")
        with col_b:
            safe_bar_chart(gasto_tipo_df, "tipo_gasto", "monto_gasto", "Gasto por tipo de gasto")
    else:
        st.info("No hay información suficiente para calcular la estructura del gasto.")


def render_rrhh(df: pd.DataFrame, kpis: dict) -> None:
    st.markdown("## 👤 RR.HH.")
    st.metric("Total RR.HH.", f"${kpis['gasto_rrhh']:,.0f}")
    detalle = kpis.get("detalle_rrhh")
    if detalle is not None:
        df_rrhh = detalle.reset_index()
        df_rrhh.columns = ["descripcion", "monto_gasto_rrhh"]
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(df_rrhh, width="stretch")
        with col2:
            safe_bar_chart(df_rrhh, "descripcion", "monto_gasto_rrhh", "Gasto RRHH por entrenador")


def render_viaticos(df: pd.DataFrame, kpis: dict) -> None:
    st.markdown("## 🚍 Viáticos")
    st.metric("Total viáticos", f"${kpis['gasto_viaticos']:,.0f}")
    detalle = kpis.get("detalle_viaticos")
    if detalle is not None:
        df_via = detalle.reset_index()
        df_via.columns = ["responsable", "monto_viatico"]
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(df_via, width="stretch")
        with col2:
            safe_bar_chart(df_via, "responsable", "monto_viatico", "Viáticos por responsable")


def render_inversiones(df: pd.DataFrame, kpis: dict) -> None:
    st.markdown("## 🛠️ Inversiones")
    st.metric("Total inversiones", f"${kpis['gasto_inversion']:,.0f}")
    detalle = kpis.get("detalle_inversion")
    if detalle is not None:
        df_inv = detalle.reset_index()
        df_inv.columns = ["descripcion", "monto_inversion"]
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(df_inv, width="stretch")
        with col2:
            safe_bar_chart(df_inv, "descripcion", "monto_inversion", "Inversiones por concepto")


def render_inscripciones(df: pd.DataFrame, kpis: dict) -> None:
    st.markdown("## 📝 Inscripciones")
    st.metric("Total inscripciones", f"${kpis['gasto_inscripciones']:,.0f}")
    detalle = kpis.get("detalle_inscripciones")
    if detalle is not None:
        df_ins = detalle.reset_index()
        df_ins.columns = ["descripcion", "monto_inscripcion"]
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(df_ins, width="stretch")
        with col2:
            safe_bar_chart(df_ins, "descripcion", "monto_inscripcion", "Inscripciones por evento")


def render_top_gastos(df: pd.DataFrame, kpis: dict) -> None:
    st.markdown("## 🔝 Top 10 gastos del mes")
    top = kpis.get("top10_gastos")
    if top is not None:
        st.dataframe(top, width="stretch")
    else:
        st.info("No se pudo calcular el Top 10 de gastos. Revisa que exista una columna de montos de gasto.")
