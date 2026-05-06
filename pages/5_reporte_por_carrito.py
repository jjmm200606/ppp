# pages/5_reporte_por_carrito.py
import streamlit as st
from datetime import date
from lib.utils import require_login, apply_theme, page_header, kpi_cards, money, section_header
from lib.patterns.facade import AccountingFacade
from lib.chatbot import render_chatbot_inline

apply_theme()
require_login()
page_header("Reporte por carrito", "Análisis de ingresos, costos y utilidad en un rango de fechas.")

facade = AccountingFacade(user_id=st.session_state.get("user_id") or 0)
carts = facade.listar_carritos()
if not carts:
    st.info("No hay carritos registrados.")
else:
    cart_map = {c["name"]: c["id"] for c in carts}
    c1, c2 = st.columns(2)
    with c1:
        cart = st.selectbox("Carrito", list(cart_map.keys()))
    with c2:
        start = st.date_input("Desde", value=date.today().replace(day=1))
        end   = st.date_input("Hasta", value=date.today())

    res = facade.resumen_por_carrito(cart_id=cart_map[cart], start=str(start), end=str(end))
    ventas = facade.detalle_ventas_carrito(cart_id=cart_map[cart], start=str(start), end=str(end))
    gastos = facade.detalle_gastos_carrito(cart_id=cart_map[cart], start=str(start), end=str(end))

    top_ventas_txt = "  (sin ventas registradas en este rango)"
    if ventas:
        top_ventas_txt = "\n".join(
            (
                f"  - {v['sale_date']} | {v['product']} | qty {v['qty']} | "
                f"importe {money(v.get('importe', 0))} | "
                f"costo {money(v.get('costo', 0))} | "
                f"utilidad {money(float(v.get('importe', 0) or 0) - float(v.get('costo', 0) or 0))}"
            )
            for v in ventas[:12]
        )

    top_gastos_txt = "  (sin gastos registrados en este rango)"
    if gastos:
        top_gastos_txt = "\n".join(
            f"  - {g['expense_date']} | {g['category']} | {g['description']} | {money(g['amount'])}"
            for g in gastos[:12]
        )

    extra_context = f"""
Página: Reporte por carrito
Carrito seleccionado: {cart}
Rango consultado: desde {start} hasta {end}
Ingresos del carrito en el rango: {money(res['ingresos'])}
Costo de ventas del carrito en el rango: {money(res['costo'])}
Gastos del carrito en el rango: {money(res['gastos'])}
Utilidad neta del carrito en el rango: {money(res['utilidad'])}

DETALLE RELEVANTE DE VENTAS DEL CARRITO:
{top_ventas_txt}

DETALLE RELEVANTE DE GASTOS DEL CARRITO:
{top_gastos_txt}

Responde tomando como prioridad este carrito y este rango de fechas.
"""
    render_chatbot_inline(
        "reporte_carrito",
        extra_context=extra_context,
        context_scope=f"{cart_map[cart]}|{start}|{end}",
    )

    section_header(f"Resultados · {cart}")
    kpi_cards([
        {"label": "Ingresos",        "value": money(res["ingresos"]), "color": "#4ade80"},
        {"label": "Costo de ventas", "value": money(res["costo"]),    "color": "#fb923c"},
        {"label": "Gastos",          "value": money(res["gastos"]),   "color": "#f87171"},
        {"label": "Utilidad neta",   "value": money(res["utilidad"]), "color": "#e8530a"},
    ])

    st.markdown("---")
    section_header("Detalle de ventas")
    st.dataframe(ventas, hide_index=True, width='stretch')

    section_header("Detalle de gastos")
    st.dataframe(gastos, hide_index=True, width='stretch')
