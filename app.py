# app.py
# Ejecuta en la terminal:
#   python -m streamlit run app.py
# python3.11 -m streamlit run app.py

from __future__ import annotations
from pathlib import Path
import streamlit as st

from lib.db import (
    validate_login,
    create_user,
    get_user_id,
    seed_basic_accounts_for_user,
    seed_knowledge_base_table,
    is_admin,
)
from lib.utils import money
from lib.patterns.facade import AccountingFacade
from lib.patterns.observer import add_global_observer, AuditObserver, CacheObserver
from lib.utils import apply_theme, kpi_cards, section_header
from lib.chatbot import render_chatbot_inline

# -------------------------------------------------------------------
# Configuración básica
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Contabilidad Hot Dogs",
    page_icon=":material/storefront:",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

# Observers globales (auditoría + limpieza de caché)
add_global_observer(AuditObserver())
add_global_observer(CacheObserver())

# Crear tablas adicionales si no existen
try:
    seed_knowledge_base_table()
except Exception:
    pass

# Estado de sesión
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user", None)
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("is_admin", False)

def _get_facade() -> AccountingFacade:
    return AccountingFacade(user_id=st.session_state.get("user_id") or 0)

# -------------------------------------------------------------------
# Barra lateral compartida (aparece en TODAS las páginas)
# -------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1.2rem 0 .6rem">
        <div style="font-size:1.6rem;font-weight:900;color:#e8530a;letter-spacing:-1px">HD</div>
        <div style="font-weight:800;color:var(--text-strong);font-size:1.1rem;letter-spacing:-.3px">Hot Dogs</div>
        <div style="color:var(--text-soft);font-size:.75rem;margin-top:2px">Sistema contable</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    if st.session_state.get("logged_in"):
        user = st.session_state.get("user") or ""
        st.markdown(f"""
        <div class="auth-note" style="background:rgba(232,83,10,.08);border:1px solid rgba(232,83,10,.24);
                    border-radius:10px;padding:.8rem 1rem;margin-bottom:1rem">
            <div style="color:var(--text-muted);font-size:.7rem;text-transform:uppercase;letter-spacing:.8px">Usuario activo</div>
            <div style="color:#e8530a;font-weight:700;font-size:1rem;margin-top:.3rem">{user}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Cerrar sesión", width='stretch'):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.user_id = None
            st.session_state.is_admin = False
            st.rerun()
    else:
        st.markdown("""
        <div class="auth-note" style="font-size:.85rem;color:var(--text-muted)">
            Inicia sesión desde la página principal.
        </div>
        """, unsafe_allow_html=True)

# -------------------------------------------------------------------
# Página principal (portada + login, o KPIs + navegación)
# -------------------------------------------------------------------
def home_page():

    def _login_logo_path() -> Path | None:
        base = Path(__file__).resolve().parent
        candidates = [
            base / "assets" / "login-logo.png",
            base / "assets" / "login-logo.webp",
            base / "assets" / "login-logo.jpg",
            base / "assets" / "ppp-logo.png",
            base / "docs" / "login-logo.png",
            base / "docs" / "ppp-logo.png",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _hero():
        pass

    _hero()

    if not st.session_state.get("logged_in") or not st.session_state.get("user_id"):
        st.markdown('<div class="auth-stage">', unsafe_allow_html=True)
        hero, card = st.columns([1.15, .95], gap="large")
        with hero:
            st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
            logo_path = _login_logo_path()
            if logo_path:
                st.markdown('<div style="margin-top:.15rem;max-width:520px">', unsafe_allow_html=True)
                st.image(str(logo_path), width=430)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div style="margin-top:.15rem" class="auth-brand-mark">HD</div>', unsafe_allow_html=True)
                st.markdown(
                    """
                    <div style="color:var(--text-strong);font-size:.86rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase">
                        Hot Dogs Contabilidad
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown(
                """
                <div style="height:.25rem"></div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)
        with card:
            st.markdown("""
            <div class="auth-login-card">
                <div style="text-align:center">
                    <div style="color:var(--accent);font-size:.78rem;font-weight:800;letter-spacing:.11em;text-transform:uppercase">
                        Acceso seguro
                    </div>
                    <div style="color:var(--text-strong);font-size:2rem;font-weight:900;margin-top:.35rem">
                        Bienvenido de nuevo
                    </div>
                    <p style="color:var(--text-muted);font-size:.95rem;margin:.7rem 0 0;line-height:1.6">
                        Accede a tu cuenta o crea una nueva para empezar a registrar tu operación.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            tabs = st.tabs(["Iniciar sesión", "Crear cuenta"])
            with tabs[0]:
                u = st.text_input("Usuario", key="login_u", placeholder="Ingresa tu usuario")
                p = st.text_input("Contraseña", type="password", key="login_p", placeholder="Ingresa tu contraseña")
                if st.button("Entrar", width='stretch'):
                    if validate_login(u, p):
                        st.session_state.logged_in = True
                        st.session_state.user = u
                        st.session_state.user_id = get_user_id(u)
                        st.session_state.is_admin = is_admin(u)
                        if st.session_state.user_id:
                            seed_basic_accounts_for_user(st.session_state.user_id)
                            try:
                                fcd = _get_facade()
                                fcd.generar_insights_automaticos()
                                from lib.model import (
                                    entrenar_modelo, predecir_proximos_dias, insights_del_modelo,
                                    guardar_modelo, cargar_modelo, estado_monitoreo, _hash_ventas,
                                )
                                uid    = st.session_state.user_id
                                ventas = fcd.listar_ventas()
                                estado = estado_monitoreo(uid, ventas)

                                if estado["necesita_reentrenar"]:
                                    resultado = entrenar_modelo(ventas)
                                    if resultado:
                                        hash_d = _hash_ventas(ventas)
                                        guardar_modelo(resultado, uid, hash_d)
                                else:
                                    resultado = cargar_modelo(uid)

                                if resultado:
                                    predicciones = predecir_proximos_dias(resultado, n_dias=30)
                                    nuevos_insights = insights_del_modelo(resultado, predicciones)
                                    fcd._execute(
                                        "DELETE FROM knowledge_base WHERE user_id=:u AND category='Modelo predictivo'",
                                        {"u": fcd._uid()},
                                    )
                                    for ins in nuevos_insights:
                                        fcd.agregar_conocimiento(**ins)
                                    st.session_state["predicciones_ml"]     = predicciones.to_dict("records")
                                    st.session_state["modelo_mae"]           = resultado.get("mae")
                                    st.session_state["modelo_rmse"]          = resultado.get("rmse")
                                    st.session_state["modelo_r2"]            = resultado.get("r2")
                                    st.session_state["modelo_importancias"]  = resultado.get("importancias")
                                    st.session_state["modelo_eval_fechas"]   = resultado.get("eval_fechas")
                                    st.session_state["modelo_eval_real"]     = resultado.get("eval_real")
                                    st.session_state["modelo_eval_pred"]     = resultado.get("eval_predicho")
                                    st.session_state["modelo_residuos"]      = resultado.get("residuos")
                                    st.session_state["modelo_mae_folds"]     = resultado.get("mae_por_fold")
                                    st.session_state["modelo_r2_folds"]      = resultado.get("r2_por_fold")
                                st.session_state["monitoreo_estado"] = estado
                            except Exception:
                                pass
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos.")
            with tabs[1]:
                nu = st.text_input("Nuevo usuario", key="reg_u", placeholder="Crea tu usuario")
                npw = st.text_input("Nueva contraseña", type="password", key="reg_p", placeholder="Crea tu contraseña")
                if st.button("Crear cuenta", width='stretch'):
                    if not nu or not npw:
                        st.warning("Completa usuario y contraseña.")
                    else:
                        ok = create_user(nu.strip(), npw)
                        if ok:
                            st.success("Cuenta creada. Ahora inicia sesión.")
                        else:
                            st.error("Ese usuario ya existe.")
            st.markdown("""
            <div class="auth-login-foot">
                Tus credenciales son privadas y cada cuenta mantiene sus propios datos.
            </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Usuario autenticado: KPIs + navegación rápida
    facade = _get_facade()
    k = facade.kpis()
    kpi_cards([
        {"label": "Ingresos",        "value": money(k.get("ingresos", 0.0)), "color": "#4ade80"},
        {"label": "Costo de ventas", "value": money(k.get("costo",    0.0)), "color": "#fb923c"},
        {"label": "Gastos",          "value": money(k.get("gastos",   0.0)), "color": "#f87171"},
        {"label": "Utilidad neta",   "value": money(k.get("utilidad", 0.0)), "color": "#e8530a"},
    ])

    st.divider()
    section_header("Navegación rápida")

    if st.session_state.get("is_admin"):
        st.markdown("""
        <style>
        [data-testid="stPageLink"]:first-of-type a {
            font-size: 1.05rem !important; font-weight: 700 !important;
            padding: .75rem 1.2rem !important;
            border: 1.5px solid rgba(232,83,10,.5) !important;
            background: rgba(232,83,10,.08) !important; color: #e8530a !important;
        }
        [data-testid="stPageLink"]:first-of-type a:hover {
            background: rgba(232,83,10,.18) !important; border-color: #e8530a !important;
        }
        </style>
        <div style="margin-bottom:.6rem">
            <div style="display:flex;align-items:center;gap:.5rem;color:#e8530a;
                        font-size:.7rem;text-transform:uppercase;letter-spacing:.8px;
                        font-weight:700">
                <span style="display:inline-block;width:6px;height:6px;border-radius:50%;
                             background:#e8530a"></span>
                Administración
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.page_link("pages/0_admin_panel.py",
                     label="Panel de Administración — Vista global de todos los usuarios",
                     width='stretch')
        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

    cols = st.columns(4)
    with cols[0]:
        st.page_link("pages/1_panel.py",    label="Panel general",       width='stretch')
        st.page_link("pages/2_carritos.py", label="Carritos",             width='stretch')
    with cols[1]:
        st.page_link("pages/3_ventas.py",   label="Ventas",               width='stretch')
        st.page_link("pages/4_gastos.py",   label="Gastos",               width='stretch')
    with cols[2]:
        st.page_link("pages/5_reporte_por_carrito.py", label="Reporte por carrito", width='stretch')
        st.page_link("pages/6_clientes.py", label="Clientes",             width='stretch')
    with cols[3]:
        st.page_link("pages/7_facturas.py", label="Facturas",             width='stretch')
        st.page_link("pages/8_entrenar_chatbot.py", label="Entrenar chatbot", width='stretch')
        st.page_link("pages/9_stock.py",    label="Existencias / Inventario",   width='stretch')
    st.caption("Las páginas filtran y guardan datos por usuario automáticamente (vía Fachada).")
    render_chatbot_inline("aplicacion")


# -------------------------------------------------------------------
# Navegación dinámica — la lista de páginas cambia según sesión
# -------------------------------------------------------------------
_logged    = st.session_state.get("logged_in") and bool(st.session_state.get("user_id"))
_is_admin  = st.session_state.get("is_admin", False)

_pages = [st.Page(home_page, title="Aplicación", icon=":material/home:", default=True)]

if _logged:
    if _is_admin:
        _pages.append(st.Page("pages/0_admin_panel.py", title="Panel Admin", icon=":material/admin_panel_settings:"))
    _pages += [
        st.Page("pages/1_panel.py",              title="Panel",              icon=":material/dashboard:"),
        st.Page("pages/2_carritos.py",           title="Carritos",           icon=":material/shopping_cart:"),
        st.Page("pages/3_ventas.py",             title="Ventas",             icon=":material/point_of_sale:"),
        st.Page("pages/4_gastos.py",             title="Gastos",             icon=":material/receipt_long:"),
        st.Page("pages/5_reporte_por_carrito.py",title="Reporte carrito",    icon=":material/analytics:"),
        st.Page("pages/6_clientes.py",           title="Clientes",           icon=":material/group:"),
        st.Page("pages/7_facturas.py",           title="Facturas",           icon=":material/description:"),
        st.Page("pages/8_entrenar_chatbot.py",   title="Entrenar chatbot",   icon=":material/smart_toy:"),
        st.Page("pages/9_stock.py",              title="Existencias / Inventario", icon=":material/inventory_2:"),
    ]

pg = st.navigation(_pages, position="sidebar")
pg.run()
