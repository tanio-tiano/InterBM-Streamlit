"""
Deterministic cleaner for messy Google Sheets tables.
Extracts the main movement table and builds a clean DataFrame.
"""

import pandas as pd
import unicodedata
from typing import List, Dict, Any


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------

def _normalize_str(s: str) -> str:
    """Lowercase, remove accents, collapse spaces."""
    if s is None:
        return ""
    s = str(s)
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.split())


def _clean_cell(v: Any) -> str:
    """Normalize a cell from Google Sheets to a cleaned string."""
    if v is None:
        return ""
    s = str(v).strip()

    # Remove garbage tokens
    if s in ("#REF!", "#N/A", "-", "--", "---", "nan", "NaN"):
        return ""

    return s


def _is_numeric_like(s: str) -> bool:
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    if s == "":
        return False
    # Remove currency symbols and thousand separators
    s = s.replace("$", "").replace(" ", "")
    s = s.replace(".", "").replace(",", "")
    return s.lstrip("-").isdigit()


# -----------------------------------------------------------
# 1. Extract MAIN TABLE from raw Google Sheets matrix
# -----------------------------------------------------------

def extract_main_table(matrix: List[List[Any]]) -> Dict[str, Any]:
    """
    Detects the main financial movement table in the messy sheet.

    Strategy:
    - Find the last row that contains "tipo de gasto" and "monto gasto".
    - Use that row as header.
    - Collect all subsequent rows that have at least one non-empty cell
      in the header-length window.
    """

    if not matrix:
        return {"headers": [], "rows": []}

    # ---------- Find header row by keywords ----------
    header_idx = None
    header_candidates = []

    for i, row in enumerate(matrix):
        row_str = " ".join(_normalize_str(c) for c in row)
        if "tipo de gasto" in row_str and "monto gasto" in row_str:
            header_candidates.append(i)

    if header_candidates:
        header_idx = header_candidates[-1]  # use LAST occurrence
    else:
        # Fallback heuristic: first row that contains "tipo de gasto"
        for i, row in enumerate(matrix):
            row_str = " ".join(_normalize_str(c) for c in row)
            if "tipo de gasto" in row_str:
                header_idx = i
                break

    if header_idx is None:
        # No recognizable header
        return {"headers": [], "rows": []}

    raw_header = matrix[header_idx]

    # Trim trailing completely empty cells in header
    eff_len = len(raw_header)
    while eff_len > 0 and str(raw_header[eff_len - 1]).strip() == "":
        eff_len -= 1

    if eff_len == 0:
        return {"headers": [], "rows": []}

    headers = []
    seen = {}
    for idx in range(eff_len):
        h = str(raw_header[idx]).strip()
        if h == "":
            h = f"Unnamed_{idx+1}"
        base = h
        count = seen.get(base, 0)
        name = base if count == 0 else f"{base}_{count+1}"
        seen[base] = count + 1
        headers.append(name)

    # ---------- Collect rows below header ----------
    rows: List[List[str]] = []

    for r in matrix[header_idx + 1:]:
        if not r:
            continue

        window = r[:eff_len]
        cleaned = [_clean_cell(c) for c in window]

        # Skip rows that are completely empty in the header window
        if all(c == "" for c in cleaned):
            continue

        rows.append(cleaned)

    return {"headers": headers, "rows": rows}


# -----------------------------------------------------------
# 2. Build clean DataFrame
# -----------------------------------------------------------

def build_clean_dataframe(clean: Dict[str, Any]) -> pd.DataFrame:
    """
    Build a clean DataFrame from the dict:
      {
        "headers": [...],
        "rows": [...]
      }
    - Normalizes column names.
    - Cleans currency strings.
    - Converts monto columns to numeric.
    - Converts fecha columns to datetime.
    """

    headers = clean.get("headers") or []
    rows = clean.get("rows") or []

    if not headers:
        return pd.DataFrame()

    if not rows:
        # No movement rows
        return pd.DataFrame(columns=headers)

    df = pd.DataFrame(rows, columns=headers)

    # Normalize column names
    norm_cols = []
    for c in df.columns:
        c_norm = _normalize_str(c)
        c_norm = c_norm.replace(" ", "_")
        c_norm = "".join(ch for ch in c_norm if ch.isalnum() or ch == "_")
        c_norm = c_norm.strip("_")
        if c_norm == "":
            c_norm = "col"
        norm_cols.append(c_norm)

    # Ensure uniqueness
    final_cols = []
    seen = {}
    for col in norm_cols:
        base = col
        count = seen.get(base, 0)
        name = base if count == 0 else f"{base}_{count+1}"
        seen[base] = count + 1
        final_cols.append(name)

    df.columns = final_cols

    # General string cleaning
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"#REF!": None, "#N/A": None, "-----": None, "": None})

    # Detect monto columns (avoid tipo_* and descripcion)
    monto_cols = []
    for c in df.columns:
        name = c.lower()
        if any(k in name for k in ["monto", "gasto", "ingreso", "total", "saldo"]):
            if not name.startswith("tipo") and "descripcion" not in name:
                monto_cols.append(c)

    for col in monto_cols:
        serie = (
            df[col]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(".", "", regex=False)   # thousands
            .str.replace(",", ".", regex=False)  # decimal comma
        )
        df[col] = pd.to_numeric(serie, errors="coerce").fillna(0)

    # Detect fecha columns
    fecha_cols = [c for c in df.columns if "fecha" in c.lower() or "dia" in c.lower()]

    for col in fecha_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    return df
