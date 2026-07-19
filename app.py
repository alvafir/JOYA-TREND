from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from api.football import api_get, get_api_key
from config.settings import DEFAULT_SCAN_LIMIT, DEFAULT_TIMEZONE, MAX_SCAN_LIMIT
from engine.cart_builder import build_cart
from engine.scanner import scan_day
from ui.components import show_cart, show_ranking

st.set_page_config(
    page_title="JOYA 20 ELITE",
    page_icon="💎",
    layout="wide",
)

st.title("💎 JOYA 20 ELITE")
st.caption("Versión 0.1 · Scanner + Ranking + Constructor de cartillas")

if not get_api_key():
    st.error("Falta APISPORTS_KEY en Streamlit Secrets.")
    st.code('APISPORTS_KEY = "TU_CLAVE"', language="toml")
    st.stop()

try:
    status = api_get("status", {}).get("response", {})
    requests_info = status.get("requests", {}) if isinstance(status, dict) else {}
    st.sidebar.success("API-Football conectada")
    st.sidebar.caption(
        f"Solicitudes hoy: {requests_info.get('current', '—')} / "
        f"{requests_info.get('limit_day', '—')}"
    )
except Exception as exc:
    st.sidebar.error(f"No se pudo conectar: {exc}")
    st.stop()

st.sidebar.header("JOYA Scanner")
selected_date = st.sidebar.date_input(
    "Fecha",
    value=date.today(),
    min_value=date.today() - timedelta(days=7),
    max_value=date.today() + timedelta(days=30),
)
timezone = st.sidebar.selectbox(
    "Zona horaria",
    [DEFAULT_TIMEZONE, "UTC"],
    index=0,
)
scan_limit = st.sidebar.slider(
    "Partidos a escanear",
    min_value=5,
    max_value=MAX_SCAN_LIMIT,
    value=DEFAULT_SCAN_LIMIT,
    step=5,
)
exclude_volatile = st.sidebar.checkbox(
    "Excluir juveniles, reservas y femenino",
    value=True,
)

fixtures_payload = api_get(
    "fixtures",
    {
        "date": selected_date.isoformat(),
        "timezone": timezone,
    },
)
fixtures = fixtures_payload.get("response", [])

st.metric("Partidos encontrados", len(fixtures))
st.info(
    "Esta primera versión limita el scanner para controlar el consumo de API. "
    "Cada partido escaneado puede usar dos consultas adicionales."
)

if "ranking" not in st.session_state:
    st.session_state.ranking = pd.DataFrame()

if st.button("🧠 EJECUTAR JOYA SCANNER", type="primary", use_container_width=True):
    progress = st.progress(0)
    label = st.empty()

    def update_progress(current: int, total: int) -> None:
        value = current / total if total else 1
        progress.progress(value)
        label.caption(f"Analizando partido {current} de {total}…")

    with st.spinner("Escaneando partidos y calculando mercados…"):
        st.session_state.ranking = scan_day(
            fixtures=fixtures,
            limit=scan_limit,
            exclude_volatile=exclude_volatile,
            progress_callback=update_progress,
        )

    progress.empty()
    label.empty()

show_ranking(st.session_state.ranking)

st.divider()
st.subheader("🚀 Crear cartilla")

c1, c2, c3, c4 = st.columns(4)
target_odds = c1.selectbox("Cuota objetivo", [2.0, 3.0, 4.0, 5.0], index=1)
max_picks = c2.selectbox("Máximo de picks", [2, 3, 4, 5], index=2)
minimum_tier = c3.selectbox("Tier mínimo", ["S++", "S+", "A++"], index=1)
assumed_odds = c4.number_input(
    "Cuota media estimada",
    min_value=1.05,
    max_value=2.00,
    value=1.30,
    step=0.05,
)

if st.button("📋 CREAR CARTILLA", use_container_width=True):
    cart, combined = build_cart(
        ranking=st.session_state.ranking,
        target_odds=float(target_odds),
        max_picks=int(max_picks),
        minimum_tier=str(minimum_tier),
        assumed_odds=float(assumed_odds),
    )
    show_cart(cart, combined, float(target_odds))

st.caption(
    "Versión inicial: las cuotas usadas para construir la cartilla son manuales. "
    "La próxima actualización consultará cuotas reales y buscará Betano cuando esté disponible."
)
