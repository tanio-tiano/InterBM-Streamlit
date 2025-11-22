"""Question-answering utilities that ask Gemini about a DataFrame.

This module serializes a DataFrame safely and constructs a prompt for Gemini
to answer natural language questions about the table.
"""
from typing import Any
import json
import pandas as pd

from services.gemini import get_gemini_model


def responder_pregunta_sobre_df(df: pd.DataFrame, pregunta: str) -> str:
    # Limit rows to avoid huge payloads
    df_sample = df.copy()
    max_rows = 80
    if len(df_sample) > max_rows:
        df_sample = df_sample.head(max_rows)

    # Convert datetime columns to ISO strings
    for col in df_sample.columns:
        if pd.api.types.is_datetime64_any_dtype(df_sample[col]):
            df_sample[col] = df_sample[col].dt.strftime("%Y-%m-%d")
        # Ensure serializable
        df_sample[col] = df_sample[col].astype(object)

    schema_info = [{"columna": col, "tipo_datos": str(df[col].dtype)} for col in df.columns]
    data_json = df_sample.to_dict(orient="records")

    prompt = f"""
Actúa como analista financiero de un club deportivo.
Tienes una tabla de movimientos financieros de UN mes.

Esquema de columnas:
{json.dumps(schema_info, ensure_ascii=False, indent=2)}

Muestra de filas (hasta {max_rows}):
{json.dumps(data_json, ensure_ascii=False)[:8000]}

Pregunta:
'''{pregunta}'''

Responde en español, de forma clara y breve.
"""

    model = get_gemini_model()
    response = model.generate_content(prompt)
    return response.text.strip()
