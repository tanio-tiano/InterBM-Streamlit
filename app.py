# app.py

import os
import json
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import google.generativeai as genai

# ---------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------------

# URL de tu Google Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1tc7me60_L-h_btVfofDnMPtVL1VVk-wSLqlFCI4SD1s/edit?usp=sharing"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Cargar variables de entorno desde .env (si existe)
load_dotenv()

# API key de Gemini (se lee primero de la variable de entorno `GOOGLE_API_KEY`)
GENAI_API_KEY = os.getenv("GOOGLE_API_KEY")

# Para pruebas locales sin .env, puedes descomentar y pegarla directo (no recomendado):
# GENAI_API_KEY = "TU_API_KEY_DE_GEMINI"

if not GENAI_API_KEY:
    st.error(
        "No se encontró GOOGLE_API_KEY.\n\n"
        "Configura la variable de entorno GOOGLE_API_KEY con tu API key de Gemini,\n"
        "o edita app.py y asigna GENAI_API_KEY directamente."
    )
    st.stop()

# Configurar cliente de Gemini
genai.configure(api_key=GENAI_API_KEY)

# Modelo Gemini a usar
GEMINI_MODEL_NAME = "gemini-2.5-flash"


# ---------------------------------------------------------
# CONEXIÓN A GOOGLE SHEETS
# ---------------------------------------------------------

@st.cache_resource
def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credenciales.json",
        SCOPES,
    )
    client = gspread.authorize(creds)
    return client


@st.cache_resource
def get_spreadsheet():
    client = get_gspread_client()
    ss = client.open_by_url(SHEET_URL)
    return ss


@st.cache_data
def get_available_sheets():
    ss = get_spreadsheet()
    return [ws.title for ws in ss.worksheets()]


@st.cache_resource
def get_worksheet(sheet_name: str):
    ss = get_spreadsheet()
    ws = ss.worksheet(sheet_name)
    return ws


# ---------------------------------------------------------
# LÓGICA CON GEMINI PARA LIMPIAR LA TABLA
# ---------------------------------------------------------

def llm_extract_table(raw_matrix):
    """
    Usa Gemini para:
      - detectar la tabla principal dentro de la matriz cruda
      - definir encabezados limpios
      - devolver solo filas válidas

    Formato esperado de salida:
    {
      "headers": [...],
      "rows": [
        [...],
        ...
      ]
    }
    """
    if not raw_matrix:
        raise ValueError("La matriz de la hoja está vacía.")

    prompt_text = f"""
Eres un asistente experto en limpieza de datos tabulares.

Te entrego el contenido completo de una hoja de cálculo, en forma de matriz (lista de filas).
Cada fila es una lista de celdas (strings). Puede haber:
- filas vacías
- encabezados desordenados
- celdas con '#REF!', '#N/A', '-----', '$330.000', etc.
- más de un bloque de información (resúmenes arriba, tablas abajo)

La hoja corresponde a la contabilidad mensual de un club deportivo:
- tipos de gasto (RR.HH., OPERATIVO, INVERSION, INSCRIPCIONES, VIATICOS, DEUDAS, etc.)
- estado (PAGADO, EN REVISIÓN, PENDIENTE, etc.)
- montos de ingreso y gasto
- fechas de pago proyectado y efectivo
- descripciones de los movimientos
- responsables, cuentas bancarias, adjuntos, etc.

Tu tarea es identificar la TABLA PRINCIPAL que contiene los movimientos de fila a fila,
no los totales o resúmenes de arriba.

Debes:

1. Detectar dónde comienza la tabla principal (ignora resúmenes o totales que estén en la parte superior).
2. Proponer nombres LIMPIOS y únicos para las columnas, en español, en minúsculas, sin tildes,
   espacios reemplazados por guion_bajo. Ejemplos:
   - "Nº" -> "numero"
   - "TIPO DE GASTO" -> "tipo_gasto"
   - "TIPO DE INGRESO" -> "tipo_ingreso"
   - "ESTADO" -> "estado"
   - "MONTO INGRESO" -> "monto_ingreso"
   - "MONTO GASTO" -> "monto_gasto"
   - "FECHA DE PAGO PROYECTADO" -> "fecha_pago_proyectado"
   - "FECHA DE PAGO EFECTIVA" -> "fecha_pago_efectiva"
   - "DESCRIPCION" -> "descripcion"
   - "CUENTA EMISORA DINEROS" -> "cuenta_emisora"
   - "CUENTA RECEPTOR" -> "cuenta_receptora"
   - "FORMA DE PAGO" -> "forma_pago"
   - "RESPONSABLE DE LA GESTIÓN" -> "responsable_gestion"
   - "ADJUNTABLES" -> "adjuntables"
3. Limpiar filas con datos basura ("-----", "#REF!", "#N/A") y convertir montos tipo "$330.000" a "330000".
4. Mantener solo las filas que realmente pertenezcan a la tabla principal.
5. Devolver SOLO un JSON con el siguiente formato EXACTO:

{{
  "headers": ["columna1", "columna2", ...],
  "rows": [
    ["valor_row_1_col_1", "valor_row_1_col_2", ...],
    ["valor_row_2_col_1", "valor_row_2_col_2", ...]
  ]
}}

No agregues explicaciones, ni texto extra fuera del JSON.
Aquí viene la matriz (lista de listas):

{raw_matrix}
"""

    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    response = model.generate_content(prompt_text)

    content = response.text
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Intento de rescate: extraer el bloque JSON
        try:
            json_str = content[content.index("{"): content.rindex("}") + 1]
            parsed = json.loads(json_str)
        except Exception as e:
            raise ValueError(
                f"No se pudo interpretar la respuesta del LLM como JSON.\n\nRespuesta cruda:\n{content}"
            ) from e

    if "headers" not in parsed or "rows" not in parsed:
        raise ValueError(
            f"El JSON devuelto por el LLM no contiene 'headers' o 'rows'.\nJSON:\n{parsed}"
        )

    return parsed

def build_clean_dataframe(clean_dict):
    """
    Construye un DataFrame limpio a partir del JSON devuelto por Gemini.
    Convierte de forma agresiva las columnas que parecen montos y fechas,
    usando el NOMBRE de la columna.
    """
    headers = clean_dict.get("headers", [])
    rows = clean_dict.get("rows", [])

    if not headers:
        raise ValueError("No se recibieron encabezados desde el LLM.")
    if not rows:
        return pd.DataFrame(columns=headers)

    df = pd.DataFrame(rows, columns=headers)

    # 1) Normalización básica
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace(
            {"#REF!": None, "#N/A": None, "-----": None, "": None}
        )

    # 2) Conversión explícita de columnas numéricas (por nombre)
    #    OJO: sacamos "gasto" para no romper "tipo_gasto"
    posibles_montos = [
        c for c in df.columns
        if any(
            key in c
            for key in ["monto", "saldo", "ingreso", "total"]
        )
    ]

    for col in posibles_montos:
        serie = (
            df[col]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(".", "", regex=False)   # separador de miles
            .str.replace(",", ".", regex=False)  # coma decimal -> punto
        )
        df[col] = pd.to_numeric(serie, errors="coerce")

    # 3) Conversión de fechas (por nombre)
    posibles_fechas = [
        c for c in df.columns
        if any(
            key in c
            for key in ["fecha", "dia"]
        )
    ]

    for col in posibles_fechas:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    return df


# ---------------------------------------------------------
# CÁLCULO DE KPIs
# ---------------------------------------------------------

def calcular_kpis(df: pd.DataFrame):
    """Devuelve un diccionario con KPIs calculados a partir del DataFrame limpio."""

    # Identificar columnas clave por nombre
    col_gasto = next((c for c in df.columns if "monto_gasto" in c), None)
    if not col_gasto:
        col_gasto = next((c for c in df.columns if "gasto" in c), None)

    col_ingreso = next((c for c in df.columns if "monto_ingreso" in c), None)
    if not col_ingreso:
        col_ingreso = next((c for c in df.columns if "ingreso" in c), None)

    col_tipo_gasto = next((c for c in df.columns if "tipo_gasto" in c), None)
    col_tipo_ingreso = next((c for c in df.columns if "tipo_ingreso" in c), None)
    col_descripcion = next((c for c in df.columns if "descripcion" in c), None)
    col_responsable = next((c for c in df.columns if "responsable" in c), None)

# --- Parches anti-error para string ---
    if col_tipo_gasto:
        df[col_tipo_gasto] = df[col_tipo_gasto].astype(str)

    if col_descripcion:
        df[col_descripcion] = df[col_descripcion].astype(str)

    if col_responsable:
        df[col_responsable] = df[col_responsable].astype(str)

    # Totales simples
    total_gastos = float(df[col_gasto].sum()) if col_gasto else 0.0
    total_ingresos = float(df[col_ingreso].sum()) if col_ingreso else 0.0
    balance_neto = total_ingresos - total_gastos

    # Estructura de gasto por tipo_gasto
    gasto_por_tipo = None
    if col_gasto and col_tipo_gasto:
        gasto_por_tipo = (
            df.groupby(col_tipo_gasto)[col_gasto]
            .sum()
            .sort_values(ascending=False)
        )

    # RRHH
    gasto_rrhh = 0.0
    detalle_rrhh = None
    if col_gasto and col_tipo_gasto:
        df_rrhh = df[df[col_tipo_gasto].str.contains("RR", case=False, na=False)]
        gasto_rrhh = float(df_rrhh[col_gasto].sum())
        if col_descripcion:
            detalle_rrhh = (
                df_rrhh.groupby(col_descripcion)[col_gasto]
                .sum()
                .sort_values(ascending=False)
            )

    # Viáticos
    gasto_viaticos = 0.0
    detalle_viaticos = None
    if col_gasto and col_tipo_gasto:
        df_via = df[df[col_tipo_gasto].str.contains("viatico", case=False, na=False)]
        gasto_viaticos = float(df_via[col_gasto].sum())
        if col_responsable:
            detalle_viaticos = (
                df_via.groupby(col_responsable)[col_gasto]
                .sum()
                .sort_values(ascending=False)
            )

    # Inversiones
    gasto_inversion = 0.0
    detalle_inversion = None
    if col_gasto and col_tipo_gasto:
        df_inv = df[df[col_tipo_gasto].str.contains("inversion", case=False, na=False)]
        gasto_inversion = float(df_inv[col_gasto].sum())
        if col_descripcion:
            detalle_inversion = (
                df_inv.groupby(col_descripcion)[col_gasto]
                .sum()
                .sort_values(ascending=False)
            )

    # Inscripciones
    gasto_inscripciones = 0.0
    detalle_inscripciones = None
    if col_gasto and col_tipo_gasto:
        df_ins = df[df[col_tipo_gasto].str.contains("inscrip", case=False, na=False)]
        gasto_inscripciones = float(df_ins[col_gasto].sum())
        if col_descripcion:
            detalle_inscripciones = (
                df_ins.groupby(col_descripcion)[col_gasto]
                .sum()
                .sort_values(ascending=False)
            )

    # Top 10 gastos del mes
    top10_gastos = None
    if col_gasto:
        top10_gastos = df.sort_values(col_gasto, ascending=False).head(10)

    return {
        "col_gasto": col_gasto,
        "col_ingreso": col_ingreso,
        "col_tipo_gasto": col_tipo_gasto,
        "col_tipo_ingreso": col_tipo_ingreso,
        "col_descripcion": col_descripcion,
        "col_responsable": col_responsable,
        "total_gastos": total_gastos,
        "total_ingresos": total_ingresos,
        "balance_neto": balance_neto,
        "gasto_por_tipo": gasto_por_tipo,
        "gasto_rrhh": gasto_rrhh,
        "detalle_rrhh": detalle_rrhh,
        "gasto_viaticos": gasto_viaticos,
        "detalle_viaticos": detalle_viaticos,
        "gasto_inversion": gasto_inversion,
        "detalle_inversion": detalle_inversion,
        "gasto_inscripciones": gasto_inscripciones,
        "detalle_inscripciones": detalle_inscripciones,
        "top10_gastos": top10_gastos,
    }

def safe_bar_chart(df, x_col, y_col, titulo=None):
    """Envuelve st.bar_chart para no graficar data vacía o rara."""
    if df is None or df.empty:
        st.info("No hay datos para este gráfico.")
        return

    df = df.copy()

    # Limpio eje X: quito espacios y filas sin etiqueta
    df[x_col] = df[x_col].astype(str).str.strip()
    df = df[df[x_col] != ""]

    if df.empty:
        st.info("No hay datos válidos para este gráfico.")
        return

    # Verifico que la columna Y tenga algo numérico
    if not pd.api.types.is_numeric_dtype(df[y_col]):
        st.info("No hay datos numéricos para graficar en esta métrica.")
        return

    if df[y_col].fillna(0).sum() == 0:
        st.info("Todos los valores son 0 o NaN. No se grafica nada.")
        return

    if titulo:
        st.markdown(f"#### {titulo}")

    st.bar_chart(df.set_index(x_col)[y_col], width="stretch")

# ---------------------------------------------------------
# UI con preguntas libres usando Gemini
# ---------------------------------------------------------
def responder_pregunta_sobre_df(df: pd.DataFrame, pregunta: str) -> str:
    """
    Usa Gemini para responder una pregunta en lenguaje natural
    sobre el DataFrame financiero limpio del mes.
    """

    # Limitamos filas para no mandar toda la planilla (por tokens)
    df_sample = df.copy()
    max_rows = 80
    if len(df_sample) > max_rows:
        df_sample = df_sample.head(max_rows)

    # Info de columnas y tipos (para que el modelo entienda el esquema)
    schema_info = []
    for col in df.columns:
        schema_info.append({
            "columna": col,
            "tipo_datos": str(df[col].dtype)
        })

    # Convertimos a JSON compacto
    # Convertir Timestamps a strings ISO para evitar errores de JSON
    df_sample = df_sample.copy()
    for col in df_sample.columns:
        if pd.api.types.is_datetime64_any_dtype(df_sample[col]):
            df_sample[col] = df_sample[col].dt.strftime("%Y-%m-%d")
    # Si quedan timestamps mezclados:
        df_sample[col] = df_sample[col].astype(object).where(
            df_sample[col].apply(lambda x: not hasattr(x, 'isoformat')),
            df_sample[col].apply(lambda x: x.isoformat())
        )

    data_json = df_sample.to_dict(orient="records")

    prompt = f"""
Actúa como analista financiero de un club deportivo.
Tienes una tabla de movimientos financieros de UN mes.

La tabla contiene columnas con nombres ya limpios (tipo_gasto, monto_gasto,
monto_ingreso, descripcion, responsable_gestion, etc.) y cada fila es un movimiento.

Tu tarea:
- Responder en español, de forma clara y breve.
- Puedes hacer cálculos (sumas, promedios, porcentajes) usando los datos entregados.
- Si la pregunta es ambigua, asume lo más razonable para un estado financiero mensual.
- Si no hay datos suficientes para responder algo, dilo explícitamente.

Primero, te doy el ESQUEMA de la tabla:
{json.dumps(schema_info, ensure_ascii=False, indent=2)}

Luego, te doy UNA MUESTRA DE LAS FILAS (hasta {max_rows} filas):
{json.dumps(data_json, ensure_ascii=False)[:8000]}

Pregunta del usuario:
\"\"\"{pregunta}\"\"\"


Responde SOLO en texto plano, sin JSON, en máximo 10–12 líneas,
explicando el resultado como si se lo presentases a la directiva del club.
"""

    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    response = model.generate_content(prompt)
    return response.text.strip()


# ---------------------------------------------------------
# UI STREAMLIT
# ---------------------------------------------------------

def main():
    st.title("📊 Dashboard InterBM — Estado Financiero Mensual")

    st.sidebar.header("Configuración")

    # Obtener lista de pestañas (cada una es un mes)
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

    # Obtener worksheet y datos crudos
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

    # Procesar con Gemini
    st.subheader("Procesando datos con Gemini…")
    with st.spinner("Limpieza y estructuración de la tabla con Gemini…"):
        try:
            clean = llm_extract_table(raw_values)
            df = build_clean_dataframe(clean)
        except Exception as e:
            st.error(f"Error al procesar la tabla con Gemini:\n{e}")
            st.stop()

    if df.empty:
        st.warning("No se obtuvieron filas válidas luego de la limpieza. Revisa el contenido de la pestaña.")
        st.stop()

    st.subheader("DataFrame limpio generado por Gemini")
    st.dataframe(df, width="stretch")

    # ---------------- Cálculo de KPIs ----------------
    kpis = calcular_kpis(df)

    # ---------- 1) Estado financiero del mes ----------
    st.markdown("## 🧾 Estado financiero del mes")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total ingresos", f"${kpis['total_ingresos']:,.0f}")
    col2.metric("Total gastos", f"${kpis['total_gastos']:,.0f}")
    col3.metric(
        "Balance neto",
        f"${kpis['balance_neto']:,.0f}",
        delta=None
    )

    # ---------- 2) Estructura del gasto por TIPO DE GASTO ----------
    if kpis["gasto_por_tipo"] is not None:
        st.markdown("## 🧩 Estructura del gasto por tipo de gasto")

        gasto_tipo_df = kpis["gasto_por_tipo"].reset_index()
        gasto_tipo_df.columns = ["tipo_gasto", "monto_gasto"]

        col_a, col_b = st.columns(2)
        with col_a:
            st.dataframe(gasto_tipo_df, width="stretch")
        with col_b:
            safe_bar_chart(gasto_tipo_df, "tipo_gasto", "monto_gasto", "Gasto por tipo de gasto")


    # ---------- 3) RR.HH. ----------
    st.markdown("## 👤 RR.HH.")

    st.metric("Total RR.HH.", f"${kpis['gasto_rrhh']:,.0f}")

    if kpis["detalle_rrhh"] is not None:
        df_rrhh = kpis["detalle_rrhh"].reset_index()
        df_rrhh.columns = ["descripcion", "monto_gasto_rrhh"]

        col_rr1, col_rr2 = st.columns(2)
        with col_rr1:
            st.dataframe(df_rrhh, width="stretch")
        with col_rr2:
            safe_bar_chart(df_rrhh, "descripcion", "monto_gasto_rrhh", "Gasto RRHH por entrenador")

    # ---------- 4) Viáticos ----------
    st.markdown("## 🚍 Viáticos")

    st.metric("Total viáticos", f"${kpis['gasto_viaticos']:,.0f}")

    if kpis["detalle_viaticos"] is not None:
        df_via = kpis["detalle_viaticos"].reset_index()
        df_via.columns = ["responsable", "monto_viatico"]

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.dataframe(df_via, width="stretch")
        with col_v2:
            safe_bar_chart(df_via, "responsable", "monto_viatico", "Viáticos por responsable")


    # ---------- 5) Inversiones ----------
    st.markdown("## 🛠️ Inversiones")

    st.metric("Total inversiones", f"${kpis['gasto_inversion']:,.0f}")

    if kpis["detalle_inversion"] is not None:
        df_inv = kpis["detalle_inversion"].reset_index()
        df_inv.columns = ["descripcion", "monto_inversion"]

        col_i1, col_i2 = st.columns(2)
        with col_i1:
            st.dataframe(df_inv, width="stretch")
        with col_i2:
            safe_bar_chart(df_inv, "descripcion", "monto_inversion", "Inversiones por concepto")


    # ---------- 6) Inscripciones ----------
    st.markdown("## 📝 Inscripciones")

    st.metric("Total inscripciones", f"${kpis['gasto_inscripciones']:,.0f}")

    if kpis["detalle_inscripciones"] is not None:
        df_ins = kpis["detalle_inscripciones"].reset_index()
        df_ins.columns = ["descripcion", "monto_inscripcion"]

        col_ins1, col_ins2 = st.columns(2)
        with col_ins1:
            st.dataframe(df_ins, width="stretch")
        with col_ins2:
            safe_bar_chart(df_ins, "descripcion", "monto_inscripcion", "Inscripciones por evento")


    # ---------- 7) Top 10 gastos del mes ----------
    st.markdown("## 🔝 Top 10 gastos del mes")

    if kpis["top10_gastos"] is not None:
        st.dataframe(kpis["top10_gastos"], width="stretch")
    else:
        st.info("No se pudo calcular el Top 10 de gastos. Revisa que exista una columna de montos de gasto.")


    # ---------- 8) Pregúntale a tus finanzas ----------
    st.markdown("## 🧠 Pregúntale a tus finanzas")

    st.write(
        "Escribe una pregunta en lenguaje natural sobre los datos de este mes. "
        "Ejemplos:\n"
        "- ¿Cuánto gastamos en RR.HH. este mes?\n"
        "- ¿Qué porcentaje del gasto total corresponde a Operativo?\n"
        "- ¿Quién es la persona con más viáticos?\n"
        "- ¿El mes fue superavitario o deficitario?"
    )

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


