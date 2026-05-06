from __future__ import annotations

import streamlit as st


def money(x) -> str:
    try:
        return f"$ {float(x):,.2f}"
    except Exception:
        return "$ 0.00"


def require_login():
    if not st.session_state.get("logged_in"):
        st.stop()


def apply_theme():
    """Inyecta CSS para seguir el modo claro/oscuro del dispositivo."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {
        color-scheme: dark;
        --bg: #0d0d0d;
        --bg-elevated: #161616;
        --bg-soft: #1b1b1b;
        --hero: linear-gradient(180deg, #181210 0%, #121010 100%);
        --panel: linear-gradient(135deg, #1e1e1e, #161616);
        --sidebar: linear-gradient(180deg, #1c1008 0%, #120c08 100%);
        --text-main: #ece8e5;
        --text-strong: #ffffff;
        --text-muted: #a19791;
        --text-soft: #7f746d;
        --border: #2b2b2b;
        --border-soft: #383838;
        --accent: #e8530a;
        --accent-strong: #c53800;
        --accent-wash: rgba(232,83,10,.11);
        --shadow-md: 0 10px 26px rgba(0,0,0,.18);
        --shadow-lg: 0 20px 50px rgba(0,0,0,.22);
        --sidebar-text: #ddd;
    }

    @media (prefers-color-scheme: light) {
        :root {
            color-scheme: light;
            --bg: #f6f3ef;
            --bg-elevated: #ffffff;
            --bg-soft: #f3ede6;
            --hero: linear-gradient(180deg, #fff8f1 0%, #fff 100%);
            --panel: linear-gradient(135deg, #ffffff, #faf6f1);
            --sidebar: linear-gradient(180deg, #fff3e7 0%, #fffaf5 100%);
            --text-main: #2b211d;
            --text-strong: #18110d;
            --text-muted: #6f635b;
            --text-soft: #8a7c73;
            --border: #e7dacf;
            --border-soft: #daccc0;
            --accent: #e8530a;
            --accent-strong: #c53800;
            --accent-wash: rgba(232,83,10,.07);
            --shadow-md: 0 8px 24px rgba(56,34,18,.08);
            --shadow-lg: 0 24px 52px rgba(56,34,18,.1);
            --sidebar-text: #3f322a;
        }
    }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

    #MainMenu { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent !important; }
    header[data-testid="stHeader"] > div:first-child { visibility: hidden; }
    footer { visibility: hidden; }

    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    button[kind="header"],
    section[data-testid="stSidebar"] + div button {
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
    }

    .stApp {
        background: var(--bg) !important;
        color: var(--text-main) !important;
    }
    .main .block-container { padding-top: 1.8rem; padding-bottom: 2.5rem; }

    [data-testid="stSidebar"] {
        background: var(--sidebar) !important;
        border-right: 1px solid rgba(232,83,10,.16) !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: var(--sidebar-text) !important;
    }
    [data-testid="stSidebar"] hr { border-color: rgba(232,83,10,.22) !important; }

    [data-testid="stSidebarNav"] a { color: var(--sidebar-text) !important; }
    [data-testid="stSidebarNav"] a:hover {
        color: var(--accent) !important;
        background: rgba(232,83,10,.1) !important;
        border-radius: 6px;
    }

    .stButton > button,
    [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 100%) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        letter-spacing: .2px;
        box-shadow: 0 3px 10px rgba(232,83,10,.28) !important;
        transition: all .2s ease !important;
    }
    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        background: linear-gradient(135deg, #ff6420 0%, var(--accent) 100%) !important;
        box-shadow: 0 6px 18px rgba(232,83,10,.4) !important;
        transform: translateY(-1px) !important;
    }

    [data-testid="metric-container"] {
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        padding: 1.1rem 1.3rem !important;
        box-shadow: var(--shadow-md) !important;
        transition: transform .2s, box-shadow .2s !important;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-lg) !important;
    }
    [data-testid="stMetricLabel"] > div {
        color: var(--text-muted) !important;
        font-size: .78rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: .8px;
    }
    [data-testid="stMetricValue"] > div {
        color: var(--accent) !important;
        font-size: 1.5rem !important;
        font-weight: 800 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: var(--bg-elevated) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        gap: 4px !important;
        border: 1px solid var(--border) !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9px !important;
        color: var(--text-muted) !important;
        font-weight: 500 !important;
        transition: all .2s !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-main) !important;
        background: var(--bg-soft) !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--accent), var(--accent-strong)) !important;
        color: #fff !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-highlight"] { display: none !important; }

    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: var(--bg-soft) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 9px !important;
        color: var(--text-main) !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px rgba(232,83,10,.16) !important;
    }
    .stSelectbox > div > div,
    .stDateInput > div > div > input {
        background: var(--bg-soft) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 9px !important;
        color: var(--text-main) !important;
    }

    [data-testid="stForm"] {
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        padding: 1.5rem !important;
    }

    [data-testid="stDataFrame"] > div {
        border-radius: 12px !important;
        border: 1px solid var(--border) !important;
        overflow: hidden;
    }

    hr {
        border: none !important;
        border-top: 1px solid var(--border) !important;
        margin: 1.5rem 0 !important;
    }

    h1 { color: var(--text-strong) !important; font-weight: 800 !important; letter-spacing: -.5px; }
    h2, h3 { color: var(--text-main) !important; }
    [data-testid="stAlert"] { border-radius: 11px !important; }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg) !important; }
    ::-webkit-scrollbar-thumb { background: #98897f; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--accent); }

    .stCaption, small { color: var(--text-soft) !important; }

    [data-testid="stPageLink"] > a {
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        color: var(--text-main) !important;
        transition: all .2s !important;
        font-weight: 500 !important;
    }
    [data-testid="stPageLink"] > a:hover {
        background: rgba(232,83,10,.12) !important;
        border-color: rgba(232,83,10,.3) !important;
        color: var(--accent) !important;
    }

    .app-surface {
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        box-shadow: var(--shadow-lg);
    }

    .auth-hero-card {
        background:
            radial-gradient(circle at top right, rgba(232,83,10,.13), transparent 35%),
            radial-gradient(circle at bottom left, rgba(255,178,92,.08), transparent 28%),
            var(--hero);
        border: 1px solid rgba(232,83,10,.16);
        border-radius: 24px;
        padding: 2rem;
        box-shadow: var(--shadow-lg);
    }

    .auth-mini-kpi {
        background: var(--accent-wash);
        border: 1px solid rgba(232,83,10,.14);
        border-radius: 14px;
        padding: .95rem 1rem;
    }

    .auth-note {
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1rem 1.05rem;
        box-shadow: var(--shadow-md);
    }

    .auth-brand-mark {
        width: 78px;
        height: 78px;
        margin: 0 auto 1rem;
        border-radius: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, var(--accent), var(--accent-strong));
        color: #fff;
        font-size: 1.7rem;
        font-weight: 900;
        box-shadow: 0 20px 44px rgba(232,83,10,.24);
    }

    .auth-stage {
        position: relative;
        overflow: hidden;
        border: 1px solid var(--border);
        border-radius: 30px;
        background:
            radial-gradient(circle at 15% 20%, rgba(232,83,10,.18), transparent 26%),
            radial-gradient(circle at 85% 15%, rgba(59,130,246,.14), transparent 22%),
            radial-gradient(circle at 70% 80%, rgba(34,197,94,.10), transparent 20%),
            linear-gradient(135deg, var(--hero), var(--bg-elevated));
        box-shadow: var(--shadow-lg);
        padding: 1.25rem;
        margin-top: .75rem;
    }

    .auth-stage::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
            linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px);
        background-size: 28px 28px;
        mask-image: linear-gradient(180deg, rgba(0,0,0,.42), transparent 90%);
        pointer-events: none;
    }

    .auth-shell {
        max-width: 560px;
        margin: 0 auto;
        text-align: left;
        padding: .2rem 0;
        position: relative;
        z-index: 1;
    }

    .auth-pill {
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        padding: .45rem .8rem;
        border-radius: 999px;
        background: rgba(232,83,10,.12);
        border: 1px solid rgba(232,83,10,.18);
        color: var(--accent);
        font-size: .78rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .08em;
    }

    .auth-pill-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: var(--accent);
        box-shadow: 0 0 0 6px rgba(232,83,10,.12);
    }

    .auth-feature-list {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: .85rem;
        margin-top: 1.5rem;
    }

    .auth-feature-card {
        position: relative;
        z-index: 1;
        background: rgba(255,255,255,.04);
        border: 1px solid rgba(255,255,255,.08);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 1rem 1rem 1.05rem;
        min-height: 118px;
    }

    .auth-feature-kicker {
        color: var(--text-muted);
        font-size: .72rem;
        text-transform: uppercase;
        font-weight: 800;
        letter-spacing: .08em;
    }

    .auth-feature-title {
        color: var(--text-strong);
        font-size: 1rem;
        font-weight: 800;
        margin-top: .35rem;
        line-height: 1.35;
    }

    .auth-feature-copy {
        color: var(--text-muted);
        font-size: .88rem;
        line-height: 1.5;
        margin-top: .42rem;
    }

    .auth-data-strip {
        display: flex;
        flex-wrap: wrap;
        gap: .6rem;
        margin-top: 1.15rem;
    }

    .auth-data-chip {
        padding: .55rem .75rem;
        border-radius: 14px;
        background: rgba(15,23,42,.2);
        border: 1px solid rgba(255,255,255,.08);
        color: var(--text-main);
        font-size: .83rem;
        font-weight: 600;
    }

    .auth-login-card {
        max-width: 520px;
        margin: 0 auto;
        padding: 1.6rem 1.35rem 1.15rem;
        background: color-mix(in srgb, var(--bg-elevated) 92%, transparent);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 26px;
        box-shadow: 0 30px 70px rgba(15,23,42,.18);
        backdrop-filter: blur(16px);
        position: relative;
        z-index: 1;
    }

    .auth-login-card .stTabs [data-baseweb="tab-list"] {
        margin-top: .95rem !important;
        background: var(--bg-soft) !important;
        border-radius: 14px !important;
    }

    .auth-login-card .stTextInput > label,
    .auth-login-card .stNumberInput > label {
        font-weight: 700 !important;
    }

    .auth-login-card .stTextInput > div > div > input {
        min-height: 52px !important;
        border-radius: 14px !important;
        font-size: 1rem !important;
        padding-left: .95rem !important;
    }

    .auth-login-foot {
        text-align: center;
        color: var(--text-soft);
        font-size: .84rem;
        margin-top: .85rem;
    }

    @media (max-width: 768px) {
        .auth-stage {
            padding: .95rem;
            border-radius: 22px;
        }

        .auth-shell {
            max-width: 100%;
            text-align: left;
        }

        .auth-login-card {
            max-width: 100%;
            padding: 1.2rem 1rem 1rem;
            border-radius: 20px;
        }

        .auth-feature-list {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", icon: str = ""):
    sub_html = (
        f'<p style="margin:5px 0 0 0;color:var(--text-muted);font-size:.86rem;font-weight:400">{subtitle}</p>'
        if subtitle else ""
    )
    st.markdown(f"""
    <div style="padding:1.1rem 1.5rem;border-radius:12px;
                background:var(--hero);
                border:1px solid rgba(232,83,10,0.2);border-left:3px solid var(--accent);
                margin-bottom:1.5rem;box-shadow:var(--shadow-md)">
        <h1 style="margin:0;color:var(--text-strong);font-size:1.5rem;font-weight:800;letter-spacing:-.4px">{title}</h1>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def section_header(title: str):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:.6rem;margin:1.4rem 0 .7rem 0">
        <div style="width:3px;height:17px;background:var(--accent);border-radius:2px;flex-shrink:0"></div>
        <span style="color:var(--text-main);font-size:.85rem;font-weight:700;letter-spacing:.5px;
                     text-transform:uppercase">{title}</span>
    </div>
    """, unsafe_allow_html=True)


def kpi_cards(items: list):
    n = len(items)
    cols = st.columns(n)
    for col, item in zip(cols, items):
        color = item.get("color", "#e8530a")
        with col:
            st.markdown(f"""
            <div style="background:var(--panel);
                        border:1px solid var(--border);border-radius:14px;
                        padding:1.2rem 1.4rem;box-shadow:var(--shadow-md)">
                <div style="display:flex;align-items:center;gap:.45rem;
                            color:var(--text-muted);font-size:.72rem;text-transform:uppercase;
                            letter-spacing:.9px;font-weight:600;margin-bottom:.5rem">
                    <span style="display:inline-block;width:7px;height:7px;border-radius:50%;
                                 background:{color};flex-shrink:0"></span>
                    {item['label']}
                </div>
                <div style="color:{color};font-size:1.55rem;font-weight:800;letter-spacing:-.4px">
                    {item['value']}
                </div>
            </div>
            """, unsafe_allow_html=True)
