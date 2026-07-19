from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Callable

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="JOYA 20 ELITE", page_icon="💎", layout="wide")

API_BASE = "https://v3.football.api-sports.io"
DEFAULT_TIMEZONE = "America/Santiago"
RECENT_MATCHES = 10

EXCLUDED_KEYWORDS = {
    "u17", "u18", "u19", "u20", "u21", "u23",
    "youth", "juvenil", "reserve", "reserves",
}
VOLATILE_KEYWORDS = {"friendly", "friendlies", "amistoso", "amistosos"}


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

    response = requests.get(
        f"{API_BASE}/{endpoint.lstrip('/')}",
        headers={"x-apisports-key": key},
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("errors"):
        raise RuntimeError(f"API-Football devolvió: {payload['errors']}")

    return payload


def response_list(endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return api_get(endpoint, params).get("response", [])


def team_metrics(fixtures: list[dict[str, Any]], team_id: int) -> dict[str, float]:
    finished = {"FT", "AET", "PEN"}
    total = wins = draws = losses = 0
    scored = conceded = over15 = btts = under45 = 0
    goals_for = goals_against = 0

    for item in fixtures:
        fixture = item.get("fixture", {}) or {}
        if (fixture.get("status", {}) or {}).get("short") not in finished:
            continue

        teams = item.get("teams", {}) or {}
        goals = item.get("goals", {}) or {}
        home = teams.get("home", {}) or {}
        gh, ga = goals.get("home"), goals.get("away")

        if gh is None or ga is None:
            continue

        is_home = home.get("id") == team_id
        gf, gc = (gh, ga) if is_home else (ga, gh)

        total += 1
        goals_for += gf
        goals_against += gc
        scored += int(gf >= 1)
        conceded += int(gc >= 1)
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

    pct = lambda value: round(value * 100 / total, 1)
    return {
        "sample": total,
        "win_pct": pct(wins),
        "draw_pct": pct(draws),
        "loss_pct": pct(losses),
        "score_pct": pct(scored),
        "concede_pct": pct(conceded),
        "over15_pct": pct(over15),
        "btts_pct": pct(btts),
        "under45_pct": pct(under45),
        "gf_avg": round(goals_for / total, 2),
        "ga_avg": round(goals_against / total, 2),
    }


def average(a: float, b: float) -> float:
    return round((a + b) / 2, 1)


def assign_tier(score: float, sample: int) -> str:
    if sample < 6:
        return "NO BET"
    if score >= 88:
        return "S++"
    if score >= 82:
        return "S+"
    if score >= 76:
        return "A++"
    return "NO BET"


def evaluate_markets(home: dict[str, float], away: dict[str, float]) -> pd.DataFrame:
    if not home.get("sample") or not away.get("sample"):
        return pd.DataFrame()

    sample = min(int(home["sample"]), int(away["sample"]))
    rows = [
        ("Total de goles - Más de 1.5",
         average(home["over15_pct"], away["over15_pct"])),
        ("Total de goles - Menos de 4.5",
         average(home["under45_pct"], away["under45_pct"])),
        ("Ambos equipos marcan - Sí",
         average(home["btts_pct"], away["btts_pct"])),
        ("Goles del equipo local - Más de 0.5",
         average(home["score_pct"], away["concede_pct"])),
        ("Goles del equipo visitante - Más de 0.5",
         average(away["score_pct"], home["concede_pct"])),
        ("Doble oportunidad - 1X",
         round((100 - home["loss_pct"] + away["loss_pct"]) / 2, 1)),
        ("Doble oportunidad - X2",
         round((100 - away["loss_pct"] + home["loss_pct"]) / 2, 1)),
    ]

    output = []
    for market, score in rows:
        output.append({
            "Pick": market,
            "JOYA Score": score,
            "Tier": assign_tier(score, sample),
            "Muestra": sample,
        })

    return pd.DataFrame(output).sort_values("JOYA Score", ascending=False)


def contains_keyword(name: str, words: set[str]) -> bool:
    value = name.lower()
    return any(word in value for word in words)


def prepare_fixtures(
    fixtures: list[dict[str, Any]],
    exclude_youth_reserves: bool,
    exclude_friendlies: bool,
) -> list[dict[str, Any]]:
    selected = []
    for item in fixtures:
        league_name = ((item.get("league", {}) or {}).get("name") or "")
        if exclude_youth_reserves and contains_keyword(league_name, EXCLUDED_KEYWORDS):
            continue
        if exclude_friendlies and contains_keyword(league_name, VOLATILE_KEYWORDS):
            continue
        selected.append(item)

    return sorted(
        selected,
        key=lambda x: (
            ((x.get("league", {}) or {}).get("country") or ""),
            ((x.get("league", {}) or {}).get("name") or ""),
            ((x.get("fixture", {}) or {}).get("date") or ""),
        ),
    )


def fixture_catalog(fixtures: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for item in fixtures:
        fixture = item.get("fixture", {}) or {}
        league = item.get("league", {}) or {}
        teams = item.get("teams", {}) or {}
        rows.append({
            "fixture_id": fixture.get("id"),
            "País": league.get("country") or "Sin país",
            "Liga": league.get("name") or "Sin liga",
            "Local": (teams.get("home", {}) or {}).get("name") or "Local",
            "Visitante": (teams.get("away", {}) or {}).get("name") or "Visitante",
            "Hora": pd.to_datetime(
                fixture.get("date"), errors="coerce", utc=True
            ).tz_convert(DEFAULT_TIMEZONE).strftime("%H:%M")
            if fixture.get("date") else "—",
        })
    return pd.DataFrame(rows)


def scan_fixture(item: dict[str, Any]) -> dict[str, Any] | None:
    fixture = item.get("fixture", {}) or {}
    league = item.get("league", {}) or {}
    teams = item.get("teams", {}) or {}
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}

    home_id, away_id = home.get("id"), away.get("id")
    if not home_id or not away_id:
        return None

    home_recent = response_list("fixtures", {"team": home_id, "last": RECENT_MATCHES})
    away_recent = response_list("fixtures", {"team": away_id, "last": RECENT_MATCHES})

    home_stats = team_metrics(home_recent, int(home_id))
    away_stats = team_metrics(away_recent, int(away_id))
    markets = evaluate_markets(home_stats, away_stats)

    if markets.empty:
        return None

    best = markets.iloc[0]
    return {
        "fixture_id": fixture.get("id"),
        "País": league.get("country") or "Sin país",
        "Liga": league.get("name") or "Sin liga",
        "Local": home.get("name") or "Local",
        "Visitante": away.get("name") or "Visitante",
        "Pick": best["Pick"],
        "JOYA Score": float(best["JOYA Score"]),
        "Tier": str(best["Tier"]),
        "Muestra": int(best["Muestra"]),
    }


def scan_all_by_league(
    fixtures: list[dict[str, Any]],
    max_matches_per_league: int,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> pd.DataFrame:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for item in fixtures:
        league = item.get("league", {}) or {}
        key = (
            league.get("country") or "Sin país",
            league.get("name") or "Sin liga",
        )
        grouped[key].append(item)

    queue = []
    for key in sorted(grouped):
        queue.extend(grouped[key][:max_matches_per_league])

    results = []
    total = len(queue)

    for index, item in enumerate(queue, start=1):
        league_name = ((item.get("league", {}) or {}).get("name") or "Sin liga")
        try:
            result = scan_fixture(item)
            if result:
                results.append(result)
        except Exception:
            pass

        if progress_callback:
            progress_callback(index, total, league_name)

    if not results:
        return pd.DataFrame()

    return pd.DataFrame(results).sort_values(
        ["País", "Liga", "JOYA Score", "Muestra"],
        ascending=[True, True, False, False],
    )


def build_cart(
    ranking: pd.DataFrame,
    target_odds: float,
    max_picks: int,
    minimum_tier: str,
    assumed_odds: float,
    selected_leagues: list[str],
    max_one_per_league: bool,
) -> tuple[pd.DataFrame, float]:
    if ranking.empty:
        return pd.DataFrame(), 1.0

    tier_order = {"S++": 3, "S+": 2, "A++": 1, "NO BET": 0}
    valid = ranking[
        ranking["Tier"].map(tier_order).fillna(0) >= tier_order[minimum_tier]
    ].copy()

    if selected_leagues:
        valid = valid[valid["Liga"].isin(selected_leagues)]

    valid = valid.sort_values(["JOYA Score", "Muestra"], ascending=[False, False])

    picks, used_leagues, used_fixtures = [], set(), set()
    combined = 1.0

    for _, row in valid.iterrows():
        if row["fixture_id"] in used_fixtures:
            continue
        if max_one_per_league and row["Liga"] in used_leagues:
            continue

        picks.append(row)
        used_fixtures.add(row["fixture_id"])
        used_leagues.add(row["Liga"])
        combined *= assumed_odds

        if combined >= target_odds or len(picks) >= max_picks:
            break

    return (pd.DataFrame(picks), round(combined, 2)) if picks else (pd.DataFrame(), 1.0)


st.title("💎 JOYA 20 ELITE")
st.caption("Versión 0.2 estable · Todas las ligas separadas")

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

st.sidebar.header("Scanner")
selected_date = st.sidebar.date_input(
    "Fecha",
    value=date.today(),
    min_value=date.today() - timedelta(days=7),
    max_value=date.today() + timedelta(days=30),
)
exclude_youth = st.sidebar.checkbox("Excluir juveniles y reservas", value=True)
exclude_friendlies = st.sidebar.checkbox("Excluir amistosos", value=False)
max_per_league = st.sidebar.select_slider(
    "Máximo de partidos por liga",
    options=[1, 2, 3, 4, 5, 10, 20],
    value=3,
)

fixtures = api_get(
    "fixtures",
    {"date": selected_date.isoformat(), "timezone": DEFAULT_TIMEZONE},
).get("response", [])

prepared = prepare_fixtures(fixtures, exclude_youth, exclude_friendlies)
catalog = fixture_catalog(prepared)

c1, c2, c3 = st.columns(3)
c1.metric("Partidos disponibles", len(catalog))
c2.metric("Ligas disponibles", catalog["Liga"].nunique() if not catalog.empty else 0)
estimated = (
    catalog.groupby(["País", "Liga"]).head(int(max_per_league)).shape[0]
    if not catalog.empty else 0
)
c3.metric("Partidos que escaneará", estimated)

st.subheader("🌍 Cartelera separada por ligas")
for (country, league), group in catalog.groupby(["País", "Liga"], sort=True):
    with st.expander(f"{country} · {league} ({len(group)} partidos)"):
        st.dataframe(
            group[["Hora", "Local", "Visitante"]],
            use_container_width=True,
            hide_index=True,
        )

if "ranking_single" not in st.session_state:
    st.session_state.ranking_single = pd.DataFrame()

if st.button("🧠 ESCANEAR TODAS LAS LIGAS", type="primary", use_container_width=True):
    progress = st.progress(0)
    status_text = st.empty()

    def update(current: int, total: int, league_name: str) -> None:
        progress.progress(current / total if total else 1)
        status_text.caption(f"Analizando {current} de {total} · {league_name}")

    with st.spinner("Analizando todas las ligas…"):
        st.session_state.ranking_single = scan_all_by_league(
            prepared,
            int(max_per_league),
            update,
        )

    progress.empty()
    status_text.empty()

ranking = st.session_state.ranking_single

if not ranking.empty:
    st.subheader("🏆 Resultados separados por liga")
    for (country, league), group in ranking.groupby(["País", "Liga"], sort=True):
        with st.expander(
            f"{country} · {league} · {len(group)} picks · mejor {group['JOYA Score'].max():.1f}"
        ):
            st.dataframe(
                group[["Local", "Visitante", "Pick", "JOYA Score", "Tier", "Muestra"]],
                use_container_width=True,
                hide_index=True,
            )
else:
    st.info("Ejecuta el scanner para generar el ranking.")

st.divider()
st.subheader("🚀 Crear cartilla")

available_leagues = sorted(ranking["Liga"].unique().tolist()) if not ranking.empty else []
selected_leagues = st.multiselect(
    "Ligas disponibles en Betano",
    options=available_leagues,
    placeholder="Vacío = todas",
)

a, b, c, d = st.columns(4)
target_odds = a.selectbox("Cuota objetivo", [2.0, 3.0, 4.0, 5.0], index=1)
max_picks = b.selectbox("Máximo de picks", [2, 3, 4, 5, 6], index=3)
minimum_tier = c.selectbox("Tier mínimo", ["S++", "S+", "A++"], index=1)
assumed_odds = d.number_input(
    "Cuota media estimada",
    min_value=1.05,
    max_value=2.00,
    value=1.30,
    step=0.05,
)
max_one_per_league = st.checkbox("Máximo un pick por liga", value=True)

if st.button("📋 CREAR CARTILLA", use_container_width=True):
    cart, combined = build_cart(
        ranking,
        float(target_odds),
        int(max_picks),
        str(minimum_tier),
        float(assumed_odds),
        selected_leagues,
        max_one_per_league,
    )

    if cart.empty:
        st.warning("No hay suficientes selecciones para crear la cartilla.")
    else:
        if combined < target_odds:
            st.warning(
                f"Cuota estimada {combined:.2f}, bajo el objetivo. JOYA no forzó picks."
            )
        else:
            st.success(f"Cartilla creada · cuota estimada {combined:.2f}")

        st.dataframe(
            cart[["País", "Liga", "Local", "Visitante", "Pick", "JOYA Score", "Tier"]],
            use_container_width=True,
            hide_index=True,
        )

st.caption(
    "Esta versión usa cuota media manual. La integración de cuotas reales de Betano "
    "se incorporará después de validar la cobertura del bookmaker."
)
