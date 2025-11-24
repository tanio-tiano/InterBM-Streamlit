"""Main Streamlit UI — orchestration only.

This file should remain thin: it wires configuration, services and UI
components together without containing heavy business logic.
"""
import streamlit as st
from logic.clean_dataframe import extract_main_table, build_clean_dataframe
from config import settings
from services.sheets import get_available_sheets, get_worksheet  # si ya usas la versión cacheada
from logic.clean_dataframe import extract_main_table, build_clean_dataframe
from logic.kpis import calcular_kpis
from components.sections import (
    render_estado_financiero,
    render_estructura_gasto,
    render_rrhh,
    render_viaticos,
    render_inversiones,
    render_inscripciones,
    render_top_gastos,
)
from analytics.qa_llm import responder_pregunta_sobre_df


def main():
    st.title("📊 Dashboard InterBM — Estado Financiero Mensual")

    st.sidebar.header("Configuración")

    # List of month sheets
    try:
        meses = get_available_sheets()
    except Exception as e:
        st.error(f"Error al obtener las pestañas del Google Sheet:\n{e}")
        st.stop()

    if not meses:
        st.error("No se encontraron pestañas en el Google Sheet.")
        st.stop()

    mes_sel = st.sidebar.selectbox("Selecciona la pestaña (mes):", meses)
    st.markdown(f"### Mes seleccionado: **{mes_sel}**")

    # Read raw values
    try:
        sheet = get_worksheet(mes_sel)
        raw_values = sheet.get_all_values()
    except Exception as e:
        st.error(f"Error al leer la pestaña '{mes_sel}':\n{e}")
        st.stop()

    if not raw_values:
        st.warning("La hoja seleccionada está vacía.")
        st.stop()

    with st.expander("Ver matriz cruda desde Google Sheets"):
        st.write(raw_values)

    # LLM extraction + cleaning
    st.subheader("Procesando datos con Gemini…")
    with st.spinner("Limpieza y estructuración de la tabla con LLM…"):
        try:
            clean = extract_main_table(raw_values)
            df = build_clean_dataframe(clean)

        except Exception as e:
            st.error(f"Error al procesar la tabla con Gemini:\n{e}")
            st.stop()

    if df.empty:
        st.warning("No se obtuvieron filas válidas luego de la limpieza. Revisa la pestaña seleccionada.")
        st.stop()

    st.subheader("DataFrame limpio generado por Gemini")
    st.dataframe(df, width="stretch")


    # KPIs
    kpis = calcular_kpis(df)

    # Render sections
    render_estado_financiero(df, kpis)
    render_estructura_gasto(df, kpis)
    render_rrhh(df, kpis)
    render_viaticos(df, kpis)
    render_inversiones(df, kpis)
    render_inscripciones(df, kpis)
    render_top_gastos(df, kpis)

    # QA LLM
    st.markdown("## 🧠 Pregúntale a tus finanzas")
    pregunta = st.text_area("Escribe tu pregunta aquí:", height=100)
    if st.button("Responder con Gemini") and pregunta.strip():
        with st.spinner("Analizando datos y generando respuesta..."):
            try:
                respuesta = responder_pregunta_sobre_df(df, pregunta)
                st.markdown("### Respuesta de Gemini")
                st.markdown(respuesta)
            except Exception as e:
                st.error(f"Ocurrió un error al consultar al modelo:\n{e}")


if __name__ == "__main__":
    main()


