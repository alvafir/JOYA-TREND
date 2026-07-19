from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="JOYA TREND LIVE",
    page_icon="💎",
    layout="wide",
)

st.title("💎 JOYA TREND LIVE")
st.caption("Cartelera automática con TheSportsDB y football-data.org")


def get_secret(name: str, default: str = "") -> str:
    """Lee una variable desde Streamlit Secrets sin detener la aplicación."""
    try:
        value = st.secrets.get(name, default)
        return str(value).strip()
    except Exception:
        return default


@st.cache_data(ttl=300, show_spinner=False)
def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Realiza una solicitud HTTP y devuelve un resultado uniforme."""
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=20,
        )

        try:
            payload: Any = response.json()
        except ValueError:
            payload = {"raw_response": response.text[:1000]}

        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "payload": payload,
            "requested_url": response.url,
            "error": "" if response.ok else f"HTTP {response.status_code}",
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "payload": {},
            "requested_url": url,
            "error": str(exc),
        }


def get_thesportsdb_matches(target_date: str, api_key: str) -> dict[str, Any]:
    """Obtiene eventos de fútbol de TheSportsDB para una fecha."""
    key = api_key or "123"
    url = f"https://www.thesportsdb.com/api/v1/json/{key}/eventsday.php"

    result = request_json(
        url,
        params={
            "d": target_date,
            "s": "Soccer",
        },
    )

    events: list[dict[str, Any]] = []
    if result["ok"] and isinstance(result["payload"], dict):
        raw_events = result["payload"].get("events")
        if isinstance(raw_events, list):
            events = raw_events

    result["events"] = events
    return result


def get_football_data_matches(
    target_date: str,
    api_key: str,
) -> dict[str, Any]:
    """Obtiene partidos de football-data.org para una fecha."""
    if not api_key:
        return {
            "ok": False,
            "status_code": None,
            "payload": {},
            "requested_url": "",
            "error": "Falta FOOTBALL_DATA_API_KEY en Streamlit Secrets.",
            "matches": [],
        }

    url = "https://api.football-data.org/v4/matches"

    result = request_json(
        url,
        headers={"X-Auth-Token": api_key},
        params={
            "dateFrom": target_date,
            "dateTo": target_date,
        },
    )

    matches: list[dict[str, Any]] = []
    if result["ok"] and isinstance(result["payload"], dict):
        raw_matches = result["payload"].get("matches")
        if isinstance(raw_matches, list):
            matches = raw_matches

    result["matches"] = matches
    return result


def parse_thesportsdb(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for event in events:
        home = str(event.get("strHomeTeam") or "").strip()
        away = str(event.get("strAwayTeam") or "").strip()

        if not home and not away:
            continue

        rows.append(
            {
                "Fuente": "TheSportsDB",
                "Competición": str(event.get("strLeague") or ""),
                "Local": home,
                "Visitante": away,
                "Fecha": str(event.get("dateEvent") or ""),
                "Hora": str(event.get("strTime") or ""),
                "Estado": str(event.get("strStatus") or "PROGRAMADO"),
            }
        )

    return rows


def parse_football_data(
    matches: list[dict[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for match in matches:
        competition = match.get("competition") or {}
        home_team = match.get("homeTeam") or {}
        away_team = match.get("awayTeam") or {}
        utc_date = str(match.get("utcDate") or "")

        home = str(home_team.get("name") or "").strip()
        away = str(away_team.get("name") or "").strip()

        if not home and not away:
            continue

        rows.append(
            {
                "Fuente": "football-data.org",
                "Competición": str(competition.get("name") or ""),
                "Local": home,
                "Visitante": away,
                "Fecha": utc_date[:10],
                "Hora": utc_date[11:16] if len(utc_date) >= 16 else "",
                "Estado": str(match.get("status") or ""),
            }
        )

    return rows


def normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


def deduplicate_matches(rows: list[dict[str, str]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=[
                "Fuente",
                "Competición",
                "Local",
                "Visitante",
                "Fecha",
                "Hora",
                "Estado",
            ]
        )

    df = pd.DataFrame(rows)

    df["_key"] = (
        df["Fecha"].fillna("").map(normalize_text)
        + "|"
        + df["Local"].fillna("").map(normalize_text)
        + "|"
        + df["Visitante"].fillna("").map(normalize_text)
    )

    df = df.drop_duplicates(subset="_key", keep="first")
    return df.drop(columns="_key").reset_index(drop=True)


football_data_key = get_secret("FOOTBALL_DATA_API_KEY")
thesportsdb_key = get_secret("THESPORTSDB_API_KEY", "123")

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

if "range_days" not in st.session_state:
    st.session_state.range_days = 1


button_columns = st.columns(4)

with button_columns[0]:
    if st.button("📅 HOY", use_container_width=True):
        st.session_state.selected_date = date.today()
        st.session_state.range_days = 1

with button_columns[1]:
    if st.button("📅 MAÑANA", use_container_width=True):
        st.session_state.selected_date = date.today() + timedelta(days=1)
        st.session_state.range_days = 1

with button_columns[2]:
    if st.button("📆 PRÓXIMOS 3 DÍAS", use_container_width=True):
        st.session_state.selected_date = date.today()
        st.session_state.range_days = 3

with button_columns[3]:
    if st.button("🗓 PRÓXIMOS 7 DÍAS", use_container_width=True):
        st.session_state.selected_date = date.today()
        st.session_state.range_days = 7


control_columns = st.columns([2, 2])

with control_columns[0]:
    selected_date = st.date_input(
        "Elegir fecha inicial",
        value=st.session_state.selected_date,
    )
    st.session_state.selected_date = selected_date

with control_columns[1]:
    range_days = st.selectbox(
        "Cantidad de días",
        options=[1, 3, 7],
        index=[1, 3, 7].index(st.session_state.range_days),
    )
    st.session_state.range_days = range_days


all_rows: list[dict[str, str]] = []
diagnostics: list[dict[str, Any]] = []

with st.spinner("Buscando partidos..."):
    for offset in range(st.session_state.range_days):
        current_date = st.session_state.selected_date + timedelta(days=offset)
        target_date = current_date.isoformat()

        sportsdb_result = get_thesportsdb_matches(
            target_date,
            thesportsdb_key,
        )
        football_result = get_football_data_matches(
            target_date,
            football_data_key,
        )

        sportsdb_rows = parse_thesportsdb(
            sportsdb_result.get("events", [])
        )
        football_rows = parse_football_data(
            football_result.get("matches", [])
        )

        all_rows.extend(sportsdb_rows)
        all_rows.extend(football_rows)

        diagnostics.append(
            {
                "Fecha": target_date,
                "TheSportsDB": (
                    "Conectada" if sportsdb_result["ok"] else "Error"
                ),
                "HTTP TheSportsDB": sportsdb_result["status_code"] or "N/D",
                "Partidos TheSportsDB": len(sportsdb_rows),
                "football-data": (
                    "Conectada" if football_result["ok"] else "Error"
                ),
                "HTTP football-data": football_result["status_code"] or "N/D",
                "Partidos football-data": len(football_rows),
                "Error TheSportsDB": sportsdb_result.get("error", ""),
                "Error football-data": football_result.get("error", ""),
            }
        )


matches_df = deduplicate_matches(all_rows)

start_label = st.session_state.selected_date.isoformat()
end_date = (
    st.session_state.selected_date
    + timedelta(days=st.session_state.range_days - 1)
)
end_label = end_date.isoformat()

if st.session_state.range_days == 1:
    st.subheader(f"⚽ Partidos del {start_label}")
else:
    st.subheader(f"⚽ Partidos del {start_label} al {end_label}")

if matches_df.empty:
    st.warning(
        "Las APIs respondieron, pero no se encontraron partidos disponibles "
        "para la fecha o el rango seleccionado."
    )
else:
    st.success(f"Se encontraron {len(matches_df)} partidos sin duplicados.")

    competition_options = sorted(
        value
        for value in matches_df["Competición"].dropna().unique().tolist()
        if value
    )

    selected_competitions = st.multiselect(
        "Filtrar por competición",
        options=competition_options,
        default=[],
    )

    filtered_df = matches_df
    if selected_competitions:
        filtered_df = matches_df[
            matches_df["Competición"].isin(selected_competitions)
        ]

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
    )


with st.expander("🧪 Diagnóstico de APIs", expanded=True):
    st.dataframe(
        pd.DataFrame(diagnostics),
        use_container_width=True,
        hide_index=True,
    )

    if not football_data_key:
        st.info(
            'Agrega FOOTBALL_DATA_API_KEY = "TU_TOKEN" en los Secrets '
            "de Streamlit para activar football-data.org."
        )

    if not thesportsdb_key:
        st.info(
            'Puedes agregar THESPORTSDB_API_KEY = "123" en los Secrets '
            "de Streamlit. La aplicación usa 123 como respaldo gratuito."
        )


st.divider()
st.subheader("🩸 JOYA TREND")
st.info(
    "La cartelera ya está preparada para incorporar posteriormente "
    "el Radar de Tendencias, Núcleo Sangrado, S++, Value y análisis JOYA 18 PRO."
)

st.caption(
    "La cantidad de partidos depende de la cobertura y límites de cada API. "
    "TheSportsDB y football-data.org pueden devolver carteleras diferentes."
)
