from __future__ import annotations

import pandas as pd
import streamlit as st

from lib.chatbot import render_chatbot_inline
from lib.patterns.facade import AccountingFacade
from lib.utils import apply_theme, kpi_cards, money, page_header, require_login, section_header


st.set_page_config(page_title="Panel", layout="wide")
apply_theme()
require_login()

facade = AccountingFacade(user_id=st.session_state.get("user_id") or 0)

page_header("Panel – Resumen general", "Vista global de ingresos, costos, gastos y utilidad.")

# KPIs principales
k = facade.kpis()
kpi_cards([
    {"label": "Ingresos",        "value": money(k.get("ingresos", 0.0)), "color": "#4ade80"},
    {"label": "Costo de ventas", "value": money(k.get("costo",    0.0)), "color": "#fb923c"},
    {"label": "Gastos",          "value": money(k.get("gastos",   0.0)), "color": "#f87171"},
    {"label": "Utilidad neta",   "value": money(k.get("utilidad", 0.0)), "color": "#e8530a"},
])

st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

tab_resumen = st.tabs(["Resumen"])[0]

with tab_resumen:
    section_header("Top carritos por utilidad")
    rows = facade.top_carritos_utilidad()
    if not rows:
        st.info("Aún no hay carritos o movimientos.")
    else:
        df_top = pd.DataFrame(rows).rename(columns={
            "id": "ID",
            "name": "Carrito",
            "location": "Ubicación",
            "ingresos": "Ingresos",
            "costo": "Costo",
            "gastos": "Gastos",
            "utilidad": "Utilidad",
        })
        st.dataframe(df_top, hide_index=True, width="stretch")

    ventas = facade.listar_ventas()
    gastos = facade.listar_gastos()

    st.divider()
    section_header("Estado rápido del negocio")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Ventas registradas", len(ventas))
    with col_b:
        st.metric("Gastos registrados", len(gastos))
    with col_c:
        margen = (k["utilidad"] / k["ingresos"] * 100) if k.get("ingresos", 0) > 0 else 0.0
        st.metric("Margen neto", f"{margen:.1f}%")

    if ventas:
        ultimas = pd.DataFrame(ventas).head(10).rename(columns={
            "sale_date": "Fecha",
            "cart_name": "Carrito",
            "product": "Producto",
            "qty": "Cantidad",
            "importe": "Importe",
            "utilidad": "Utilidad",
        })
        st.divider()
        section_header("Últimas ventas")
        st.dataframe(
            ultimas[["Fecha", "Carrito", "Producto", "Cantidad", "Importe", "Utilidad"]],
            hide_index=True,
            width="stretch",
        )

render_chatbot_inline("panel")
