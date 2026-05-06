# lib/patterns/facade.py
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Tuple
from sqlalchemy import text

from lib.db import get_engine, is_postgres, upsert_inventory_sql
from lib.patterns.observer import notify_observers, Event
from lib.strategies.precio import PrecioFactory

class AccountingFacade:
    """
    Fachada: todas las operaciones del dominio.
    **Multitenant por usuario**: cada consulta filtra por user_id y cada inserción lo guarda.
    """

    def __init__(self, user_id: int = 0):
        self._user_id = int(user_id or 0)

    # helpers internos
    def _eng(self):
        return get_engine()

    def _uid(self) -> int:
        return self._user_id

    def _fetchall(self, sql: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        params = params or {}
        with self._eng().connect() as cn:
            rows = cn.execute(text(sql), params).mappings().all()
            return [dict(r) for r in rows]

    def _execute(self, sql: str, params: Dict[str, Any]) -> None:
        with self._eng().begin() as cn:
            cn.execute(text(sql), params)

    def _insert_and_get_id(self, cn, sql: str, params: Dict[str, Any]) -> int:
        if is_postgres():
            row = cn.execute(text(sql + " RETURNING id"), params).first()
            return int(row[0])
        res = cn.execute(text(sql), params)
        return int(res.lastrowid)

    def _notify(self, event: str, payload: Dict[str, Any]) -> None:
        notify_observers(event, payload)

    def importar_dataset_proyecto(self, dataset: Dict[str, List[Dict[str, Any]]], *, replace: bool = True) -> Dict[str, int]:
        """Importa un dataset completo del proyecto para el usuario actual.
        Usa nombres de carrito/cliente para reconstruir relaciones aunque cambien los IDs.
        """
        u = self._uid()
        if not u:
            raise ValueError("Usuario no valido para importar datos.")

        counts = {
            "carritos": 0,
            "ventas": 0,
            "gastos": 0,
            "clientes": 0,
            "facturas": 0,
            "factura_items": 0,
            "inventario": 0,
            "conocimiento": 0,
        }

        with self._eng().begin() as cn:
            if replace:
                if is_postgres():
                    cn.execute(text("""
                        DELETE FROM invoice_items
                        WHERE invoice_id IN (
                            SELECT id FROM invoices WHERE user_id = :u
                        )
                    """), {"u": u})
                else:
                    cn.execute(text("""
                        DELETE ii FROM invoice_items ii
                        INNER JOIN invoices i ON i.id = ii.invoice_id
                        WHERE i.user_id = :u
                    """), {"u": u})
                cn.execute(text("DELETE FROM invoices WHERE user_id=:u"), {"u": u})
                cn.execute(text("DELETE FROM cart_sales WHERE user_id=:u"), {"u": u})
                cn.execute(text("DELETE FROM cart_expenses WHERE user_id=:u"), {"u": u})
                cn.execute(text("DELETE FROM inventory WHERE user_id=:u"), {"u": u})
                cn.execute(text("DELETE FROM clients WHERE user_id=:u"), {"u": u})
                cn.execute(text("DELETE FROM carts WHERE user_id=:u"), {"u": u})
                cn.execute(text("DELETE FROM knowledge_base WHERE user_id=:u"), {"u": u})

            cart_name_to_id: Dict[str, int] = {}
            for row in dataset.get("carritos", []):
                name = str(row.get("name") or "").strip()
                if not name:
                    continue
                location = str(row.get("location") or "").strip()
                active_raw = str(row.get("active") if row.get("active") is not None else "1").strip().lower()
                active = 0 if active_raw in {"0", "false", "no"} else 1
                cart_name_to_id[name] = self._insert_and_get_id(
                    cn,
                    "INSERT INTO carts(user_id, name, location, active) VALUES(:u, :n, :l, :a)",
                    {"u": u, "n": name, "l": location, "a": active},
                )
                counts["carritos"] += 1

            client_name_to_id: Dict[str, int] = {}
            for row in dataset.get("clientes", []):
                name = str(row.get("name") or "").strip()
                if not name:
                    continue
                email = str(row.get("email") or "").strip()
                phone = str(row.get("phone") or "").strip()
                client_name_to_id[name] = self._insert_and_get_id(
                    cn,
                    "INSERT INTO clients(user_id, name, email, phone) VALUES(:u, :n, :e, :p)",
                    {"u": u, "n": name, "e": email, "p": phone},
                )
                counts["clientes"] += 1

            for row in dataset.get("ventas", []):
                cart_name = str(row.get("cart_name") or "").strip()
                cart_id = cart_name_to_id.get(cart_name)
                if not cart_id:
                    continue
                cn.execute(
                    text("""
                        INSERT INTO cart_sales(user_id, sale_date, cart_id, product, qty, unit_price, unit_cost, notes)
                        VALUES(:u, :d, :c, :p, :q, :pu, :cu, :n)
                    """),
                    {
                        "u": u,
                        "d": str(row.get("sale_date") or "").strip(),
                        "c": cart_id,
                        "p": str(row.get("product") or "Perro caliente").strip() or "Perro caliente",
                        "q": float(row.get("qty") or 0),
                        "pu": float(row.get("unit_price") or 0),
                        "cu": float(row.get("unit_cost") or 0),
                        "n": str(row.get("notes") or "").strip(),
                    },
                )
                counts["ventas"] += 1

            for row in dataset.get("gastos", []):
                cart_name = str(row.get("cart_name") or "").strip()
                cart_id = cart_name_to_id.get(cart_name)
                if not cart_id:
                    continue
                cn.execute(
                    text("""
                        INSERT INTO cart_expenses(user_id, expense_date, cart_id, category, description, amount)
                        VALUES(:u, :d, :c, :cat, :desc, :amt)
                    """),
                    {
                        "u": u,
                        "d": str(row.get("expense_date") or "").strip(),
                        "c": cart_id,
                        "cat": str(row.get("category") or "General").strip() or "General",
                        "desc": str(row.get("description") or "").strip(),
                        "amt": float(row.get("amount") or 0),
                    },
                )
                counts["gastos"] += 1

            invoice_old_to_new: Dict[str, int] = {}
            for row in dataset.get("facturas", []):
                client_name = str(row.get("client") or "").strip()
                client_id = client_name_to_id.get(client_name)
                if not client_id:
                    continue
                cart_name = str(row.get("cart") or "").strip()
                cart_id = cart_name_to_id.get(cart_name) if cart_name else None
                invoice_old_to_new[old_id] = self._insert_and_get_id(
                    cn,
                    """
                        INSERT INTO invoices(user_id, client_id, invoice_date, due_date, status, total, cart_id)
                        VALUES(:u, :cl, :fd, :vd, :st, :tt, :ca)
                    """,
                    {
                        "u": u,
                        "cl": client_id,
                        "fd": str(row.get("invoice_date") or "").strip(),
                        "vd": str(row.get("due_date") or "").strip(),
                        "st": str(row.get("status") or "Pendiente").strip() or "Pendiente",
                        "tt": float(row.get("total") or 0),
                        "ca": cart_id,
                    },
                )
                old_id = str(row.get("id") or "").strip()
                counts["facturas"] += 1

            for row in dataset.get("factura_items", []):
                old_invoice_id = str(row.get("invoice_id") or "").strip()
                new_invoice_id = invoice_old_to_new.get(old_invoice_id)
                if not new_invoice_id:
                    continue
                description = str(row.get("description") or "").strip()
                qty = float(row.get("qty") or 0)
                if not description or qty <= 0:
                    continue
                cn.execute(
                    text("""
                        INSERT INTO invoice_items(invoice_id, description, qty, unit_price)
                        VALUES(:i, :d, :q, :p)
                    """),
                    {
                        "i": new_invoice_id,
                        "d": description,
                        "q": qty,
                        "p": float(row.get("unit_price") or 0),
                    },
                )
                counts["factura_items"] += 1

            for row in dataset.get("inventario", []):
                product = str(row.get("product") or "").strip()
                if not product:
                    continue
                cn.execute(
                    text(upsert_inventory_sql()),
                    {
                        "u": u,
                        "p": product,
                        "cs": float(row.get("current_stock") or 0),
                        "ms": float(row.get("min_stock") or 0),
                        "un": str(row.get("unit") or "unidades").strip() or "unidades",
                    },
                )
                counts["inventario"] += 1

            for row in dataset.get("conocimiento_chatbot", []):
                title = str(row.get("title") or "").strip()
                content = str(row.get("content") or "").strip()
                if not title or not content:
                    continue
                cn.execute(
                    text("""
                        INSERT INTO knowledge_base(user_id, category, title, content)
                        VALUES(:u, :cat, :tit, :con)
                    """),
                    {
                        "u": u,
                        "cat": str(row.get("category") or "General").strip() or "General",
                        "tit": title,
                        "con": content,
                    },
                )
                counts["conocimiento"] += 1

        return counts

    #Carritos
    def listar_carritos(self, solo_activos: bool = False) -> List[Dict[str, Any]]:
        u = self._uid()
        where = " AND active=1" if solo_activos else ""
        sql = f"""
        SELECT id, name, location, active
        FROM carts
        WHERE user_id=:u{where}
        ORDER BY id DESC;
        """
        return self._fetchall(sql, {"u": u})

    def crear_carrito(self, *, name: str, location: str = "", active: bool = True) -> None:
        u = self._uid()
        self._execute(
            "INSERT INTO carts(user_id,name,location,active) VALUES(:u,:n,:l,:a)",
            {"u": u, "n": name.strip(), "l": location.strip(), "a": 1 if active else 0},
        )
        self._notify(Event.CART_CREATED, {"name": name, "location": location, "active": bool(active)})

    # Ventas
    def listar_ventas(self) -> List[Dict[str, Any]]:
        u = self._uid()
        sql = """
        SELECT cs.id, cs.sale_date, c.name AS cart_name, cs.product,
               cs.qty, cs.unit_price, cs.unit_cost, cs.notes,
               ROUND(cs.qty*cs.unit_price,2) AS importe,
               ROUND(cs.qty*cs.unit_cost,2)  AS costo,
               ROUND(cs.qty*cs.unit_price - cs.qty*cs.unit_cost,2) AS utilidad
        FROM cart_sales cs
        JOIN carts c ON c.id=cs.cart_id
        WHERE cs.user_id=:u
        ORDER BY cs.sale_date DESC, cs.id DESC;
        """
        return self._fetchall(sql, {"u": u})

    def crear_venta(self, *, sale_date: str, cart_id: int, product: str,
                    qty: float, unit_price: float, unit_cost: float, notes: str = "") -> None:
        u = self._uid()
        # estrategia de utilidad (por si la necesitas en UI)
        estrategia = PrecioFactory.get()
        _ = estrategia.utilidad(qty, unit_price, unit_cost)

        self._execute(
            """
            INSERT INTO cart_sales(user_id, sale_date, cart_id, product, qty, unit_price, unit_cost, notes)
            VALUES(:u,:d,:c,:p,:q,:pu,:cu,:n)
            """,
            {"u": u, "d": sale_date, "c": cart_id, "p": product.strip() or "Perro caliente",
             "q": qty, "pu": unit_price, "cu": unit_cost, "n": notes.strip()},
        )
        self._notify(Event.SALE_CREATED, {
            "sale_date": sale_date, "cart_id": cart_id, "product": product,
            "qty": float(qty), "unit_price": float(unit_price), "unit_cost": float(unit_cost), "notes": notes
        })

    def eliminar_venta(self, sale_id: int) -> None:
        u = self._uid()
        self._execute(
            "DELETE FROM cart_sales WHERE id=:id AND user_id=:u",
            {"id": int(sale_id), "u": u},
        )

    # Gastos
    def listar_gastos(self) -> List[Dict[str, Any]]:
        u = self._uid()
        sql = """
        SELECT ce.id, ce.expense_date, c.name AS cart_name,
               ce.category, ce.description, ce.amount
        FROM cart_expenses ce
        JOIN carts c ON c.id=ce.cart_id
        WHERE ce.user_id=:u
        ORDER BY ce.expense_date DESC, ce.id DESC;
        """
        return self._fetchall(sql, {"u": u})

    def crear_gasto(self, *, expense_date: str, cart_id: int, category: str,
                    description: str, amount: float) -> None:
        u = self._uid()
        self._execute(
            """
            INSERT INTO cart_expenses(user_id, expense_date, cart_id, category, description, amount)
            VALUES(:u,:d,:c,:cat,:desc,:amt)
            """,
            {"u": u, "d": expense_date, "c": cart_id, "cat": category,
             "desc": description.strip(), "amt": amount},
        )
        self._notify(Event.EXPENSE_CREATED, {
            "expense_date": expense_date, "cart_id": cart_id, "category": category,
            "description": description, "amount": float(amount)
        })

    # KPIs / Panel
    def kpis(self) -> Dict[str, float]:
        u = self._uid()
        sql_ing = "SELECT COALESCE(SUM(qty*unit_price),0) FROM cart_sales WHERE user_id=:u"
        sql_cos = "SELECT COALESCE(SUM(qty*unit_cost),0)  FROM cart_sales WHERE user_id=:u"
        sql_gas = "SELECT COALESCE(SUM(amount),0)         FROM cart_expenses WHERE user_id=:u"
        with self._eng().connect() as cn:
            ingresos = float(cn.execute(text(sql_ing), {"u": u}).scalar() or 0)
            costo    = float(cn.execute(text(sql_cos), {"u": u}).scalar() or 0)
            gastos   = float(cn.execute(text(sql_gas), {"u": u}).scalar() or 0)
        utilidad = ingresos - costo - gastos
        return {"ingresos": ingresos, "costo": costo, "gastos": gastos, "utilidad": utilidad}

    def top_carritos_utilidad(self) -> List[Dict[str, Any]]:
        u = self._uid()
        sql = """
        WITH ventas AS (
            SELECT cart_id, COALESCE(SUM(qty*unit_price),0) AS ingreso,
                   COALESCE(SUM(qty*unit_cost),0)  AS costo
            FROM cart_sales WHERE user_id=:u GROUP BY cart_id
        ), gastos AS (
            SELECT cart_id, COALESCE(SUM(amount),0) AS gasto
            FROM cart_expenses WHERE user_id=:u GROUP BY cart_id
        )
        SELECT c.id, c.name, c.location,
               COALESCE(v.ingreso,0) AS ingresos,
               COALESCE(v.costo,0)   AS costo,
               COALESCE(g.gasto,0)   AS gastos,
               COALESCE(v.ingreso,0)-COALESCE(v.costo,0)-COALESCE(g.gasto,0) AS utilidad
        FROM carts c
        LEFT JOIN ventas v ON v.cart_id=c.id
        LEFT JOIN gastos g ON g.cart_id=c.id
        WHERE c.user_id=:u
        ORDER BY utilidad DESC;
        """
        return self._fetchall(sql, {"u": u})

    #  Reporte por carrito
    def resumen_por_carrito(self, cart_id: int, start: str, end: str) -> Dict[str, float]:
        u = self._uid()
        sql = """
        WITH ventas AS (
            SELECT COALESCE(SUM(qty*unit_price),0) AS ingreso,
                   COALESCE(SUM(qty*unit_cost),0)  AS costo
            FROM cart_sales
            WHERE user_id=:u AND cart_id=:c AND sale_date BETWEEN :s AND :e
        ), gastos AS (
            SELECT COALESCE(SUM(amount),0) AS gasto
            FROM cart_expenses
            WHERE user_id=:u AND cart_id=:c AND expense_date BETWEEN :s AND :e
        )
        SELECT (SELECT ingreso FROM ventas)  AS ingresos,
               (SELECT costo   FROM ventas)  AS costo,
               (SELECT gasto   FROM gastos)  AS gastos;
        """
        r = self._fetchall(sql, {"u": u, "c": cart_id, "s": start, "e": end})[0]
        ingresos, costo, gastos = float(r["ingresos"]), float(r["costo"]), float(r["gastos"])
        return {"ingresos": ingresos, "costo": costo, "gastos": gastos, "utilidad": ingresos - costo - gastos}

    def detalle_ventas_carrito(self, cart_id: int, start: str, end: str) -> List[Dict[str, Any]]:
        u = self._uid()
        sql = """
        SELECT sale_date, product, qty, unit_price, unit_cost,
               ROUND(qty*unit_price,2) AS importe,
               ROUND(qty*unit_cost,2)  AS costo
        FROM cart_sales
        WHERE user_id=:u AND cart_id=:c AND sale_date BETWEEN :s AND :e
        ORDER BY sale_date DESC, id DESC;
        """
        return self._fetchall(sql, {"u": u, "c": cart_id, "s": start, "e": end})

    def detalle_gastos_carrito(self, cart_id: int, start: str, end: str) -> List[Dict[str, Any]]:
        u = self._uid()
        sql = """
        SELECT expense_date, category, description, amount
        FROM cart_expenses
        WHERE user_id=:u AND cart_id=:c AND expense_date BETWEEN :s AND :e
        ORDER BY expense_date DESC, id DESC;
        """
        return self._fetchall(sql, {"u": u, "c": cart_id, "s": start, "e": end})

    # Clientes
    def listar_clientes(self) -> List[Dict[str, Any]]:
        u = self._uid()
        sql = "SELECT id, name, email, phone, created_at FROM clients WHERE user_id=:u ORDER BY id DESC"
        return self._fetchall(sql, {"u": u})

    def crear_cliente(self, *, name: str, email: str = "", phone: str = "") -> None:
        u = self._uid()
        self._execute(
            "INSERT INTO clients(user_id,name,email,phone) VALUES(:u,:n,:e,:p)",
            {"u": u, "n": name.strip(), "e": email.strip(), "p": phone.strip()},
        )
        self._notify(Event.CLIENT_CREATED, {"name": name, "email": email, "phone": phone})

    #Facturas 
    def listar_facturas(self) -> List[Dict[str, Any]]:
        u = self._uid()
        sql = """
        SELECT i.id, c.name AS client, i.invoice_date, i.due_date, i.status, i.total,
               (SELECT name FROM carts WHERE id=i.cart_id) AS cart
        FROM invoices i
        JOIN clients c ON c.id=i.client_id
        WHERE i.user_id=:u
        ORDER BY i.id DESC;
        """
        return self._fetchall(sql, {"u": u})

    def crear_factura(self, *, client_id: int, cart_id: int | None, invoice_date: str,
                      due_date: str, status: str, total: float,
                      items: List[Tuple[str, float, float]]) -> int:
        u = self._uid()
        with self._eng().begin() as cn:
            inv_id = self._insert_and_get_id(
                cn,
                """INSERT INTO invoices(user_id, client_id, invoice_date, due_date, status, total, cart_id)
                        VALUES(:u,:cl,:fd,:vd,:st,:tt,:ca)""",
                {"u": u, "cl": client_id, "fd": invoice_date, "vd": due_date,
                 "st": status, "tt": total, "ca": cart_id}
            )
            for desc, qty, price in items:
                if desc.strip() and qty > 0:
                    cn.execute(
                        text("INSERT INTO invoice_items(invoice_id, description, qty, unit_price) "
                             "VALUES(:i,:d,:q,:p)"),
                        {"i": inv_id, "d": desc.strip(), "q": qty, "p": price}
                    )
        self._notify(Event.INVOICE_CREATED, {"invoice_id": int(inv_id), "client_id": client_id, "total": float(total)})
        return int(inv_id)

    # Cuentas contables 
    def listar_cuentas(self) -> List[Dict[str, Any]]:
        u = self._uid()
        sql = "SELECT code, name, type FROM accounts WHERE user_id=:u ORDER BY code"
        return self._fetchall(sql, {"u": u})

    def crear_cuenta(self, *, code: str, name: str, type_: str) -> None:
        u = self._uid()
        self._execute(
            "INSERT INTO accounts(user_id, code, name, type) VALUES(:u,:c,:n,:t)",
            {"u": u, "c": code.strip(), "n": name.strip(), "t": type_},
        )
        self._notify(Event.ACCOUNT_CREATED, {"code": code, "name": name, "type": type_})

    # Inventario / Stock
    def listar_stock(self) -> List[Dict[str, Any]]:
        u = self._uid()
        sql = """
        SELECT id, product, current_stock, min_stock, unit, updated_at,
               CASE WHEN current_stock < min_stock THEN 1 ELSE 0 END AS bajo_stock
        FROM inventory
        WHERE user_id=:u
        ORDER BY product ASC;
        """
        return self._fetchall(sql, {"u": u})

    def stock_bajo(self) -> List[Dict[str, Any]]:
        """Devuelve solo los productos con stock por debajo del mínimo."""
        u = self._uid()
        sql = """
        SELECT product, current_stock, min_stock, unit,
               ROUND(min_stock - current_stock, 2) AS faltante
        FROM inventory
        WHERE user_id=:u AND current_stock < min_stock
        ORDER BY faltante DESC;
        """
        return self._fetchall(sql, {"u": u})

    def guardar_stock(self, *, product: str, current_stock: float,
                      min_stock: float, unit: str = "unidades") -> None:
        """Inserta o actualiza un producto en el inventario."""
        u = self._uid()
        self._execute(
            upsert_inventory_sql(),
            {"u": u, "p": product.strip(), "cs": current_stock,
             "ms": min_stock, "un": unit.strip() or "unidades"},
        )

    def eliminar_stock(self, stock_id: int) -> None:
        u = self._uid()
        self._execute(
            "DELETE FROM inventory WHERE id=:i AND user_id=:u",
            {"i": stock_id, "u": u},
        )

    # ──────────────────────────────────────────────────────────────
    # Métodos de ADMINISTRADOR — sin filtro de usuario
    # Solo llamar desde páginas protegidas con require_admin()
    # ──────────────────────────────────────────────────────────────

    def admin_resumen_usuarios(self) -> List[Dict[str, Any]]:
        """Retorna KPIs financieros agrupados por usuario."""
        sql = """
        SELECT u.id AS user_id, u.username,
               COALESCE(SUM(cs.qty * cs.unit_price), 0)                          AS ingresos,
               COALESCE(SUM(cs.qty * cs.unit_cost),  0)                          AS costo,
               COALESCE((SELECT SUM(amount)
                         FROM cart_expenses ce
                         WHERE ce.user_id = u.id), 0)                            AS gastos,
               COALESCE(SUM(cs.qty * cs.unit_price), 0)
                 - COALESCE(SUM(cs.qty * cs.unit_cost), 0)
                 - COALESCE((SELECT SUM(amount)
                              FROM cart_expenses ce
                              WHERE ce.user_id = u.id), 0)                       AS utilidad,
               COUNT(DISTINCT cs.cart_id)                                        AS carritos,
               COUNT(cs.id)                                                      AS num_ventas
        FROM users u
        LEFT JOIN cart_sales cs ON cs.user_id = u.id
        GROUP BY u.id, u.username
        ORDER BY utilidad DESC;
        """
        return self._fetchall(sql, {})

    def admin_listar_carritos(self) -> List[Dict[str, Any]]:
        """Retorna todos los carritos de todos los usuarios."""
        sql = """
        SELECT c.id, u.username, c.name, c.location, c.active,
               COALESCE(SUM(cs.qty * cs.unit_price), 0) AS ingresos,
               COALESCE(SUM(cs.qty * cs.unit_cost),  0) AS costo,
               COALESCE((SELECT SUM(amount) FROM cart_expenses ce
                         WHERE ce.cart_id = c.id), 0)    AS gastos,
               COALESCE(SUM(cs.qty * cs.unit_price), 0)
                 - COALESCE(SUM(cs.qty * cs.unit_cost), 0)
                 - COALESCE((SELECT SUM(amount) FROM cart_expenses ce
                              WHERE ce.cart_id = c.id), 0) AS utilidad
        FROM carts c
        JOIN users u ON u.id = c.user_id
        LEFT JOIN cart_sales cs ON cs.cart_id = c.id
        GROUP BY c.id, u.username, c.name, c.location, c.active
        ORDER BY utilidad DESC;
        """
        return self._fetchall(sql, {})

    def admin_kpis_globales(self) -> Dict[str, float]:
        """KPIs totales de toda la plataforma."""
        sql_ing = "SELECT COALESCE(SUM(qty*unit_price),0) FROM cart_sales"
        sql_cos = "SELECT COALESCE(SUM(qty*unit_cost),0)  FROM cart_sales"
        sql_gas = "SELECT COALESCE(SUM(amount),0)         FROM cart_expenses"
        sql_usr = "SELECT COUNT(*)                        FROM users"
        with self._eng().connect() as cn:
            ingresos = float(cn.execute(text(sql_ing)).scalar() or 0)
            costo    = float(cn.execute(text(sql_cos)).scalar() or 0)
            gastos   = float(cn.execute(text(sql_gas)).scalar() or 0)
            usuarios = int(cn.execute(text(sql_usr)).scalar() or 0)
        return {
            "ingresos": ingresos, "costo": costo,
            "gastos": gastos, "utilidad": ingresos - costo - gastos,
            "usuarios": usuarios,
        }

    # ──────────────────────────────────────────────────────────────
    # Base de conocimiento del chatbot
    # ──────────────────────────────────────────────────────────────

    def listar_conocimiento(self, solo_activos: bool = True) -> List[Dict[str, Any]]:
        u = self._uid()
        where = "AND active=1" if solo_activos else ""
        sql = f"""
        SELECT id, category, title, content, active, created_at
        FROM knowledge_base
        WHERE user_id=:u {where}
        ORDER BY category, id ASC;
        """
        return self._fetchall(sql, {"u": u})

    def agregar_conocimiento(self, *, category: str, title: str, content: str) -> None:
        u = self._uid()
        self._execute(
            """INSERT INTO knowledge_base(user_id, category, title, content)
               VALUES(:u, :cat, :tit, :con)""",
            {"u": u, "cat": category.strip(), "tit": title.strip(), "con": content.strip()},
        )

    def actualizar_conocimiento(self, kb_id: int, *, category: str,
                                 title: str, content: str, active: bool) -> None:
        u = self._uid()
        self._execute(
            """UPDATE knowledge_base
               SET category=:cat, title=:tit, content=:con, active=:act
               WHERE id=:i AND user_id=:u""",
            {"cat": category.strip(), "tit": title.strip(), "con": content.strip(),
             "act": 1 if active else 0, "i": kb_id, "u": u},
        )

    def eliminar_conocimiento(self, kb_id: int) -> None:
        u = self._uid()
        self._execute(
            "DELETE FROM knowledge_base WHERE id=:i AND user_id=:u",
            {"i": kb_id, "u": u},
        )

    def generar_insights_automaticos(self) -> int:
        """Analiza la BD y regenera los insights automáticos en knowledge_base.
        Devuelve el número de insights generados."""
        u = self._uid()
        ventas  = self.listar_ventas()
        gastos  = self.listar_gastos()
        kpis    = self.kpis()
        insights: List[Dict[str, str]] = []

        # ── Calcular insights solo si hay datos ───────────────────
        if ventas:
            import pandas as pd

            df_v = pd.DataFrame(ventas)
            df_v["importe"]  = pd.to_numeric(df_v["importe"],  errors="coerce").fillna(0)
            df_v["utilidad"] = pd.to_numeric(df_v["utilidad"], errors="coerce").fillna(0)
            df_v["sale_date"] = pd.to_datetime(df_v["sale_date"])
            df_v["dia_semana"] = df_v["sale_date"].dt.day_name()
            df_v["mes"] = df_v["sale_date"].dt.to_period("M").astype(str)

            # Día con más ventas
            dia_top = df_v.groupby("dia_semana")["importe"].sum().idxmax()
            dia_val = df_v.groupby("dia_semana")["importe"].sum().max()
            insights.append({
                "category": "Tendencias de ventas",
                "title": "Día con más ventas",
                "content": f"El día con más ingresos es {dia_top} con un total acumulado de ${dia_val:,.2f}.",
            })

            # Producto más vendido
            prod_top = df_v.groupby("product")["importe"].sum().idxmax()
            prod_val = df_v.groupby("product")["importe"].sum().max()
            insights.append({
                "category": "Tendencias de ventas",
                "title": "Producto más vendido",
                "content": f"El producto con más ingresos es '{prod_top}' con ${prod_val:,.2f} en ventas totales.",
            })

            # Carrito con más ingresos
            cart_top = df_v.groupby("cart_name")["importe"].sum().idxmax()
            cart_val = df_v.groupby("cart_name")["importe"].sum().max()
            insights.append({
                "category": "Rendimiento por carrito",
                "title": "Carrito con más ingresos",
                "content": f"El carrito '{cart_top}' es el que más ingresos genera con ${cart_val:,.2f} acumulados.",
            })

            # Carrito con mejor margen
            cart_mg = df_v.groupby("cart_name")[["importe","utilidad"]].sum()
            cart_mg = cart_mg[cart_mg["importe"] > 0]
            if not cart_mg.empty:
                cart_mg["margen"] = (cart_mg["utilidad"] / cart_mg["importe"] * 100).round(1)
                mejor = cart_mg["margen"].idxmax()
                mval  = cart_mg.loc[mejor, "margen"]
                insights.append({
                    "category": "Rendimiento por carrito",
                    "title": "Carrito con mejor margen",
                    "content": f"El carrito '{mejor}' tiene el mejor margen de utilidad bruta: {mval}%.",
                })

            # Mes con más ventas
            mes_top = df_v.groupby("mes")["importe"].sum().idxmax()
            mes_val = df_v.groupby("mes")["importe"].sum().max()
            insights.append({
                "category": "Tendencias de ventas",
                "title": "Mes con más ingresos",
                "content": f"El mes con más ingresos registrado es {mes_top} con ${mes_val:,.2f}.",
            })

            # Ticket promedio
            ticket_avg = df_v["importe"].mean()
            insights.append({
                "category": "Tendencias de ventas",
                "title": "Ticket promedio por venta",
                "content": f"El valor promedio por registro de venta es ${ticket_avg:,.2f}.",
            })

        if gastos:
            import pandas as pd
            df_g = pd.DataFrame(gastos)
            df_g["amount"] = pd.to_numeric(df_g["amount"], errors="coerce").fillna(0)

            # Categoría de gasto más alta
            cat_top = df_g.groupby("category")["amount"].sum().idxmax()
            cat_val = df_g.groupby("category")["amount"].sum().max()
            insights.append({
                "category": "Análisis de gastos",
                "title": "Categoría de gasto más alta",
                "content": f"La categoría de gasto con más dinero invertido es '{cat_top}' con ${cat_val:,.2f}.",
            })

        # KPIs globales
        insights.append({
            "category": "Resumen financiero",
            "title": "Resumen financiero general",
            "content": (
                f"Ingresos totales: ${kpis['ingresos']:,.2f}. "
                f"Costo de ventas: ${kpis['costo']:,.2f}. "
                f"Gastos operativos: ${kpis['gastos']:,.2f}. "
                f"Utilidad neta: ${kpis['utilidad']:,.2f}."
            ),
        })

        # ── Borrar insights anteriores y reinsertar ───────────────
        self._execute(
            "DELETE FROM knowledge_base WHERE user_id=:u AND category IN "
            "('Tendencias de ventas','Rendimiento por carrito','Análisis de gastos','Resumen financiero')",
            {"u": u},
        )
        for item in insights:
            self.agregar_conocimiento(
                category=item["category"],
                title=item["title"],
                content=item["content"],
            )
        return len(insights)
