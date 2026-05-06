# pages/4_gastos.py
import streamlit as st
from datetime import date
from lib.utils import require_login, apply_theme, page_header
from lib.patterns.facade import AccountingFacade
from lib.chatbot import render_chatbot_inline

apply_theme()
require_login()
page_header("Gastos por carrito", "Registra y consulta los gastos operativos de cada carrito.")
render_chatbot_inline("gastos")

facade = AccountingFacade(user_id=st.session_state.get("user_id") or 0)
tab1, tab2 = st.tabs(["Listado", "Nuevo gasto"])

with tab1:
    rows = facade.listar_gastos()
    st.dataframe(rows, hide_index=True, width='stretch')

with tab2:
    carritos = facade.listar_carritos(solo_activos=True)
    if not carritos:
        st.warning("Primero crea un carrito en *Carritos*.")
    else:
        cart_map = {c["name"]: c["id"] for c in carritos}
        with st.form("new_expense", clear_on_submit=True):
            cart = st.selectbox("Carrito *", list(cart_map.keys()))
            expense_date = st.date_input("Fecha", value=date.today())
            category = st.selectbox("Categoría", ["Ingredientes","Gas","Hielo","Transporte","Comisiones","Otros"])
            description = st.text_input("Descripción")
            amount = st.number_input("Monto *", min_value=0.0, value=5.0, step=0.5)
            ok = st.form_submit_button("Registrar gasto")
        if ok:
            facade.crear_gasto(
                expense_date=str(expense_date),
                cart_id=cart_map[cart],
                category=category,
                description=description.strip(),
                amount=amount
            )
            st.success("Gasto registrado")
            st.rerun()
