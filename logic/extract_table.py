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

    return parsed
