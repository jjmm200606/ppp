# pages/9_stock.py
import streamlit as st
from lib.utils import require_login, apply_theme, page_header, section_header
from lib.patterns.facade import AccountingFacade
from lib.chatbot import render_chatbot_inline

apply_theme()
require_login()
page_header("Inventario / Stock", "Controla los niveles de stock de tus productos.")
render_chatbot_inline("inventario")

facade = AccountingFacade(user_id=st.session_state.get("user_id") or 0)

# -------------------------------------------------------------------
# Alertas de bajo stock
# -------------------------------------------------------------------
bajos = facade.stock_bajo()
if bajos:
    st.error(f"{len(bajos)} producto(s) por debajo del stock mínimo")
    cols = st.columns(min(len(bajos), 4))
    for i, p in enumerate(bajos):
        with cols[i % 4]:
            st.markdown(f"""
            <div style="background:#2a1414;border:1px solid #c0392b;border-radius:10px;
                        padding:.8rem 1rem;text-align:center">
                <div style="font-size:.75rem;color:#e74c3c;text-transform:uppercase;
                            letter-spacing:.6px;margin-bottom:.3rem">Stock bajo</div>
                <div style="font-weight:700;color:#f1f1f1;font-size:1rem">{p['product']}</div>
                <div style="color:#e74c3c;font-size:.85rem;margin-top:.3rem">
                    {p['current_stock']} / mín {p['min_stock']} {p['unit']}
                </div>
                <div style="color:#aaa;font-size:.75rem;margin-top:.2rem">
                    Faltan <b style="color:#e8530a">{p['faltante']}</b> {p['unit']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("")
else:
    st.success("Todos los productos tienen stock suficiente")

st.markdown("---")

# -------------------------------------------------------------------
# Tabla completa de inventario
# -------------------------------------------------------------------
section_header("Estado del inventario")

items = facade.listar_stock()
if items:
    import pandas as pd
    df = pd.DataFrame(items)
    df["estado"] = df["bajo_stock"].map({1: "Bajo", 0: "OK"})
    df = df.rename(columns={
        "product": "Producto",
        "current_stock": "Stock actual",
        "min_stock": "Stock mínimo",
        "unit": "Unidad",
        "updated_at": "Última actualización",
        "estado": "Estado",
    })
    st.dataframe(
        df[["Producto", "Stock actual", "Stock mínimo", "Unidad", "Estado", "Última actualización"]],
        hide_index=True,
        width='stretch',
    )
else:
    st.info("Aún no tienes productos registrados en el inventario.")

st.markdown("---")

# -------------------------------------------------------------------
# Formulario agregar / actualizar producto
# -------------------------------------------------------------------
section_header("Agregar o actualizar producto")

with st.form("form_stock", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
    with col1:
        producto = st.text_input("Producto *", placeholder="Ej: Salchichas, Pan, Gas...")
    with col2:
        current = st.number_input("Stock actual", min_value=0.0, step=1.0, value=0.0)
    with col3:
        minimo = st.number_input("Stock mínimo", min_value=0.0, step=1.0, value=10.0)
    with col4:
        unidad = st.selectbox("Unidad", ["unidades", "kg", "litros", "paquetes", "bolsas", "cajas"])
    guardar = st.form_submit_button("Guardar", width='stretch')

if guardar:
    if not producto.strip():
        st.error("El nombre del producto es obligatorio.")
    else:
        try:
            facade.guardar_stock(
                product=producto,
                current_stock=current,
                min_stock=minimo,
                unit=unidad,
            )
            st.success(f"'{producto}' guardado correctamente.")
            st.rerun()
        except Exception as exc:
            st.error(f"Error al guardar: {exc}")

# -------------------------------------------------------------------
# Eliminar producto
# -------------------------------------------------------------------
if items:
    st.markdown("---")
    section_header("Eliminar producto")
    opciones = {f"{p['product']} ({p['current_stock']} {p['unit']})": p["id"] for p in items}
    sel = st.selectbox("Selecciona el producto a eliminar", list(opciones.keys()))
    if st.button("Eliminar", type="secondary"):
        facade.eliminar_stock(opciones[sel])
        st.success("Producto eliminado.")
        st.rerun()
