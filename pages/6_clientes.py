# pages/6_clientes.py
import streamlit as st
from lib.utils import require_login, apply_theme, page_header
from lib.patterns.facade import AccountingFacade
from lib.chatbot import render_chatbot_inline

apply_theme()
require_login()
page_header("Clientes", "Gestiona el directorio de clientes de tu negocio.")
render_chatbot_inline("clientes")
facade = AccountingFacade(user_id=st.session_state.get("user_id") or 0)

tab1, tab2 = st.tabs(["Listado", "Nuevo cliente"])

with tab1:
    rows = facade.listar_clientes()
    st.dataframe(rows, hide_index=True, width='stretch')

with tab2:
    with st.form("new_client"):
        name = st.text_input("Nombre *")
        email = st.text_input("Email")
        phone = st.text_input("Teléfono")
        submitted = st.form_submit_button("Guardar")
    if submitted:
        if not name.strip():
            st.error("El nombre es obligatorio")
        else:
            facade.crear_cliente(name=name, email=email, phone=phone)
            st.success("Cliente guardado")
            st.rerun()
