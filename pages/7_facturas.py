# pages/7_facturas.py
import streamlit as st
from datetime import date
from typing import List, Tuple
from lib.utils import require_login, apply_theme, page_header, money
from lib.patterns.facade import AccountingFacade
from lib.chatbot import render_chatbot_inline

apply_theme()
require_login()
page_header("Facturas", "Emite y consulta facturas asociadas a clientes y carritos.")
render_chatbot_inline("facturas")
facade = AccountingFacade(user_id=st.session_state.get("user_id") or 0)

tab1, tab2 = st.tabs(["Listado", "Nueva"])

with tab1:
    rows = facade.listar_facturas()
    st.dataframe(rows, hide_index=True, width='stretch')

with tab2:
    clients = facade.listar_clientes()
    carts = facade.listar_carritos()
    if not clients:
        st.warning("Primero crea un cliente en *Clientes*.")
    else:
        client_map = {f"{c['name']} (#{c['id']})": c["id"] for c in clients}
        cart_map = {c['name']: c['id'] for c in carts} if carts else {}

        with st.form("new_invoice", clear_on_submit=True):
            client_label = st.selectbox("Cliente *", list(client_map.keys()))
            cart_label = st.selectbox("Carrito (opcional)", ["—"] + list(cart_map.keys()))
            invoice_date = st.date_input("Fecha", value=date.today())
            due_date = st.date_input("Vencimiento", value=date.today())
            st.markdown("**Ítems**")
            n_items = st.number_input("Cantidad de ítems", min_value=1, max_value=20, value=1, step=1)
            items: List[Tuple[str, float, float]] = []
            for i in range(int(n_items)):
                c1, c2, c3 = st.columns([5,2,2])
                with c1:
                    desc = st.text_input(f"Descripción {i+1}", key=f"desc_{i}")
                with c2:
                    qty = st.number_input(f"Cant. {i+1}", min_value=0.0, value=1.0, step=1.0, key=f"qty_{i}")
                with c3:
                    price = st.number_input(f"Precio {i+1}", min_value=0.0, value=0.0, step=0.5, key=f"price_{i}")
                items.append((desc, qty, price))

            submitted = st.form_submit_button("Guardar factura")

        if submitted:
            client_id = client_map[client_label]
            valid_items = [(desc.strip(), qty, price) for (desc, qty, price) in items if desc.strip() and qty > 0]
            if not valid_items:
                st.error("Agrega al menos un item con descripcion y cantidad mayor a cero.")
                st.stop()

            total = sum(q * p for (_, q, p) in valid_items)
            inv_id = facade.crear_factura(
                client_id=client_id,
                invoice_date=str(invoice_date),
                due_date=str(due_date),
                status="Pendiente",
                total=total,
                cart_id=cart_map.get(cart_label),
                items=valid_items,
            )
            st.success(f"Factura #{inv_id} guardada por {money(total)}")
            st.rerun()
