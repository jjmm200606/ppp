# lib/chatbot.py
from __future__ import annotations
import streamlit as st
from lib.utils import money

_SYSTEM = """Eres un asistente contable experto llamado "PerrocalienteBot", especializado en negocios de carritos de perros calientes.

TU ROL:
- Ayudas al dueño del negocio a entender sus finanzas y tomar mejores decisiones.
- Interpretas ventas, costos, gastos, utilidades y métricas clave.
- Detectas alertas: márgenes bajos, gastos elevados, carritos poco rentables.
- Sugieres acciones concretas basadas en los números reales del negocio.

CONCEPTOS CLAVE DEL NEGOCIO:
- Utilidad neta = Ingresos - Costo de ventas - Gastos operativos
- Margen saludable: >40%. Entre 20-40%: aceptable. <20%: preocupante.
- Costo de ventas = lo que cuesta hacer cada perro caliente (ingredientes, etc.)
- Gastos operativos = gas, hielo, transporte, comisiones, otros

SECCIONES DE LA APP:
- Panel: resumen general de KPIs del negocio
- Carritos: gestiona y consulta tus puntos de venta
- Ventas: registra ingresos por carrito y producto
- Gastos: registra costos operativos por carrito
- Reporte por carrito: análisis individual por rango de fechas
- Clientes: directorio y seguimiento de clientes
- Facturas: emisión y consulta de facturas
- Cuentas: catálogo contable del negocio
- Entrenar chatbot: registra reglas, preguntas frecuentes y conocimiento del negocio

REGLAS:
- Responde siempre en español, de forma concisa y práctica.
- Si los datos muestran una utilidad negativa o margen bajo, adviértelo claramente.
- Si no tienes datos suficientes para responder algo específico, dílo honestamente.
- No inventes cifras; usa solo los datos que se te proporcionan.
- El conocimiento personalizado registrado por el usuario tiene prioridad sobre recomendaciones generales.
- Si recibes un bloque llamado CONTEXTO ACTIVO DE LA PÁGINA, úsalo como prioridad sobre el contexto global.
- Si el contexto activo corresponde a "Reporte por carrito", responde solo sobre ese carrito y ese rango de fechas, salvo que el usuario pida explícitamente una comparación global.

GRÁFICOS DISPONIBLES:
Cuando sea útil visualizar datos, incluye al final de tu respuesta UNA etiqueta con este formato exacto: [CHART:tipo]
Tipos disponibles:
- [CHART:financiero] — resumen general: ingresos, costo, gastos, utilidad
- [CHART:utilidad_carrito] — comparativa de utilidad entre carritos
- [CHART:ventas_diario] — evolución diaria de ventas en el tiempo
- [CHART:ventas_producto] — top productos por importe vendido
- [CHART:gastos_categoria] — distribución de gastos por categoría
- [CHART:gastos_diario] — gastos acumulados por día
- [CHART:stock] — stock actual vs mínimo por producto

Usa un gráfico cuando:
- El usuario lo pida explícitamente
- Estés comparando múltiples valores entre categorías, carritos o fechas
- Un visual aclararía mejor los datos que solo texto

Solo una etiqueta [CHART:xxx] por respuesta. Si no aplica, no la incluyas."""

def _build_system_with_data(extra_context: str | None = None) -> str:
    """Construye el prompt del sistema inyectando los KPIs reales del usuario."""
    try:
        from lib.patterns.facade import AccountingFacade  # noqa: PLC0415
        uid = st.session_state.get("user_id") or 0
        if not uid:
            return _SYSTEM
        facade = AccountingFacade(user_id=uid)

        # --- KPIs globales ---
        k = facade.kpis()
        ingresos = k.get("ingresos", 0.0)
        costo    = k.get("costo",    0.0)
        gastos   = k.get("gastos",   0.0)
        utilidad = k.get("utilidad", 0.0)
        margen   = (utilidad / ingresos * 100) if ingresos > 0 else 0.0
        estado   = "saludable ✅" if margen >= 40 else ("aceptable ⚠️" if margen >= 20 else "preocupante ❌")

        # --- Carritos con sus finanzas ---
        carritos = facade.top_carritos_utilidad()
        carritos_txt = ""
        for c in carritos:
            margen_c = (c["utilidad"] / c["ingresos"] * 100) if c["ingresos"] > 0 else 0.0
            carritos_txt += (
                f"  - {c['name']} ({c.get('location','') or 'sin ubicación'}): "
                f"ingresos {money(c['ingresos'])}, costo {money(c['costo'])}, "
                f"gastos {money(c['gastos'])}, utilidad {money(c['utilidad'])} "
                f"(margen {margen_c:.1f}%)\n"
            )

        # --- Últimas 50 ventas ---
        ventas = facade.listar_ventas()[:50]
        ventas_txt = ""
        for v in ventas:
            ventas_txt += (
                f"  - {v['sale_date']} | {v['cart_name']} | {v['product']} | "
                f"qty {v['qty']} | importe {money(v['importe'])} | utilidad {money(v['utilidad'])}\n"
            )

        # --- Últimos 50 gastos ---
        gastos_list = facade.listar_gastos()[:50]
        gastos_txt = ""
        for g in gastos_list:
            gastos_txt += (
                f"  - {g['expense_date']} | {g['cart_name']} | {g['category']} | "
                f"{g['description']} | {money(g['amount'])}\n"
            )

        # --- Clientes ---
        try:
            clientes = facade.listar_clientes()
            clientes_txt = ""
            for cl in clientes:
                clientes_txt += (
                    f"  - {cl['name']}"
                    + (f" | email: {cl['email']}" if cl.get('email') else "")
                    + (f" | tel: {cl['phone']}" if cl.get('phone') else "")
                    + "\n"
                )
        except Exception:
            clientes_txt = "  (información de clientes no disponible)"

        # --- Facturas ---
        try:
            facturas = facade.listar_facturas()
            facturas_txt = ""
            pendiente_total = 0.0
            for f in facturas:
                facturas_txt += (
                    f"  - #{f['id']} | {f['invoice_date']} | {f['client']} | "
                    f"total {money(f['total'])} | estado: {f['status']}\n"
                )
                if str(f.get('status', '')).lower() in ('pendiente', 'pending'):
                    pendiente_total += float(f.get('total') or 0)
        except Exception:
            facturas_txt = "  (información de facturas no disponible)"
            pendiente_total = 0.0

        # --- Stock ---
        try:
            stock_items = facade.listar_stock()
            stock_bajos = facade.stock_bajo()
            stock_txt = ""
            for s in stock_items:
                alerta = " ⚠️ BAJO" if s["bajo_stock"] else ""
                stock_txt += (
                    f"  - {s['product']}: {s['current_stock']} {s['unit']} "
                    f"(mínimo: {s['min_stock']} {s['unit']}){alerta}\n"
                )
            if stock_bajos:
                falta_txt = "\n".join(
                    f"  - {s['product']}: faltan {s['faltante']} {s['unit']} "
                    f"(tiene {s['current_stock']}, mínimo {s['min_stock']})"
                    for s in stock_bajos
                )
            else:
                falta_txt = "  (todos los productos tienen stock suficiente)"
        except Exception:
            stock_txt = "  (información de stock no disponible)"
            falta_txt = "  (información de stock no disponible)"

        # --- Base de conocimiento personalizada ---
        try:
            kb_items = facade.listar_conocimiento(solo_activos=True)
            kb_txt = ""
            if kb_items:
                from itertools import groupby  # noqa: PLC0415
                kb_items_sorted = sorted(kb_items, key=lambda x: x.get("category", ""))
                for cat, group in groupby(kb_items_sorted, key=lambda x: x.get("category", "General")):
                    kb_txt += f"\n  [{cat}]\n"
                    for item in group:
                        kb_txt += f"    • {item['title']}: {item['content']}\n"
            else:
                kb_txt = "  (sin conocimiento personalizado registrado aún)"
        except Exception:
            kb_txt = "  (base de conocimiento no disponible)"

        extra_context_block = ""
        if extra_context:
            extra_context_block = f"""

CONTEXTO ACTIVO DE LA PÁGINA:
{extra_context}
"""

        contexto = f"""

DATOS REALES ACTUALES DEL NEGOCIO (usuario: {st.session_state.get('user', '?')}):

RESUMEN FINANCIERO GLOBAL:
- Ingresos totales: {money(ingresos)}
- Costo de ventas: {money(costo)}
- Gastos operativos: {money(gastos)}
- Utilidad neta: {money(utilidad)}
- Margen de utilidad: {margen:.1f}% — {estado}

CARRITOS (ganancias y gastos por punto de venta):
{carritos_txt if carritos_txt else '  (sin carritos registrados)'}

ÚLTIMAS 50 VENTAS:
{ventas_txt if ventas_txt else '  (sin ventas registradas)'}

ÚLTIMOS 50 GASTOS:
{gastos_txt if gastos_txt else '  (sin gastos registrados)'}

CLIENTES REGISTRADOS ({len(clientes) if 'clientes' in dir() else 0}):
{clientes_txt if clientes_txt else '  (sin clientes registrados)'}

FACTURAS (total pendiente por cobrar: {money(pendiente_total)}):
{facturas_txt if facturas_txt else '  (sin facturas registradas)'}

ESTADO DEL INVENTARIO / STOCK:
{stock_txt if stock_txt else '  (inventario vacío)'}

PRODUCTOS CON STOCK BAJO (lista de reabastecimiento):
{falta_txt}

CONOCIMIENTO PERSONALIZADO DEL NEGOCIO:
{kb_txt}

{extra_context_block}

Usa estos datos para responder preguntas específicas del usuario sobre su negocio."""
        return _SYSTEM + contexto
    except Exception:
        return _SYSTEM


# ── Parser de etiqueta de gráfico (la IA decide) ─────────────────────────────
import re

_CHART_TAG_RE = re.compile(r"\[CHART:([\w_]+)\]", re.IGNORECASE)

_VALID_CHARTS = {
    "financiero", "utilidad_carrito", "ventas_diario",
    "ventas_producto", "gastos_categoria", "gastos_diario", "stock",
}

_SECTION_QUESTIONS = {
    "aplicacion": [
        "Dame un resumen financiero general.",
        "Cual es el carrito con mayor utilidad?",
        "Que gastos son los mas altos?",
        "Hay productos con stock bajo?",
    ],
    "panel": [
        "Dame un resumen financiero general.",
        "Cual es el margen neto actual del negocio?",
        "Cual es el carrito con mayor utilidad?",
        "Que me recomiendas hacer para mejorar la utilidad?",
    ],
    "carritos": [
        "Cual carrito tiene mejor utilidad?",
        "Que carrito tiene peor margen?",
        "Como comparas el rendimiento entre carritos?",
        "Que accion recomiendas para el carrito menos rentable?",
    ],
    "ventas": [
        "Cuales son los productos mas vendidos?",
        "Como van las ventas recientes?",
        "Que dia vende mejor el negocio?",
        "Que recomendacion me das para vender mas?",
    ],
    "gastos": [
        "Cuales son los gastos mas altos?",
        "Que categoria de gasto pesa mas?",
        "Como van los gastos por carrito?",
        "Que gasto deberia vigilar primero?",
    ],
    "reporte_carrito": [
        "Resume el rendimiento del carrito seleccionado.",
        "Ese carrito deja buena utilidad?",
        "Que gastos afectan mas ese carrito?",
        "Que recomendacion puntual das para ese carrito?",
    ],
    "clientes": [
        "Cuantos clientes registrados tengo?",
        "Como puedo aprovechar mejor mis clientes frecuentes?",
        "Me falta informacion de contacto de clientes?",
        "Que estrategia recomiendas para fidelizar clientes?",
    ],
    "facturas": [
        "Cuanto tengo pendiente por cobrar en facturas?",
        "Cuantas facturas pendientes hay?",
        "Que clientes tienen facturas por cobrar?",
        "Que accion recomiendas para recuperar cartera?",
    ],
    "entrenar_chatbot": [
        "Que conocimiento ya tiene el chatbot sobre el negocio?",
        "Que reglas me falta agregar al chatbot?",
        "Como debo entrenar mejor al chatbot?",
        "Que preguntas frecuentes conviene registrar?",
    ],
    "inventario": [
        "Hay productos con stock bajo?",
        "Hazme una lista de productos para reponer inventario.",
        "Como esta el inventario general?",
        "Que riesgo ves en el stock actual?",
    ],
}


def _messages_for_api(messages: list[dict]) -> list[dict]:
    """Limpia el historial local para enviarlo al proveedor sin claves extra."""
    clean_messages = []
    for msg in messages:
        role = str(msg.get("role") or "").strip()
        content = str(msg.get("content") or "").strip()
        if role and content:
            clean_messages.append({"role": role, "content": content})
    return clean_messages


def _get_section_questions(section_key: str | None) -> list[str]:
    return _SECTION_QUESTIONS.get(section_key or "", _SECTION_QUESTIONS["aplicacion"])


def _run_user_prompt(
    oai,
    prompt: str,
    *,
    admin: bool = False,
    extra_context: str | None = None,
) -> dict:
    prompt = (prompt or "").strip()
    if admin:
        st.session_state.chat_admin_msgs.append({"role": "user", "content": prompt})
        history = st.session_state.chat_admin_msgs
        system = _build_admin_system_with_data()
    else:
        st.session_state.chat_msgs.append({"role": "user", "content": prompt})
        history = st.session_state.chat_msgs
        system = _build_system_with_data(extra_context=extra_context)

    with st.spinner("Consultando datos..." if admin else "Pensando..."):
        try:
            resp = oai.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system}] + _messages_for_api(history[-14:]),
                max_tokens=600,
                temperature=0.7,
            )
            raw_reply = resp.choices[0].message.content
        except Exception as exc:
            raw_reply = f"❌ Error al contactar Groq: {exc}"

    reply_text, chart_type = _parse_chart_from_reply(raw_reply)
    if admin and chart_type and chart_type not in _ADMIN_CHARTS:
        chart_type = None

    new_msg = {"role": "assistant", "content": reply_text}
    if chart_type:
        new_msg["chart_type"] = chart_type

    if admin:
        st.session_state.chat_admin_msgs.append(new_msg)
    else:
        st.session_state.chat_msgs.append(new_msg)
    return new_msg


def _parse_chart_from_reply(reply: str) -> "tuple[str, str | None]":
    """Extrae la etiqueta [CHART:tipo] de la respuesta de Groq.
    Retorna (texto_limpio, chart_type) o (reply, None) si no hay etiqueta.
    """
    m = _CHART_TAG_RE.search(reply)
    if not m:
        return reply, None
    chart_type = m.group(1).lower()
    clean = _CHART_TAG_RE.sub("", reply).strip()
    if chart_type not in _VALID_CHARTS:
        return clean, None
    return clean, chart_type


def _build_chart(chart_type: str):
    """Construye y devuelve una figura Plotly según el tipo, o None si no hay datos."""
    try:
        import plotly.express as px  # noqa: PLC0415
        import pandas as pd           # noqa: PLC0415
        from lib.patterns.facade import AccountingFacade  # noqa: PLC0415

        uid = st.session_state.get("user_id") or 0
        facade = AccountingFacade(user_id=uid)

        fig = None

        if chart_type == "financiero":
            k = facade.kpis()
            vals = [k["ingresos"], k["costo"], k["gastos"], max(k["utilidad"], 0)]
            if sum(vals) == 0:
                return None
            df = pd.DataFrame({"Métrica": ["Ingresos", "Costo", "Gastos", "Utilidad"], "Valor": vals})
            fig = px.bar(df, x="Métrica", y="Valor", color="Métrica",
                         color_discrete_map={"Ingresos": "#4ade80", "Costo": "#fb923c",
                                             "Gastos": "#f87171", "Utilidad": "#e8530a"},
                         title="Resumen financiero")

        elif chart_type == "utilidad_carrito":
            rows = facade.top_carritos_utilidad()
            if not rows:
                return None
            df = pd.DataFrame(rows).sort_values("utilidad")
            fig = px.bar(df, x="utilidad", y="name", orientation="h", color="utilidad",
                         color_continuous_scale=["#c0392b", "#e8530a", "#4ade80"],
                         labels={"utilidad": "Utilidad ($)", "name": "Carrito"},
                         title="Utilidad por carrito")
            fig.update_layout(coloraxis_showscale=False)

        elif chart_type == "ventas_diario":
            v = facade.listar_ventas()
            if not v:
                return None
            df = pd.DataFrame(v)
            df["sale_date"] = pd.to_datetime(df["sale_date"])
            daily = df.groupby("sale_date")[["importe", "utilidad"]].sum().reset_index()
            fig = px.line(daily, x="sale_date", y=["importe", "utilidad"],
                          color_discrete_map={"importe": "#4ade80", "utilidad": "#e8530a"},
                          labels={"sale_date": "Fecha", "value": "$", "variable": ""},
                          title="Ingresos y utilidad por día")

        elif chart_type == "ventas_producto":
            v = facade.listar_ventas()
            if not v:
                return None
            df = pd.DataFrame(v)
            by_prod = (df.groupby("product")[["importe", "utilidad"]]
                       .sum().reset_index()
                       .sort_values("importe", ascending=False).head(10))
            fig = px.bar(by_prod, x="product", y=["importe", "utilidad"], barmode="group",
                         color_discrete_map={"importe": "#4ade80", "utilidad": "#e8530a"},
                         labels={"product": "Producto", "value": "$", "variable": ""},
                         title="Top productos por ventas")

        elif chart_type == "gastos_categoria":
            g = facade.listar_gastos()
            if not g:
                return None
            df = pd.DataFrame(g)
            by_cat = df.groupby("category")["amount"].sum().reset_index()
            fig = px.pie(by_cat, names="category", values="amount", hole=0.4,
                         title="Distribución de gastos por categoría",
                         color_discrete_sequence=px.colors.qualitative.Bold)

        elif chart_type == "gastos_diario":
            g = facade.listar_gastos()
            if not g:
                return None
            df = pd.DataFrame(g)
            df["expense_date"] = pd.to_datetime(df["expense_date"])
            daily = df.groupby("expense_date")["amount"].sum().reset_index()
            fig = px.bar(daily, x="expense_date", y="amount",
                         labels={"expense_date": "Fecha", "amount": "Monto ($)"},
                         color_discrete_sequence=["#f87171"],
                         title="Gastos por día")

        elif chart_type == "stock":
            items = facade.listar_stock()
            if not items:
                return None
            df = pd.DataFrame(items)[["product", "current_stock", "min_stock"]]
            df = df.rename(columns={"current_stock": "Stock actual",
                                    "min_stock": "Stock mínimo", "product": "Producto"})
            df_m = df.melt(id_vars="Producto", var_name="Tipo", value_name="Cantidad")
            fig = px.bar(df_m, x="Cantidad", y="Producto", color="Tipo",
                         orientation="h", barmode="group",
                         color_discrete_map={"Stock actual": "#4ade80", "Stock mínimo": "#e8530a"},
                         title="Stock actual vs mínimo por producto")

        if fig is None:
            return None

        # Tema oscuro uniforme
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ddd",
            xaxis=dict(gridcolor="#2a2a2a"),
            yaxis=dict(gridcolor="#2a2a2a"),
            margin=dict(t=40, b=20, l=10, r=10),
            title_font_color="#ddd",
            legend=dict(orientation="h"),
        )
        return fig
    except Exception:
        return None


# ── Sistema y contexto para el ADMINISTRADOR ──────────────────────────

_SYSTEM_ADMIN = """Eres un asistente de administración llamado \"AdminBot\" para la plataforma de contabilidad de carritos de perros calientes.

TU ROL:
- Tienes acceso a los datos de TODOS los usuarios de la plataforma.
- Ayudas al administrador a monitorear el rendimiento global y por usuario.
- Detectas usuarios con bajo margen, carritos poco rentables, tendencias.
- Comparas el desempeño entre usuarios y entre carritos.

CONCEPTOS CLAVE:
- Utilidad neta = Ingresos - Costo de ventas - Gastos operativos
- Margen saludable: >40%. Entre 20-40%: aceptable. <20%: preocupante.

REGLAS:
- Responde siempre en español, de forma concisa y directa.
- Usa los datos reales que se te proporcionan; no inventes cifras.
- Si detectas anomalías o usuarios con bajo rendimiento, meníciónalos.

GRÁFICOS DISPONIBLES (solo para admin):
Cuando sea útil, incluye al final de tu respuesta UNA etiqueta: [CHART:tipo]
Tipos disponibles:
- [CHART:admin_usuarios] — utilidad comparada entre todos los usuarios
- [CHART:admin_carritos] — utilidad de todos los carritos, agrupados por usuario
- [CHART:admin_ingresos_vs_costo] — barras agrupadas: ingresos, costo y gastos por usuario
- [CHART:financiero] — resumen global: ingresos, costo, gastos, utilidad de la plataforma

Usa un gráfico cuando compares múltiples usuarios o carritos, o cuando el usuario lo pida.
Solo una etiqueta [CHART:xxx] por respuesta. Si no aplica, no la incluyas."""


def _build_admin_system_with_data() -> str:
    """Construye el prompt del sistema admin inyectando datos globales de todos los usuarios."""
    try:
        from lib.patterns.facade import AccountingFacade  # noqa: PLC0415
        facade = AccountingFacade(user_id=0)

        k = facade.admin_kpis_globales()
        ingresos = k["ingresos"]; costo = k["costo"]
        gastos = k["gastos"];   utilidad = k["utilidad"]
        margen = (utilidad / ingresos * 100) if ingresos > 0 else 0.0
        estado = "saludable ✅" if margen >= 40 else ("aceptable ⚠️" if margen >= 20 else "preocupante ❌")

        usuarios = facade.admin_resumen_usuarios()
        usuarios_txt = ""
        for u in usuarios:
            m = (u["utilidad"] / u["ingresos"] * 100) if u["ingresos"] > 0 else 0.0
            usuarios_txt += (
                f"  - {u['username']}: ingresos {money(u['ingresos'])}, "
                f"costo {money(u['costo'])}, gastos {money(u['gastos'])}, "
                f"utilidad {money(u['utilidad'])} (margen {m:.1f}%), "
                f"{u['carritos']} carrito(s), {u['num_ventas']} venta(s)\n"
            )

        carritos = facade.admin_listar_carritos()
        carritos_txt = ""
        for c in carritos:
            m = (c["utilidad"] / c["ingresos"] * 100) if c["ingresos"] > 0 else 0.0
            carritos_txt += (
                f"  - [{c['username']}] {c['name']} ({c.get('location') or 'sin ubicación'}): "
                f"ingresos {money(c['ingresos'])}, utilidad {money(c['utilidad'])} "
                f"(margen {m:.1f}%), activo={'Sí' if c['active'] else 'No'}\n"
            )

        contexto = f"""

DATOS GLOBALES DE LA PLATAFORMA:

RESUMEN FINANCIERO GLOBAL:
- Ingresos totales: {money(ingresos)}
- Costo de ventas: {money(costo)}
- Gastos operativos: {money(gastos)}
- Utilidad neta: {money(utilidad)}
- Margen global: {margen:.1f}% — {estado}
- Total usuarios registrados: {int(k['usuarios'])}

RESUMEN POR USUARIO:
{usuarios_txt if usuarios_txt else '  (sin usuarios con datos)'}

TODOS LOS CARRITOS:
{carritos_txt if carritos_txt else '  (sin carritos registrados)'}

Usa estos datos para responder las preguntas del administrador."""
        return _SYSTEM_ADMIN + contexto
    except Exception:
        return _SYSTEM_ADMIN


def _build_chart_admin(chart_type: str):
    """Charts exclusivos de la vista de administrador."""
    try:
        import plotly.express as px  # noqa: PLC0415
        import pandas as pd           # noqa: PLC0415
        from lib.patterns.facade import AccountingFacade  # noqa: PLC0415
        facade = AccountingFacade(user_id=0)
        fig = None

        if chart_type == "admin_usuarios":
            rows = facade.admin_resumen_usuarios()
            if not rows:
                return None
            df = pd.DataFrame(rows).sort_values("utilidad")
            fig = px.bar(
                df, x="utilidad", y="username", orientation="h", color="utilidad",
                color_continuous_scale=["#c0392b", "#e8530a", "#4ade80"],
                labels={"utilidad": "Utilidad ($)", "username": "Usuario"},
                title="Utilidad neta por usuario",
            )
            fig.update_layout(coloraxis_showscale=False)

        elif chart_type == "admin_carritos":
            rows = facade.admin_listar_carritos()
            if not rows:
                return None
            df = pd.DataFrame(rows).sort_values("utilidad")
            fig = px.bar(
                df, x="utilidad", y="name", color="username", orientation="h",
                labels={"utilidad": "Utilidad ($)", "name": "Carrito", "username": "Usuario"},
                title="Utilidad por carrito (todos los usuarios)",
            )

        elif chart_type == "admin_ingresos_vs_costo":
            rows = facade.admin_resumen_usuarios()
            if not rows:
                return None
            df = pd.DataFrame(rows)
            df_m = df.rename(columns={"ingresos": "Ingresos", "costo": "Costo", "gastos": "Gastos",
                                      "username": "Usuario"})
            df_m = df_m.melt(id_vars="Usuario", value_vars=["Ingresos", "Costo", "Gastos"],
                             var_name="Tipo", value_name="Valor")
            fig = px.bar(
                df_m, x="Usuario", y="Valor", color="Tipo", barmode="group",
                color_discrete_map={"Ingresos": "#4ade80", "Costo": "#fb923c", "Gastos": "#f87171"},
                title="Ingresos, costo y gastos por usuario",
            )

        elif chart_type == "financiero":
            k = facade.admin_kpis_globales()
            vals = [k["ingresos"], k["costo"], k["gastos"], max(k["utilidad"], 0)]
            if sum(vals) == 0:
                return None
            df = pd.DataFrame({"Métrica": ["Ingresos", "Costo", "Gastos", "Utilidad"], "Valor": vals})
            fig = px.bar(df, x="Métrica", y="Valor", color="Métrica",
                         color_discrete_map={"Ingresos": "#4ade80", "Costo": "#fb923c",
                                             "Gastos": "#f87171", "Utilidad": "#e8530a"},
                         title="Resumen financiero global")

        if fig is None:
            return None
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ddd", legend=dict(orientation="h"),
            xaxis=dict(gridcolor="#2a2a2a"), yaxis=dict(gridcolor="#2a2a2a"),
            margin=dict(t=40, b=20, l=10, r=10), title_font_color="#ddd",
        )
        return fig
    except Exception:
        return None


_ADMIN_CHARTS = {"admin_usuarios", "admin_carritos", "admin_ingresos_vs_costo", "financiero"}


def render_chatbot_admin():
    """Chatbot inline con contexto de administrador (ve datos de todos los usuarios)."""
    oai = _client()

    st.divider()
    st.markdown("""
    <div style="display:flex;align-items:center;gap:.7rem;margin-bottom:1rem">
        <div style="font-size:1.6rem">⚙️</div>
        <div>
            <h3 style="margin:0;color:#ddd;font-weight:700">Asistente Admin</h3>
            <p style="margin:0;color:#888;font-size:.8rem">Pregúntame sobre usuarios, carritos, rentabilidad global o pide gráficos</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not oai:
        st.markdown("""
        <div style="background:#161616;border:1px solid #282828;border-radius:12px;
                    padding:1.5rem;text-align:center;color:#aaa">
            <p style="margin:0">Agrega tu API key de Groq en
            <code style="color:#e8530a">.streamlit/secrets.toml</code> para activar el asistente.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    if "chat_admin_msgs" not in st.session_state:
        st.session_state.chat_admin_msgs = []

    with st.container(height=400):
        if not st.session_state.chat_admin_msgs:
            st.markdown("""
            <div style="text-align:center;padding:2.5rem 1rem;color:#555">
                <div style="font-size:2.5rem">⚙️</div>
                <p style="margin-top:.8rem;font-size:.9rem">
                    Hola, soy tu asistente de administración.<br>
                    Tengo acceso a los datos de todos los usuarios.<br><br>
                    <span style="color:#e8530a;font-size:.82rem">
                    Ejemplos: <i>"resumen de usuarios"</i> · <i>"qué carrito genera más"</i><br>
                    <i>"gráfico de utilidad por usuario"</i> · <i>"qué usuario tiene mejor margen"</i>
                    </span>
                </p>
            </div>
            """, unsafe_allow_html=True)
        for idx, m in enumerate(st.session_state.chat_admin_msgs):
            avatar = "⚙️" if m["role"] == "assistant" else "👤"
            with st.chat_message(m["role"], avatar=avatar):
                st.markdown(m["content"])
                if m.get("chart_type"):
                    fig = _build_chart_admin(m["chart_type"])
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, key=f"admin_chart_{idx}")

    col_input, col_clear = st.columns([8, 1])
    with col_input:
        user_input = st.chat_input("Escribe tu pregunta...", key="chat_admin_input")
    with col_clear:
        if st.button("Limpiar", help="Limpiar conversación", width='stretch', key="clear_admin_chat"):
            st.session_state.chat_admin_msgs = []
            st.rerun()

    if user_input and user_input.strip():
        st.session_state.chat_admin_msgs.append({"role": "user", "content": user_input.strip()})
        with st.spinner("Consultando datos..."):
            try:
                resp = oai.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": _build_admin_system_with_data()}]
                             + _messages_for_api(st.session_state.chat_admin_msgs[-14:]),
                    max_tokens=600,
                    temperature=0.7,
                )
                raw_reply = resp.choices[0].message.content
            except Exception as exc:
                raw_reply = f"❌ Error al contactar Groq: {exc}"
        reply_text, chart_type = _parse_chart_from_reply(raw_reply)
        # chart_type solo válido si es un tipo admin
        if chart_type and chart_type not in _ADMIN_CHARTS:
            chart_type = None
        new_msg = {"role": "assistant", "content": reply_text}
        if chart_type:
            new_msg["chart_type"] = chart_type
        st.session_state.chat_admin_msgs.append(new_msg)
        st.rerun()


def _client():
    """Devuelve un cliente Groq o None si no hay key válida."""
    try:
        from groq import Groq  # noqa: PLC0415
        key = st.secrets.get("GROQ_API_KEY", "")
        if not key or key == "gsk_...":
            return None
        return Groq(api_key=key)
    except Exception:
        return None


@st.dialog("Asistente IA", width="large")
def _modal():
    oai = _client()

    # CSS interno del modal
    st.markdown("""
    <style>
    [data-testid="stForm"] { background: #161616 !important; border: 1px solid #282828 !important;
        border-radius: 12px !important; padding: 1rem !important; }
    [data-testid="stChatMessage"] { background: #1a1a1a !important;
        border-radius: 10px !important; margin-bottom: .5rem !important; }
    </style>
    """, unsafe_allow_html=True)

    if not oai:
        st.markdown("""
        <div style="text-align:center;padding:2rem;color:#aaa">
            <div style="font-size:2.5rem;margin-bottom:.8rem">🔑</div>
            <p>Para usar el asistente, agrega tu API key de Groq<br>en
            <code style="color:#e8530a">.streamlit/secrets.toml</code>:</p>
        </div>
        """, unsafe_allow_html=True)
        st.code('GROQ_API_KEY = "gsk_..."', language="toml")
        st.caption("Obtén tu key gratis en [console.groq.com](https://console.groq.com)")
        return

    if "chat_msgs" not in st.session_state:
        st.session_state.chat_msgs = []

    # Historial de mensajes
    with st.container(height=370):
        if not st.session_state.chat_msgs:
            st.markdown("""
            <div style="text-align:center;padding:2.5rem;color:#666;margin-top:1.5rem">
                <div style="font-size:2.8rem">🌭</div>
                <p style="margin-top:.8rem;font-size:.95rem">
                    ¡Hola! Soy tu asistente contable.<br>
                    Pregunta sobre ventas, utilidades o gastos.<br><br>
                    <span style="color:#e8530a;font-size:.85rem">
                    📊 También puedo generar gráficos:<br>
                    <i>"gráfico de ventas por día"</i><br>
                    <i>"gráfico de gastos por categoría"</i><br>
                    <i>"gráfico de stock"</i>
                    </span>
                </p>
            </div>
            """, unsafe_allow_html=True)
        for idx, m in enumerate(st.session_state.chat_msgs):
            avatar = "🤖" if m["role"] == "assistant" else "👤"
            with st.chat_message(m["role"], avatar=avatar):
                st.markdown(m["content"])
                if m.get("chart_type"):
                    fig = _build_chart(m["chart_type"])
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, key=f"modal_chart_{idx}")

    # Input
    with st.form("chatbot_form", clear_on_submit=True):
        col_txt, col_btn = st.columns([6, 1])
        with col_txt:
            user_input = st.text_input(
                "", placeholder="Escribe tu pregunta...", label_visibility="collapsed"
            )
        with col_btn:
            send = st.form_submit_button("➤", width='stretch')

    if st.button("Limpiar conversación", width='stretch', key="clear_chat_btn"):
        st.session_state.chat_msgs = []
        st.rerun()

    if send and user_input.strip():
        msg_text = user_input.strip()
        st.session_state.chat_msgs.append({"role": "user", "content": msg_text})
        with st.spinner("Pensando..."):
            try:
                resp = oai.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": _build_system_with_data()}]
                             + _messages_for_api(st.session_state.chat_msgs[-14:]),
                    max_tokens=600,
                    temperature=0.7,
                )
                raw_reply = resp.choices[0].message.content
            except Exception as exc:
                raw_reply = f"❌ Error al contactar Groq: {exc}"
        reply_text, chart_type = _parse_chart_from_reply(raw_reply)
        new_msg = {"role": "assistant", "content": reply_text}
        if chart_type:
            new_msg["chart_type"] = chart_type
        st.session_state.chat_msgs.append(new_msg)
        st.rerun()


def render_chatbot_sidebar():
    """Agrega el botón flotante del chatbot en el sidebar."""
    with st.sidebar:
        st.markdown("---")
        n_msgs = len(st.session_state.get("chat_msgs", []))
        badge = f" ({n_msgs})" if n_msgs else ""
        st.markdown(f"""
        <div style="text-align:center;color:#888;font-size:.7rem;
                    text-transform:uppercase;letter-spacing:.8px;margin-bottom:.5rem">
            Asistente IA{badge}
        </div>
        """, unsafe_allow_html=True)
        if st.button("Abrir chat inteligente", width='stretch', key="open_chatbot_modal"):
            _modal()


def render_chatbot_inline(
    section_key: str | None = None,
    *,
    extra_context: str | None = None,
    context_scope: str | None = None,
):
    """Renderiza el chat directamente en el contenido principal de la página."""
    oai = _client()

    st.divider()
    st.markdown("""
    <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:1rem">
        <div style="width:4px;height:22px;background:#e8530a;border-radius:2px;flex-shrink:0"></div>
        <div>
            <h3 style="margin:0;color:#ddd;font-weight:700;font-size:1rem">Asistente IA</h3>
            <p style="margin:0;color:#888;font-size:.78rem">Pregúntame sobre ventas, gastos, utilidades o cómo usar la app</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not oai:
        st.markdown("""
        <div style="background:#161616;border:1px solid #282828;border-radius:12px;
                    padding:1.5rem;text-align:center;color:#aaa">
            <div style="font-size:2rem;margin-bottom:.6rem">🔑</div>
            <p style="margin:0">Agrega tu API key de Groq en
            <code style="color:#e8530a">.streamlit/secrets.toml</code><br>
            para activar el asistente.</p>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Obtén tu key gratis en [console.groq.com](https://console.groq.com)")
        return

    if "chat_msgs" not in st.session_state:
        st.session_state.chat_msgs = []

    current_scope = f"{section_key or 'general'}::{context_scope or ''}"
    if st.session_state.get("chat_inline_scope") != current_scope:
        st.session_state.chat_inline_scope = current_scope
        st.session_state.chat_msgs = []

    questions = _get_section_questions(section_key)

    # Contenedor del historial
    with st.container(height=340):
        if not st.session_state.chat_msgs:
            st.markdown("""
            <div style="text-align:center;padding:2.5rem 1rem;color:#555">
                <div style="font-size:2.5rem">🌭</div>
                <p style="margin-top:.8rem;font-size:.9rem">
                    ¡Hola! Soy tu asistente contable.<br>
                    Pregunta sobre ventas, utilidades o gastos.
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(
                "<div style='color:#888;font-size:.8rem;margin:.2rem 0 .7rem 0'>Sugerencias para empezar</div>",
                unsafe_allow_html=True,
            )
            qcols = st.columns(2)
            for idx, question in enumerate(questions[:4]):
                with qcols[idx % 2]:
                    if st.button(
                        question,
                        key=f"preset_{section_key or 'general'}_{idx}",
                        width='stretch',
                    ):
                        if oai:
                            _run_user_prompt(oai, question, admin=False, extra_context=extra_context)
                            st.rerun()
        for idx, m in enumerate(st.session_state.chat_msgs):
            avatar = "🤖" if m["role"] == "assistant" else "👤"
            with st.chat_message(m["role"], avatar=avatar):
                st.markdown(m["content"])
                if m.get("chart_type"):
                    fig = _build_chart(m["chart_type"])
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, key=f"inline_chart_{idx}")

    # Input y botones
    col_input, col_send, col_clear = st.columns([7, 1, 1])
    with col_input:
        user_input = st.chat_input("Escribe tu pregunta...", key="chat_inline_input")
    with col_clear:
        if st.button("Limpiar", help="Limpiar conversación", width='stretch', key="clear_inline_chat"):
            st.session_state.chat_msgs = []
            st.rerun()

    if user_input and user_input.strip():
        _run_user_prompt(oai, user_input.strip(), admin=False, extra_context=extra_context)
        st.rerun()
