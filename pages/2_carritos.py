# pages/2_carritos.py
import streamlit as st
from lib.utils import require_login, apply_theme, page_header
from lib.patterns.facade import AccountingFacade
from lib.chatbot import render_chatbot_inline

apply_theme()
require_login()
page_header("Carritos", "Administra y consulta tus carritos activos.")
render_chatbot_inline("carritos")
facade = AccountingFacade(user_id=st.session_state.get("user_id") or 0)

tab1, tab2 = st.tabs(["Listado", "Nuevo carrito"])

with tab1:
    rows = facade.listar_carritos()
    st.dataframe(rows, hide_index=True, width='stretch')

with tab2:
    with st.form("new_cart"):
        name = st.text_input("Nombre del carrito *", placeholder="Carrito #1")
        location = st.text_input("Ubicación", placeholder="Parque Central")
        active = st.checkbox("Activo", value=True)
        submitted = st.form_submit_button("Guardar")
    if submitted:
        if not name.strip():
            st.error("El nombre es obligatorio")
        else:
            facade.crear_carrito(name=name, location=location, active=active)
            st.success("Carrito guardado")
            st.rerun()
