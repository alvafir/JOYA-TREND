from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from io import BytesIO
from typing import Any, Callable

import math
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="JOYA 22 AI", page_icon="💎", layout="wide")

API_BASE = "https://v3.football.api-sports.io"
TZ = "America/Santiago"
RECENT_GENERAL = 10
RECENT_VENUE = 8
EVENT_SAMPLE = 6

EXCLUDED = {
    "u17", "u18", "u19", "u20", "u21", "u23",
    "youth", "juvenil", "reserve", "reserves",
}
FRIENDLY = {"friendly", "friendlies", "amistoso", "amistosos"}

MARKET_PENALTIES = {
    "Total de goles - Menos de 4.5": 10.0,
    "Total de goles - Menos de 3.5": 5.0,
    "Total de goles - Más de 1.5": 3.0,
    "Total de goles - Más de 2.5": 1.0,
    "Doble oportunidad - 1X": 5.0,
    "Doble oportunidad - X2": 5.0,
    "Doble oportunidad - 12": 6.0,
    "Goles del local - Más de 0.5": 2.0,
    "Goles del visitante - Más de 0.5": 2.0,
    "Goles del local - Más de 1.5": 1.0,
    "Goles del visitante - Más de 1.5": 1.0,
    "Goles del local - Menos de 2.5": 4.0,
    "Goles del visitante - Menos de 2.5": 4.0,
    "Ningún gol antes del minuto 10": 3.0,
    "Gol antes del minuto 70": 3.0,
    "Local marca primero": 3.0,
    "Visitante marca primero": 3.0,
}

TIER_ORDER = {"S++": 4, "S+": 3, "A++": 2, "A+": 1, "NO BET": 0}


def api_key() -> str:
    try:
        return str(st.secrets["APISPORTS_KEY"]).strip()
    except Exception:
        return ""


@st.cache_data(ttl=300, show_spinner=False)
def api_get(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    key = api_key()
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
        raise RuntimeError(str(payload["errors"]))

    return payload


def api_list(endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return api_get(endpoint, params).get("response", [])


def finished(item: dict[str, Any]) -> bool:
    status = ((item.get("fixture", {}) or {}).get("status", {}) or {}).get("short")
    return status in {"FT", "AET", "PEN"}


def contains_keyword(text: str, words: set[str]) -> bool:
    value = text.lower()
    return any(word in value for word in words)


def get_team_fixtures(team_id: int, last: int = 25) -> list[dict[str, Any]]:
    return api_list("fixtures", {"team": team_id, "last": last})


def venue_fixtures(fixtures: list[dict[str, Any]], team_id: int, home: bool, limit: int) -> list[dict[str, Any]]:
    result = []
    for item in fixtures:
        if not finished(item):
            continue

        teams = item.get("teams", {}) or {}
        selected_id = (
            (teams.get("home", {}) or {}).get("id")
            if home
            else (teams.get("away", {}) or {}).get("id")
        )

        if selected_id == team_id:
            result.append(item)

        if len(result) >= limit:
            break

    return result


def basic_metrics(fixtures: list[dict[str, Any]], team_id: int) -> dict[str, float]:
    n = 0
    scored = conceded = over15 = over25 = under35 = under45 = btts = 0
    team_over15 = team_under25 = 0
    first_half_over05 = first_half_under25 = 0
    wins = draws = losses = 0
    goals_for = goals_against = 0

    for item in fixtures:
        if not finished(item):
            continue

        teams = item.get("teams", {}) or {}
        goals = item.get("goals", {}) or {}
        score = item.get("score", {}) or {}
        halftime = score.get("halftime", {}) or {}

        home = teams.get("home", {}) or {}
        gh, ga = goals.get("home"), goals.get("away")
        hth, hta = halftime.get("home"), halftime.get("away")

        if gh is None or ga is None:
            continue

        is_home = home.get("id") == team_id
        gf, gc = (gh, ga) if is_home else (ga, gh)

        n += 1
        goals_for += gf
        goals_against += gc
        scored += int(gf >= 1)
        conceded += int(gc >= 1)
        over15 += int(gf + gc >= 2)
        over25 += int(gf + gc >= 3)
        under35 += int(gf + gc <= 3)
        under45 += int(gf + gc <= 4)
        btts += int(gf >= 1 and gc >= 1)
        team_over15 += int(gf >= 2)
        team_under25 += int(gf <= 2)

        if hth is not None and hta is not None:
            first_half_over05 += int(hth + hta >= 1)
            first_half_under25 += int(hth + hta <= 2)

        wins += int(gf > gc)
        draws += int(gf == gc)
        losses += int(gf < gc)

    if n == 0:
        return {"sample": 0}

    pct = lambda value: round(100 * value / n, 1)

    return {
        "sample": n,
        "score": pct(scored),
        "concede": pct(conceded),
        "over15": pct(over15),
        "over25": pct(over25),
        "under35": pct(under35),
        "under45": pct(under45),
        "btts": pct(btts),
        "team_over15": pct(team_over15),
        "team_under25": pct(team_under25),
        "first_half_over05": pct(first_half_over05),
        "first_half_under25": pct(first_half_under25),
        "win": pct(wins),
        "draw": pct(draws),
        "loss": pct(losses),
        "gf_avg": round(goals_for / n, 2),
        "ga_avg": round(goals_against / n, 2),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fixture_goal_events(fixture_id: int) -> list[dict[str, Any]]:
    events = api_list("fixtures/events", {"fixture": fixture_id})
    return [
        event
        for event in events
        if event.get("type") == "Goal"
        and event.get("detail") != "Missed Penalty"
    ]


def event_minute(event: dict[str, Any]) -> int | None:
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

    n = 0
    no_goal_10 = goal_before_70 = goal_first_half = 0
    team_goal_70 = opponent_goal_70 = 0
    team_first = opponent_first = 0
    first_goal_minutes = []

    for item in valid:
        fixture_id = int((item.get("fixture", {}) or {}).get("id"))
        events = fixture_goal_events(fixture_id)

        goals: list[tuple[int, int | None]] = []

        for event in events:
            minute = event_minute(event)
            event_team_id = (event.get("team", {}) or {}).get("id")
            if minute is not None:
                goals.append((minute, event_team_id))

        goals.sort(key=lambda value: value[0])
        first = goals[0] if goals else None

        n += 1
        no_goal_10 += int(first is None or first[0] > 10)
        goal_before_70 += int(first is not None and first[0] <= 70)
        goal_first_half += int(any(minute <= 45 for minute, _ in goals))
        team_goal_70 += int(any(minute <= 70 and event_team == team_id for minute, event_team in goals))
        opponent_goal_70 += int(any(minute <= 70 and event_team != team_id for minute, event_team in goals))

        if first:
            first_goal_minutes.append(first[0])
            team_first += int(first[1] == team_id)
            opponent_first += int(first[1] != team_id)

    if n == 0:
        return {"event_sample": 0}

    pct = lambda value: round(100 * value / n, 1)

    return {
        "event_sample": n,
        "no_goal_10": pct(no_goal_10),
        "goal_before_70": pct(goal_before_70),
        "goal_first_half": pct(goal_first_half),
        "team_goal_before_70": pct(team_goal_70),
        "opponent_goal_before_70": pct(opponent_goal_70),
        "team_scores_first": pct(team_first),
        "opponent_scores_first": pct(opponent_first),
        "avg_first_goal_minute": round(sum(first_goal_minutes) / len(first_goal_minutes), 1)
        if first_goal_minutes else 0.0,
    }


def avg(a: float, b: float) -> float:
    return round((a + b) / 2, 1)


def calibrated_score(raw_score: float, sample: int, penalty: float = 0.0, brain_adjustment: float = 0.0) -> float:
    """
    Conservative calibration:
    - shrinks extreme percentages toward 75;
    - rewards larger samples slightly;
    - applies market and JOYA Brain adjustments;
    - makes 98-100 genuinely rare.
    """
    sample_weight = min(1.0, sample / 12)
    shrink_target = 75.0
    shrunk = shrink_target + (raw_score - shrink_target) * (0.55 + 0.25 * sample_weight)
    sample_bonus = min(4.0, max(0.0, sample - 5) * 0.45)
    score = shrunk + sample_bonus - penalty + brain_adjustment
    return round(max(0.0, min(99.0, score)), 1)


def assign_tier(score: float, sample: int) -> str:
    if sample < 5:
        return "NO BET"
    if score >= 95:
        return "S++"
    if score >= 90:
        return "S+"
    if score >= 85:
        return "A++"
    if score >= 80:
        return "A+"
    return "NO BET"


def load_brain(uploaded_file: Any) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame(columns=["Liga", "Mercado", "Picks", "Aciertos"])

    try:
        df = pd.read_csv(uploaded_file)
        required = {"Liga", "Mercado", "Picks", "Aciertos"}
        if not required.issubset(df.columns):
            return pd.DataFrame(columns=["Liga", "Mercado", "Picks", "Aciertos"])
        return df
    except Exception:
        return pd.DataFrame(columns=["Liga", "Mercado", "Picks", "Aciertos"])


def brain_adjustment(brain: pd.DataFrame, league_name: str, market: str) -> tuple[float, str]:
    if brain.empty:
        return 0.0, "Sin historial JOYA Brain"

    subset = brain[
        (brain["Liga"].astype(str) == str(league_name))
        & (brain["Mercado"].astype(str) == str(market))
    ]

    if subset.empty:
        return 0.0, "Sin historial específico"

    row = subset.iloc[0]
    picks = max(0, int(row.get("Picks", 0)))
    hits = max(0, int(row.get("Aciertos", 0)))

    if picks < 20:
        return 0.0, f"Historial insuficiente ({picks} picks)"

    hit_rate = hits / picks
    adjustment = max(-4.0, min(4.0, (hit_rate - 0.72) * 18))
    return round(adjustment, 1), f"Histórico liga/mercado: {hit_rate*100:.1f}% en {picks} picks"


def market_row(
    group: str,
    market: str,
    raw_score: float,
    sample: int,
    league_name: str,
    brain: pd.DataFrame,
    explanation: str,
) -> dict[str, Any]:
    brain_adj, brain_reason = brain_adjustment(brain, league_name, market)
    penalty = MARKET_PENALTIES.get(market, 0.0)
    score = calibrated_score(raw_score, sample, penalty, brain_adj)

    return {
        "Grupo": group,
        "Mercado": market,
        "Score bruto": round(raw_score, 1),
        "JOYA Score": score,
        "Tier": assign_tier(score, sample),
        "Muestra": sample,
        "Explicación": explanation,
        "JOYA Brain": brain_reason,
    }


def radar_components(home_metrics: dict[str, float], away_metrics: dict[str, float], minute_data: float = 0.0) -> dict[str, float]:
    return {
        "Ataque local": round((home_metrics.get("score", 0) + home_metrics.get("win", 0)) / 2, 1),
        "Fragilidad visitante": round((away_metrics.get("concede", 0) + away_metrics.get("loss", 0)) / 2, 1),
        "Goles": round((home_metrics.get("over15", 0) + away_metrics.get("over15", 0)) / 2, 1),
        "Localía": round(home_metrics.get("win", 0), 1),
        "Visitante": round(100 - away_metrics.get("loss", 0), 1),
        "Minutos": round(minute_data, 1),
    }


def analyze_fixture(
    item: dict[str, Any],
    enabled_groups: set[str],
    brain: pd.DataFrame,
) -> tuple[dict[str, Any] | None, pd.DataFrame, dict[str, float], dict[str, Any]]:
    fixture = item.get("fixture", {}) or {}
    league = item.get("league", {}) or {}
    teams = item.get("teams", {}) or {}
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}
    league_name = league.get("name") or "Sin liga"

    home_id, away_id = home.get("id"), away.get("id")
    if not home_id or not away_id:
        return None, pd.DataFrame(), {}, {}

    home_all = get_team_fixtures(int(home_id))
    away_all = get_team_fixtures(int(away_id))

    home_base = venue_fixtures(home_all, int(home_id), True, RECENT_VENUE) or home_all[:RECENT_GENERAL]
    away_base = venue_fixtures(away_all, int(away_id), False, RECENT_VENUE) or away_all[:RECENT_GENERAL]

    hm = basic_metrics(home_base, int(home_id))
    am = basic_metrics(away_base, int(away_id))
    sample = min(int(hm.get("sample", 0)), int(am.get("sample", 0)))

    rows: list[dict[str, Any]] = []
    minute_strength = 0.0
    minute_context: dict[str, Any] = {}

    if "Goles" in enabled_groups:
        rows.extend([
            market_row("Goles", "Total de goles - Más de 1.5",
                       avg(hm.get("over15", 0), am.get("over15", 0)), sample, league_name, brain,
                       f"Local en casa: {hm.get('over15',0)}% · Visitante fuera: {am.get('over15',0)}%"),
            market_row("Goles", "Total de goles - Más de 2.5",
                       avg(hm.get("over25", 0), am.get("over25", 0)), sample, league_name, brain,
                       f"Local en casa: {hm.get('over25',0)}% · Visitante fuera: {am.get('over25',0)}%"),
            market_row("Goles", "Total de goles - Menos de 3.5",
                       avg(hm.get("under35", 0), am.get("under35", 0)), sample, league_name, brain,
                       f"Local en casa: {hm.get('under35',0)}% · Visitante fuera: {am.get('under35',0)}%"),
            market_row("Goles", "Total de goles - Menos de 4.5",
                       avg(hm.get("under45", 0), am.get("under45", 0)), sample, league_name, brain,
                       f"Local en casa: {hm.get('under45',0)}% · Visitante fuera: {am.get('under45',0)}%"),
            market_row("Goles", "Goles del local - Más de 0.5",
                       avg(hm.get("score", 0), am.get("concede", 0)), sample, league_name, brain,
                       f"Local marca: {hm.get('score',0)}% · Visitante concede: {am.get('concede',0)}%"),
            market_row("Goles", "Goles del visitante - Más de 0.5",
                       avg(am.get("score", 0), hm.get("concede", 0)), sample, league_name, brain,
                       f"Visitante marca: {am.get('score',0)}% · Local concede: {hm.get('concede',0)}%"),
        ])

    if "BTTS" in enabled_groups:
        rows.extend([
            market_row("BTTS", "Ambos equipos marcan - Sí",
                       avg(hm.get("btts", 0), am.get("btts", 0)), sample, league_name, brain,
                       f"BTTS local casa: {hm.get('btts',0)}% · visitante fuera: {am.get('btts',0)}%"),
            market_row("BTTS", "Ambos equipos marcan - No",
                       avg(100 - hm.get("btts", 0), 100 - am.get("btts", 0)), sample, league_name, brain,
                       f"BTTS No local casa: {100-hm.get('btts',0)}% · visitante fuera: {100-am.get('btts',0)}%"),
        ])

    if "Doble oportunidad" in enabled_groups:
        rows.extend([
            market_row("Doble oportunidad", "Doble oportunidad - 1X",
                       round((100 - hm.get("loss", 0) + am.get("loss", 0)) / 2, 1),
                       sample, league_name, brain,
                       f"Local evita perder: {100-hm.get('loss',0)}% · Visitante pierde: {am.get('loss',0)}%"),
            market_row("Doble oportunidad", "Doble oportunidad - X2",
                       round((100 - am.get("loss", 0) + hm.get("loss", 0)) / 2, 1),
                       sample, league_name, brain,
                       f"Visitante evita perder: {100-am.get('loss',0)}% · Local pierde: {hm.get('loss',0)}%"),
        ])

    if "Primer tiempo" in enabled_groups:
        rows.extend([
            market_row("Primer tiempo", "1ª parte - Más de 0.5 goles",
                       avg(hm.get("first_half_over05", 0), am.get("first_half_over05", 0)),
                       sample, league_name, brain,
                       f"Local casa: {hm.get('first_half_over05',0)}% · Visitante fuera: {am.get('first_half_over05',0)}%"),
            market_row("Primer tiempo", "1ª parte - Menos de 2.5 goles",
                       avg(hm.get("first_half_under25", 0), am.get("first_half_under25", 0)),
                       sample, league_name, brain,
                       f"Local casa: {hm.get('first_half_under25',0)}% · Visitante fuera: {am.get('first_half_under25',0)}%"),
        ])

    if "Minutos" in enabled_groups or "Primer gol" in enabled_groups:
        hmin = minute_metrics(home_base, int(home_id), EVENT_SAMPLE)
        amin = minute_metrics(away_base, int(away_id), EVENT_SAMPLE)
        event_sample = min(int(hmin.get("event_sample", 0)), int(amin.get("event_sample", 0)))

        if event_sample >= 5:
            no10 = avg(hmin["no_goal_10"], amin["no_goal_10"])
            before70 = avg(hmin["goal_before_70"], amin["goal_before_70"])
            minute_strength = before70
            minute_context = {
                "local_no10": hmin["no_goal_10"],
                "away_no10": amin["no_goal_10"],
                "local_before70": hmin["goal_before_70"],
                "away_before70": amin["goal_before_70"],
                "local_avg_first": hmin["avg_first_goal_minute"],
                "away_avg_first": amin["avg_first_goal_minute"],
                "event_sample": event_sample,
            }

            if "Minutos" in enabled_groups:
                rows.extend([
                    market_row("Minutos", "Ningún gol antes del minuto 10",
                               no10, event_sample, league_name, brain,
                               f"Local casa: {hmin['no_goal_10']}% · Visitante fuera: {amin['no_goal_10']}%"),
                    market_row("Minutos", "Gol antes del minuto 70",
                               before70, event_sample, league_name, brain,
                               f"Local casa: {hmin['goal_before_70']}% · Visitante fuera: {amin['goal_before_70']}%"),
                    market_row("Minutos", "Sin gol 0-10 + gol antes del 70",
                               round(no10 * before70 / 100, 1), event_sample, league_name, brain,
                               f"Sin gol 0-10 combinado: {no10}% · Gol antes del 70 combinado: {before70}%"),
                ])

            if "Primer gol" in enabled_groups:
                rows.extend([
                    market_row("Primer gol", "Local marca primero",
                               avg(hmin["team_scores_first"], amin["opponent_scores_first"]),
                               event_sample, league_name, brain,
                               f"Local marca primero: {hmin['team_scores_first']}% · Visitante recibe primero: {amin['opponent_scores_first']}%"),
                    market_row("Primer gol", "Visitante marca primero",
                               avg(amin["team_scores_first"], hmin["opponent_scores_first"]),
                               event_sample, league_name, brain,
                               f"Visitante marca primero: {amin['team_scores_first']}% · Local recibe primero: {hmin['opponent_scores_first']}%"),
                ])

    table = pd.DataFrame(rows)
    radar = radar_components(hm, am, minute_strength)

    context = {
        "home_name": home.get("name") or "Local",
        "away_name": away.get("name") or "Visitante",
        "home_metrics": hm,
        "away_metrics": am,
        "minute_context": minute_context,
    }

    if table.empty:
        return None, table, radar, context

    table = table.sort_values(["JOYA Score", "Muestra"], ascending=[False, False])
    valid = table[table["Tier"] != "NO BET"]

    if valid.empty:
        return None, table, radar, context

    top = valid.head(3).reset_index(drop=True)
    best = top.iloc[0]

    summary = {
        "fixture_id": fixture.get("id"),
        "País": league.get("country") or "Sin país",
        "Liga": league_name,
        "Local": home.get("name") or "Local",
        "Visitante": away.get("name") or "Visitante",
        "Grupo": best["Grupo"],
        "Pick": best["Mercado"],
        "JOYA Score": float(best["JOYA Score"]),
        "Tier": str(best["Tier"]),
        "Muestra": int(best["Muestra"]),
        "Explicación": best["Explicación"],
        "JOYA Brain": best["JOYA Brain"],
        "Alternativa 2": top.iloc[1]["Mercado"] if len(top) > 1 else "—",
        "Score 2": float(top.iloc[1]["JOYA Score"]) if len(top) > 1 else 0.0,
        "Alternativa 3": top.iloc[2]["Mercado"] if len(top) > 2 else "—",
        "Score 3": float(top.iloc[2]["JOYA Score"]) if len(top) > 2 else 0.0,
    }

    return summary, table, radar, context


def prepare_fixtures(fixtures: list[dict[str, Any]], exclude_youth: bool, exclude_friendlies: bool) -> list[dict[str, Any]]:
    result = []

    for item in fixtures:
        league_name = ((item.get("league", {}) or {}).get("name") or "").lower()

        if exclude_youth and contains_keyword(league_name, EXCLUDED):
            continue

        if exclude_friendlies and contains_keyword(league_name, FRIENDLY):
            continue

        result.append(item)

    return sorted(
        result,
        key=lambda item: (
            ((item.get("league", {}) or {}).get("country") or ""),
            ((item.get("league", {}) or {}).get("name") or ""),
            ((item.get("fixture", {}) or {}).get("date") or ""),
        ),
    )


def fixture_catalog(fixtures: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []

    for item in fixtures:
        fixture = item.get("fixture", {}) or {}
        league = item.get("league", {}) or {}
        teams = item.get("teams", {}) or {}

        dt = pd.to_datetime(fixture.get("date"), errors="coerce", utc=True)
        hour = "—"

        if not pd.isna(dt):
            try:
                hour = dt.tz_convert(TZ).strftime("%H:%M")
            except Exception:
                hour = dt.strftime("%H:%M")

        rows.append({
            "fixture_id": fixture.get("id"),
            "País": league.get("country") or "Sin país",
            "Liga": league.get("name") or "Sin liga",
            "Local": (teams.get("home", {}) or {}).get("name") or "Local",
            "Visitante": (teams.get("away", {}) or {}).get("name") or "Visitante",
            "Hora": hour,
        })

    return pd.DataFrame(rows)


def scan_all_by_league(
    fixtures: list[dict[str, Any]],
    max_matches_per_league: int,
    enabled_groups: set[str],
    brain: pd.DataFrame,
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
            summary, _, _, _ = analyze_fixture(item, enabled_groups, brain)
            if summary:
                results.append(summary)
        except Exception:
            pass

        if progress_callback:
            progress_callback(index, total, league_name)

    if not results:
        return pd.DataFrame()

    return pd.DataFrame(results).sort_values(
        ["JOYA Score", "Muestra"],
        ascending=[False, False],
    )


def build_smart_cart(
    ranking: pd.DataFrame,
    target_odds: float,
    max_picks: int,
    minimum_tier: str,
    assumed_odds: float,
    selected_leagues: list[str],
    max_one_per_league: bool,
    max_one_per_country: bool,
    max_same_market: int,
    max_same_group: int,
) -> tuple[pd.DataFrame, float, list[str]]:
    if ranking.empty:
        return pd.DataFrame(), 1.0, ["No existe ranking."]

    valid = ranking[
        ranking["Tier"].map(TIER_ORDER).fillna(0) >= TIER_ORDER[minimum_tier]
    ].copy()

    if selected_leagues:
        valid = valid[valid["Liga"].isin(selected_leagues)]

    valid = valid.sort_values(["JOYA Score", "Muestra"], ascending=[False, False])

    picks = []
    used_fixtures = set()
    used_leagues = set()
    used_countries = set()
    market_counts: dict[str, int] = defaultdict(int)
    group_counts: dict[str, int] = defaultdict(int)
    reasons = []
    combined = 1.0

    for _, row in valid.iterrows():
        if row["fixture_id"] in used_fixtures:
            continue
        if max_one_per_league and row["Liga"] in used_leagues:
            continue
        if max_one_per_country and row["País"] in used_countries:
            continue
        if market_counts[row["Pick"]] >= max_same_market:
            continue
        if group_counts[row["Grupo"]] >= max_same_group:
            continue

        picks.append(row)
        used_fixtures.add(row["fixture_id"])
        used_leagues.add(row["Liga"])
        used_countries.add(row["País"])
        market_counts[row["Pick"]] += 1
        group_counts[row["Grupo"]] += 1
        combined *= assumed_odds
        reasons.append(
            f"{row['Local']} vs {row['Visitante']}: {row['Pick']} · "
            f"{row['Tier']} · Score {row['JOYA Score']}"
        )

        if combined >= target_odds or len(picks) >= max_picks:
            break

    if not picks:
        return pd.DataFrame(), 1.0, ["No se encontraron selecciones compatibles con los filtros."]

    return pd.DataFrame(picks), round(combined, 2), reasons


def export_brain_template() -> bytes:
    template = pd.DataFrame(
        columns=["Liga", "Mercado", "Picks", "Aciertos"]
    )
    return template.to_csv(index=False).encode("utf-8")


def render_bar(label: str, value: float) -> None:
    st.write(f"**{label}** · {value:.1f}")
    st.progress(min(100, max(0, int(value))))


st.title("💎 JOYA 22 AI")
st.caption("Score calibrado · Explicaciones · Radar · JOYA Brain · Constructor inteligente")

if not api_key():
    st.error("Falta APISPORTS_KEY en Streamlit Secrets.")
    st.stop()

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
    options=[1, 2, 3, 4, 5],
    value=2,
)

enabled_groups_list = st.sidebar.multiselect(
    "Mercados a analizar",
    options=[
        "Goles",
        "BTTS",
        "Doble oportunidad",
        "Primer tiempo",
        "Minutos",
        "Primer gol",
    ],
    default=[
        "Goles",
        "BTTS",
        "Doble oportunidad",
        "Primer tiempo",
    ],
)

enabled_groups = set(enabled_groups_list)

st.sidebar.subheader("JOYA Brain")
brain_file = st.sidebar.file_uploader(
    "Subir historial CSV",
    type=["csv"],
    help="Columnas requeridas: Liga, Mercado, Picks, Aciertos",
)
brain = load_brain(brain_file)

st.sidebar.download_button(
    "Descargar plantilla Brain",
    data=export_brain_template(),
    file_name="joya_brain_template.csv",
    mime="text/csv",
)

fixtures = api_list(
    "fixtures",
    {"date": selected_date.isoformat(), "timezone": TZ},
)

prepared = prepare_fixtures(
    fixtures,
    exclude_youth=exclude_youth,
    exclude_friendlies=exclude_friendlies,
)

catalog = fixture_catalog(prepared)

if "ranking_joya22" not in st.session_state:
    st.session_state.ranking_joya22 = pd.DataFrame()

if "single_joya22" not in st.session_state:
    st.session_state.single_joya22 = None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Partidos", len(catalog))
c2.metric("Ligas", catalog["Liga"].nunique() if not catalog.empty else 0)
c3.metric("Mercados activos", len(enabled_groups))
c4.metric("Brain cargado", "Sí" if not brain.empty else "No")

st.subheader("🧠 Scanner JOYA 22")

process_box = st.empty()

if st.button("🔥 ANALIZAR TODO", type="primary", use_container_width=True):
    if not enabled_groups:
        st.error("Selecciona al menos un grupo de mercados.")
    else:
        progress = st.progress(0)
        status_text = st.empty()

        process_box.info(
            f"{len(catalog)} partidos detectados → filtros aplicados → "
            f"{catalog['Liga'].nunique() if not catalog.empty else 0} ligas disponibles"
        )

        def update(current: int, total: int, league_name: str) -> None:
            progress.progress(current / total if total else 1)
            status_text.caption(
                f"Analizando {current} de {total} · {league_name}"
            )

        with st.spinner("Calculando forma, localía, minutos, Brain y mercados…"):
            st.session_state.ranking_joya22 = scan_all_by_league(
                fixtures=prepared,
                max_matches_per_league=int(max_per_league),
                enabled_groups=enabled_groups,
                brain=brain,
                progress_callback=update,
            )

        progress.empty()
        status_text.empty()

ranking = st.session_state.ranking_joya22

if not ranking.empty:
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Analizados con datos", len(ranking))
    s2.metric("S++", int((ranking["Tier"] == "S++").sum()))
    s3.metric("S+", int((ranking["Tier"] == "S+").sum()))
    s4.metric("NO BET descartados", max(0, len(catalog) - len(ranking)))

    st.subheader("🏆 Ranking calibrado")

    st.dataframe(
        ranking[
            [
                "País",
                "Liga",
                "Local",
                "Visitante",
                "Grupo",
                "Pick",
                "JOYA Score",
                "Tier",
                "Explicación",
                "JOYA Brain",
                "Alternativa 2",
                "Score 2",
                "Alternativa 3",
                "Score 3",
                "Muestra",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("📚 Resultados por liga")
    for (country, league), group in ranking.groupby(["País", "Liga"], sort=True):
        with st.expander(
            f"{country} · {league} · {len(group)} candidatos · "
            f"mejor {group['JOYA Score'].max():.1f}"
        ):
            st.dataframe(
                group[
                    [
                        "Local",
                        "Visitante",
                        "Pick",
                        "JOYA Score",
                        "Tier",
                        "Explicación",
                        "Alternativa 2",
                        "Score 2",
                        "Alternativa 3",
                        "Score 3",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
else:
    st.info("Pulsa ANALIZAR TODO para generar el ranking.")

st.divider()
st.subheader("🔎 Análisis profundo de un partido")

labels = {}

for index, item in enumerate(prepared):
    league = item.get("league", {}) or {}
    teams = item.get("teams", {}) or {}
    home = (teams.get("home", {}) or {}).get("name", "Local")
    away = (teams.get("away", {}) or {}).get("name", "Visitante")

    labels[
        f"{league.get('country','')} · {league.get('name','')} · {home} vs {away}"
    ] = index

if labels:
    selected_label = st.selectbox("Selecciona partido", list(labels.keys()))
    selected_item = prepared[labels[selected_label]]

    if st.button("📊 ANALIZAR PARTIDO", use_container_width=True):
        with st.spinner("Construyendo diagnóstico completo…"):
            st.session_state.single_joya22 = analyze_fixture(
                selected_item,
                enabled_groups,
                brain,
            )

    if st.session_state.single_joya22:
        summary, markets, radar, context = st.session_state.single_joya22

        if summary:
            a, b, c = st.columns(3)
            a.metric("Mejor mercado", summary["Pick"])
            b.metric("JOYA Score", summary["JOYA Score"])
            c.metric("Tier", summary["Tier"])

            st.success(summary["Explicación"])
            st.caption(summary["JOYA Brain"])
        else:
            st.warning("NO BET: ningún mercado superó los filtros.")

        left, right = st.columns(2)

        with left:
            st.subheader("📡 Radar JOYA")
            for name, value in radar.items():
                render_bar(name, value)

        with right:
            st.subheader("📈 Tendencias local/visitante")
            hm = context.get("home_metrics", {})
            am = context.get("away_metrics", {})
            st.write(f"**{context.get('home_name')} en casa**")
            st.write(
                f"Muestra {hm.get('sample',0)} · Marca {hm.get('score',0)}% · "
                f"Concede {hm.get('concede',0)}% · Gana {hm.get('win',0)}%"
            )
            st.write(f"**{context.get('away_name')} fuera**")
            st.write(
                f"Muestra {am.get('sample',0)} · Marca {am.get('score',0)}% · "
                f"Concede {am.get('concede',0)}% · Pierde {am.get('loss',0)}%"
            )

            minute_context = context.get("minute_context", {})
            if minute_context:
                st.write("**Minutos**")
                st.write(
                    f"Sin gol antes del 10: local {minute_context.get('local_no10',0)}% · "
                    f"visitante {minute_context.get('away_no10',0)}%"
                )
                st.write(
                    f"Gol antes del 70: local {minute_context.get('local_before70',0)}% · "
                    f"visitante {minute_context.get('away_before70',0)}%"
                )
                st.write(
                    f"Minuto medio primer gol: local {minute_context.get('local_avg_first',0)}' · "
                    f"visitante {minute_context.get('away_avg_first',0)}'"
                )

        st.subheader("Todos los mercados analizados")
        st.dataframe(markets, use_container_width=True, hide_index=True)

st.divider()
st.subheader("🚀 Constructor inteligente de cartillas")

available_leagues = (
    sorted(ranking["Liga"].unique().tolist())
    if not ranking.empty
    else []
)

selected_leagues = st.multiselect(
    "Ligas disponibles en Betano",
    options=available_leagues,
    placeholder="Vacío = todas",
)

a, b, c, d = st.columns(4)
target_odds = a.selectbox("Cuota objetivo", [2.0, 3.0, 4.0, 5.0], index=1)
max_picks = b.selectbox("Máximo de picks", [2, 3, 4, 5, 6], index=3)
minimum_tier = c.selectbox("Tier mínimo", ["S++", "S+", "A++", "A+"], index=1)
assumed_odds = d.number_input(
    "Cuota media estimada",
    min_value=1.05,
    max_value=2.00,
    value=1.30,
    step=0.05,
)

f1, f2, f3, f4 = st.columns(4)
max_one_per_league = f1.checkbox("Máximo 1 por liga", value=True)
max_one_per_country = f2.checkbox("Máximo 1 por país", value=False)
max_same_market = f3.selectbox("Máximo mismo mercado", [1, 2, 3], index=1)
max_same_group = f4.selectbox("Máximo mismo grupo", [1, 2, 3], index=1)

if st.button("📋 CREAR CARTILLA INTELIGENTE", use_container_width=True):
    cart, combined, reasons = build_smart_cart(
        ranking=ranking,
        target_odds=float(target_odds),
        max_picks=int(max_picks),
        minimum_tier=str(minimum_tier),
        assumed_odds=float(assumed_odds),
        selected_leagues=selected_leagues,
        max_one_per_league=max_one_per_league,
        max_one_per_country=max_one_per_country,
        max_same_market=int(max_same_market),
        max_same_group=int(max_same_group),
    )

    if cart.empty:
        st.warning(reasons[0])
    else:
        if combined < target_odds:
            st.warning(
                f"Cuota estimada {combined:.2f}. JOYA no forzó picks."
            )
        else:
            st.success(
                f"Cartilla creada · cuota estimada {combined:.2f}"
            )

        st.dataframe(
            cart[
                [
                    "País",
                    "Liga",
                    "Local",
                    "Visitante",
                    "Grupo",
                    "Pick",
                    "JOYA Score",
                    "Tier",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("Por qué eligió estos picks"):
            for reason in reasons:
                st.write("•", reason)

st.caption(
    "JOYA Brain en esta versión se alimenta mediante CSV. Streamlit Community Cloud "
    "no garantiza almacenamiento permanente local, por eso el historial debe subirse "
    "o conectarse a una base de datos en una etapa posterior."
)
