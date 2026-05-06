# lib/db.py
from __future__ import annotations
import os
import hashlib
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --------------------------------------------------------------------
# Conexión a MariaDB / MySQL
# --------------------------------------------------------------------
_ENGINE: Engine | None = None


def _clean_env(value: str | None) -> str:
    return (value or "").strip().strip('"').strip("'")


def _build_db_url() -> str:
    direct_url = (
        _clean_env(os.getenv("DATABASE_URL"))
        or _clean_env(os.getenv("MYSQL_URL"))
        or _clean_env(os.getenv("MARIADB_URL"))
        or _clean_env(os.getenv("MYSQL_PUBLIC_URL"))
    )
    if direct_url:
        url = direct_url
        if url.startswith("mysql://"):
            url = "mysql+pymysql://" + url[len("mysql://"):]
        return url

    host = _clean_env(os.getenv("MARIADB_HOST")) or _clean_env(os.getenv("MYSQLHOST")) or "127.0.0.1"
    port = int(_clean_env(os.getenv("MARIADB_PORT")) or _clean_env(os.getenv("MYSQLPORT")) or "3307")
    user = _clean_env(os.getenv("MARIADB_USER")) or _clean_env(os.getenv("MYSQLUSER")) or "root"
    pwd  = _clean_env(os.getenv("MARIADB_PASSWORD")) or _clean_env(os.getenv("MYSQLPASSWORD")) or ""
    db   = _clean_env(os.getenv("MARIADB_DB")) or _clean_env(os.getenv("MYSQLDATABASE")) or "perrospacho"
    return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"


def get_db_debug_snapshot() -> dict[str, str]:
    url = _build_db_url()
    safe_url = url
    if "@" in safe_url and "://" in safe_url:
        scheme, rest = safe_url.split("://", 1)
        creds, tail = rest.split("@", 1)
        if ":" in creds:
            user, _pwd = creds.split(":", 1)
            safe_url = f"{scheme}://{user}:***@{tail}"

    return {
        "DATABASE_URL": "set" if _clean_env(os.getenv("DATABASE_URL")) else "empty",
        "MYSQL_URL": "set" if _clean_env(os.getenv("MYSQL_URL")) else "empty",
        "MARIADB_URL": "set" if _clean_env(os.getenv("MARIADB_URL")) else "empty",
        "MYSQL_PUBLIC_URL": "set" if _clean_env(os.getenv("MYSQL_PUBLIC_URL")) else "empty",
        "MARIADB_HOST": _clean_env(os.getenv("MARIADB_HOST")) or "(empty)",
        "MYSQLHOST": _clean_env(os.getenv("MYSQLHOST")) or "(empty)",
        "resolved_url": safe_url,
    }

def get_engine() -> Engine:
    """
    Retorna la conexión global del motor SQLAlchemy (MariaDB).
    Lee las variables de entorno: MARIADB_HOST, MARIADB_USER, MARIADB_PASSWORD, MARIADB_DB.
    """
    global _ENGINE
    url = _build_db_url()
    current_url = str(_ENGINE.url) if _ENGINE is not None else None
    if _ENGINE is None or current_url != url:
        _ENGINE = create_engine(url, pool_pre_ping=True, future=True)
    return _ENGINE


# --------------------------------------------------------------------
# Funciones de autenticación y usuarios
# --------------------------------------------------------------------
def _hash_password(raw: str) -> str:
    """Devuelve el hash SHA-256 de la contraseña."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_login(username: str, password: str) -> bool:
    """Valida que el usuario exista y la contraseña coincida."""
    if not username or not password:
        return False
    eng = get_engine()
    with eng.connect() as cn:
        row = cn.execute(
            text("SELECT password_hash FROM users WHERE username=:u"),
            {"u": username}
        ).first()
        if not row:
            return False
        return row[0] == _hash_password(password)


def username_exists(username: str) -> bool:
    """Verifica si el usuario ya existe."""
    eng = get_engine()
    with eng.connect() as cn:
        cnt = cn.execute(
            text("SELECT COUNT(*) FROM users WHERE username=:u"),
            {"u": username}
        ).scalar() or 0
        return cnt > 0


def create_user(username: str, password: str) -> bool:
    """Crea un nuevo usuario si no existe."""
    if username_exists(username):
        return False
    eng = get_engine()
    with eng.begin() as cn:
        cn.execute(
            text("INSERT INTO users(username, password_hash) VALUES(:u,:p)"),
            {"u": username, "p": _hash_password(password)}
        )
    return True


_ADMIN_USERNAME = "admin"

def is_admin(username: str) -> bool:
    """Retorna True si el usuario es administrador del sistema."""
    return (username or "").strip().lower() == _ADMIN_USERNAME


def get_all_users() -> list:
    """Devuelve la lista de todos los usuarios (id, username). Solo para admin."""
    eng = get_engine()
    with eng.connect() as cn:
        rows = cn.execute(text("SELECT id, username FROM users ORDER BY id")).mappings().all()
        return [dict(r) for r in rows]


def get_user_id(username: str) -> Optional[int]:
    """Devuelve el ID del usuario dado su nombre."""
    eng = get_engine()
    with eng.connect() as cn:
        return cn.execute(
            text("SELECT id FROM users WHERE username=:u"),
            {"u": username}
        ).scalar()


# --------------------------------------------------------------------
# Seeder del catálogo contable base por usuario
# --------------------------------------------------------------------
def seed_basic_accounts_for_user(user_id: int) -> None:
    """
    Crea el catálogo mínimo de cuentas contables para un usuario.
    Usa 'ON DUPLICATE KEY UPDATE' para no fallar si ya existen.
    """
    eng = get_engine()
    data = [
        ("1000", "Caja", "Activo"),
        ("1100", "Banco", "Activo"),
        ("1200", "Cuentas por cobrar", "Activo"),
        ("2000", "Cuentas por pagar", "Pasivo"),
        ("3000", "Capital", "Patrimonio"),
        ("4000", "Ingresos por ventas", "Ingreso"),
        ("5000", "Gastos operativos", "Gasto"),
        ("5100", "Costo de ventas", "Gasto"),
    ]

    sql = text("""
        INSERT INTO accounts(user_id, code, name, type)
        VALUES(:u, :c, :n, :t)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            type = VALUES(type)
    """)

    with eng.begin() as cn:
        for code, name, tipo in data:
            cn.execute(sql, {"u": user_id, "c": code, "n": name, "t": tipo})


def seed_knowledge_base_table() -> None:
    """Crea la tabla knowledge_base si no existe. Se llama una vez al arrancar."""
    eng = get_engine()
    with eng.begin() as cn:
        cn.execute(text("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                user_id    INT          NOT NULL,
                category   VARCHAR(80)  NOT NULL DEFAULT 'General',
                title      VARCHAR(200) NOT NULL,
                content    TEXT         NOT NULL,
                active     TINYINT(1)   NOT NULL DEFAULT 1,
                created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_kb_user (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """))
