"""Build a cleaned pandas DataFrame from the LLM output dict.

This module focuses on deterministic cleaning and type conversions.
"""
from typing import Dict, Any, List
import pandas as pd


def build_clean_dataframe(clean_dict: Dict[str, List[Any]]) -> pd.DataFrame:
    headers = clean_dict.get("headers", [])
    rows = clean_dict.get("rows", [])

    # Fallbacks when headers are missing
    if not headers:
        # If there are no rows, we cannot infer headers
        if not rows:
            raise ValueError("No se recibieron encabezados desde el LLM.")

        # Heurística 1: if the first row looks like header names (mostly non-numeric strings)
        def looks_like_header(row: List[Any]) -> bool:
            non_empty = [str(x).strip() for x in row if str(x).strip() != ""]
            if not non_empty:
                return False
            # if majority of cells contain letters (not numbers), assume header
            lettery = sum(1 for v in non_empty if any(c.isalpha() for c in v))
            return lettery >= max(1, len(non_empty) // 2)

        if rows and looks_like_header(rows[0]) and len(rows) > 1:
            # Promote first row to headers, drop from rows
            headers = [str(x).strip() or f"Unnamed_Column_{i+1}" for i, x in enumerate(rows[0])]
            rows = rows[1:]
        else:
            # Fallback: synthesize generic column names based on max row length
            max_cols = max((len(r) for r in rows), default=0)
            headers = [f"col_{i+1}" for i in range(max_cols)]

    if not rows:
        return pd.DataFrame(columns=headers)

    df = pd.DataFrame(rows, columns=headers)

    # Normalize strings and replace garbage values
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"#REF!": None, "#N/A": None, "-----": None, "": None})

    # Detect amount-like columns using only these keys (important)
    amount_keys = ["monto", "saldo", "ingreso", "total"]
    posibles_montos = [
        c for c in df.columns if any(k in c.lower() for k in amount_keys)
    ]

    # Convert amount columns: remove currency symbols and thousands separators
    for col in posibles_montos:
        serie = df[col].astype(str)
        serie = serie.str.replace("$", "", regex=False).str.replace(" ", "", regex=False)
        # Remove dots used as thousands separator but keep decimal comma
        serie = serie.str.replace(".", "", regex=False)
        serie = serie.str.replace(",", ".", regex=False)
        df[col] = pd.to_numeric(serie, errors="coerce")

    # Detect date-like columns by these keys
    date_keys = ["fecha", "dia"]
    posibles_fechas = [c for c in df.columns if any(k in c.lower() for k in date_keys)]
    for col in posibles_fechas:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    return df
