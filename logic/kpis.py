import pandas as pd
from typing import Dict, Any


def calcular_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula KPIs financieros para el dashboard InterBM, pensado para el
    reporte a socios, usando la estructura real de la planilla.

    Columnas esperadas (con nombres similares / equivalentes):
      - TIPO DE GASTO     -> tipo_de_gasto, tipo de gasto, etc.
      - TIPO DE INGRESO   -> tipo_de_ingreso, tipo de ingreso, etc.
      - ESTADO
      - MONTO GASTO       -> monto_gasto, monto gasto, etc.
      - MONTO INGRESO     -> monto_ingreso, monto ingreso, etc.
      - DESCRIPCION

    Devuelve un dict con:

      - columnas: nombres detectados
      - ingresos:
          - total
          - por_tipo (dict {tipo_ingreso: monto})
      - gastos:
          - total
          - por_categoria (dict {tipo_gasto: monto})
          - pendientes:
              - total
              - cantidad
              - detalle (lista de dicts)
      - salud_financiera:
          - saldo_neto
          - ratio_gastos_ingresos
      - top_gastos: lista de dicts (top 10 egresos por monto)
    """

    df = df.copy()

    # ---------------------------------------------------------
    # 1) Detección robusta de columnas clave
    # ---------------------------------------------------------
    def _normalize_name(s: str) -> str:
        """Normaliza nombres: minúsculas, sin espacios, sin guiones bajos."""
        return s.lower().replace(" ", "").replace("_", "")

    # Mapa de nombre_normalizado -> nombre_original
    norm_map = {_normalize_name(c): c for c in df.columns}

    def find_col(candidates) -> str | None:
        """
        Busca una columna por lista de patrones.
        - Normaliza patterns y columnas (lower, sin espacios ni '_')
        - Intenta match exacto y luego por substring.
        """
        if df.empty:
            return None

        # 1) Intenta match exacto normalizado
        for pattern in candidates:
            norm_pat = _normalize_name(pattern)
            if norm_pat in norm_map:
                return norm_map[norm_pat]

        # 2) Intenta como substring
        for pattern in candidates:
            norm_pat = _normalize_name(pattern)
            for col_norm, col_orig in norm_map.items():
                if norm_pat in col_norm:
                    return col_orig

        return None

    # Montos
    col_monto_gasto = find_col(["monto gasto", "monto_gasto"])
    col_monto_ingreso = find_col(["monto ingreso", "monto_ingreso"])

    # Tipos / categorías
    col_tipo_gasto = find_col(["tipo de gasto", "tipo_gasto", "tipo gasto"])
    col_tipo_ingreso = find_col(["tipo de ingreso", "tipo_ingreso", "tipo ingreso"])

    # Estado y descripción
    col_estado = find_col(["estado"])
    col_descripcion = find_col(["descripcion", "descripción"])

    # ---------------------------------------------------------
    # 2) Normalizar tipos numéricos y texto
    # ---------------------------------------------------------
    if col_monto_gasto and col_monto_gasto in df.columns:
        df[col_monto_gasto] = pd.to_numeric(df[col_monto_gasto], errors="coerce")
    if col_monto_ingreso and col_monto_ingreso in df.columns:
        df[col_monto_ingreso] = pd.to_numeric(df[col_monto_ingreso], errors="coerce")

    text_cols = [col_tipo_gasto, col_tipo_ingreso, col_estado, col_descripcion]
    for c in text_cols:
        if c and c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    # ---------------------------------------------------------
    # 3) Totales simples
    # ---------------------------------------------------------
    total_ingresos = 0.0
    total_gastos = 0.0

    if col_monto_ingreso and col_monto_ingreso in df.columns:
        total_ingresos = float(df[col_monto_ingreso].sum(skipna=True))

    if col_monto_gasto and col_monto_gasto in df.columns:
        total_gastos = float(df[col_monto_gasto].sum(skipna=True))

    # ---------------------------------------------------------
    # 4) Ingresos por tipo (TIPO DE INGRESO)
    # ---------------------------------------------------------
    ingresos_por_tipo: dict[str, float] = {}
    if (
        col_monto_ingreso
        and col_tipo_ingreso
        and col_monto_ingreso in df.columns
        and col_tipo_ingreso in df.columns
    ):
        ingresos_por_tipo = (
            df.groupby(col_tipo_ingreso)[col_monto_ingreso]
            .sum()
            .sort_values(ascending=False)
            .to_dict()
        )

    # ---------------------------------------------------------
    # 5) Gastos por categoría (TIPO DE GASTO)
    # ---------------------------------------------------------
    gastos_por_categoria: dict[str, float] = {}
    if (
        col_monto_gasto
        and col_tipo_gasto
        and col_monto_gasto in df.columns
        and col_tipo_gasto in df.columns
    ):
        gastos_por_categoria = (
            df.groupby(col_tipo_gasto)[col_monto_gasto]
            .sum()
            .sort_values(ascending=False)
            .to_dict()
        )

    # ---------------------------------------------------------
    # 6) Gastos pendientes (ESTADO contiene "pend")
    # ---------------------------------------------------------
    total_gastos_pendientes = 0.0
    cantidad_gastos_pendientes = 0
    detalle_gastos_pendientes: list[dict[str, Any]] = []

    if (
        col_estado
        and col_monto_gasto
        and col_estado in df.columns
        and col_monto_gasto in df.columns
    ):
        mask_pend = df[col_estado].str.lower().str.contains("pend", na=False)
        pendientes_df = df[mask_pend].copy()

        if not pendientes_df.empty:
            total_gastos_pendientes = float(pendientes_df[col_monto_gasto].sum(skipna=True))
            cantidad_gastos_pendientes = int(len(pendientes_df))

            columnas_detalle: list[str] = []

            if col_descripcion and col_descripcion in pendientes_df.columns:
                columnas_detalle.append(col_descripcion)

            if col_tipo_gasto and col_tipo_gasto in pendientes_df.columns:
                if col_tipo_gasto not in columnas_detalle:
                    columnas_detalle.append(col_tipo_gasto)

            if col_estado and col_estado in pendientes_df.columns:
                if col_estado not in columnas_detalle:
                    columnas_detalle.append(col_estado)

            columnas_detalle.append(col_monto_gasto)

            detalle_gastos_pendientes = pendientes_df[columnas_detalle].to_dict(
                orient="records"
            )

    # ---------------------------------------------------------
    # 7) Salud financiera
    # ---------------------------------------------------------
    saldo_neto = total_ingresos - total_gastos
    ratio_gastos_ingresos = total_gastos / total_ingresos if total_ingresos > 0 else None

    # ---------------------------------------------------------
    # 8) Top 10 gastos (por MONTO GASTO)
    # ---------------------------------------------------------
    top_gastos: list[dict[str, Any]] = []
    if col_monto_gasto and col_monto_gasto in df.columns:
        df_gastos = df.dropna(subset=[col_monto_gasto])
        if not df_gastos.empty:
            df_gastos = df_gastos.sort_values(col_monto_gasto, ascending=False).head(10)

            columnas_top: list[str] = []
            if col_descripcion and col_descripcion in df_gastos.columns:
                columnas_top.append(col_descripcion)
            if col_tipo_gasto and col_tipo_gasto in df_gastos.columns:
                if col_tipo_gasto not in columnas_top:
                    columnas_top.append(col_tipo_gasto)
            columnas_top.append(col_monto_gasto)

            top_gastos = df_gastos[columnas_top].to_dict(orient="records")

    # ---------------------------------------------------------
    # 9) Resultado estructurado
    # ---------------------------------------------------------
    return {
        "columnas": {
            "col_monto_gasto": col_monto_gasto,
            "col_monto_ingreso": col_monto_ingreso,
            "col_tipo_gasto": col_tipo_gasto,
            "col_tipo_ingreso": col_tipo_ingreso,
            "col_estado": col_estado,
            "col_descripcion": col_descripcion,
        },
        "ingresos": {
            "total": total_ingresos,
            "por_tipo": ingresos_por_tipo,
        },
        "gastos": {
            "total": total_gastos,
            "por_categoria": gastos_por_categoria,
            "pendientes": {
                "total": total_gastos_pendientes,
                "cantidad": cantidad_gastos_pendientes,
                "detalle": detalle_gastos_pendientes,
            },
        },
        "salud_financiera": {
            "saldo_neto": saldo_neto,
            "ratio_gastos_ingresos": ratio_gastos_ingresos,
        },
        "top_gastos": top_gastos,
    }
