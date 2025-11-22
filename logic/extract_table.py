# logic/extract_table.py
"""LLM-driven extraction of the main table from a raw sheet matrix."""

from typing import Any, Dict, List
import json

from services.gemini import get_gemini_model
from logic.clean_dataframe import clean_tabular_data


def llm_extract_table(raw_matrix: List[List[Any]]) -> Dict[str, Any]:
    """
    Usa Gemini para detectar la tabla principal dentro de la matriz cruda
    obtenida desde Google Sheets y devolver un dict con:

        {
          "headers": [...],
          "rows": [...]
        }

    Si la respuesta viene vacía, aplica fallback clean_tabular_data().
    """

    if not raw_matrix:
        raise ValueError("llm_extract_table: la matriz de Google Sheets está vacía.")

    model = get_gemini_model()

    prompt = f"""
Eres un asistente experto en hojas de cálculo y limpieza de datos tabulares.

Te entrego el contenido COMPLETO de una hoja de cálculo de contabilidad mensual
de un club deportivo, como una matriz (lista de filas). Cada fila es una lista
de celdas (strings).

La hoja puede contener:
- Resúmenes y totales en las primeras filas.
- Una tabla principal con movimientos de gasto e ingreso (una fila por movimiento).
- Celdas vacías, "#REF!", "#N/A", "-----", etc.

TU TAREA:
1. Identificar la TABLA PRINCIPAL de movimientos (no los resúmenes).
2. Tomar la fila de encabezados de esa tabla y normalizar los nombres:
   - en minúsculas
   - sin tildes
   - espacios -> guion_bajo
3. Mantener solo las filas de la tabla principal (una fila por movimiento).
4. NO conviertas montos a número ni fechas a datetime; deja los valores como strings.
5. Devuelve EXCLUSIVAMENTE un JSON válido con el siguiente formato EXACTO:

{{
  "headers": ["columna1", "columna2", ...],
  "rows": [
    ["valor_row_1_col_1", "valor_row_1_col_2", ...],
    ["valor_row_2_col_1", "valor_row_2_col_2", ...]
  ]
}}

No agregues ningún texto fuera de ese JSON.

Aquí está la matriz (lista de filas):
{raw_matrix}
"""

    response = model.generate_content(prompt)
    text = response.text or ""

    # --- Primer intento: parsear JSON directo ---
    parsed = None
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None

    # --- Segundo intento: extraer el bloque {...} ---
    if parsed is None:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            json_str = text[start:end]
            parsed = json.loads(json_str)
        except Exception:
            parsed = None

    # --- Si parseo falla completamente ---
    if parsed is None:
        raise ValueError(
            "llm_extract_table: Gemini no devolvió JSON válido.\n\n"
            f"Respuesta cruda:\n{text}"
        )

    if not isinstance(parsed, dict):
        raise ValueError(
            f"llm_extract_table: el JSON devuelto no es un objeto dict.\nJSON:\n{parsed}"
        )

    headers = parsed.get("headers", [])
    rows = parsed.get("rows", [])

    # Si viene vacío, usamos el fallback determinista
    if (not headers) and (not rows):
        fallback = clean_tabular_data(raw_matrix)
        return fallback

    if not isinstance(headers, list) or not isinstance(rows, list):
        raise ValueError(
            f"llm_extract_table: el JSON devuelto no tiene 'headers' o 'rows' válidos.\nJSON:\n{parsed}"
        )

    return {
        "headers": headers,
        "rows": rows,
    }
