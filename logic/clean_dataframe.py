"""
Deterministic cleaner for messy Google Sheets tables.
Extracts the main movement table and builds a clean DataFrame.
"""

import pandas as pd
import re
from typing import List, Dict, Any


# -----------------------------------------------------------
# Utility functions
# -----------------------------------------------------------

def _clean_cell(v: Any) -> str:
    """Normalize a cell from Google Sheets."""
    if v is None:
        return ""
    s = str(v).strip()

    # Remove common garbage values
    if s in ("#REF!", "#N/A", "-", "--", "---", "nan", "NaN"):
        return ""

    # Normalize currency like "$2.500.000"
    if s.startswith("$"):
        s = s[1:]
    if s.startswith("-$"):
        s = "-" + s[2:]

    # Remove thousand separators
    s = s.replace(".", "")

    # Replace decimal comma with dot
    s = s.replace(",", ".")

    return s.strip()


def _is_numeric_like(s: str) -> bool:
    if not isinstance(s, str):
        return False
    s = s.strip().replace(".", "").replace(",", "")
    return s.lstrip("-").isdigit()


# -----------------------------------------------------------
# 1. Extract MAIN TABLE from raw Google Sheets matrix
# -----------------------------------------------------------

def extract_main_table(matrix: List[List[str]]) -> Dict[str, Any]:
    """
    Detect header row and extract consecutive movement rows.
    Returns:
    {
        "headers": [...],
        "rows": [...]
    }
    """

    # ---------- Find header row ----------
    header_idx = None
    for i, row in enumerate(matrix):
        if not row:
            continue

        first = str(row[0]).strip().lower()
        if first in ("nº", "no", "no.", "n°"):
            header_idx = i
            break

        # Alternative: row containing many text cells (likely a header)
        non_empty = [c for c in row if str(c).strip() != ""]
        if non_empty:
            letters = sum(any(ch.isalpha() for ch in str(c)) for c in non_empty)
            if letters >= max(1, len(non_empty)//2):
                header_idx = i
                break

    if header_idx is None:
        return {"headers": [], "rows": []}

    raw_header = matrix[header_idx]
    headers = [h.strip() if h.strip() != "" else f"Unnamed_{i+1}"
               for i, h in enumerate(raw_header)]

    # Remove trailing empty headers
    while headers and headers[-1].startswith("Unnamed"):
        headers.pop()

    # ---------- Extract body BELOW the header ----------
    rows = []
    for r in matrix[header_idx + 1:]:

        if not r or all(str(c).strip() == "" for c in r):
            continue  # skip empty, but DO NOT stop — sheet may contain gaps

        first = _clean_cell(r[0])

        # If first cell is not numeric, the table ended
        if first and not _is_numeric_like(first):
            break

        cleaned = [_clean_cell(c) for c in r[:len(headers)]]
        rows.append(cleaned)

    return {"headers": headers, "rows": rows}


# -----------------------------------------------------------
# 2. Convert to DataFrame and normalize column types
# -----------------------------------------------------------

def build_clean_dataframe(clean: Dict[str, Any]) -> pd.DataFrame:
    if not clean or not clean.get("headers"):
        return pd.DataFrame()

    df = pd.DataFrame(clean["rows"], columns=clean["headers"])

    # Normalize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("utf-8")
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )

    # Detect monto columns
    monto_cols = [c for c in df.columns if "monto" in c or "gasto" in c or "ingreso" in c]

    for col in monto_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(r"[^\d\.\-]", "", regex=True)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Detect dates
    date_cols = [c for c in df.columns if "fecha" in c]

    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    return df
