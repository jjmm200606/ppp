# lib/ml.py  — Fase 3 CRISP-DM: Preparación de datos para modelos predictivos
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Optional


def preparar_datos_ventas(ventas: list[dict]) -> Optional[pd.DataFrame]:
    """
    Recibe la lista cruda de ventas (listar_ventas()) y devuelve un DataFrame
    diario enriquecido con variables para el modelo predictivo.

    Columnas del resultado:
    - fecha          : date
    - total_dia      : suma de importe del día
    - num_ventas     : cantidad de registros ese día
    - dia_semana     : 0=lunes … 6=domingo
    - mes            : 1-12
    - semana_anio    : 1-53
    - dia_anio       : 1-366
    - es_fin_semana  : 1 si sábado o domingo, 0 si no
    - lag_1          : ventas del día anterior
    - lag_7          : ventas de hace 7 días
    - media_7d       : media móvil de los últimos 7 días
    - media_30d      : media móvil de los últimos 30 días
    - tendencia      : diferencia rolling(7) vs rolling(30) — indica si va al alza
    """
    if not ventas:
        return None

    df = pd.DataFrame(ventas)
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["importe"]   = pd.to_numeric(df["importe"], errors="coerce").fillna(0)

    # ── Agregar por día ───────────────────────────────────────────
    diario = (
        df.groupby("sale_date")
        .agg(total_dia=("importe", "sum"), num_ventas=("importe", "count"))
        .reset_index()
        .sort_values("sale_date")
    )

    # Rellenar días sin ventas (para series continuas)
    fecha_min = diario["sale_date"].min()
    fecha_max = diario["sale_date"].max()
    rango     = pd.date_range(start=fecha_min, end=fecha_max, freq="D")
    diario    = diario.set_index("sale_date").reindex(rango, fill_value=0).reset_index()
    diario.rename(columns={"index": "fecha"}, inplace=True)

    # ── Variables de calendario ───────────────────────────────────
    diario["dia_semana"]   = diario["fecha"].dt.dayofweek          # 0=lun … 6=dom
    diario["mes"]          = diario["fecha"].dt.month
    diario["semana_anio"]  = diario["fecha"].dt.isocalendar().week.astype(int)
    diario["dia_anio"]     = diario["fecha"].dt.dayofyear
    diario["es_fin_semana"] = (diario["dia_semana"] >= 5).astype(int)

    # ── Lags (valores pasados) ────────────────────────────────────
    diario["lag_1"] = diario["total_dia"].shift(1).fillna(0)
    diario["lag_7"] = diario["total_dia"].shift(7).fillna(0)

    # ── Medias móviles ────────────────────────────────────────────
    diario["media_7d"]  = (
        diario["total_dia"].shift(1).rolling(window=7,  min_periods=1).mean().fillna(0)
    )
    diario["media_30d"] = (
        diario["total_dia"].shift(1).rolling(window=30, min_periods=1).mean().fillna(0)
    )

    # ── Tendencia: media_7d vs media_30d ─────────────────────────
    diario["tendencia"] = (diario["media_7d"] - diario["media_30d"]).fillna(0)

    return diario


def preparar_datos_gastos(gastos: list[dict]) -> Optional[pd.DataFrame]:
    """
    Igual que preparar_datos_ventas pero para gastos.
    Columnas: fecha, total_dia, num_gastos + variables de calendario + lags + medias.
    """
    if not gastos:
        return None

    df = pd.DataFrame(gastos)
    df["expense_date"] = pd.to_datetime(df["expense_date"])
    df["amount"]       = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    diario = (
        df.groupby("expense_date")
        .agg(total_dia=("amount", "sum"), num_gastos=("amount", "count"))
        .reset_index()
        .sort_values("expense_date")
    )

    fecha_min = diario["expense_date"].min()
    fecha_max = diario["expense_date"].max()
    rango     = pd.date_range(start=fecha_min, end=fecha_max, freq="D")
    diario    = diario.set_index("expense_date").reindex(rango, fill_value=0).reset_index()
    diario.rename(columns={"index": "fecha"}, inplace=True)

    diario["dia_semana"]    = diario["fecha"].dt.dayofweek
    diario["mes"]           = diario["fecha"].dt.month
    diario["semana_anio"]   = diario["fecha"].dt.isocalendar().week.astype(int)
    diario["es_fin_semana"] = (diario["dia_semana"] >= 5).astype(int)
    diario["lag_1"]         = diario["total_dia"].shift(1).fillna(0)
    diario["media_7d"]      = diario["total_dia"].shift(1).rolling(7,  min_periods=1).mean().fillna(0)
    diario["media_30d"]     = diario["total_dia"].shift(1).rolling(30, min_periods=1).mean().fillna(0)

    return diario


def features_target(df: pd.DataFrame, col_target: str = "total_dia"):
    """
    Separa el DataFrame preparado en X (variables) e y (objetivo).
    X incluye solo las columnas numéricas útiles para el modelo.
    """
    FEATURES = [
        "dia_semana", "mes", "semana_anio", "dia_anio",
        "es_fin_semana", "lag_1", "lag_7", "media_7d", "media_30d", "tendencia",
    ]
    cols_disponibles = [c for c in FEATURES if c in df.columns]
    X = df[cols_disponibles].values
    y = df[col_target].values
    return X, y, cols_disponibles


def resumen_preparacion(df: pd.DataFrame) -> dict:
    """Devuelve estadísticas básicas del DataFrame preparado."""
    return {
        "filas":          len(df),
        "fecha_inicio":   str(df["fecha"].min().date()),
        "fecha_fin":      str(df["fecha"].max().date()),
        "dias_con_datos": int((df["total_dia"] > 0).sum()),
        "dias_sin_datos": int((df["total_dia"] == 0).sum()),
        "promedio_diario": round(float(df["total_dia"].mean()), 2),
        "maximo_dia":      round(float(df["total_dia"].max()), 2),
        "minimo_dia":      round(float(df[df["total_dia"] > 0]["total_dia"].min()), 2)
                           if (df["total_dia"] > 0).any() else 0,
    }
