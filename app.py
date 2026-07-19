from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="JOYA 19 PRO",
    page_icon="💎",
    layout="wide",
)

API_BASE = "https://v3.football.api-sports.io"


def get_api_key() -> str:
    """Read the API key securely from Streamlit Secrets."""
    try:
        key = str(st.secrets["APISPORTS_KEY"]).strip()
    except Exception:
        key = ""
    return key


@st.cache_data(ttl=300, show_spinner=False)
def api_get(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    """Perform a cached GET request to API-Football."""
    key = get_api_key()
    if not key:
        raise RuntimeError(
            'Falta APISPORTS_KEY en Streamlit Secrets.'
        )

    response = requests.get(
        f"{API_BASE}/{endpoint.lstrip('/')}",
        headers={"x-apisports-key": key},
        params=params,
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()

    errors = payload.get("errors")
    if errors:
        raise RuntimeError(f"API-Football devolvió un error: {errors}")

    return payload


def fixture_rows(fixtures: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in fixtures:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})

        home = teams.get("home", {}) or {}
        away = teams.get("away", {}) or {}
        status = fixture.get("status", {}) or {}

        rows.append(
            {
                "fixture_id": fixture.get("id"),
                "Hora": pd.to_datetime(
                    fixture.get("date"), errors="coerce", utc=True
                ).tz_convert("America/Santiago").strftime("%H:%M")
                if fixture.get("date")
                else "—",
                "País": league.get("country") or "Sin país",
                "Liga": league.get("name") or "Sin liga",
                "Local": home.get("name") or "Local",
                "Visitante": away.get("name") or "Visitante",
                "Marcador": (
                    f"{goals.get('home')}–{goals.get('away')}"
                    if goals.get("home") is not None
                    else "—"
                ),
                "Estado": status.get("short") or status.get("long") or "—",
                "home_id": home.get("id"),
                "away_id": away.get("id"),
                "league_id": league.get("id"),
                "season": league.get("season"),
            }
        )
    return pd.DataFrame(rows)


def safe_response(endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return api_get(endpoint, params).get("response", [])
    except Exception as exc:
        st.warning(f"No se pudo cargar {endpoint}: {exc}")
        return []


def show_api_status() -> None:
    key = get_api_key()
    if not key:
        st.error("No encuentro APISPORTS_KEY en Streamlit Secrets.")
        st.code('APISPORTS_KEY = "PEGA_AQUI_TU_CLAVE_NUEVA"', language="toml")
        st.stop()

    try:
        status = api_get("status", {}).get("response", {})
        requests_info = status.get("requests", {}) if isinstance(status, dict) else {}
        current = requests_info.get("current", "—")
        limit = requests_info.get("limit_day", "—")
        st.sidebar.success("API-Football conectada")
        st.sidebar.caption(f"Solicitudes hoy: {current} / {limit}")
    except Exception as exc:
        st.sidebar.error(f"Error de conexión: {exc}")
        st.stop()


def render_overview(selected: pd.Series) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hora Chile", selected["Hora"])
    c2.metric("Liga", selected["Liga"])
    c3.metric("Estado", selected["Estado"])
    c4.metric("Temporada", selected["season"] or "—")

    st.markdown(
        f"## {selected['Local']}  **vs**  {selected['Visitante']}"
    )
    st.caption(f"{selected['País']} · {selected['Liga']}")


def render_h2h(selected: pd.Series) -> None:
    data = safe_response(
        "fixtures/headtohead",
        {
            "h2h": f"{int(selected['home_id'])}-{int(selected['away_id'])}",
            "last": 10,
        },
    )
    if not data:
        st.info("No hay H2H disponible para este partido.")
        return

    df = fixture_rows(data)
    st.dataframe(
        df[["Hora", "Liga", "Local", "Marcador", "Visitante", "Estado"]],
        use_container_width=True,
        hide_index=True,
    )


def render_recent_form(selected: pd.Series) -> None:
    home_id = int(selected["home_id"])
    away_id = int(selected["away_id"])

    left, right = st.columns(2)
    for column, team_id, team_name in [
        (left, home_id, selected["Local"]),
        (right, away_id, selected["Visitante"]),
    ]:
        with column:
            st.subheader(team_name)
            matches = safe_response("fixtures", {"team": team_id, "last": 10})
            if not matches:
                st.info("Sin partidos recientes disponibles.")
                continue
            df = fixture_rows(matches)
            st.dataframe(
                df[["Liga", "Local", "Marcador", "Visitante", "Estado"]],
                use_container_width=True,
                hide_index=True,
            )


def render_standings(selected: pd.Series) -> None:
    if not selected["league_id"] or not selected["season"]:
        st.info("No hay liga o temporada disponible.")
        return

    data = safe_response(
        "standings",
        {
            "league": int(selected["league_id"]),
            "season": int(selected["season"]),
        },
    )
    if not data:
        st.info("Esta competición no entrega tabla de posiciones.")
        return

    standings_groups = (
        data[0].get("league", {}).get("standings", [])
        if data
        else []
    )
    if not standings_groups:
        st.info("Tabla no disponible.")
        return

    rows = []
    for group in standings_groups:
        for item in group:
            all_stats = item.get("all", {}) or {}
            goals = all_stats.get("goals", {}) or {}
            team = item.get("team", {}) or {}
            rows.append(
                {
                    "Pos": item.get("rank"),
                    "Equipo": team.get("name"),
                    "PJ": all_stats.get("played"),
                    "G": all_stats.get("win"),
                    "E": all_stats.get("draw"),
                    "P": all_stats.get("lose"),
                    "GF": goals.get("for"),
                    "GC": goals.get("against"),
                    "DG": item.get("goalsDiff"),
                    "Pts": item.get("points"),
                    "Forma": item.get("form"),
                }
            )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_predictions(selected: pd.Series) -> None:
    data = safe_response("predictions", {"fixture": int(selected["fixture_id"])})
    if not data:
        st.info(
            "Predicción no disponible. La cobertura varía según liga y partido."
        )
        return

    item = data[0]
    predictions = item.get("predictions", {}) or {}
    percent = predictions.get("percent", {}) or {}
    winner = predictions.get("winner", {}) or {}

    c1, c2, c3 = st.columns(3)
    c1.metric("Local", percent.get("home", "—"))
    c2.metric("Empate", percent.get("draw", "—"))
    c3.metric("Visitante", percent.get("away", "—"))

    st.write("**Sugerencia de la API:**", predictions.get("advice", "—"))
    st.write("**Ganador señalado:**", winner.get("name", "—"))
    st.caption(
        "Esta predicción es un dato externo de apoyo; todavía no es el motor JOYA."
    )


def render_injuries(selected: pd.Series) -> None:
    data = safe_response("injuries", {"fixture": int(selected["fixture_id"])})
    if not data:
        st.info("No hay lesiones registradas para este partido.")
        return

    rows = []
    for item in data:
        player = item.get("player", {}) or {}
        team = item.get("team", {}) or {}
        rows.append(
            {
                "Equipo": team.get("name"),
                "Jugador": player.get("name"),
                "Tipo": player.get("type"),
                "Motivo": player.get("reason"),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_odds(selected: pd.Series) -> None:
    data = safe_response("odds", {"fixture": int(selected["fixture_id"])})
    if not data:
        st.info("No hay cuotas prepartido disponibles para este encuentro.")
        return

    rows = []
    for fixture_item in data:
        for bookmaker in fixture_item.get("bookmakers", []) or []:
            for bet in bookmaker.get("bets", []) or []:
                for value in bet.get("values", []) or []:
                    rows.append(
                        {
                            "Casa": bookmaker.get("name"),
                            "Mercado": bet.get("name"),
                            "Selección": value.get("value"),
                            "Cuota": value.get("odd"),
                        }
                    )

    odds_df = pd.DataFrame(rows)
    if odds_df.empty:
        st.info("La respuesta no contiene mercados disponibles.")
        return

    market_query = st.text_input(
        "Filtrar mercado",
        placeholder="Ej.: Goals Over/Under, Double Chance, Both Teams Score",
    )
    if market_query:
        odds_df = odds_df[
            odds_df["Mercado"].str.contains(
                market_query, case=False, na=False
            )
        ]

    st.dataframe(odds_df.head(300), use_container_width=True, hide_index=True)


st.title("💎 JOYA 19 PRO")
st.caption("Fase 1 · API-Football Pro · Centro de datos y análisis")

show_api_status()

st.sidebar.header("Cartelera")
selected_date = st.sidebar.date_input(
    "Fecha",
    value=date.today(),
    min_value=date.today() - timedelta(days=14),
    max_value=date.today() + timedelta(days=60),
)
timezone = st.sidebar.selectbox(
    "Zona horaria",
    ["America/Santiago", "UTC"],
    index=0,
)

with st.spinner("Cargando partidos..."):
    fixtures_payload = api_get(
        "fixtures",
        {
            "date": selected_date.isoformat(),
            "timezone": timezone,
        },
    )
fixtures = fixtures_payload.get("response", [])
fixtures_df = fixture_rows(fixtures)

if fixtures_df.empty:
    st.warning("No se encontraron partidos para la fecha seleccionada.")
    st.stop()

countries = ["Todos"] + sorted(fixtures_df["País"].dropna().unique().tolist())
country = st.sidebar.selectbox("País", countries)
filtered = fixtures_df.copy()
if country != "Todos":
    filtered = filtered[filtered["País"] == country]

leagues = ["Todas"] + sorted(filtered["Liga"].dropna().unique().tolist())
league = st.sidebar.selectbox("Liga", leagues)
if league != "Todas":
    filtered = filtered[filtered["Liga"] == league]

search = st.sidebar.text_input("Buscar equipo")
if search:
    mask = (
        filtered["Local"].str.contains(search, case=False, na=False)
        | filtered["Visitante"].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]

st.subheader(f"Partidos · {selected_date.strftime('%d-%m-%Y')}")
st.write(f"Se encontraron **{len(filtered)}** encuentros con los filtros actuales.")

display_df = filtered[
    ["Hora", "País", "Liga", "Local", "Visitante", "Marcador", "Estado"]
]
st.dataframe(display_df, use_container_width=True, hide_index=True)

if filtered.empty:
    st.stop()

options = {
    f"{row.Hora} · {row.Local} vs {row.Visitante} · {row.Liga}": idx
    for idx, row in filtered.iterrows()
}
selected_label = st.selectbox("Selecciona un partido para analizar", options.keys())
selected = filtered.loc[options[selected_label]]

st.divider()
render_overview(selected)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Forma reciente",
        "H2H",
        "Clasificación",
        "Predicción API",
        "Lesiones",
        "Cuotas",
    ]
)

with tab1:
    render_recent_form(selected)
with tab2:
    render_h2h(selected)
with tab3:
    render_standings(selected)
with tab4:
    render_predictions(selected)
with tab5:
    render_injuries(selected)
with tab6:
    render_odds(selected)

st.divider()
st.info(
    "Fase 1 terminada: conexión, cartelera, filtros y datos del partido. "
    "El JOYA Score, los mercados automáticos y el Núcleo Sangrado se incorporan "
    "en la Fase 2 después de validar que esta base funciona correctamente."
)
