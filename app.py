
from datetime import date, timedelta
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="JOYA TREND LIVE", page_icon="💎", layout="wide")
st.title("💎 JOYA TREND LIVE")
st.caption("Partidos reales de hoy, mañana o una fecha elegida")

def get_api_key():
    try:
        return st.secrets["FOOTBALL_DATA_API_KEY"]
    except Exception:
        st.error("No se encontró FOOTBALL_DATA_API_KEY en los Secrets de Streamlit.")
        st.stop()

@st.cache_data(ttl=300)
def get_matches(target_date, api_key):
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": api_key}
    params = {"dateFrom": target_date, "dateTo": target_date}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        return response.json().get("matches", [])
    except requests.RequestException as exc:
        st.error(f"Error consultando football-data.org: {exc}")
        return []

def matches_to_df(matches):
    rows = []
    for match in matches:
        competition = match.get("competition", {})
        home = match.get("homeTeam", {})
        away = match.get("awayTeam", {})
        rows.append({
            "Competición": competition.get("name", ""),
            "Local": home.get("name", ""),
            "Visitante": away.get("name", ""),
            "Hora UTC": match.get("utcDate", ""),
            "Estado": match.get("status", ""),
        })
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
    selected = st.date_input("🗓 Elegir fecha", value=st.session_state.selected_date)
    st.session_state.selected_date = selected

target = st.session_state.selected_date.strftime("%Y-%m-%d")
st.subheader(f"⚽ Partidos del {target}")

matches = get_matches(target, api_key)
df = matches_to_df(matches)

if df.empty:
    st.info("No hay partidos disponibles en tu cobertura gratuita para esta fecha.")
else:
    st.metric("Partidos encontrados", len(df))
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.divider()
    st.subheader("🩸 JOYA TREND")
    st.info(
        "Siguiente etapa: conectar estos partidos reales con el motor de tendencias "
        "para calcular Sin gol 0-10, Gol antes del 70, +1.5 goles, S++, Núcleo Sangrado y Value."
    )

st.caption(
    "La cobertura depende del plan de football-data.org y de las competiciones habilitadas."
)
