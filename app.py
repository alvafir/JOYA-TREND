from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="JOYA 19 PRO", page_icon="💎", layout="wide")
API_BASE = "https://v3.football.api-sports.io"


def get_api_key() -> str:
    try:
        return str(st.secrets["APISPORTS_KEY"]).strip()
    except Exception:
        return ""


@st.cache_data(ttl=300, show_spinner=False)
def api_get(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    key = get_api_key()
    if not key:
        raise RuntimeError("Falta APISPORTS_KEY en Streamlit Secrets.")

    r = requests.get(
        f"{API_BASE}/{endpoint.lstrip('/')}",
        headers={"x-apisports-key": key},
        params=params,
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()

    if payload.get("errors"):
        raise RuntimeError(str(payload["errors"]))

    return payload


def safe_response(endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return api_get(endpoint, params).get("response", [])
    except Exception as exc:
        st.warning(f"No se pudo cargar {endpoint}: {exc}")
        return []


def fixture_rows(fixtures: list[dict[str, Any]], timezone: str) -> pd.DataFrame:
    rows = []
    for item in fixtures:
        fixture = item.get("fixture", {}) or {}
        league = item.get("league", {}) or {}
        teams = item.get("teams", {}) or {}
        goals = item.get("goals", {}) or {}
        status = fixture.get("status", {}) or {}

        home = teams.get("home", {}) or {}
        away = teams.get("away", {}) or {}

        dt = pd.to_datetime(fixture.get("date"), errors="coerce", utc=True)
        hour = "—"
        if not pd.isna(dt):
            try:
                hour = dt.tz_convert(timezone).strftime("%H:%M")
            except Exception:
                hour = dt.strftime("%H:%M")

        rows.append(
            {
                "fixture_id": fixture.get("id"),
                "Hora": hour,
                "País": league.get("country") or "Sin país",
                "Liga": league.get("name") or "Sin liga",
                "Local": home.get("name") or "Local",
                "Visitante": away.get("name") or "Visitante",
                "Marcador": (
                    f"{goals.get('home')}–{goals.get('away')}"
                    if goals.get("home") is not None
                    else "—"
                ),
                "Estado": status.get("short") or "—",
                "home_id": home.get("id"),
                "away_id": away.get("id"),
                "league_id": league.get("id"),
                "season": league.get("season"),
            }
        )
    return pd.DataFrame(rows)


def team_match_metrics(fixtures: list[dict[str, Any]], team_id: int) -> dict[str, float]:
    total = 0
    wins = draws = losses = 0
    scored_matches = 0
    conceded_matches = 0
    over15 = btts = under45 = 0
    goals_for = goals_against = 0

    for item in fixtures:
        status = (item.get("fixture", {}).get("status", {}) or {}).get("short")
        if status not in {"FT", "AET", "PEN"}:
            continue

        teams = item.get("teams", {}) or {}
        goals = item.get("goals", {}) or {}
        home = teams.get("home", {}) or {}
        away = teams.get("away", {}) or {}

        gh = goals.get("home")
        ga = goals.get("away")
        if gh is None or ga is None:
            continue

        is_home = home.get("id") == team_id
        gf = gh if is_home else ga
        gc = ga if is_home else gh

        total += 1
        goals_for += gf
        goals_against += gc
        scored_matches += int(gf >= 1)
        conceded_matches += int(gc >= 1)
        over15 += int(gf + gc >= 2)
        btts += int(gf >= 1 and gc >= 1)
        under45 += int(gf + gc <= 4)

        if gf > gc:
            wins += 1
        elif gf == gc:
            draws += 1
        else:
            losses += 1

    if total == 0:
        return {"sample": 0}

    pct = lambda x: round(100 * x / total, 1)
    return {
        "sample": total,
        "win_pct": pct(wins),
        "draw_pct": pct(draws),
        "loss_pct": pct(losses),
        "score_pct": pct(scored_matches),
        "concede_pct": pct(conceded_matches),
        "over15_pct": pct(over15),
        "btts_pct": pct(btts),
        "under45_pct": pct(under45),
        "gf_avg": round(goals_for / total, 2),
        "ga_avg": round(goals_against / total, 2),
    }


def combine_probability(a: float, b: float) -> float:
    return round((a + b) / 2, 1)


def tier(score: float, sample: int) -> str:
    if sample < 6:
        return "NO BET"
    if score >= 88:
        return "S++"
    if score >= 82:
        return "S+"
    if score >= 76:
        return "A++"
    return "NO BET"


def build_market_analysis(home: dict[str, float], away: dict[str, float]) -> pd.DataFrame:
    if not home.get("sample") or not away.get("sample"):
        return pd.DataFrame()

    markets = [
        {
            "Mercado": "Más de 1.5 goles",
            "Respaldo": combine_probability(home["over15_pct"], away["over15_pct"]),
            "Fundamento": "Frecuencia de +1.5 en los últimos partidos de ambos equipos.",
        },
        {
            "Mercado": "Menos de 4.5 goles",
            "Respaldo": combine_probability(home["under45_pct"], away["under45_pct"]),
            "Fundamento": "Frecuencia de partidos con 4 goles o menos.",
        },
        {
            "Mercado": "Ambos equipos anotan",
            "Respaldo": combine_probability(home["btts_pct"], away["btts_pct"]),
            "Fundamento": "Frecuencia BTTS reciente de ambos equipos.",
        },
        {
            "Mercado": "Local marca +0.5",
            "Respaldo": combine_probability(home["score_pct"], away["concede_pct"]),
            "Fundamento": "Local anotando y visitante concediendo.",
        },
        {
            "Mercado": "Visitante marca +0.5",
            "Respaldo": combine_probability(away["score_pct"], home["concede_pct"]),
            "Fundamento": "Visitante anotando y local concediendo.",
        },
        {
            "Mercado": "Local o empate (1X)",
            "Respaldo": round((100 - home["loss_pct"] + away["loss_pct"]) / 2, 1),
            "Fundamento": "Resistencia del local a perder y derrotas recientes del visitante.",
        },
        {
            "Mercado": "Visitante o empate (X2)",
            "Respaldo": round((100 - away["loss_pct"] + home["loss_pct"]) / 2, 1),
            "Fundamento": "Resistencia del visitante a perder y derrotas recientes del local.",
        },
    ]

    min_sample = min(int(home["sample"]), int(away["sample"]))
    for market in markets:
        market["Tier"] = tier(float(market["Respaldo"]), min_sample)

    return pd.DataFrame(markets).sort_values("Respaldo", ascending=False)


def show_api_status() -> None:
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
        st.sidebar.error(f"Error de conexión: {exc}")
        st.stop()


st.title("💎 JOYA 19 PRO")
st.caption("Fase 2 · JOYA Engine inicial · API-Football Pro")
show_api_status()

st.sidebar.header("Cartelera")
selected_date = st.sidebar.date_input(
    "Fecha",
    value=date.today(),
    min_value=date.today() - timedelta(days=14),
    max_value=date.today() + timedelta(days=60),
)
timezone = st.sidebar.selectbox("Zona horaria", ["America/Santiago", "UTC"], index=0)

with st.spinner("Cargando partidos..."):
    fixtures = api_get(
        "fixtures",
        {"date": selected_date.isoformat(), "timezone": timezone},
    ).get("response", [])

fixtures_df = fixture_rows(fixtures, timezone)

if fixtures_df.empty:
    st.warning("No se encontraron partidos para la fecha seleccionada.")
    st.stop()

country_options = ["Todos"] + sorted(fixtures_df["País"].dropna().unique().tolist())
country = st.sidebar.selectbox("País", country_options)

filtered = fixtures_df.copy()
if country != "Todos":
    filtered = filtered[filtered["País"] == country]

league_options = ["Todas"] + sorted(filtered["Liga"].dropna().unique().tolist())
league = st.sidebar.selectbox("Liga", league_options)
if league != "Todas":
    filtered = filtered[filtered["Liga"] == league]

search = st.sidebar.text_input("Buscar equipo")
if search:
    filtered = filtered[
        filtered["Local"].str.contains(search, case=False, na=False)
        | filtered["Visitante"].str.contains(search, case=False, na=False)
    ]

st.subheader(f"Partidos · {selected_date.strftime('%d-%m-%Y')}")
st.write(f"Se encontraron **{len(filtered)}** encuentros con los filtros actuales.")
st.dataframe(
    filtered[["Hora", "País", "Liga", "Local", "Visitante", "Marcador", "Estado"]],
    use_container_width=True,
    hide_index=True,
)

if filtered.empty:
    st.stop()

options = {
    f"{row.Hora} · {row.Local} vs {row.Visitante} · {row.Liga}": idx
    for idx, row in filtered.iterrows()
}
label = st.selectbox("Selecciona un partido para analizar", options.keys())
selected = filtered.loc[options[label]]

st.divider()
st.markdown(f"## {selected['Local']} **vs** {selected['Visitante']}")
st.caption(f"{selected['País']} · {selected['Liga']} · {selected['Hora']}")

analyze = st.button("🧠 ANALIZAR CON JOYA ENGINE", type="primary", use_container_width=True)

if analyze:
    with st.spinner("Consultando últimos partidos y calculando tendencias..."):
        home_recent = safe_response("fixtures", {"team": int(selected["home_id"]), "last": 10})
        away_recent = safe_response("fixtures", {"team": int(selected["away_id"]), "last": 10})

        home_metrics = team_match_metrics(home_recent, int(selected["home_id"]))
        away_metrics = team_match_metrics(away_recent, int(selected["away_id"]))
        markets = build_market_analysis(home_metrics, away_metrics)

    if markets.empty:
        st.error("No hay suficientes partidos finalizados para construir el análisis.")
        st.stop()

    min_sample = min(int(home_metrics["sample"]), int(away_metrics["sample"]))
    top = markets.iloc[0]
    top_score = float(top["Respaldo"])
    top_tier = str(top["Tier"])

    st.subheader("💎 Veredicto JOYA")
    c1, c2, c3 = st.columns(3)
    c1.metric("JOYA Score", f"{top_score:.1f}/100")
    c2.metric("Tier interno", top_tier)
    c3.metric("Muestra mínima", f"{min_sample} partidos")

    if top_tier == "NO BET":
        st.warning(
            "NO BET: el mercado mejor puntuado no supera el umbral interno "
            "o la muestra es insuficiente."
        )
    else:
        st.success(f"Núcleo inicial: **{top['Mercado']}**")

    st.dataframe(
        markets[["Mercado", "Respaldo", "Tier", "Fundamento"]],
        use_container_width=True,
        hide_index=True,
    )

    left, right = st.columns(2)
    with left:
        st.subheader(selected["Local"])
        st.json(home_metrics)
    with right:
        st.subheader(selected["Visitante"])
        st.json(away_metrics)

    st.caption(
        "Los porcentajes son indicadores descriptivos basados en resultados recientes, "
        "no probabilidades garantizadas. Esta versión todavía no incorpora cuotas, "
        "alineaciones confirmadas ni modelos por minuto."
    )

st.divider()
st.info(
    "Fase 2 inicial: JOYA Score por partido, ranking de mercados y NO BET. "
    "La siguiente mejora incorporará gol antes del 70', ningún gol antes del 10' "
    "y un ranking diario automatizado con control de consumo de API."
)
