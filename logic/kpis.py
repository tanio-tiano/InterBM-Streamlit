import pandas as pd
from typing import Dict, Any


def calcular_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula KPIs financieros a partir de un DataFrame limpio.

    Se asume que df viene de build_clean_dataframe, con nombres de columnas
    parecidos a:
      - "monto_gasto", "monto_ingreso"
      - "tipo_gasto", "tipo_ingreso"
      - "descripcion"
      - "responsable_gestion" (o similar)

    Devuelve un dict con:
      - col_gasto, col_ingreso, col_tipo_gasto, col_tipo_ingreso,
        col_descripcion, col_responsable
      - total_gastos, total_ingresos, balance_neto
      - gasto_por_tipo (Series)
      - gasto_rrhh, detalle_rrhh (Series)
      - gasto_viaticos, detalle_viaticos (Series)
      - gasto_inversion, detalle_inversion (Series)
      - gasto_inscripciones, detalle_inscripciones (Series)
      - top10_gastos (DataFrame)
    """

    df = df.copy()

    # ---------------------------------------------------------
    # 1) Detección de columnas clave por nombre
    # ---------------------------------------------------------
    def find_col(candidates):
        for pattern in candidates:
            for c in df.columns:
                if pattern in c.lower():
                    return c
        return None

    col_gasto = find_col(["monto_gasto", "gasto"])
    col_ingreso = find_col(["monto_ingreso", "ingreso"])
    col_tipo_gasto = find_col(["tipo_gasto", "tipo de gasto", "tipo gasto"])
    col_tipo_ingreso = find_col(["tipo_ingreso", "tipo de ingreso", "tipo ingreso"])
    col_descripcion = find_col(["descripcion", "descripción"])
    col_responsable = find_col(["responsable", "responsable_gestion"])

    # ---------------------------------------------------------
    # 2) Forzar tipos correctos (numéricos y texto)
    # ---------------------------------------------------------
    if col_gasto and col_gasto in df.columns:
        df[col_gasto] = pd.to_numeric(df[col_gasto], errors="coerce")
    if col_ingreso and col_ingreso in df.columns:
        df[col_ingreso] = pd.to_numeric(df[col_ingreso], errors="coerce")

    # columnas de texto que usamos con .str.contains o como índice
    text_cols = [col_tipo_gasto, col_tipo_ingreso, col_descripcion, col_responsable]
    for c in text_cols:
        if c and c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    # ---------------------------------------------------------
    # 3) Totales globales
    # ---------------------------------------------------------
    total_gastos = 0.0
    total_ingresos = 0.0

    if col_gasto and col_gasto in df.columns:
        total_gastos = float(pd.to_numeric(df[col_gasto], errors="coerce").sum())

    if col_ingreso and col_ingreso in df.columns:
        total_ingresos = float(pd.to_numeric(df[col_ingreso], errors="coerce").sum())

    balance_neto = total_ingresos - total_gastos

    # ---------------------------------------------------------
    # 4) Estructura del gasto por TIPO DE GASTO
    # ---------------------------------------------------------
    gasto_por_tipo = None
    if col_gasto and col_tipo_gasto and col_gasto in df.columns and col_tipo_gasto in df.columns:
        gasto_por_tipo = (
            df.groupby(col_tipo_gasto)[col_gasto]
            .sum()
            .sort_values(ascending=False)
        )

    # ---------------------------------------------------------
    # 5) RR.HH.
    # ---------------------------------------------------------
    gasto_rrhh = 0.0
    detalle_rrhh = None
    if col_gasto and col_tipo_gasto and col_gasto in df.columns and col_tipo_gasto in df.columns:
        df_rrhh = df[df[col_tipo_gasto].str.contains("rr", case=False, na=False)]
        gasto_rrhh = float(pd.to_numeric(df_rrhh[col_gasto], errors="coerce").sum())

        if col_descripcion and col_descripcion in df_rrhh.columns:
            detalle_rrhh = (
                df_rrhh.groupby(col_descripcion)[col_gasto]
                .sum()
                .sort_values(ascending=False)
            )

    # ---------------------------------------------------------
    # 6) Viáticos
    # ---------------------------------------------------------
    gasto_viaticos = 0.0
    detalle_viaticos = None
    if col_gasto and col_tipo_gasto and col_gasto in df.columns and col_tipo_gasto in df.columns:
        df_via = df[df[col_tipo_gasto].str.contains("viatico", case=False, na=False)]
        if not df_via.empty:
            gasto_viaticos = float(pd.to_numeric(df_via[col_gasto], errors="coerce").sum())
            if col_responsable and col_responsable in df_via.columns:
                detalle_viaticos = (
                    df_via.groupby(col_responsable)[col_gasto]
                    .sum()
                    .sort_values(ascending=False)
                )

    # ---------------------------------------------------------
    # 7) Inversiones
    # ---------------------------------------------------------
    gasto_inversion = 0.0
    detalle_inversion = None
    if col_gasto and col_tipo_gasto and col_gasto in df.columns and col_tipo_gasto in df.columns:
        df_inv = df[df[col_tipo_gasto].str.contains("inversion", case=False, na=False)]
        if not df_inv.empty:
            gasto_inversion = float(pd.to_numeric(df_inv[col_gasto], errors="coerce").sum())
            if col_descripcion and col_descripcion in df_inv.columns:
                detalle_inversion = (
                    df_inv.groupby(col_descripcion)[col_gasto]
                    .sum()
                    .sort_values(ascending=False)
                )

    # ---------------------------------------------------------
    # 8) Inscripciones
    # ---------------------------------------------------------
    gasto_inscripciones = 0.0
    detalle_inscripciones = None
    if col_gasto and col_tipo_gasto and col_gasto in df.columns and col_tipo_gasto in df.columns:
        df_ins = df[df[col_tipo_gasto].str.contains("inscrip", case=False, na=False)]
        if not df_ins.empty:
            gasto_inscripciones = float(pd.to_numeric(df_ins[col_gasto], errors="coerce").sum())
            if col_descripcion and col_descripcion in df_ins.columns:
                detalle_inscripciones = (
                    df_ins.groupby(col_descripcion)[col_gasto]
                    .sum()
                    .sort_values(ascending=False)
                )

    # ---------------------------------------------------------
    # 9) Top 10 gastos del mes
    # ---------------------------------------------------------
    top10_gastos = None
    if col_gasto and col_gasto in df.columns:
        # Ordenamos por monto_gasto descendente
        df_gastos = df.copy()
        df_gastos[col_gasto] = pd.to_numeric(df_gastos[col_gasto], errors="coerce")
        df_gastos = df_gastos.dropna(subset=[col_gasto])
        if not df_gastos.empty:
            top10_gastos = df_gastos.sort_values(col_gasto, ascending=False).head(10)

    # ---------------------------------------------------------
    # 10) Resultado
    # ---------------------------------------------------------
    return {
        "col_gasto": col_gasto,
        "col_ingreso": col_ingreso,
        "col_tipo_gasto": col_tipo_gasto,
        "col_tipo_ingreso": col_tipo_ingreso,
        "col_descripcion": col_descripcion,
        "col_responsable": col_responsable,
        "total_gastos": total_gastos,
        "total_ingresos": total_ingresos,
        "balance_neto": balance_neto,
        "gasto_por_tipo": gasto_por_tipo,
        "gasto_rrhh": gasto_rrhh,
        "detalle_rrhh": detalle_rrhh,
        "gasto_viaticos": gasto_viaticos,
        "detalle_viaticos": detalle_viaticos,
        "gasto_inversion": gasto_inversion,
        "detalle_inversion": detalle_inversion,
        "gasto_inscripciones": gasto_inscripciones,
        "detalle_inscripciones": detalle_inscripciones,
        "top10_gastos": top10_gastos,
    }
