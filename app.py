
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="JOYA TREND LIVE",
    page_icon="💎",
    layout="wide",
)

st.title("💎 JOYA TREND LIVE")
st.caption("Partidos reales + diagnóstico de conexión")


def get_api_key() -> str:
    try:
        key = st.secrets["FOOTBALL_DATA_API_KEY"]
        if not key:
            raise KeyError
        return key
    except Exception:
        st.error("No se encontró FOOTBALL_DATA_API_KEY en los Secrets de Streamlit.")
        st.stop()


@st.cache_data(ttl=300)
def api_get(endpoint: str, api_key: str, params: dict | None = None):
    url = f"https://api.football-data.org/v4/{endpoint}"
    headers = {"X-Auth-Token": api_key}

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params or {},
            timeout=20,
        )

        status_code = response.status_code

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        return {
            "ok": response.ok,
            "status_code": status_code,
            "payload": payload,
            "url": response.url,
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "payload": {"error": str(exc)},
            "url": url,
        }


def matches_to_df(matches: list[dict]) -> pd.DataFrame:
    rows = []

    for match in matches:
        competition = match.get("competition", {})
        home = match.get("homeTeam", {})
        away = match.get("awayTeam", {})

        rows.append(
            {
                "Competición": competition.get("name", ""),
                "Local": home.get("name", ""),
                "Visitante": away.get("name", ""),
                "Hora UTC": match.get("utcDate", ""),
                "Estado": match.get("status", ""),
            }
        )

    return pd.DataFrame(rows)


api_key = get_api_key()

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

c1, c2, c3 = st.columns(3)

with c1:
    if st.button("📅 HOY", use_container_width=True):
        st.session_state.selected_date = date.today()

with c2:
    if st.button("📅 MAÑANA", use_container_width=True):
        st.session_state.selected_date = date.today() + timedelta(days=1)

with c3:
    selected = st.date_input(
        "🗓 Elegir fecha",
        value=st.session_state.selected_date,
    )
    st.session_state.selected_date = selected

selected_date = st.session_state.selected_date
date_from = selected_date.strftime("%Y-%m-%d")
date_to = (selected_date + timedelta(days=1)).strftime("%Y-%m-%d")

st.subheader(f"⚽ Partidos del {date_from}")

matches_result = api_get(
    "matches",
    api_key,
    params={
        "dateFrom": date_from,
        "dateTo": date_to,
    },
)

competitions_result = api_get("competitions", api_key)

with st.expander("🧪 Diagnóstico de conexión", expanded=True):
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "API",
        "Conectada" if matches_result["ok"] else "Error",
    )

    c2.metric(
        "Código HTTP",
        matches_result["status_code"] if matches_result["status_code"] else "N/D",
    )

    competitions = competitions_result["payload"].get("competitions", []) if competitions_result["ok"] else []

    c3.metric(
        "Competiciones disponibles",
        len(competitions),
    )

    matches = matches_result["payload"].get("matches", []) if matches_result["ok"] else []

    c4.metric(
        "Partidos encontrados",
        len(matches),
    )

    if not matches_result["ok"]:
        st.error("La consulta de partidos falló.")
        st.json(matches_result["payload"])

    if not competitions_result["ok"]:
        st.warning("No se pudieron consultar las competiciones disponibles.")
        st.json(competitions_result["payload"])

if competitions:
    with st.expander("🏆 Competiciones disponibles en tu cuenta"):
        comp_df = pd.DataFrame(
            [
                {
                    "Código": c.get("code", ""),
                    "Competición": c.get("name", ""),
                    "Área": c.get("area", {}).get("name", ""),
                }
                for c in competitions
            ]
        )
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

if matches_result["ok"]:
    matches = matches_result["payload"].get("matches", [])
    df = matches_to_df(matches)

    if df.empty:
        st.info(
            "La API respondió correctamente, pero no encontró partidos en las competiciones "
            "incluidas en tu cobertura para esta fecha."
        )
    else:
        st.success(f"Se encontraron {len(df)} partidos.")
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.subheader("🩸 JOYA TREND")
        st.info(
            "Siguiente etapa: usar estos partidos reales como entrada del Radar de Tendencias, "
            "Núcleo Sangrado, S++ y Value."
        )

st.caption(
    "La cantidad de partidos depende de las competiciones habilitadas en tu cuenta de football-data.org."
)
