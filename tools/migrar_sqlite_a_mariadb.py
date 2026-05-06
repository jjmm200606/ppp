from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQLITE_PATH = ROOT / "accounting.db"
SCHEMA_PATH_MARIADB = ROOT / "docs" / "schema_mariadb.sql"
SCHEMA_PATH_POSTGRES = ROOT / "docs" / "schema_postgresql.sql"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from lib.db import get_engine, is_postgres, seed_basic_accounts_for_user, upsert_accounts_sql


def _bootstrap_schema() -> None:
    schema_path = SCHEMA_PATH_POSTGRES if is_postgres() else SCHEMA_PATH_MARIADB
    raw_sql = schema_path.read_text(encoding="utf-8")
    statements: list[str] = []
    for chunk in raw_sql.split(";"):
        stmt = chunk.strip()
        if not stmt:
            continue
        upper = stmt.upper()
        if upper.startswith("CREATE DATABASE ") or upper.startswith("USE "):
            continue
        statements.append(stmt)

    eng = get_engine()
    raw = eng.raw_connection()
    try:
        cur = raw.cursor()
        for stmt in statements:
            cur.execute(stmt)
        raw.commit()
    finally:
        raw.close()


def _sqlite_rows(cn: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    cn.row_factory = sqlite3.Row
    return cn.execute(f"SELECT * FROM {table}").fetchall()


def _insert_and_get_id(cn, sql: str, params: dict) -> int:
    if is_postgres():
        row = cn.execute(text(sql + " RETURNING id"), params).first()
        return int(row[0])
    res = cn.execute(text(sql), params)
    return int(res.lastrowid)


def _upsert_user(username: str, password_hash: str) -> int:
    eng = get_engine()
    with eng.begin() as cn:
        existing = cn.execute(
            text("SELECT id FROM users WHERE username=:u"),
            {"u": username},
        ).scalar()
        if existing:
            cn.execute(
                text("UPDATE users SET password_hash=:p WHERE id=:i"),
                {"p": password_hash, "i": int(existing)},
            )
            return int(existing)

        return _insert_and_get_id(
            cn,
            "INSERT INTO users(username, password_hash) VALUES(:u, :p)",
            {"u": username, "p": password_hash},
        )


def _clear_user_data(user_id: int) -> None:
    eng = get_engine()
    with eng.begin() as cn:
        invoice_ids = [
            int(r[0])
            for r in cn.execute(
                text("SELECT id FROM invoices WHERE user_id=:u"),
                {"u": user_id},
            ).fetchall()
        ]
        for invoice_id in invoice_ids:
            cn.execute(
                text("DELETE FROM invoice_items WHERE invoice_id=:i"),
                {"i": invoice_id},
            )

        cn.execute(text("DELETE FROM invoices WHERE user_id=:u"), {"u": user_id})
        cn.execute(text("DELETE FROM cart_sales WHERE user_id=:u"), {"u": user_id})
        cn.execute(text("DELETE FROM cart_expenses WHERE user_id=:u"), {"u": user_id})
        cn.execute(text("DELETE FROM inventory WHERE user_id=:u"), {"u": user_id})
        cn.execute(text("DELETE FROM knowledge_base WHERE user_id=:u"), {"u": user_id})
        cn.execute(text("DELETE FROM clients WHERE user_id=:u"), {"u": user_id})
        cn.execute(text("DELETE FROM carts WHERE user_id=:u"), {"u": user_id})
        cn.execute(text("DELETE FROM accounts WHERE user_id=:u"), {"u": user_id})


def migrar() -> dict[str, int]:
    if not SQLITE_PATH.exists():
        raise FileNotFoundError(f"No existe la base SQLite local: {SQLITE_PATH}")

    _bootstrap_schema()

    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row

    users = _sqlite_rows(src, "users")
    if not users:
        raise ValueError("La base SQLite no tiene usuarios para migrar.")

    principal = users[0]
    username = str(principal["username"])
    password_hash = str(principal["password_hash"])
    user_id = _upsert_user(username, password_hash)
    _clear_user_data(user_id)

    counts = {
        "users": 1,
        "accounts": 0,
        "carts": 0,
        "sales": 0,
        "expenses": 0,
        "clients": 0,
        "invoices": 0,
        "invoice_items": 0,
    }

    eng = get_engine()
    with eng.begin() as cn:
        for row in _sqlite_rows(src, "accounts"):
            cn.execute(
                text(upsert_accounts_sql()),
                {"u": user_id, "c": row["code"], "n": row["name"], "t": row["type"]},
            )
            counts["accounts"] += 1

        cart_map: dict[int, int] = {}
        for row in _sqlite_rows(src, "carts"):
            cart_map[int(row["id"])] = _insert_and_get_id(
                cn,
                "INSERT INTO carts(user_id, name, location, active) VALUES(:u, :n, :l, :a)",
                {
                    "u": user_id,
                    "n": row["name"],
                    "l": row["location"] or "",
                    "a": int(row["active"] or 0),
                },
            )
            counts["carts"] += 1

        for row in _sqlite_rows(src, "cart_sales"):
            cart_id = cart_map.get(int(row["cart_id"]))
            if not cart_id:
                continue
            cn.execute(
                text("""
                    INSERT INTO cart_sales(user_id, sale_date, cart_id, product, qty, unit_price, unit_cost, notes)
                    VALUES(:u, :d, :c, :p, :q, :pu, :cu, :n)
                """),
                {
                    "u": user_id,
                    "d": row["sale_date"],
                    "c": cart_id,
                    "p": row["product"] or "Perro caliente",
                    "q": float(row["qty"] or 0),
                    "pu": float(row["unit_price"] or 0),
                    "cu": float(row["unit_cost"] or 0),
                    "n": row["notes"] or "",
                },
            )
            counts["sales"] += 1

        for row in _sqlite_rows(src, "cart_expenses"):
            cart_id = cart_map.get(int(row["cart_id"]))
            if not cart_id:
                continue
            cn.execute(
                text("""
                    INSERT INTO cart_expenses(user_id, expense_date, cart_id, category, description, amount)
                    VALUES(:u, :d, :c, :cat, :desc, :amt)
                """),
                {
                    "u": user_id,
                    "d": row["expense_date"],
                    "c": cart_id,
                    "cat": row["category"],
                    "desc": row["description"] or "",
                    "amt": float(row["amount"] or 0),
                },
            )
            counts["expenses"] += 1

        client_map: dict[int, int] = {}
        for row in _sqlite_rows(src, "clients"):
            client_map[int(row["id"])] = _insert_and_get_id(
                cn,
                "INSERT INTO clients(user_id, name, email, phone) VALUES(:u, :n, :e, :p)",
                {
                    "u": user_id,
                    "n": row["name"],
                    "e": row["email"] or "",
                    "p": row["phone"] or "",
                },
            )
            counts["clients"] += 1

        invoice_map: dict[int, int] = {}
        for row in _sqlite_rows(src, "invoices"):
            client_id = client_map.get(int(row["client_id"]))
            if not client_id:
                continue
            cart_id = cart_map.get(int(row["cart_id"])) if row["cart_id"] is not None else None
            invoice_map[int(row["id"])] = _insert_and_get_id(
                cn,
                """
                    INSERT INTO invoices(user_id, client_id, cart_id, invoice_date, due_date, status, total)
                    VALUES(:u, :cl, :ca, :fd, :dd, :st, :tt)
                """,
                {
                    "u": user_id,
                    "cl": client_id,
                    "ca": cart_id,
                    "fd": row["invoice_date"],
                    "dd": row["due_date"],
                    "st": row["status"] or "Pendiente",
                    "tt": float(row["total"] or 0),
                },
            )
            counts["invoices"] += 1

        for row in _sqlite_rows(src, "invoice_items"):
            invoice_id = invoice_map.get(int(row["invoice_id"]))
            if not invoice_id:
                continue
            cn.execute(
                text("""
                    INSERT INTO invoice_items(invoice_id, description, qty, unit_price)
                    VALUES(:i, :d, :q, :p)
                """),
                {
                    "i": invoice_id,
                    "d": row["description"],
                    "q": float(row["qty"] or 0),
                    "p": float(row["unit_price"] or 0),
                },
            )
            counts["invoice_items"] += 1

    seed_basic_accounts_for_user(user_id)
    src.close()
    return counts


if __name__ == "__main__":
    result = migrar()
    print("Migracion completada:")
    for key, value in result.items():
        print(f" - {key}: {value}")
