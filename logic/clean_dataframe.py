# logic/clean_dataframe.py

import pandas as pd
from typing import Dict, Any, List, Optional


def build_clean_dataframe(clean_dict: Dict[str, Any]) -> pd.DataFrame:
    """
    Construye un DataFrame limpio a partir del dict devuelto por Gemini.

    clean_dict debe tener el formato:
    {
      "headers": [...],
      "rows": [
        [...],
        ...
      ]
    }

    - Normaliza strings.
    - Limpia marcadores como #REF!, #N/A, -----, "".
    - Detecta columnas de montos y las convierte a numérico.
    - Detecta columnas de fecha y las convierte a datetime.
    """

    raw_headers: List[Any] = clean_dict.get("headers") or []
    rows: List[List[Any]] = clean_dict.get("rows") or []

    if not raw_headers:
        raise ValueError("build_clean_dataframe: 'headers' está vacío o no existe.")

    # ---------------------------------------------------------
    # 0) Normalizar y hacer ÚNICOS los headers
    # ---------------------------------------------------------
    headers: List[str] = []
    seen: dict[str, int] = {}

    for idx, h in enumerate(raw_headers):
        base = str(h).strip().lower().replace(" ", "_") if h is not None else ""
        if base == "":
            base = f"col_{idx+1}"

        count = seen.get(base, 0)
        if count == 0:
            name = base
        else:
            name = f"{base}_{count+1}"
        seen[base] = count + 1
        headers.append(name)

    # Si no hay filas, devolvemos DF vacío con las columnas ya normalizadas
    if not rows:
        return pd.DataFrame(columns=headers)

    df = pd.DataFrame(rows, columns=headers)

    # ---------------------------------------------------------
    # 1) Limpieza general de strings (columna por columna)
    # ---------------------------------------------------------
    replacements = {
        "#REF!": None,
        "#N/A": None,
        "-----": None,
        "": None,
    }

    for col in df.columns:
        # Todo a string + strip SOLO a nivel de serie
        df[col] = df[col].astype(str).str.strip()
        # Reemplazar marcadores por None (NaN al convertir)
        df[col] = df[col].replace(replacements)

    # ---------------------------------------------------------
    # 2) Detectar columnas de montos
    #    OJO: no queremos agarrar "tipo_gasto", "tipo_ingreso", etc.
    # ---------------------------------------------------------
    columnas_monto: List[str] = []
    for c in df.columns:
        name = c.lower()
        if any(key in name for key in ["monto", "saldo", "ingreso", "total"]):
            if not name.startswith("tipo") and "descripcion" not in name:
                columnas_monto.append(c)

    for col in columnas_monto:
        serie = (
            df[col]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(".", "", regex=False)   # separador de miles
            .str.replace(",", ".", regex=False)  # coma decimal -> punto
        )
        df[col] = pd.to_numeric(serie, errors="coerce")

    # ---------------------------------------------------------
    # 3) Detectar columnas de fecha
    # ---------------------------------------------------------
    columnas_fecha: List[str] = [
        c for c in df.columns
        if any(key in c.lower() for key in ["fecha", "dia"])
    ]

    for col in columnas_fecha:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    return df


# ==========================================================
#   HELPERS PARA TESTING (SIN IA / SIN GEMINI)
# ==========================================================

def clean_tabular_data(matrix: List[List[Any]]) -> Dict[str, Any]:
    """
    Extrae filas tipo tabla desde una matriz 2D (como la devuelta por Google Sheets).
    Versión heurística sin LLM, útil para tests locales.

    Retorna:
      {
        "headers": [...],
        "rows": [...]
      }
    """

    header_idx: Optional[int] = None
    max_nonempty = 0

    # Buscar la fila con más columnas no vacías
    for i, row in enumerate(matrix):
        non_empty = sum(1 for cell in row if str(cell).strip() != "")
        if non_empty > max_nonempty:
            max_nonempty = non_empty
            header_idx = i

    if header_idx is None:
        raise ValueError("clean_tabular_data: No se pudo detectar un encabezado válido.")

    headers = [str(h).strip() for h in matrix[header_idx]]

    # Recoger filas siguientes mientras no estén completamente vacías
    rows: List[List[Optional[str]]] = []
    for r in matrix[header_idx + 1:]:
        cleaned = [None if str(c).strip() == "" else str(c).strip() for c in r]
        if all(x is None for x in cleaned):
            break
        rows.append(cleaned)

    return {"headers": headers, "rows": rows}


def extract_main_table(matrix: List[List[Any]]) -> Dict[str, Any]:
    """
    Versión heurística NO LLM para detectar la tabla principal.
    Se usa solo para testing.

    Busca la fila con más "pinta" de encabezado (Nº, TIPO, GASTO, INGRESO, etc.),
    y toma lo que viene debajo como tabla.
    """

    header_keywords = [
        "Nº", "TIPO", "GASTO", "INGRESO", "ESTADO",
        "MONTO", "FECHA", "DESCRIPCION", "RESPONSABLE"
    ]

    best_match_row: Optional[List[Any]] = None
    best_score = 0

    for row in matrix:
        row_str = " ".join([str(c).upper() for c in row])
        score = sum(1 for k in header_keywords if k in row_str)
        if score > best_score:
            best_score = score
            best_match_row = row

    if best_match_row is None:
        raise ValueError("extract_main_table: No se encontró encabezado principal.")

    headers = [str(h).strip() if str(h).strip() != "" else None for h in best_match_row]

    start = matrix.index(best_match_row) + 1
    rows: List[List[Optional[str]]] = []

    for r in matrix[start:]:
        cleaned = [None if str(x).strip() == "" else str(x).strip() for x in r]
        if all(v is None for v in cleaned):
            break
        rows.append(cleaned)

    return {"headers": headers, "rows": rows}
