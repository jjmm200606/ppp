from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
XLSX_PATH = DOCS / "datos_proyecto_entrenamiento.xlsx"
CSV_PATH = DOCS / "conocimiento_desde_datos_proyecto.csv"
DATASET_DIR = DOCS / "dataset_proyecto_csv"


def _cell_ref(col_idx: int, row_idx: int) -> str:
    letters = ""
    col = col_idx
    while col:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{row_idx}"


def _sheet_xml(rows: list[list[object]]) -> str:
    xml_rows = []
    for row_idx, row in enumerate(rows, start=1):
        cells = []
        for col_idx, value in enumerate(row, start=1):
            ref = _cell_ref(col_idx, row_idx)
            if value is None:
                cells.append(f'<c r="{ref}"/>')
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                text = escape(str(value))
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        xml_rows.append(f'<row r="{row_idx}">{"".join(cells)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        + "".join(xml_rows)
        + '</sheetData></worksheet>'
    )


def _build_data() -> dict[str, list[list[object]]]:
    carritos = [
        [1, "Carrito Centro", "Parque Central", 1],
        [2, "Carrito Universidad", "Salida universidad", 1],
        [3, "Carrito Terminal", "Terminal de transporte", 1],
        [4, "Carrito Estadio", "Entrada estadio", 1],
    ]

    productos = [
        ("Perro caliente clasico", 8500, 4200),
        ("Perro especial", 12000, 6200),
        ("Perro ranchero", 14000, 7600),
        ("Combo perro + bebida", 15500, 8300),
        ("Bebida", 3500, 1800),
    ]

    ventas = []
    sale_id = 1
    start = date(2026, 3, 1)
    random.seed(42)
    for day in range(35):
        current = start + timedelta(days=day)
        for cart_id, cart_name, *_ in carritos:
            registros = random.randint(1, 3)
            for _ in range(registros):
                product, price, cost = random.choice(productos)
                weekend_boost = 1.25 if current.weekday() >= 5 else 1.0
                qty = int(random.randint(8, 28) * weekend_boost)
                ventas.append(
                    [
                        sale_id,
                        current.isoformat(),
                        cart_id,
                        cart_name,
                        product,
                        qty,
                        price,
                        cost,
                        round(qty * price, 2),
                        round(qty * cost, 2),
                        round(qty * (price - cost), 2),
                        "Dato de entrenamiento",
                    ]
                )
                sale_id += 1

    gastos = []
    expense_id = 1
    categorias = [
        ("Gas", 28000, 45000),
        ("Hielo", 12000, 24000),
        ("Transporte", 18000, 38000),
        ("Empaques", 22000, 42000),
        ("Mantenimiento", 30000, 75000),
        ("Comisiones", 15000, 35000),
    ]
    for day in range(0, 35, 2):
        current = start + timedelta(days=day)
        for cart_id, cart_name, *_ in carritos:
            category, low, high = random.choice(categorias)
            amount = random.randint(low, high)
            gastos.append(
                [
                    expense_id,
                    current.isoformat(),
                    cart_id,
                    cart_name,
                    category,
                    f"{category} del {cart_name}",
                    amount,
                ]
            )
            expense_id += 1

    clientes = [
        [1, "Colegio San Martin", "compras@sanmartin.edu", "3101112233"],
        [2, "Eventos La 40", "eventos40@mail.com", "3112223344"],
        [3, "Empresa ServiPlus", "admin@serviplus.com", "3123334455"],
        [4, "Juan Perez", "juanp@mail.com", "3134445566"],
        [5, "Laura Gomez", "laura.gomez@mail.com", "3145556677"],
    ]

    facturas = [
        [1, 1, "Colegio San Martin", 2, "Carrito Universidad", "2026-03-12", "2026-03-20", "Pendiente", 480000],
        [2, 2, "Eventos La 40", 4, "Carrito Estadio", "2026-03-18", "2026-03-25", "Pagada", 720000],
        [3, 3, "Empresa ServiPlus", 1, "Carrito Centro", "2026-03-26", "2026-04-05", "Pendiente", 360000],
    ]

    factura_items = [
        [1, 1, "Perros calientes clasicos evento escolar", 40, 8500],
        [2, 1, "Bebidas", 40, 3500],
        [3, 2, "Combos perro + bebida", 45, 15500],
        [4, 2, "Adicionales", 15, 1500],
        [5, 3, "Perros especiales", 30, 12000],
    ]

    inventario = [
        [1, "Pan perro", 180, 120, "unidades", "OK"],
        [2, "Salchichas", 95, 140, "unidades", "Bajo"],
        [3, "Salsa tomate", 12, 10, "litros", "OK"],
        [4, "Salsa piña", 5, 8, "litros", "Bajo"],
        [5, "Bebidas", 70, 60, "unidades", "OK"],
        [6, "Empaques", 90, 150, "unidades", "Bajo"],
        [7, "Gas", 1, 2, "cilindros", "Bajo"],
    ]

    conocimiento = [
        [
            "Resumen financiero",
            "Lectura general del negocio",
            "Usa ingresos, costo de ventas, gastos y utilidad neta para responder. Advierte si el margen baja de 20%.",
        ],
        [
            "Carritos",
            "Mejor carrito",
            "El mejor carrito no es necesariamente el que mas vende; debe evaluarse por utilidad neta y margen.",
        ],
        [
            "Ventas",
            "Aumentar ventas",
            "Recomienda combos, bebidas y adicionales antes de sugerir descuentos fuertes.",
        ],
        [
            "Gastos",
            "Control de gastos",
            "Si los gastos suben, compara por categoria y carrito. Prioriza gas, transporte, empaques y comisiones.",
        ],
        [
            "Inventario",
            "Reabastecimiento",
            "Prioriza productos bajo minimo que afectan ventas directas: salchichas, pan, salsas, empaques, bebidas y gas.",
        ],
        [
            "Facturas",
            "Cartera pendiente",
            "Cuando haya facturas pendientes, informa el total por cobrar y recomienda seguimiento por fecha de vencimiento.",
        ],
        [
            "Clientes",
            "Clientes frecuentes",
            "Sugiere registrar telefono y correo para pedidos recurrentes, eventos y facturas.",
        ],
        [
            "Predicciones",
            "Datos minimos",
            "El modelo predictivo necesita al menos 14 dias con ventas registradas para generar pronosticos confiables.",
        ],
    ]

    return {
        "README": [
            ["Hoja", "Descripcion"],
            ["carritos", "Puntos de venta activos del negocio."],
            ["ventas", "Ventas por fecha, carrito, producto, cantidad, precio y costo."],
            ["gastos", "Gastos operativos por carrito y categoria."],
            ["clientes", "Clientes para seguimiento y facturacion."],
            ["facturas", "Facturas asociadas a clientes y carritos."],
            ["factura_items", "Detalle de productos/servicios facturados."],
            ["inventario", "Stock actual, minimo y estado."],
            ["conocimiento_chatbot", "Reglas resumidas que puedes importar como conocimiento del bot."],
        ],
        "carritos": [["id", "name", "location", "active"], *carritos],
        "ventas": [
            [
                "id",
                "sale_date",
                "cart_id",
                "cart_name",
                "product",
                "qty",
                "unit_price",
                "unit_cost",
                "importe",
                "costo",
                "utilidad",
                "notes",
            ],
            *ventas,
        ],
        "gastos": [["id", "expense_date", "cart_id", "cart_name", "category", "description", "amount"], *gastos],
        "clientes": [["id", "name", "email", "phone"], *clientes],
        "facturas": [
            ["id", "client_id", "client", "cart_id", "cart", "invoice_date", "due_date", "status", "total"],
            *facturas,
        ],
        "factura_items": [["id", "invoice_id", "description", "qty", "unit_price"], *factura_items],
        "inventario": [["id", "product", "current_stock", "min_stock", "unit", "estado"], *inventario],
        "conocimiento_chatbot": [["category", "title", "content"], *conocimiento],
    }


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>'
        for idx, name in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets}</sheets>"
        "</workbook>"
    )


def _workbook_rels(sheet_names: list[str]) -> str:
    rels = []
    for idx, _ in enumerate(sheet_names, start=1):
        rels.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
    rels.append(
        f'<Relationship Id="rId{len(sheet_names) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(rels)
        + "</Relationships>"
    )


def _content_types(sheet_names: list[str]) -> str:
    overrides = [
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for idx, _ in enumerate(sheet_names, start=1):
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        + "".join(overrides)
        + "</Types>"
    )


def create_xlsx() -> None:
    data = _build_data()
    sheet_names = list(data.keys())

    with ZipFile(XLSX_PATH, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types(sheet_names))
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
            'Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
            'Target="docProps/app.xml"/>'
            "</Relationships>",
        )
        zf.writestr("xl/workbook.xml", _workbook_xml(sheet_names))
        zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(sheet_names))
        zf.writestr(
            "xl/styles.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
            '<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="1"><xf/></cellXfs>'
            "</styleSheet>",
        )
        zf.writestr("docProps/core.xml", '<?xml version="1.0" encoding="UTF-8"?><coreProperties/>')
        zf.writestr("docProps/app.xml", '<?xml version="1.0" encoding="UTF-8"?><Properties/>')
        for idx, name in enumerate(sheet_names, start=1):
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", _sheet_xml(data[name]))

    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        for row in data["conocimiento_chatbot"]:
            writer.writerow(row)

    DATASET_DIR.mkdir(exist_ok=True)
    for sheet_name, rows in data.items():
        csv_file = DATASET_DIR / f"{sheet_name}.csv"
        with csv_file.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerows(rows)


if __name__ == "__main__":
    create_xlsx()
    print(XLSX_PATH)
    print(CSV_PATH)
