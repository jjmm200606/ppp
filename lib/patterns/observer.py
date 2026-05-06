# lib/patterns/observer.py
from __future__ import annotations
import json
import os
import smtplib
from email.message import EmailMessage
from typing import Protocol, Any, Dict, List
from sqlalchemy import text
from lib.db import get_engine

#Eventos soportados
class Event:
    SALE_CREATED     = "SALE_CREATED"
    EXPENSE_CREATED  = "EXPENSE_CREATED"
    INVOICE_CREATED  = "INVOICE_CREATED"
    CLIENT_CREATED   = "CLIENT_CREATED"
    CART_CREATED     = "CART_CREATED"
    ACCOUNT_CREATED  = "ACCOUNT_CREATED"

#Interfaz Observer
class Observer(Protocol):
    def update(self, event: str, payload: Dict[str, Any]) -> None: ...

# Registro global
_GLOBAL_OBSERVERS: List[Observer] = []

def add_global_observer(obs: Observer) -> None:
    # evita duplicados
    if not any(type(o) is type(obs) for o in _GLOBAL_OBSERVERS):
        _GLOBAL_OBSERVERS.append(obs)

def notify_observers(event: str, payload: Dict[str, Any]) -> None:
    for obs in _GLOBAL_OBSERVERS:
        try:
            obs.update(event, payload)
        except Exception:
            # no romper flujo de la app por un observer
            pass

#Observers concretos
class AuditObserver:
    """Inserta cada evento en la tabla audit_log"""
    def update(self, event: str, payload: Dict[str, Any]) -> None:
        import streamlit as st
        username = st.session_state.get("user", "anon")
        eng = get_engine()
        with eng.begin() as cn:
            cn.execute(
                text("INSERT INTO audit_log(event, payload, username) VALUES(:e,:p,:u)"),
                {"e": event, "p": json.dumps(payload, ensure_ascii=False), "u": username}
            )

class CacheObserver:
    """Limpia caches de Streamlit cuando hay cambios"""
    def update(self, event: str, payload: Dict[str, Any]) -> None:
        import streamlit as st
        st.cache_data.clear()

class EmailObserver:
    """Envía correo (opcional) si configuras variables SMTP_*"""
    def update(self, event: str, payload: Dict[str, Any]) -> None:
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        pwd  = os.getenv("SMTP_PASSWORD")
        from_addr = os.getenv("SMTP_FROM")
        to_addr   = os.getenv("SMTP_TO")
        if not all([host, user, pwd, from_addr, to_addr]):
            return
        msg = EmailMessage()
        msg["Subject"] = f"[HotDogs] Evento: {event}"
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg.set_content(json.dumps(payload, indent=2, ensure_ascii=False))
        with smtplib.SMTP(host, port) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
