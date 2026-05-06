# pages/3_ventas.py
import streamlit as st
from datetime import date
from lib.utils import require_login, apply_theme, page_header, money
from lib.patterns.facade import AccountingFacade
from lib.chatbot import render_chatbot_inline
from lib.strategies.precio import PrecioFactory

apply_theme()
require_login()
page_header("Ventas por carrito", "Registra y consulta las ventas de cada carrito.")
render_chatbot_inline("ventas")

facade = AccountingFacade(user_id=st.session_state.get("user_id") or 0)

tab1, tab2, tab3 = st.tabs(["Listado", "Nueva venta", "Eliminar"])

with tab1:
    ventas = facade.listar_ventas()
    if not ventas:
        st.info("Aún no hay ventas registradas.")
    else:
        st.dataframe(ventas, hide_index=True, width='stretch')

with tab2:
    carritos = facade.listar_carritos(solo_activos=True)
    if not carritos:
        st.warning("Primero crea un carrito en *Carritos*.")
    else:
        cart_map = {c["name"]: c["id"] for c in carritos}
        with st.form("new_sale", clear_on_submit=True):
            cart = st.selectbox("Carrito *", list(cart_map.keys()))
            sale_date = st.date_input("Fecha", value=date.today())
            product = st.text_input("Producto", value="Perro caliente")
            qty = st.number_input("Cantidad vendida *", min_value=1.0, value=10.0, step=1.0)
            unit_price = st.number_input("Precio unitario *", min_value=0.0, value=2.5, step=0.1)
            unit_cost  = st.number_input("Costo unitario *",  min_value=0.0, value=1.0, step=0.1)
            notes = st.text_input("Notas")

            # preview de utilidad
            estrategia = PrecioFactory.get()
            utilidad_preview = estrategia.utilidad(qty, unit_price, unit_cost)
            st.caption(f"Utilidad estimada: {money(utilidad_preview)}")

            ok = st.form_submit_button("Registrar venta")

        if ok:
            facade.crear_venta(
                sale_date=str(sale_date),
                cart_id=cart_map[cart],
                product=product.strip() or "Perro caliente",
                qty=qty, unit_price=unit_price, unit_cost=unit_cost, notes=notes.strip()
            )
            st.success("Venta registrada")
            st.rerun()

with tab3:
    ventas_lista = facade.listar_ventas()
    if not ventas_lista:
        st.info("No hay ventas registradas para eliminar.")
    else:
        opciones = {
            f"#{v['id']} — {v['sale_date']} | {v['cart_name']} | {v['product']} | {money(v['importe'])}": v['id']
            for v in ventas_lista
        }
        sel = st.selectbox("Selecciona la venta a eliminar", list(opciones.keys()))
        st.warning("Esta acción no se puede deshacer.")
        if st.button("Eliminar venta", type="primary"):
            facade.eliminar_venta(opciones[sel])
            st.success("Venta eliminada correctamente.")
            st.rerun()
