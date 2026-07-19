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
st.caption("Cartelera automática usando TheSportsDB + football-data.org")

def get_secret(name):
try:
return st.secrets[name]
except Exception:
return None


@st.cache_data(ttl=300)
def get_thesportsdb_matches(target_date, api_key):
url = (
f"https://www.thesportsdb.com/api/v1/json/"
f"{api_key}/eventsday.php"
)

params = {
"d": target_date,
"s": "Soccer",
}

try:
response = requests.get(
url,
params=params,
timeout=20,
)
response.raise_for_status()
data = response.json()
return {
"ok": True,
"status": response.status_code,
"events": data.get("events") or [],
}

except Exception as exc:
return {
"ok": False,
"status": None,
"events": [],
"error": str(exc),
}


@st.cache_data(ttl=300)
def get_football_data_matches(target_date, api_key):
if not api_key:
return {
"ok": False,
"status": None,
"matches": [],
}

next_date = (
date.fromisoformat(target_date)
+ timedelta(days=1)
).isoformat()

url = "https://api.football-data.org/v4/matches"

headers = {
"X-Auth-Token": api_key
}

params = {
"dateFrom": target_date,
"dateTo": next_date,
}

try:
response = requests.get(
url,
headers=headers,
params=params,
timeout=20,
)
response.raise_for_status()
data = response.json()

return {
"ok": True,
"status": response.status_code,
"matches": data.get("matches") or [],
}

except Exception as exc:
return {
"ok": False,
"status": None,
"matches": [],
"error": str(exc),
}


def parse_thesportsdb(events):
rows = []

for event in events:
rows.append(
{
"Fuente": "TheSportsDB",
"Competición": event.get("strLeague", ""),
"Local": event.get("strHomeTeam", ""),
"Visitante": event.get("strAwayTeam", ""),
"Fecha": event.get("dateEvent", ""),
"Hora": event.get("strTime", ""),
"Estado": event.get("strStatus", ""),
}
)

return rows


def parse_football_data(matches):
rows = []

for match in matches:
competition = match.get("competition", {})
home = match.get("homeTeam", {})
away = match.get("awayTeam", {})

rows.append(
{
"Fuente": "football-data.org",
"Competición": competition.get("name", ""),
"Local": home.get("name", ""),
"Visitante": away.get("name", ""),
"Fecha": match.get("utcDate", "")[:10],
"Hora": match.get("utcDate", "")[11:16],
"Estado": match.get("status", ""),
}
)

return rows


thesportsdb_key = get_secret(
"THESPORTSDB_API_KEY"
)

football_data_key = get_secret(
"FOOTBALL_DATA_API_KEY"
)


if "selected_date" not in st.session_state:
st.session_state.selected_date = date.today()


c1, c2, c3 = st.columns(3)

with c1:
if st.button(
"📅 HOY",
use_container_width=True
):
st.session_state.selected_date = date.today()

with c2:
if st.button(
"📅 MAÑANA",
use_container_width=True
):
st.session_state.selected_date = (
date.today()
+ timedelta(days=1)
)

with c3:
selected = st.date_input(
"🗓 Elegir fecha",
value=st.session_state.selected_date,
)

st.session_state.selected_date = selected


target_date = (
st.session_state.selected_date
.strftime("%Y-%m-%d")
)


st.subheader(
f"⚽ Partidos del {target_date}"
)


sportsdb_result = get_thesportsdb_matches(
target_date,
thesportsdb_key or "123",
)

football_result = get_football_data_matches(
target_date,
football_data_key,
)


sportsdb_rows = parse_thesportsdb(
sportsdb_result["events"]
)

football_rows = parse_football_data(
football_result["matches"]
)


all_rows = sportsdb_rows + football_rows


if all_rows:

df = pd.DataFrame(all_rows)

df = df.drop_duplicates(
subset=[
"Local",
"Visitante",
"Fecha",
]
)

st.success(
f"Se encontraron {len(df)} partidos."
)

st.dataframe(
df,
use_container_width=True,
hide_index=True,
)

else:

st.warning(
"Las APIs respondieron, pero no encontraron "
"partidos disponibles para esta fecha."
)


with st.expander(
"🧪 Diagnóstico de APIs",
expanded=True,
):

c1, c2, c3, c4 = st.columns(4)

c1.metric(
"TheSportsDB",
"Conectada"
if sportsdb_result["ok"]
else "Error",
)

c2.metric(
"Partidos TheSportsDB",
len(sportsdb_rows),
)

c3.metric(
"football-data",
"Conectada"
if football_result["ok"]
else "Error",
)

c4.metric(
"Partidos football-data",
len(football_rows),
)


st.divider()

st.subheader("🩸 JOYA TREND")

st.info(
"Próximo paso: usar la cartelera encontrada "
"para ejecutar automáticamente el Radar de "
"Tendencias, Núcleo Sangrado, S++ y Value."
)
