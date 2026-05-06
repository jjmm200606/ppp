from pathlib import Path

import streamlit as st

from lib.chatbot import render_chatbot_inline
from lib.patterns.facade import AccountingFacade
from lib.utils import apply_theme, page_header, require_login, section_header


st.set_page_config(page_title="Entrenar chatbot", layout="wide")
apply_theme()
require_login()

facade = AccountingFacade(user_id=st.session_state.get("user_id") or 0)
DATASET_DIR = Path(__file__).resolve().parents[1] / "docs" / "dataset_proyecto_csv"

page_header(
    "Entrenar chatbot",
    "Agrega reglas, preguntas frecuentes y contexto para que el asistente responda como tu negocio.",
)
render_chatbot_inline("entrenar_chatbot")

st.info(
    "Este entrenamiento no modifica el modelo de Groq. Guarda conocimiento en tu base de datos "
    "y el asistente lo usa como contexto en cada respuesta."
)


def _seed_examples() -> list[dict]:
    return [
        {
            "category": "Reglas del negocio",
            "title": "Margen objetivo",
            "content": (
                "Recomienda mantener un margen neto minimo del 30%. "
                "Si el margen baja de 20%, sugiere revisar precios, costos de ingredientes y gastos por carrito."
            ),
        },
        {
            "category": "Atencion al cliente",
            "title": "Tono de respuesta",
            "content": (
                "Responde con lenguaje sencillo, directo y amable. "
                "Evita explicaciones largas si el usuario pide una recomendacion rapida."
            ),
        },
        {
            "category": "Inventario",
            "title": "Stock critico",
            "content": (
                "Cuando un producto este por debajo del stock minimo, recomienda comprar primero los insumos "
                "directamente relacionados con ventas: pan, salchichas, salsas y bebidas."
            ),
        },
    ]


tab_add, tab_manage = st.tabs(["Agregar conocimiento", "Gestionar conocimiento"])

with tab_add:
    section_header("Nuevo conocimiento")

    with st.form("form_conocimiento", clear_on_submit=True):
        category = st.selectbox(
            "Categoria",
            [
                "Reglas del negocio",
                "Preguntas frecuentes",
                "Productos y precios",
                "Inventario",
                "Atencion al cliente",
                "Promociones",
                "Procedimientos",
                "General",
            ],
        )
        title = st.text_input("Titulo *", placeholder="Ej: Politica de descuentos")
        content = st.text_area(
            "Contenido *",
            placeholder=(
                "Ej: Si el cliente compra mas de 10 perros calientes, sugerir descuento maximo del 8% "
                "solo si el margen sigue por encima del 25%."
            ),
            height=170,
        )
        submitted = st.form_submit_button("Guardar conocimiento", width="stretch")

    if submitted:
        if not title.strip() or not content.strip():
            st.error("Completa titulo y contenido.")
        else:
            facade.agregar_conocimiento(
                category=category,
                title=title,
                content=content,
            )
            st.success("Conocimiento guardado. El chatbot lo usara desde la proxima pregunta.")
            st.rerun()

    st.divider()
    section_header("Entrenamiento rapido")
    st.caption("Carga ejemplos base y luego editalos segun tu negocio.")
    if st.button("Cargar ejemplos recomendados", width="stretch"):
        for item in _seed_examples():
            facade.agregar_conocimiento(**item)
        st.success("Ejemplos agregados.")
        st.rerun()

    st.divider()
    section_header("Importar datos del proyecto")
    st.caption(
        "Esto carga los CSV de carritos, ventas, gastos, clientes, facturas, inventario y conocimiento "
        "desde la carpeta docs/dataset_proyecto_csv."
    )
    if DATASET_DIR.exists():
        archivos = sorted(p.name for p in DATASET_DIR.glob("*.csv"))
        st.code("\n".join(archivos), language="text")
        st.warning("Esta importacion reemplaza los datos actuales del usuario logueado en esos modulos.")
        if st.button("Importar dataset completo del proyecto", width="stretch"):
            try:
                import pandas as pd

                dataset = {}
                for csv_path in DATASET_DIR.glob("*.csv"):
                    if csv_path.name.lower() == "readme.csv":
                        continue
                    df = pd.read_csv(csv_path).fillna("")
                    dataset[csv_path.stem] = df.to_dict("records")

                counts = facade.importar_dataset_proyecto(dataset, replace=True)
                st.success(
                    "Importacion completada: "
                    f"{counts['carritos']} carritos, "
                    f"{counts['ventas']} ventas, "
                    f"{counts['gastos']} gastos, "
                    f"{counts['clientes']} clientes, "
                    f"{counts['facturas']} facturas, "
                    f"{counts['factura_items']} items, "
                    f"{counts['inventario']} productos de inventario y "
                    f"{counts['conocimiento']} registros de conocimiento."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"No pude importar el dataset del proyecto: {exc}")
    else:
        st.error(f"No encuentro la carpeta del dataset: {DATASET_DIR}")

    st.divider()
    section_header("Importar desde Excel / CSV")
    st.caption("El archivo debe tener las columnas: category, title, content.")
    uploaded = st.file_uploader("Sube un CSV exportado desde Excel", type=["csv"])
    if uploaded is not None:
        try:
            import pandas as pd

            df = pd.read_csv(uploaded)
            required = {"category", "title", "content"}
            missing = required.difference(df.columns)
            if missing:
                st.error(f"Faltan columnas requeridas: {', '.join(sorted(missing))}")
            else:
                preview = df[list(required)].fillna("").head(20)
                st.dataframe(preview, hide_index=True, width="stretch")
                if st.button("Importar conocimiento", width="stretch"):
                    total = 0
                    for row in df.to_dict("records"):
                        category = str(row.get("category") or "").strip()
                        title = str(row.get("title") or "").strip()
                        content = str(row.get("content") or "").strip()
                        if title and content:
                            facade.agregar_conocimiento(
                                category=category or "General",
                                title=title,
                                content=content,
                            )
                            total += 1
                    st.success(f"Se importaron {total} registros de conocimiento.")
                    st.rerun()
        except Exception as exc:
            st.error(f"No pude leer el archivo: {exc}")

with tab_manage:
    section_header("Conocimiento guardado")
    items = facade.listar_conocimiento(solo_activos=False)

    if not items:
        st.info("Aun no has agregado conocimiento para el chatbot.")
    else:
        for item in items:
            status = "Activo" if item.get("active") else "Inactivo"
            label = f"{item['category']} - {item['title']} ({status})"
            with st.expander(label):
                with st.form(f"edit_kb_{item['id']}"):
                    new_category = st.text_input("Categoria", value=item["category"])
                    new_title = st.text_input("Titulo", value=item["title"])
                    new_content = st.text_area("Contenido", value=item["content"], height=140)
                    new_active = st.checkbox("Activo", value=bool(item.get("active")))
                    col_save, col_delete = st.columns(2)
                    with col_save:
                        save = st.form_submit_button("Actualizar", width="stretch")
                    with col_delete:
                        delete = st.form_submit_button("Eliminar", width="stretch")

                if save:
                    if not new_title.strip() or not new_content.strip():
                        st.error("Titulo y contenido no pueden quedar vacios.")
                    else:
                        facade.actualizar_conocimiento(
                            item["id"],
                            category=new_category,
                            title=new_title,
                            content=new_content,
                            active=new_active,
                        )
                        st.success("Conocimiento actualizado.")
                        st.rerun()

                if delete:
                    facade.eliminar_conocimiento(item["id"])
                    st.success("Conocimiento eliminado.")
                    st.rerun()
