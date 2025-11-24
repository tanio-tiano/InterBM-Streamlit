"""UI section components for the InterBM dashboard.

En esta versión TODO está pensado para el reporte a socios.
Las funciones clave son:

- render_reporte_socios: visión completa para socios (ingresos, gastos, salud financiera,
  distribución de gastos, ingresos por tipo, pendientes, top gastos).
- render_grafico_gastos_por_tipo: gráfico de barras de gastos por tipo (complemento visual).
"""

from typing import Any
import streamlit as st
import pandas as pd
import plotly.express as px


# -------------------------------------------------------------------
# Helpers internos
# -------------------------------------------------------------------
def _format_currency(value: float | None) -> str:
    if value is None:
        return "$0"
    try:
        return f"${value:,.0f}"
    except Exception:
        return str(value)


# -------------------------------------------------------------------
# Reporte general para socios (VISTA PRINCIPAL)
# -------------------------------------------------------------------
def render_reporte_socios(df: pd.DataFrame, kpis: dict) -> None:
    ingresos = kpis.get("ingresos", {}) or {}
    gastos = kpis.get("gastos", {}) or {}
    salud = kpis.get("salud_financiera", {}) or {}

    total_ingresos = ingresos.get("total", 0.0)
    total_gastos = gastos.get("total", 0.0)
    saldo_neto = salud.get("saldo_neto", total_ingresos - total_gastos)
    ratio_gastos_ingresos = salud.get("ratio_gastos_ingresos", None)

    pendientes = gastos.get("pendientes", {}) or {}
    total_pend = pendientes.get("total", 0.0)
    cant_pend = pendientes.get("cantidad", 0)

    por_tipo_ingreso = ingresos.get("por_tipo") or {}
    por_categoria_gasto = gastos.get("por_categoria") or {}
    top_gastos = kpis.get("top_gastos") or []

    # ------------------------------------------------------------------
    # KPIs principales
    # ------------------------------------------------------------------
    st.markdown("## 📊 Resumen general del período")

    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos del mes", _format_currency(total_ingresos))
    col2.metric("Gastos del mes", _format_currency(total_gastos))
    col3.metric("Saldo neto", _format_currency(saldo_neto))

    if ratio_gastos_ingresos is not None:
        st.caption(
            f"En este período, los gastos representan aproximadamente **{ratio_gastos_ingresos:.1%}** de los ingresos."
        )

    st.markdown("---")

    # ------------------------------------------------------------------
    # Distribución de gastos (donut) + Ingresos por tipo (barras)
    # ------------------------------------------------------------------
    st.markdown("## 💰 ¿De dónde vienen los recursos y en qué se usan?")

    col_a, col_b = st.columns(2)

    # Donut: distribución de gastos por categoría
    with col_a:
        st.markdown("#### 🧩 Distribución de gastos por tipo")
        if por_categoria_gasto:
            gasto_df = (
                pd.DataFrame(
                    [{"tipo_gasto": k, "monto_gasto": v} for k, v in por_categoria_gasto.items()]
                )
                .sort_values("monto_gasto", ascending=False)
            )

            # Agrupar categorías pequeñas en "Otros" si hay muchas
            if len(gasto_df) > 6:
                top = gasto_df.head(5)
                otros = pd.DataFrame(
                    [{
                        "tipo_gasto": "Otros",
                        "monto_gasto": gasto_df["monto_gasto"].iloc[5:].sum(),
                    }]
                )
                gasto_df = pd.concat([top, otros], ignore_index=True)

            fig_gasto = px.pie(
                gasto_df,
                names="tipo_gasto",
                values="monto_gasto",
                hole=0.5,
            )
            fig_gasto.update_layout(showlegend=True)
            st.plotly_chart(fig_gasto, width="stretch")
        else:
            st.info("Aún no hay datos suficientes de gastos para mostrar un resumen.")

    # Barras: ingresos por tipo
    with col_b:
        st.markdown("#### 💵 Ingresos por tipo")
        if por_tipo_ingreso:
            ingreso_df = (
                pd.DataFrame(
                    [{"tipo_ingreso": k, "monto_ingreso": v} for k, v in por_tipo_ingreso.items()]
                )
                .sort_values("monto_ingreso", ascending=False)
            )

            fig_ing = px.bar(
                ingreso_df,
                x="tipo_ingreso",
                y="monto_ingreso",
                text_auto=True,
            )
            fig_ing.update_layout(xaxis_title="", yaxis_title="Monto")
            st.plotly_chart(fig_ing, width="stretch")
        else:
            st.info("Aún no hay datos suficientes de ingresos para mostrar un resumen.")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Salud financiera (bloque explícito para socios)
    # ------------------------------------------------------------------
    st.markdown("## 🩺 Salud financiera")

    col_sf1, col_sf2 = st.columns(2)
    col_sf1.metric("Saldo neto del período", _format_currency(saldo_neto))
    if ratio_gastos_ingresos is not None:
        col_sf2.metric(
            "Relación gastos / ingresos",
            f"{ratio_gastos_ingresos:.1%}",
        )
    else:
        col_sf2.metric("Relación gastos / ingresos", "N/D")

    if saldo_neto >= 0:
        st.success(
            "El saldo neto del período es **positivo**, lo que indica que los ingresos "
            "han sido suficientes para cubrir los gastos."
        )
    else:
        st.warning(
            "El saldo neto del período es **negativo**, lo que indica que los gastos "
            "han superado a los ingresos."
        )

    st.markdown("---")

    # ------------------------------------------------------------------
    # Gastos pendientes
    # ------------------------------------------------------------------
    st.markdown("## ⏳ Compromisos pendientes")

    colp1, colp2 = st.columns(2)
    colp1.metric("Total gastos pendientes", _format_currency(total_pend))
    colp2.metric("Cantidad de gastos pendientes", f"{cant_pend}")

    if total_gastos > 0 and total_pend > 0:
        porcentaje_pend = total_pend / total_gastos
        st.caption(
            f"Los gastos pendientes corresponden a aproximadamente **{porcentaje_pend:.1%}** "
            "del gasto total del período."
        )
    elif total_pend == 0:
        st.caption("Actualmente no hay gastos pendientes registrados.")

    # ------------------------------------------------------------------
    # Top 10 gastos del mes (resumen, amigable para socios)
    # ------------------------------------------------------------------
    st.markdown("## 🔝 Top 10 gastos del mes")

    if top_gastos:
        top_df = pd.DataFrame(top_gastos)

        # Intentar usar nombres amigables si existen
        posibles_desc = [c for c in top_df.columns if "desc" in c.lower()]
        posibles_tipo = [c for c in top_df.columns if "tipo" in c.lower()]
        posibles_monto = [c for c in top_df.columns if "monto" in c.lower()]

        columnas = []
        if posibles_desc:
            columnas.append(posibles_desc[0])
        if posibles_tipo:
            columnas.append(posibles_tipo[0])
        if posibles_monto:
            columnas.append(posibles_monto[0])

        if columnas:
            top_df = top_df[columnas]

        st.dataframe(top_df, width="stretch")
        st.caption(
            "Este listado muestra los 10 egresos de mayor monto en el período seleccionado."
        )
    else:
        st.info("No se encontraron gastos suficientes para construir el Top 10.")


# -------------------------------------------------------------------
# Gráfico de barras de gastos por tipo de gasto (complementario)
# -------------------------------------------------------------------
def render_grafico_gastos_por_tipo(df: pd.DataFrame, kpis: dict) -> None:
    st.markdown("## 📊 Gastos por tipo de gasto (detalle visual)")

    por_categoria = kpis.get("gastos", {}).get("por_categoria", {})

    if not por_categoria:
        st.info("No hay datos suficientes para mostrar el gráfico de gastos por tipo.")
        return

    gasto_df = (
        pd.DataFrame(
            [{"tipo_gasto": k, "monto_gasto": v} for k, v in por_categoria.items()]
        )
        .sort_values("monto_gasto", ascending=False)
    )

    fig = px.bar(
        gasto_df,
        x="tipo_gasto",
        y="monto_gasto",
        text_auto=True,
        title="Gastos segmentados por tipo de gasto",
    )
    fig.update_layout(
        xaxis_title="Categoría de gasto",
        yaxis_title="Monto gastado",
        showlegend=False,
    )

    st.plotly_chart(fig, width="stretch")
