"""LLM-driven extraction of the main table from a raw sheet matrix."""
from typing import Dict, Any, List, Optional
import json
import re
import ast

from services.gemini import get_gemini_model


def llm_extract_table(raw_matrix: List[List[str]]) -> Dict[str, Any]:
    """Ask Gemini to detect the main table and return {'headers': [...], 'rows': [...]}.

    This function preserves the original prompt logic but delegates model access
    to services.gemini.get_gemini_model(). It raises ValueError when the model
    response cannot be parsed or lacks headers/rows.
    """
    if not raw_matrix:
        raise ValueError("La matriz de la hoja está vacía.")

    prompt_text = f"""
Eres un asistente experto en limpieza de datos tabulares.

Te entrego el contenido completo de una hoja de cálculo, en forma de matriz (lista de filas).
Cada fila es una lista de celdas (strings). Puede haber filas vacías, encabezados desordenados,
errores (#REF!, #N/A), valores con formato monetario como "$330.000", y bloques adicionales.

Tu tarea es identificar la TABLA PRINCIPAL que contiene los movimientos fila a fila y devolver
SOLO un JSON con el formato:
{{
  "headers": ["col1","col2",...],
  "rows": [["v1","v2",...], ...]
}}

Aquí viene la matriz (lista de listas):

{raw_matrix}
"""

    model = get_gemini_model()
    response = model.generate_content(prompt_text)
    content = response.text

    # Primary attempt: strict JSON
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = None

    def find_balanced_brace_substring(s: str, start_pos: int = 0) -> Optional[str]:
        """Find the first balanced {...} substring in s starting at start_pos.

        Returns the substring including the braces or None if not found.
        """
        for i in range(start_pos, len(s)):
            if s[i] == "{":
                depth = 0
                for j in range(i, len(s)):
                    if s[j] == "{":
                        depth += 1
                    elif s[j] == "}":
                        depth -= 1
                        if depth == 0:
                            return s[i : j + 1]
                # if we get here, braces didn't close for this opening; try next
        return None

    # Fallbacks: try to extract a JSON-like or Python-dict-like substring
    if parsed is None:
        # 1) Scan for any balanced brace JSON and try to json.loads
        candidate = find_balanced_brace_substring(content)
        if candidate:
            try:
                parsed = json.loads(candidate)
            except Exception:
                # try ast.literal_eval for Python dict literals (safer than exec)
                try:
                    parsed = ast.literal_eval(candidate)
                except Exception:
                    parsed = None

    if parsed is None:
        # 2) Look for assignments like "result = { ... }" or "return { ... }" inside the text
        m = re.search(r"(?:result|resultado)\s*=\s*\{", content, flags=re.IGNORECASE)
        if not m:
            m = re.search(r"return\s+\{", content, flags=re.IGNORECASE)
        if m:
            start = m.start()
            candidate = find_balanced_brace_substring(content, start_pos=start)
            if candidate:
                try:
                    parsed = ast.literal_eval(candidate)
                except Exception:
                    try:
                        parsed = json.loads(candidate)
                    except Exception:
                        parsed = None

    if parsed is None:
        # 3) Try to extract last balanced block (some LLMs append explanation then JSON)
        last_candidate = None
        idx = 0
        while True:
            cand = find_balanced_brace_substring(content, start_pos=idx)
            if not cand:
                break
            last_candidate = cand
            # move index past this candidate
            idx_pos = content.find(cand, idx)
            if idx_pos == -1:
                break
            idx = idx_pos + len(cand)

        if last_candidate:
            try:
                parsed = json.loads(last_candidate)
            except Exception:
                try:
                    parsed = ast.literal_eval(last_candidate)
                except Exception:
                    parsed = None

    if parsed is None:
        raise ValueError(f"No se pudo interpretar la respuesta del LLM como JSON. Respuesta cruda:\n{content}")

    if not isinstance(parsed, dict) or "headers" not in parsed or "rows" not in parsed:
        raise ValueError(f"El JSON devuelto por el LLM no contiene 'headers' o 'rows'. JSON:\n{parsed}")

    # If LLM returned empty result (no headers and no rows), try a deterministic
    # fallback that extracts a table directly from the raw matrix without calling the LLM.
    if isinstance(parsed, dict) and (not parsed.get("headers") and not parsed.get("rows")):
        fallback = _fallback_extract_from_matrix(raw_matrix)
        if fallback.get("headers") or fallback.get("rows"):
            return fallback

    return parsed


def _fallback_extract_from_matrix(matrix: List[List[str]]) -> Dict[str, Any]:
    """Deterministic extraction of a table from a raw sheet matrix.

    Heuristics implemented:
    - find a header row (look for 'Nº'/'No.' or a row of mostly text followed by a numeric-first row)
    - normalize header names, handle duplicate headers
    - extract consecutive data rows starting after the header where first column is numeric
    - clean common garbage values and currency formatting
    """
    def clean_cell(cell_value: Any) -> str:
        v = str(cell_value).strip()
        if v in ("#REF!", "#N/A", "-", "--", "---"):
            return ""
        if v.startswith("-$"):
            v = "-" + v[2:]
        if v.startswith("$"):
            v = v[1:]
        # remove thousands separators and normalize decimal comma
        v = v.replace(".", "").replace(",", ".")
        return v

    def is_numeric_string(s: str) -> bool:
        s_clean = s.strip().replace(".", "").replace(",", "")
        return s_clean.lstrip("-+").isdigit()

    header_row_idx = -1
    # Strategy: find row with first cell like 'Nº' or 'No.' OR a row with many letters
    for i, row in enumerate(matrix):
        if not row:
            continue
        first = str(row[0]).strip().lower()
        if first in ("nº", "no.", "no"):
            header_row_idx = i
            break
        # if row looks header-like (majority lettery) and next non-empty row starts numeric
        non_empty = [c for c in row if str(c).strip() != ""]
        if non_empty:
            lettery = sum(1 for c in non_empty if any(ch.isalpha() for ch in str(c)))
            next_row_num = False
            # find next non-empty row
            for j in range(i + 1, len(matrix)):
                if matrix[j] and any(str(x).strip() != "" for x in matrix[j]):
                    if is_numeric_string(str(matrix[j][0])):
                        next_row_num = True
                    break
            if lettery >= max(1, len(non_empty) // 2) and next_row_num:
                header_row_idx = i
                break

    if header_row_idx == -1:
        return {"headers": [], "rows": []}

    raw_header = matrix[header_row_idx]
    # compute effective header length trimming trailing empty cells
    eff_len = 0
    for k in range(len(raw_header) - 1, -1, -1):
        if str(raw_header[k]).strip() != "":
            eff_len = k + 1
            break
    if eff_len == 0:
        return {"headers": [], "rows": []}

    processed_headers = []
    seen = {}
    for idx in range(eff_len):
        h = str(raw_header[idx]).strip().replace('"', "")
        if h == "":
            h = f"Unnamed_Column_{idx+1}"
        base = h
        count = seen.get(base, 0)
        if count > 0:
            h = f"{base}_{count+1}"
        seen[base] = count + 1
        processed_headers.append(h)

    rows_out = []
    for r in matrix[header_row_idx + 1:]:
        if not r or all(str(c).strip() == "" for c in r):
            # skip empty rows but don't terminate immediately; allow continuation
            continue
        first = str(r[0]).strip()
        if first != "" and not is_numeric_string(first):
            # likely end of table
            break
        # build cleaned row of eff_len length
        cleaned = [clean_cell(r[i]) if i < len(r) else "" for i in range(eff_len)]
        rows_out.append(cleaned)

    return {"headers": processed_headers, "rows": rows_out}
