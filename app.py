from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="JOYA 20 ELITE", page_icon="💎", layout="wide")

API_BASE = "https://v3.football.api-sports.io"
TZ = "America/Santiago"
RECENT_GENERAL = 10
RECENT_VENUE = 8
EVENT_SAMPLE = 8

EXCLUDED = {"u17", "u18", "u19", "u20", "u21", "u23", "youth", "reserve", "reserves"}
FRIENDLY = {"friendly", "friendlies", "amistoso", "amistosos"}


def api_key() -> str:
    try:
        return str(st.secrets["APISPORTS_KEY"]).strip()
    except Exception:
        return ""


@st.cache_data(ttl=300, show_spinner=False)
def api_get(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    if not api_key():
        raise RuntimeError("Falta APISPORTS_KEY en Streamlit Secrets.")

    response = requests.get(
        f"{API_BASE}/{endpoint.lstrip('/')}",
        headers={"x-apisports-key": api_key()},
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(str(payload["errors"]))
    return payload


def api_list(endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return api_get(endpoint, params).get("response", [])


def finished(item: dict[str, Any]) -> bool:
    return ((item.get("fixture", {}).get("status", {}) or {}).get("short")) in {"FT", "AET", "PEN"}


def get_team_fixtures(team_id: int, last: int = 20) -> list[dict[str, Any]]:
    return api_list("fixtures", {"team": team_id, "last": last})


def venue_fixtures(fixtures: list[dict[str, Any]], team_id: int, home: bool, limit: int) -> list[dict[str, Any]]:
    output = []
    for item in fixtures:
        if not finished(item):
            continue
        teams = item.get("teams", {}) or {}
        target = (teams.get("home", {}) or {}).get("id") if home else (teams.get("away", {}) or {}).get("id")
        if target == team_id:
            output.append(item)
        if len(output) >= limit:
            break
    return output


def basic_metrics(fixtures: list[dict[str, Any]], team_id: int) -> dict[str, float]:
    n = scored = conceded = over15 = over25 = under35 = under45 = btts = 0
    wins = draws = losses = 0

    for item in fixtures:
        if not finished(item):
            continue
        teams = item.get("teams", {}) or {}
        goals = item.get("goals", {}) or {}
        gh, ga = goals.get("home"), goals.get("away")
        if gh is None or ga is None:
            continue

        is_home = (teams.get("home", {}) or {}).get("id") == team_id
        gf, gc = (gh, ga) if is_home else (ga, gh)
        n += 1
        scored += gf >= 1
        conceded += gc >= 1
        over15 += gf + gc >= 2
        over25 += gf + gc >= 3
        under35 += gf + gc <= 3
        under45 += gf + gc <= 4
        btts += gf >= 1 and gc >= 1
        wins += gf > gc
        draws += gf == gc
        losses += gf < gc

    if n == 0:
        return {"sample": 0}

    pct = lambda x: round(100 * x / n, 1)
    return {
        "sample": n,
        "score": pct(scored),
        "concede": pct(conceded),
        "over15": pct(over15),
        "over25": pct(over25),
        "under35": pct(under35),
        "under45": pct(under45),
        "btts": pct(btts),
        "win": pct(wins),
        "draw": pct(draws),
        "loss": pct(losses),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fixture_goal_events(fixture_id: int) -> list[dict[str, Any]]:
    events = api_list("fixtures/events", {"fixture": fixture_id})
    return [
        event for event in events
        if event.get("type") == "Goal"
        and event.get("detail") not in {"Missed Penalty"}
    ]


def minute_value(event: dict[str, Any]) -> int | None:
    time = event.get("time", {}) or {}
    elapsed = time.get("elapsed")
    extra = time.get("extra") or 0
    if elapsed is None:
        return None
    return int(elapsed) + int(extra)


def minute_metrics(fixtures: list[dict[str, Any]], team_id: int, max_games: int) -> dict[str, float]:
    valid = []
    for item in fixtures:
        fixture_id = (item.get("fixture", {}) or {}).get("id")
        if fixture_id and finished(item):
            valid.append(item)
        if len(valid) >= max_games:
            break

    n = no_goal_10 = goal_70 = goal_1h = team_first = opp_first = 0
    team_goal_70 = opp_goal_70 = 0
    first_minutes = []

    for item in valid:
        fixture = item.get("fixture", {}) or {}
        teams = item.get("teams", {}) or {}
        events = fixture_goal_events(int(fixture["id"]))

        goals = []
        for event in events:
            minute = minute_value(event)
            team_event = (event.get("team", {}) or {}).get("id")
            if minute is not None:
                goals.append((minute, team_event))

        goals.sort(key=lambda x: x[0])
        n += 1

        first = goals[0] if goals else None
        no_goal_10 += first is None or first[0] > 10
        goal_70 += first is not None and first[0] <= 70
        goal_1h += any(minute <= 45 for minute, _ in goals)
        team_goal_70 += any(minute <= 70 and event_team == team_id for minute, event_team in goals)
        opp_goal_70 += any(minute <= 70 and event_team != team_id for minute, event_team in goals)

        if first:
            first_minutes.append(first[0])
            if first[1] == team_id:
                team_first += 1
            else:
                opp_first += 1

    if n == 0:
        return {"event_sample": 0}

    pct = lambda x: round(100 * x / n, 1)
    return {
        "event_sample": n,
        "no_goal_10": pct(no_goal_10),
        "goal_before_70": pct(goal_70),
        "goal_first_half": pct(goal_1h),
        "team_goal_before_70": pct(team_goal_70),
        "opp_goal_before_70": pct(opp_goal_70),
        "team_scores_first": pct(team_first),
        "opponent_scores_first": pct(opp_first),
        "avg_first_goal_minute": round(sum(first_minutes) / len(first_minutes), 1) if first_minutes else 0.0,
    }


def avg(a: float, b: float) -> float:
    return round((a + b) / 2, 1)


def tier(score: float, sample: int) -> str:
    if sample < 5:
        return "NO BET"
    if score >= 88:
        return "S++"
    if score >= 82:
        return "S+"
    if score >= 76:
        return "A++"
    return "NO BET"


def analyze_fixture(item: dict[str, Any]) -> tuple[dict[str, Any] | None, pd.DataFrame]:
    fixture = item.get("fixture", {}) or {}
    league = item.get("league", {}) or {}
    teams = item.get("teams", {}) or {}
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}
    home_id, away_id = home.get("id"), away.get("id")
    if not home_id or not away_id:
        return None, pd.DataFrame()

    home_all = get_team_fixtures(int(home_id), 25)
    away_all = get_team_fixtures(int(away_id), 25)
    home_venue = venue_fixtures(home_all, int(home_id), True, RECENT_VENUE)
    away_venue = venue_fixtures(away_all, int(away_id), False, RECENT_VENUE)

    hm = basic_metrics(home_venue or home_all[:RECENT_GENERAL], int(home_id))
    am = basic_metrics(away_venue or away_all[:RECENT_GENERAL], int(away_id))
    hmin = minute_metrics(home_venue or home_all, int(home_id), EVENT_SAMPLE)
    amin = minute_metrics(away_venue or away_all, int(away_id), EVENT_SAMPLE)

    sample = min(int(hm.get("sample", 0)), int(am.get("sample", 0)))
    event_sample = min(int(hmin.get("event_sample", 0)), int(amin.get("event_sample", 0)))

    rows = [
        ("Goles", "Total de goles - Más de 1.5", avg(hm.get("over15", 0), am.get("over15", 0))),
        ("Goles", "Total de goles - Más de 2.5", avg(hm.get("over25", 0), am.get("over25", 0))),
        ("Goles", "Total de goles - Menos de 3.5", avg(hm.get("under35", 0), am.get("under35", 0))),
        ("Goles", "Total de goles - Menos de 4.5", avg(hm.get("under45", 0), am.get("under45", 0)) - 7),
        ("BTTS", "Ambos equipos marcan - Sí", avg(hm.get("btts", 0), am.get("btts", 0))),
        ("Doble oportunidad", "Doble oportunidad - 1X", round((100-hm.get("loss",0)+am.get("loss",0))/2,1)-3),
        ("Doble oportunidad", "Doble oportunidad - X2", round((100-am.get("loss",0)+hm.get("loss",0))/2,1)-3),
        ("Equipo", "Goles del local - Más de 0.5", avg(hm.get("score",0), am.get("concede",0))),
        ("Equipo", "Goles del visitante - Más de 0.5", avg(am.get("score",0), hm.get("concede",0))),
    ]

    if event_sample >= 5:
        no10 = avg(hmin["no_goal_10"], amin["no_goal_10"])
        before70 = avg(hmin["goal_before_70"], amin["goal_before_70"])
        rows.extend([
            ("Minutos", "Ningún gol antes del minuto 10", no10),
            ("Minutos", "Gol antes del minuto 70", before70),
            ("Minutos", "Más de 0.5 goles en 1ª parte", avg(hmin["goal_first_half"], amin["goal_first_half"])),
            ("Minutos", "Sin gol 0–10 + gol antes del 70", round(no10 * before70 / 100, 1)),
            ("Minutos", "Local marca antes del 70", avg(hmin["team_goal_before_70"], amin["opp_goal_before_70"])),
            ("Minutos", "Visitante marca antes del 70", avg(amin["team_goal_before_70"], hmin["opp_goal_before_70"])),
            ("Primer gol", "Local marca primero", avg(hmin["team_scores_first"], amin["opponent_scores_first"])),
            ("Primer gol", "Visitante marca primero", avg(amin["team_scores_first"], hmin["opponent_scores_first"])),
        ])

    table = pd.DataFrame(rows, columns=["Grupo", "Mercado", "JOYA Score"])
    table["JOYA Score"] = table["JOYA Score"].clip(lower=0, upper=100).round(1)
    table["Muestra"] = table["Grupo"].apply(lambda g: event_sample if g in {"Minutos", "Primer gol"} else sample)
    table["Tier"] = table.apply(lambda r: tier(float(r["JOYA Score"]), int(r["Muestra"])), axis=1)
    table = table.sort_values(["JOYA Score", "Muestra"], ascending=[False, False])

    valid = table[table["Tier"] != "NO BET"]
    if valid.empty:
        return None, table

    best = valid.iloc[0]
    summary = {
        "fixture_id": fixture.get("id"),
        "País": league.get("country") or "Sin país",
        "Liga": league.get("name") or "Sin liga",
        "Local": home.get("name") or "Local",
        "Visitante": away.get("name") or "Visitante",
        "Pick": best["Mercado"],
        "Grupo": best["Grupo"],
        "JOYA Score": float(best["JOYA Score"]),
        "Tier": best["Tier"],
        "Muestra": int(best["Muestra"]),
        "Local casa": int(hm.get("sample", 0)),
        "Visitante fuera": int(am.get("sample", 0)),
        "Eventos": event_sample,
    }
    return summary, table


def next_goal_live(item: dict[str, Any]) -> dict[str, Any]:
    fixture = item.get("fixture", {}) or {}
    fixture_id = int(fixture["id"])
    teams = item.get("teams", {}) or {}
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}
    home_id, away_id = home.get("id"), away.get("id")

    stats = api_list("fixtures/statistics", {"fixture": fixture_id})
    events = api_list("fixtures/events", {"fixture": fixture_id})

    home_pressure = away_pressure = 0.0
    weights = {
        "Shots on Goal": 3.0,
        "Total Shots": 1.2,
        "Corner Kicks": 1.0,
        "Ball Possession": 0.15,
        "Dangerous Attacks": 0.08,
    }

    for block in stats:
        team_id = (block.get("team", {}) or {}).get("id")
        score = 0.0
        for stat in block.get("statistics", []) or []:
            stat_type = stat.get("type")
            value = stat.get("value")
            if isinstance(value, str) and value.endswith("%"):
                try:
                    value = float(value.rstrip("%"))
                except Exception:
                    value = 0
            try:
                numeric = float(value or 0)
            except Exception:
                numeric = 0
            score += weights.get(stat_type, 0) * numeric

        if team_id == home_id:
            home_pressure = score
        elif team_id == away_id:
            away_pressure = score

    red_home = red_away = 0
    for event in events:
        if event.get("type") == "Card" and event.get("detail") == "Red Card":
            event_team = (event.get("team", {}) or {}).get("id")
            if event_team == home_id:
                red_home += 1
            elif event_team == away_id:
                red_away += 1

    home_pressure *= max(0.45, 1 - 0.35 * red_home)
    away_pressure *= max(0.45, 1 - 0.35 * red_away)
    total = home_pressure + away_pressure

    if total <= 0:
        return {"pick": "NO DATA", "home": 0, "away": 0, "confidence": "NO BET"}

    home_pct = round(100 * home_pressure / total, 1)
    away_pct = round(100 - home_pct, 1)
    difference = abs(home_pct - away_pct)

    if difference < 10:
        pick = "Sin ventaja clara"
        confidence = "NO BET"
    elif home_pct > away_pct:
        pick = f"Próximo gol: {home.get('name', 'Local')}"
        confidence = "S+" if difference >= 25 else "A++"
    else:
        pick = f"Próximo gol: {away.get('name', 'Visitante')}"
        confidence = "S+" if difference >= 25 else "A++"

    return {"pick": pick, "home": home_pct, "away": away_pct, "confidence": confidence}


st.title("💎 JOYA 20 ELITE")
st.caption("Versión 0.5 · Minute Engine + local/visitante + próximo gol en vivo")

if not api_key():
    st.error("Falta APISPORTS_KEY en Streamlit Secrets.")
    st.stop()

selected_date = st.sidebar.date_input(
    "Fecha",
    value=date.today(),
    min_value=date.today() - timedelta(days=7),
    max_value=date.today() + timedelta(days=30),
)
exclude_youth = st.sidebar.checkbox("Excluir juveniles y reservas", True)
exclude_friendlies = st.sidebar.checkbox("Excluir amistosos", False)

fixtures = api_list("fixtures", {"date": selected_date.isoformat(), "timezone": TZ})

prepared = []
for item in fixtures:
    league = ((item.get("league", {}) or {}).get("name") or "").lower()
    if exclude_youth and any(word in league for word in EXCLUDED):
        continue
    if exclude_friendlies and any(word in league for word in FRIENDLY):
        continue
    prepared.append(item)

st.metric("Partidos disponibles", len(prepared))

labels = {}
for index, item in enumerate(prepared):
    teams = item.get("teams", {}) or {}
    league = item.get("league", {}) or {}
    home = (teams.get("home", {}) or {}).get("name", "Local")
    away = (teams.get("away", {}) or {}).get("name", "Visitante")
    labels[f"{league.get('country','')} · {league.get('name','')} · {home} vs {away}"] = index

if not labels:
    st.warning("No hay partidos para la fecha seleccionada.")
    st.stop()

selected_label = st.selectbox("Selecciona un partido", labels.keys())
selected_item = prepared[labels[selected_label]]

tab1, tab2 = st.tabs(["📊 Prepartido Minute Engine", "🔴 Próximo gol en vivo"])

with tab1:
    st.warning(
        "El análisis por minutos consume más solicitudes porque revisa eventos históricos. "
        "Úsalo partido por partido antes de activar un scanner masivo."
    )
    if st.button("🧠 ANALIZAR PARTIDO", type="primary", use_container_width=True):
        with st.spinner("Analizando local en casa, visitante fuera y minutos de gol…"):
            summary, markets = analyze_fixture(selected_item)

        if markets.empty:
            st.error("No hay datos suficientes.")
        else:
            if summary:
                a, b, c = st.columns(3)
                a.metric("Mejor mercado", summary["Pick"])
                b.metric("JOYA Score", summary["JOYA Score"])
                c.metric("Tier", summary["Tier"])

                st.write(
                    f"Muestras: **{summary['Local casa']}** del local en casa · "
                    f"**{summary['Visitante fuera']}** del visitante fuera · "
                    f"**{summary['Eventos']}** con eventos de minutos."
                )
            else:
                st.warning("NO BET: ningún mercado superó los filtros.")

            st.dataframe(markets, use_container_width=True, hide_index=True)

with tab2:
    status = ((selected_item.get("fixture", {}) or {}).get("status", {}) or {}).get("short")
    elapsed = ((selected_item.get("fixture", {}) or {}).get("status", {}) or {}).get("elapsed")

    st.write(f"Estado API: **{status}** · minuto **{elapsed or '—'}**")
    st.caption(
        "Este módulo usa presión en vivo: tiros al arco, tiros totales, córners, "
        "posesión y expulsiones, cuando la competición entrega esos datos."
    )

    if st.button("⚡ CALCULAR PRÓXIMO GOL", use_container_width=True):
        if status not in {"1H", "HT", "2H", "ET", "BT", "P"}:
            st.warning("El partido no aparece en vivo o no tiene cobertura activa.")
        else:
            with st.spinner("Consultando estadísticas y eventos en vivo…"):
                result = next_goal_live(selected_item)

            st.subheader(result["pick"])
            x, y, z = st.columns(3)
            teams = selected_item.get("teams", {}) or {}
            x.metric((teams.get("home", {}) or {}).get("name", "Local"), f"{result['home']}%")
            y.metric((teams.get("away", {}) or {}).get("name", "Visitante"), f"{result['away']}%")
            z.metric("Tier interno", result["confidence"])

            st.caption(
                "Es una lectura de presión relativa, no una probabilidad garantizada. "
                "Devuelve NO BET cuando la diferencia entre ambos equipos es pequeña."
            )
