from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
import streamlit as st

from api.football import api_get, get_api_key
from config.settings import DEFAULT_TIMEZONE
from engine.cart_builder import build_cart
from engine.scanner import fixture_catalog, prepare_fixtures, scan_all_by_league
from ui.components import show_catalog_by_league, show_cart, show_ranking_by_league

st.set_page_config(page_title="JOYA 20 ELITE", page_icon="💎", layout="wide")

st.title("💎 JOYA 20 ELITE")
st.caption("Versión 0.2 · Scanner de todas las ligas + resultados agrupados")

if not get_api_key():
    st.error("Falta APISPORTS_KEY en Streamlit Secrets.")
    st.stop()

try:
    status = api_get("status", {}).get("response", {})
    req = status.get("requests", {}) if isinstance(status, dict) else {}
    st.sidebar.success("API-Football conectada")
    st.sidebar.caption(
        f"Solicitudes hoy: {req.get('current', '—')} / {req.get('limit_day', '—')}"
    )
except Exception as exc:
    st.sidebar.error(f"No se pudo conectar: {exc}")
    st.stop()

st.sidebar.header("Configuración del Scanner")
selected_date = st.sidebar.date_input(
    "Fecha",
    value=date.today(),
    min_value=date.today() - timedelta(days=7),
    max_value=date.today() + timedelta(days=30),
)
timezone = st.sidebar.selectbox("Zona horaria", [DEFAULT_TIMEZONE, "UTC"], index=0)

exclude_youth = st.sidebar.checkbox("Excluir juveniles y reservas", value=True)
exclude_friendlies = st.sidebar.checkbox("Excluir amistosos", value=False)
max_per_league = st.sidebar.select_slider(
    "Máximo de partidos analizados por liga",
    options=[1, 2, 3, 4, 5, 10, 20],
    value=3,
)

fixtures = api_get(
    "fixtures",
    {"date": selected_date.isoformat(), "timezone": timezone},
).get("response", [])

prepared = prepare_fixtures(
    fixtures,
    exclude_youth_reserves=exclude_youth,
    exclude_friendlies=exclude_friendlies,
)
catalog = fixture_catalog(prepared)

c1, c2, c3 = st.columns(3)
c1.metric("Partidos disponibles", len(catalog))
c2.metric("Ligas disponibles", catalog["Liga"].nunique() if not catalog.empty else 0)
estimated_scan = (
    catalog.groupby(["País", "Liga"]).head(int(max_per_league)).shape[0]
    if not catalog.empty else 0
)
c3.metric("Partidos que escaneará", estimated_scan)

st.info(
    "Ahora JOYA reparte el escaneo entre todas las ligas. "
    "Con 3 partidos por liga, cada competición disponible tendrá representación "
    "y no quedarán ocultas España, Suecia, Noruega u otras por estar al final de la lista."
)

show_catalog_by_league(catalog)

if "ranking_v02" not in st.session_state:
    st.session_state.ranking_v02 = pd.DataFrame()

if st.button("🧠 ESCANEAR TODAS LAS LIGAS", type="primary", use_container_width=True):
    progress = st.progress(0)
    status_text = st.empty()

    def update(current: int, total: int, league_name: str) -> None:
        progress.progress(current / total if total else 1)
        status_text.caption(
            f"Analizando {current} de {total} · {league_name}"
        )

    with st.spinner("Analizando todas las ligas disponibles…"):
        st.session_state.ranking_v02 = scan_all_by_league(
            fixtures=fixtures,
            max_matches_per_league=int(max_per_league),
            exclude_youth_reserves=exclude_youth,
            exclude_friendlies=exclude_friendlies,
            progress_callback=update,
        )

    progress.empty()
    status_text.empty()

show_ranking_by_league(st.session_state.ranking_v02)

st.divider()
st.subheader("🚀 Crear cartilla con ligas seleccionadas")

ranking = st.session_state.ranking_v02
available_leagues = sorted(ranking["Liga"].unique().tolist()) if not ranking.empty else []

selected_leagues = st.multiselect(
    "Ligas que encontraste disponibles en Betano",
    options=available_leagues,
    default=[],
    placeholder="Déjalo vacío para usar todas",
)

c1, c2, c3, c4 = st.columns(4)
target_odds = c1.selectbox("Cuota objetivo", [2.0, 3.0, 4.0, 5.0], index=1)
max_picks = c2.selectbox("Máximo de picks", [2, 3, 4, 5, 6], index=3)
minimum_tier = c3.selectbox("Tier mínimo", ["S++", "S+", "A++"], index=1)
assumed_odds = c4.number_input(
    "Cuota media estimada",
    min_value=1.05,
    max_value=2.00,
    value=1.30,
    step=0.05,
)
max_one_per_league = st.checkbox("Máximo un pick por liga", value=True)

if st.button("📋 CREAR CARTILLA", use_container_width=True):
    cart, combined = build_cart(
        ranking=ranking,
        target_odds=float(target_odds),
        max_picks=int(max_picks),
        minimum_tier=str(minimum_tier),
        assumed_odds=float(assumed_odds),
        selected_leagues=selected_leagues,
        max_one_per_league=max_one_per_league,
    )
    show_cart(cart, combined, float(target_odds))

st.caption(
    "Las cuotas siguen siendo estimadas manualmente. Próxima versión: consulta de cuotas reales "
    "y detección de Betano cuando API-Football la entregue."
)
