"""Main Streamlit UI — InterBM Dashboard
Versión enfocada en reporte para socios.
"""

import streamlit as st

from services.sheets import get_available_sheets, get_worksheet
from logic.clean_dataframe import extract_main_table, build_clean_dataframe
from logic.kpis import calcular_kpis
from components.sections import (
    render_reporte_socios,
    render_grafico_gastos_por_tipo,
)


def main():
    st.title("📊 Dashboard InterBM — Reporte para Socios")

    # ------------------------------------------------------------------
    # Sidebar: selección de mes
    # ------------------------------------------------------------------
    st.sidebar.header("Configuración")

    try:
        meses = get_available_sheets()
    except Exception as e:
        st.error(f"Error al obtener las pestañas del Google Sheet:\n{e}")
        st.stop()

    if not meses:
        st.error("No se encontraron pestañas en la hoja de Google.")
        st.stop()

    mes_sel = st.sidebar.selectbox("Selecciona el mes:", meses)
    st.markdown(f"### Mes seleccionado: **{mes_sel}**")

    # ------------------------------------------------------------------
    # Lectura desde Google Sheets
    # ------------------------------------------------------------------
    try:
        sheet = get_worksheet(mes_sel)
        raw_values = sheet.get_all_values()
    except Exception as e:
        st.error(f"Error al leer la pestaña '{mes_sel}':\n{e}")
        st.stop()

    if not raw_values:
        st.warning("La hoja seleccionada está vacía.")
        st.stop()

    # ------------------------------------------------------------------
    # Extracción y limpieza determinista
    # ------------------------------------------------------------------
    with st.spinner("Procesando datos del mes…"):
        try:
            clean = extract_main_table(raw_values)   # versión determinista
            df = build_clean_dataframe(clean)
        except Exception as e:
            st.error(f"Error al procesar los datos:\n{e}")
            st.stop()

    if df.empty:
        st.warning(
            "No se obtuvieron datos válidos después de la limpieza. "
            "Revisa la pestaña seleccionada en Google Sheets."
        )
        st.stop()

    # ------------------------------------------------------------------
    # Cálculo de KPIs
    # ------------------------------------------------------------------
    kpis = calcular_kpis(df)

    # ------------------------------------------------------------------
    # Reporte para socios (única vista)
    # ------------------------------------------------------------------
    render_reporte_socios(df, kpis)

    # Gráfico adicional: gastos por tipo de gasto (barras)
    render_grafico_gastos_por_tipo(df, kpis)


if __name__ == "__main__":
    main()
