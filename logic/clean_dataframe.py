"""Build a cleaned pandas DataFrame from the LLM output dict.

This module focuses on deterministic cleaning and type conversions.
"""
from typing import Dict, Any, List
import pandas as pd
import json


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


def clean_tabular_data(spreadsheet_data: List[List[Any]]) -> Dict[str, List[Any]]:
    """
    Identifica la tabla principal en una matriz de celdas de hoja de cálculo,
    limpia sus encabezados y filas, y la devuelve en formato {'headers':..., 'rows':...}.

    This implements the legacy cleaning function provided by the user.
    """

    def clean_cell(cell_value: Any) -> str:
        # Normalize to string
        if cell_value is None:
            return ""
        if not isinstance(cell_value, str):
            # If it's numeric or other, convert to str and strip
            cell_value = str(cell_value)

        cleaned_value = cell_value.strip()

        # Handle errors and placeholders
        if cleaned_value in ["#REF!", "#N/A", "---", "--", "      -", "----------", "-"]:
            return ""

        # Monetary values: remove '$' and '.' thousands separators
        if cleaned_value.startswith('-$'):
            cleaned_value = '-' + cleaned_value[2:].replace('.', '').replace(',', '')
        elif cleaned_value.startswith('$'):
            cleaned_value = cleaned_value[1:].replace('.', '').replace(',', '')

        # Remove surrounding double quotes
        if cleaned_value.startswith('"') and cleaned_value.endswith('"'):
            cleaned_value = cleaned_value[1:-1]

        return cleaned_value

    headers: List[str] = []
    rows: List[List[str]] = []

    # Heuristic: header row appears at index 5 (0-based) in the example
    # but fall back to searching for a row that starts with 'Nº'
    header_index = None
    if len(spreadsheet_data) > 6 and any(str(c).strip().lower().startswith('nº') or str(c).strip().lower().startswith('no') for c in spreadsheet_data[6]):
        header_index = 6
    else:
        for i, row in enumerate(spreadsheet_data):
            if not row:
                continue
            first = str(row[0]).strip().lower()
            if first in ('nº', 'no', 'no.'):
                header_index = i
                break

    # Default to index 6 if not found but array long enough
    if header_index is None and len(spreadsheet_data) > 6:
        header_index = 6

    if header_index is None:
        return {"headers": [], "rows": []}

    header_raw = spreadsheet_data[header_index][:14]
    headers = [clean_cell(h) for h in header_raw]

    # Extract rows starting after header_index
    for i in range(header_index + 1, len(spreadsheet_data)):
        raw_row = spreadsheet_data[i]
        if not raw_row:
            continue
        current_row_sliced = raw_row[:14]
        cleaned_row = [clean_cell(cell) for cell in current_row_sliced]

        # First col must be numeric id
        first_col_value = cleaned_row[0]
        is_numeric_id = False
        if first_col_value:
            try:
                int(first_col_value)
                is_numeric_id = True
            except ValueError:
                is_numeric_id = False

        has_meaningful_data = (
            (len(cleaned_row) > 2 and cleaned_row[2] != "") or
            (len(cleaned_row) > 4 and cleaned_row[4] != "") or
            (len(cleaned_row) > 5 and cleaned_row[5] != "")
        )

        # Stop on explicit 'Total proyecto' marker
        if isinstance(first_col_value, str) and first_col_value.lower().startswith('total proyecto'):
            break

        if not any(cleaned_row):
            continue

        if is_numeric_id and has_meaningful_data:
            rows.append(cleaned_row)

    return {"headers": headers, "rows": rows}
