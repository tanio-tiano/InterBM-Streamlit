"""Main Streamlit UI — orchestration only.

This file should remain thin: it wires configuration, services and UI
components together without containing heavy business logic.
"""
import streamlit as st

from config import settings  # reservado para futura configuración / Gemini después
from services.sheets import get_available_sheets, get_worksheet
from logic.clean_dataframe import extract_main_table, build_clean_dataframe
from logic.kpis import calcular_kpis

from components.sections import (
    render_reporte_socios,
    render_estado_financiero,
    render_estructura_ingresos,
    render_estructura_gasto,
    render_rrhh,
    render_viaticos,
    render_inversiones,
    render_inscripciones,
    render_gastos_pendientes,
    render_top_gastos,
)

# 🔜 Cuando quieras reactivar Gemini, descomenta esta línea:
# from analytics.qa_llm import responder_pregunta_sobre_df


def main():
    st.title("📊 Dashboard InterBM — Estado Financiero Mensual")

    # ------------------------------------------------------------------
    # Sidebar: configuración general
    # ------------------------------------------------------------------
    st.sidebar.header("Configuración")

    vista = st.sidebar.selectbox(
        "Vista del dashboard:",
        ["Reporte para socios", "Vista detallada interna"],
    )

    # Listado de pestañas (meses) desde Google Sheets
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

    # ------------------------------------------------------------------
    # Lectura de datos crudos desde Google Sheets
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

    # Vista interna → muestra la matriz cruda
    if vista == "Vista detallada interna":
        with st.expander("Ver matriz cruda desde Google Sheets"):
            st.write(raw_values)

    # ------------------------------------------------------------------
    # Extracción y limpieza determinista
    # ------------------------------------------------------------------
    st.subheader("Procesando datos…")
    with st.spinner("Limpieza y estructuración de la tabla…"):
        try:
            # ⚠️ Aquí ya asumimos versión determinista de extract_main_table
            clean = extract_main_table(raw_values)
            df = build_clean_dataframe(clean)
        except Exception as e:
            st.error(f"Error al procesar la tabla:\n{e}")
            st.stop()

    if df.empty:
        st.warning(
            "No se obtuvieron filas válidas luego de la limpieza. "
            "Revisa la pestaña seleccionada."
        )
        st.stop()

    if vista == "Vista detallada interna":
        st.subheader("DataFrame limpio generado")
        st.dataframe(df, use_container_width=True)

    # ------------------------------------------------------------------
    # Cálculo de KPIs
    # ------------------------------------------------------------------
    kpis = calcular_kpis(df)

    # ------------------------------------------------------------------
    # Render de secciones según la vista seleccionada
    # ------------------------------------------------------------------
    if vista == "Reporte para socios":
        render_reporte_socios(df, kpis)

    else:
        render_estado_financiero(df, kpis)
        render_estructura_ingresos(df, kpis)
        render_estructura_gasto(df, kpis)
        render_rrhh(df, kpis)
        render_viaticos(df, kpis)
        render_inversiones(df, kpis)
        render_inscripciones(df, kpis)
        render_gastos_pendientes(df, kpis)
        render_top_gastos(df, kpis)

        # --------------------------------------------------------------
        # 🔜 Bloque listo para reactivar Gemini QA más adelante:
        # --------------------------------------------------------------
        # st.markdown("## 🧠 Pregúntale a tus finanzas")
        # pregunta = st.text_area("Escribe tu pregunta aquí:", height=100)
        # if st.button("Responder con Gemini") and pregunta.strip():
        #     with st.spinner("Analizando datos y generando respuesta..."):
        #         try:
        #             respuesta = responder_pregunta_sobre_df(df, pregunta)
        #             st.markdown("### Respuesta de Gemini")
        #             st.markdown(respuesta)
        #         except Exception as e:
        #             st.error(f"Ocurrió un error al consultar al modelo:\n{e}")


if __name__ == "__main__":
    main()
