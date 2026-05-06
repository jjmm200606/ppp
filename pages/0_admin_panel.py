# pages/0_admin_panel.py
import streamlit as st
from lib.utils import require_login, apply_theme, page_header, kpi_cards, money, section_header
from lib.patterns.facade import AccountingFacade
from lib.chatbot import render_chatbot_admin

st.set_page_config(page_title="Admin", layout="wide")
apply_theme()
require_login()

# ── Guard: solo admin ─────────────────────────────────────────────
if not st.session_state.get("is_admin"):
    st.error("Acceso denegado. Esta sección es solo para administradores.")
    st.stop()

page_header("Panel de Administración", "Vista global de todos los usuarios y sus operaciones.")

facade = AccountingFacade(user_id=0)

# ── KPIs globales ─────────────────────────────────────────────────
k = facade.admin_kpis_globales()
kpi_cards([
    {"label": "Ingresos totales",   "value": money(k["ingresos"]),    "color": "#4ade80"},
    {"label": "Costo total",        "value": money(k["costo"]),       "color": "#fb923c"},
    {"label": "Gastos totales",     "value": money(k["gastos"]),      "color": "#f87171"},
    {"label": "Utilidad global",    "value": money(k["utilidad"]),    "color": "#e8530a"},
    {"label": "Usuarios activos",   "value": str(int(k["usuarios"])), "color": "#818cf8"},
])

# ── Chatbot admin ─────────────────────────────────────────────────
render_chatbot_admin()


st.divider()

# ── Resumen por usuario ───────────────────────────────────────────
section_header("Resumen por usuario")

import pandas as pd
import plotly.express as px

usuarios = facade.admin_resumen_usuarios()
if not usuarios:
    st.info("No hay usuarios registrados.")
else:
    df_u = pd.DataFrame(usuarios)
    df_u["margen_%"] = df_u.apply(
        lambda r: round(float(r["utilidad"]) / float(r["ingresos"]) * 100, 1) if float(r["ingresos"]) > 0 else 0.0, axis=1
    ).astype(float)
    df_u = df_u.rename(columns={
        "username": "Usuario", "ingresos": "Ingresos", "costo": "Costo",
        "gastos": "Gastos", "utilidad": "Utilidad",
        "carritos": "Carritos", "num_ventas": "Ventas",
    })

    col_tbl, col_chart = st.columns([3, 2])
    with col_tbl:
        st.dataframe(
            df_u[["Usuario", "Ingresos", "Costo", "Gastos", "Utilidad", "margen_%", "Carritos", "Ventas"]],
            hide_index=True, width='stretch',
        )
    with col_chart:
        if df_u["Utilidad"].sum() != 0:
            fig = px.bar(
                df_u.sort_values("Utilidad"), x="Utilidad", y="Usuario",
                orientation="h", color="Utilidad",
                color_continuous_scale=["#c0392b", "#e8530a", "#4ade80"],
                title="Utilidad por usuario",
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#ddd", coloraxis_showscale=False,
                xaxis=dict(gridcolor="#2a2a2a"), yaxis=dict(gridcolor="#2a2a2a"),
                margin=dict(t=40, b=10, l=10, r=10), title_font_color="#ddd",
            )
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Carritos de toda la plataforma ───────────────────────────────
section_header("Todos los carritos")

carritos = facade.admin_listar_carritos()
if not carritos:
    st.info("No hay carritos registrados.")
else:
    df_c = pd.DataFrame(carritos)
    df_c["margen_%"] = df_c.apply(
        lambda r: round(float(r["utilidad"]) / float(r["ingresos"]) * 100, 1) if float(r["ingresos"]) > 0 else 0.0, axis=1
    ).astype(float)
    df_c["activo"] = df_c["active"].map({1: "Activo", 0: "Inactivo"})
    df_c = df_c.rename(columns={
        "username": "Usuario", "name": "Carrito", "location": "Ubicación",
        "ingresos": "Ingresos", "costo": "Costo",
        "gastos": "Gastos", "utilidad": "Utilidad",
    })
    st.dataframe(
        df_c[["Usuario", "Carrito", "Ubicación", "activo", "Ingresos", "Costo", "Gastos", "Utilidad", "margen_%"]],
        hide_index=True, width='stretch',
    )

    # Gráfico top carritos
    if len(df_c) > 1:
        fig2 = px.bar(
            df_c.sort_values("Utilidad").tail(10),
            x="Utilidad", y="Carrito", orientation="h",
            color="Usuario",
            title="Top carritos por utilidad",
            labels={"Utilidad": "Utilidad ($)"},
        )
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ddd", legend=dict(orientation="h"),
            xaxis=dict(gridcolor="#2a2a2a"), yaxis=dict(gridcolor="#2a2a2a"),
            margin=dict(t=40, b=10, l=10, r=10), title_font_color="#ddd",
        )
        st.plotly_chart(fig2, use_container_width=True)
