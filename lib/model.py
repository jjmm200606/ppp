# lib/model.py  — Fases 3-4-5-6 CRISP-ML(Q): Engineering, Evaluation, Deployment & Monitoring
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from lib.ml import preparar_datos_ventas, features_target, resumen_preparacion

# ── Constantes ────────────────────────────────────────────────────
MIN_DIAS_PARA_ENTRENAR = 14
_MODELS_DIR = Path(__file__).parent / "models"
_MODELS_DIR.mkdir(exist_ok=True)


def _model_path(user_id: int) -> Path:
    return _MODELS_DIR / f"model_user_{user_id}.joblib"


def _meta_path(user_id: int) -> Path:
    return _MODELS_DIR / f"meta_user_{user_id}.json"


def _hash_ventas(ventas: list[dict]) -> str:
    """Hash del conjunto de ventas — cambia si se agregan o borran registros."""
    resumen = f"{len(ventas)}_{sum(v.get('id', i) for i, v in enumerate(ventas))}"
    return hashlib.md5(resumen.encode()).hexdigest()[:12]


# ════════════════════════════════════════════════════════════════════
# Fase 5 — Deployment: guardar y cargar modelo
# ════════════════════════════════════════════════════════════════════

def guardar_modelo(resultado: dict, user_id: int, hash_datos: str) -> None:
    """Persiste el modelo entrenado y sus metadatos en disco."""
    import joblib
    joblib.dump(resultado["modelo"], _model_path(user_id))
    meta = {
        "hash_datos":      hash_datos,
        "mae":             resultado.get("mae"),
        "rmse":            resultado.get("rmse"),
        "r2":              resultado.get("r2"),
        "mae_por_fold":    resultado.get("mae_por_fold"),
        "rmse_por_fold":   resultado.get("rmse_por_fold"),
        "r2_por_fold":     resultado.get("r2_por_fold"),
        "eval_fechas":     resultado.get("eval_fechas"),
        "eval_real":       resultado.get("eval_real"),
        "eval_predicho":   resultado.get("eval_predicho"),
        "residuos":        resultado.get("residuos"),
        "importancias":    resultado.get("importancias"),
        "feature_names":   resultado.get("feature_names"),
        "resumen_datos":   resultado.get("resumen_datos"),
        "entrenado_en":    datetime.now(timezone.utc).isoformat(),
    }
    _meta_path(user_id).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def cargar_modelo(user_id: int) -> Optional[dict]:
    """Carga el modelo y metadatos desde disco. Devuelve None si no existe."""
    import joblib
    mp = _model_path(user_id)
    ep = _meta_path(user_id)
    if not mp.exists() or not ep.exists():
        return None
    meta = json.loads(ep.read_text(encoding="utf-8"))
    modelo = joblib.load(mp)
    return {**meta, "modelo": modelo}


# ════════════════════════════════════════════════════════════════════
# Fase 6 — Monitoring: detectar drift y decidir si reentrenar
# ════════════════════════════════════════════════════════════════════

def estado_monitoreo(user_id: int, ventas: list[dict]) -> dict:
    """
    Evalúa si el modelo necesita reentrenamiento.
    Devuelve un dict con: necesita_reentrenar, motivo, ultimo_entrenamiento, r2_actual.
    """
    hash_actual = _hash_ventas(ventas)
    ep = _meta_path(user_id)

    if not ep.exists():
        return {"necesita_reentrenar": True, "motivo": "Sin modelo previo",
                "ultimo_entrenamiento": None, "r2_actual": None,
                "hash_actual": hash_actual, "hash_guardado": None}

    meta = json.loads(ep.read_text(encoding="utf-8"))
    hash_guardado = meta.get("hash_datos")
    r2_actual     = meta.get("r2")
    entrenado_en  = meta.get("entrenado_en")

    # Motivo 1: datos nuevos desde el último entrenamiento
    if hash_actual != hash_guardado:
        return {"necesita_reentrenar": True, "motivo": "Datos nuevos detectados",
                "ultimo_entrenamiento": entrenado_en, "r2_actual": r2_actual,
                "hash_actual": hash_actual, "hash_guardado": hash_guardado}

    # Motivo 2: R² por debajo del umbral mínimo
    if r2_actual is not None and r2_actual < 0.30:
        return {"necesita_reentrenar": True, "motivo": f"R² bajo ({r2_actual:.3f} < 0.30)",
                "ultimo_entrenamiento": entrenado_en, "r2_actual": r2_actual,
                "hash_actual": hash_actual, "hash_guardado": hash_guardado}

    return {"necesita_reentrenar": False, "motivo": "Modelo vigente",
            "ultimo_entrenamiento": entrenado_en, "r2_actual": r2_actual,
            "hash_actual": hash_actual, "hash_guardado": hash_guardado}



def entrenar_modelo(ventas: list[dict]) -> Optional[dict]:
    """
    Entrena un RandomForestRegressor con los datos de ventas.
    Devuelve un dict con el modelo, métricas y metadatos,
    o None si no hay suficientes datos.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

    df = preparar_datos_ventas(ventas)
    if df is None:
        return None

    dias_con_datos = int((df["total_dia"] > 0).sum())
    if dias_con_datos < MIN_DIAS_PARA_ENTRENAR:
        return None

    X, y, feature_names = features_target(df)

    # ── Validación temporal (TimeSeriesSplit) ─────────────────────
    tscv = TimeSeriesSplit(n_splits=3)
    maes, rmses, r2s = [], [], []
    # Para curva real vs predicho (último fold)
    y_real_eval, y_pred_eval, fechas_eval = [], [], []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]
        if len(X_tr) < 5 or len(X_te) < 1:
            continue
        m = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        m.fit(X_tr, y_tr)
        preds = m.predict(X_te)
        maes.append(mean_absolute_error(y_te, preds))
        rmses.append(root_mean_squared_error(y_te, preds))
        r2s.append(r2_score(y_te, preds))
        # Guardar último fold para visualización
        y_real_eval = y_te.tolist()
        y_pred_eval = preds.tolist()
        fechas_eval = df["fecha"].iloc[test_idx].dt.strftime("%Y-%m-%d").tolist()

    # ── Entrenar modelo final con todos los datos ─────────────────
    modelo_final = RandomForestRegressor(n_estimators=150, random_state=42, n_jobs=-1)
    modelo_final.fit(X, y)

    # ── Importancia de variables ──────────────────────────────────
    importancias = dict(zip(feature_names, modelo_final.feature_importances_.tolist()))

    # ── Residuos (real - predicho) en training completo ──────────
    y_train_pred = modelo_final.predict(X)
    residuos = (y - y_train_pred).tolist()

    resumen = resumen_preparacion(df)

    return {
        "modelo":          modelo_final,
        "feature_names":   feature_names,
        "df_preparado":    df,
        # Métricas CV
        "mae":             round(float(np.mean(maes)),  2) if maes  else None,
        "rmse":            round(float(np.mean(rmses)), 2) if rmses else None,
        "r2":              round(float(np.mean(r2s)),   3) if r2s   else None,
        "mae_por_fold":    [round(v, 2) for v in maes],
        "rmse_por_fold":   [round(v, 2) for v in rmses],
        "r2_por_fold":     [round(v, 3) for v in r2s],
        # Evaluación visual
        "eval_fechas":     fechas_eval,
        "eval_real":       y_real_eval,
        "eval_predicho":   y_pred_eval,
        "residuos":        residuos,
        # Importancia
        "importancias":    importancias,
        "resumen_datos":   resumen,
    }


def predecir_proximos_dias(resultado_modelo: dict, n_dias: int = 30) -> pd.DataFrame:
    """
    Genera predicciones para los próximos n_dias.
    Devuelve DataFrame con: fecha, prediccion, intervalo_bajo, intervalo_alto.
    """
    modelo        = resultado_modelo["modelo"]
    feature_names = resultado_modelo["feature_names"]
    df_hist       = resultado_modelo["df_preparado"]

    ultima_fecha  = df_hist["fecha"].max()
    ultima_serie  = df_hist["total_dia"].values.tolist()

    predicciones = []
    for i in range(1, n_dias + 1):
        fecha = ultima_fecha + pd.Timedelta(days=i)

        # Variables de calendario
        fila = {
            "dia_semana":    fecha.dayofweek,
            "mes":           fecha.month,
            "semana_anio":   fecha.isocalendar()[1],
            "dia_anio":      fecha.dayofyear,
            "es_fin_semana": int(fecha.dayofweek >= 5),
            "lag_1":         ultima_serie[-1] if ultima_serie else 0,
            "lag_7":         ultima_serie[-7] if len(ultima_serie) >= 7 else 0,
            "media_7d":      float(np.mean(ultima_serie[-7:]))  if ultima_serie else 0,
            "media_30d":     float(np.mean(ultima_serie[-30:])) if ultima_serie else 0,
            "tendencia":     0.0,
        }
        if "media_7d" in fila and "media_30d" in fila:
            fila["tendencia"] = fila["media_7d"] - fila["media_30d"]

        X_pred = np.array([[fila[f] for f in feature_names]])

        # Predicción por árbol individual para intervalo de confianza
        preds_arboles = np.array([t.predict(X_pred)[0] for t in modelo.estimators_])
        pred_media    = max(0.0, float(preds_arboles.mean()))
        pred_std      = float(preds_arboles.std())

        predicciones.append({
            "fecha":           fecha.date(),
            "prediccion":      round(pred_media, 2),
            "intervalo_bajo":  round(max(0.0, pred_media - pred_std), 2),
            "intervalo_alto":  round(pred_media + pred_std, 2),
        })

        # Agregar predicción a la serie para los siguientes lags
        ultima_serie.append(pred_media)

    return pd.DataFrame(predicciones)


def insights_del_modelo(resultado_modelo: dict, predicciones: pd.DataFrame) -> list[dict]:
    """
    Genera una lista de insights de texto listos para guardar en knowledge_base.
    """
    insights = []
    mae  = resultado_modelo.get("mae")
    rmse = resultado_modelo.get("rmse")
    res  = resultado_modelo.get("resumen_datos", {})

    # Calidad del modelo
    if mae is not None:
        insights.append({
            "category": "Modelo predictivo",
            "title":    "Precisión del modelo (MAE / RMSE)",
            "content":  (
                f"El modelo de predicción de ventas tiene un error absoluto medio (MAE) de ${mae:,.2f} "
                f"y un error cuadrático medio (RMSE) de ${rmse:,.2f}. "
                f"Fue entrenado con {res.get('filas', 0)} días de historial "
                f"({res.get('dias_con_datos', 0)} días con ventas reales)."
            ),
        })

    # Proyección próximos 7 días
    prox_7  = predicciones.head(7)
    total_7 = prox_7["prediccion"].sum()
    dia_top = prox_7.loc[prox_7["prediccion"].idxmax()]
    insights.append({
        "category": "Modelo predictivo",
        "title":    "Proyección próximos 7 días",
        "content":  (
            f"Se proyectan ventas totales de ${total_7:,.2f} en los próximos 7 días. "
            f"El día con mayor proyección es {dia_top['fecha']} con ${dia_top['prediccion']:,.2f}."
        ),
    })

    # Proyección próximos 30 días
    total_30   = predicciones["prediccion"].sum()
    promedio_d = predicciones["prediccion"].mean()
    insights.append({
        "category": "Modelo predictivo",
        "title":    "Proyección próximos 30 días",
        "content":  (
            f"Se proyectan ventas totales de ${total_30:,.2f} en los próximos 30 días, "
            f"con un promedio diario proyectado de ${promedio_d:,.2f}."
        ),
    })

    # Comparación historico vs proyección
    prom_hist = res.get("promedio_diario", 0)
    if prom_hist > 0:
        diff_pct = ((promedio_d - prom_hist) / prom_hist * 100)
        tendencia_txt = "al alza" if diff_pct > 2 else ("a la baja" if diff_pct < -2 else "estable")
        insights.append({
            "category": "Modelo predictivo",
            "title":    "Tendencia proyectada vs histórico",
            "content":  (
                f"El promedio histórico diario es ${prom_hist:,.2f}. "
                f"La proyección de los próximos 30 días es ${promedio_d:,.2f} por día, "
                f"lo que indica una tendencia {tendencia_txt} ({diff_pct:+.1f}%)."
            ),
        })

    return insights
