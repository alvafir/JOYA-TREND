from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Callable

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="JOYA 21 AI", page_icon="💎", layout="wide")

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
    "Total de goles - Menos de 4.5": 8.0,
    "Total de goles - Menos de 3.5": 4.0,
    "Total de goles - Más de 1.5": 2.0,
    "Total de goles - Más de 2.5": 1.0,
    "Doble oportunidad - 1X": 4.0,
    "Doble oportunidad - X2": 4.0,
    "Doble oportunidad - 12": 5.0,
    "Goles del local - Más de 0.5": 1.0,
    "Goles del visitante - Más de 0.5": 1.0,
    "Goles del local - Más de 1.5": 1.0,
    "Goles del visitante - Más de 1.5": 1.0,
    "Goles del local - Menos de 2.5": 3.0,
    "Goles del visitante - Menos de 2.5": 3.0,
    "Ningún gol antes del minuto 10": 2.0,
    "Gol antes del minuto 70": 2.0,
    "Local marca primero": 2.0,
    "Visitante marca primero": 2.0,
}


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


def venue_fixtures(
    fixtures: list[dict[str, Any]],
    team_id: int,
    home: bool,
    limit: int,
) -> list[dict[str, Any]]:
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


def minute_metrics(
    fixtures: list[dict[str, Any]],
    team_id: int,
    max_games: int,
) -> dict[str, float]:
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
        team_goal_70 += int(
            any(minute <= 70 and event_team == team_id for minute, event_team in goals)
        )
        opponent_goal_70 += int(
            any(minute <= 70 and event_team != team_id for minute, event_team in goals)
        )

        if first:
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
    }


def avg(a: float, b: float) -> float:
    return round((a + b) / 2, 1)


def assign_tier(score: float, sample: int) -> str:
    if sample < 5:
        return "NO BET"
    if score >= 88:
        return "S++"
    if score >= 82:
        return "S+"
    if score >= 76:
        return "A++"
    return "NO BET"


def market_row(
    group: str,
    market: str,
    raw_score: float,
    sample: int,
) -> dict[str, Any]:
    adjusted = max(
        0.0,
        min(100.0, round(raw_score - MARKET_PENALTIES.get(market, 0.0), 1)),
    )

    return {
        "Grupo": group,
        "Mercado": market,
        "Score bruto": round(raw_score, 1),
        "JOYA Score": adjusted,
        "Tier": assign_tier(adjusted, sample),
        "Muestra": sample,
    }


def analyze_fixture(
    item: dict[str, Any],
    enabled_groups: set[str],
) -> tuple[dict[str, Any] | None, pd.DataFrame]:
    fixture = item.get("fixture", {}) or {}
    league = item.get("league", {}) or {}
    teams = item.get("teams", {}) or {}
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}

    home_id, away_id = home.get("id"), away.get("id")
    if not home_id or not away_id:
        return None, pd.DataFrame()

    home_all = get_team_fixtures(int(home_id))
    away_all = get_team_fixtures(int(away_id))

    home_base = venue_fixtures(
        home_all,
        int(home_id),
        home=True,
        limit=RECENT_VENUE,
    ) or home_all[:RECENT_GENERAL]

    away_base = venue_fixtures(
        away_all,
        int(away_id),
        home=False,
        limit=RECENT_VENUE,
    ) or away_all[:RECENT_GENERAL]

    hm = basic_metrics(home_base, int(home_id))
    am = basic_metrics(away_base, int(away_id))
    sample = min(int(hm.get("sample", 0)), int(am.get("sample", 0)))

    rows: list[dict[str, Any]] = []

    if "Goles" in enabled_groups:
        rows.extend([
            market_row("Goles", "Total de goles - Más de 1.5",
                       avg(hm.get("over15", 0), am.get("over15", 0)), sample),
            market_row("Goles", "Total de goles - Más de 2.5",
                       avg(hm.get("over25", 0), am.get("over25", 0)), sample),
            market_row("Goles", "Total de goles - Menos de 3.5",
                       avg(hm.get("under35", 0), am.get("under35", 0)), sample),
            market_row("Goles", "Total de goles - Menos de 4.5",
                       avg(hm.get("under45", 0), am.get("under45", 0)), sample),
            market_row("Goles", "Goles del local - Más de 0.5",
                       avg(hm.get("score", 0), am.get("concede", 0)), sample),
            market_row("Goles", "Goles del visitante - Más de 0.5",
                       avg(am.get("score", 0), hm.get("concede", 0)), sample),
            market_row("Goles", "Goles del local - Más de 1.5",
                       avg(hm.get("team_over15", 0), am.get("concede", 0)), sample),
            market_row("Goles", "Goles del visitante - Más de 1.5",
                       avg(am.get("team_over15", 0), hm.get("concede", 0)), sample),
            market_row("Goles", "Goles del local - Menos de 2.5",
                       avg(hm.get("team_under25", 0), 100 - am.get("concede", 0) / 2), sample),
            market_row("Goles", "Goles del visitante - Menos de 2.5",
                       avg(am.get("team_under25", 0), 100 - hm.get("concede", 0) / 2), sample),
        ])

    if "BTTS" in enabled_groups:
        rows.extend([
            market_row("BTTS", "Ambos equipos marcan - Sí",
                       avg(hm.get("btts", 0), am.get("btts", 0)), sample),
            market_row("BTTS", "Ambos equipos marcan - No",
                       avg(100 - hm.get("btts", 0), 100 - am.get("btts", 0)), sample),
        ])

    if "Doble oportunidad" in enabled_groups:
        rows.extend([
            market_row(
                "Doble oportunidad",
                "Doble oportunidad - 1X",
                round((100 - hm.get("loss", 0) + am.get("loss", 0)) / 2, 1),
                sample,
            ),
            market_row(
                "Doble oportunidad",
                "Doble oportunidad - X2",
                round((100 - am.get("loss", 0) + hm.get("loss", 0)) / 2, 1),
                sample,
            ),
            market_row(
                "Doble oportunidad",
                "Doble oportunidad - 12",
                avg(100 - hm.get("draw", 0), 100 - am.get("draw", 0)),
                sample,
            ),
        ])

    if "Primer tiempo" in enabled_groups:
        rows.extend([
            market_row(
                "Primer tiempo",
                "1ª parte - Más de 0.5 goles",
                avg(hm.get("first_half_over05", 0), am.get("first_half_over05", 0)),
                sample,
            ),
            market_row(
                "Primer tiempo",
                "1ª parte - Menos de 2.5 goles",
                avg(hm.get("first_half_under25", 0), am.get("first_half_under25", 0)),
                sample,
            ),
        ])

    if "Minutos" in enabled_groups or "Primer gol" in enabled_groups:
        hmin = minute_metrics(home_base, int(home_id), EVENT_SAMPLE)
        amin = minute_metrics(away_base, int(away_id), EVENT_SAMPLE)

        event_sample = min(
            int(hmin.get("event_sample", 0)),
            int(amin.get("event_sample", 0)),
        )

        if event_sample >= 5:
            no10 = avg(hmin["no_goal_10"], amin["no_goal_10"])
            before70 = avg(hmin["goal_before_70"], amin["goal_before_70"])

            if "Minutos" in enabled_groups:
                rows.extend([
                    market_row("Minutos", "Ningún gol antes del minuto 10",
                               no10, event_sample),
                    market_row("Minutos", "Gol antes del minuto 70",
                               before70, event_sample),
                    market_row(
                        "Minutos",
                        "Sin gol 0-10 + gol antes del 70",
                        round(no10 * before70 / 100, 1),
                        event_sample,
                    ),
                    market_row(
                        "Minutos",
                        "Más de 0.5 goles en 1ª parte",
                        avg(hmin["goal_first_half"], amin["goal_first_half"]),
                        event_sample,
                    ),
                    market_row(
                        "Minutos",
                        "Local marca antes del 70",
                        avg(hmin["team_goal_before_70"], amin["opponent_goal_before_70"]),
                        event_sample,
                    ),
                    market_row(
                        "Minutos",
                        "Visitante marca antes del 70",
                        avg(amin["team_goal_before_70"], hmin["opponent_goal_before_70"]),
                        event_sample,
                    ),
                ])

            if "Primer gol" in enabled_groups:
                rows.extend([
                    market_row(
                        "Primer gol",
                        "Local marca primero",
                        avg(hmin["team_scores_first"], amin["opponent_scores_first"]),
                        event_sample,
                    ),
                    market_row(
                        "Primer gol",
                        "Visitante marca primero",
                        avg(amin["team_scores_first"], hmin["opponent_scores_first"]),
                        event_sample,
                    ),
                ])

    table = pd.DataFrame(rows)

    if table.empty:
        return None, table

    table = table.sort_values(
        ["JOYA Score", "Muestra"],
        ascending=[False, False],
    )

    valid = table[table["Tier"] != "NO BET"]

    if valid.empty:
        return None, table

    top = valid.head(3).reset_index(drop=True)
    best = top.iloc[0]

    summary = {
        "fixture_id": fixture.get("id"),
        "País": league.get("country") or "Sin país",
        "Liga": league.get("name") or "Sin liga",
        "Local": home.get("name") or "Local",
        "Visitante": away.get("name") or "Visitante",
        "Grupo": best["Grupo"],
        "Pick": best["Mercado"],
        "JOYA Score": float(best["JOYA Score"]),
        "Tier": str(best["Tier"]),
        "Muestra": int(best["Muestra"]),
        "Alternativa 2": top.iloc[1]["Mercado"] if len(top) > 1 else "—",
        "Score 2": float(top.iloc[1]["JOYA Score"]) if len(top) > 1 else 0.0,
        "Alternativa 3": top.iloc[2]["Mercado"] if len(top) > 2 else "—",
        "Score 3": float(top.iloc[2]["JOYA Score"]) if len(top) > 2 else 0.0,
    }

    return summary, table


def prepare_fixtures(
    fixtures: list[dict[str, Any]],
    exclude_youth: bool,
    exclude_friendlies: bool,
) -> list[dict[str, Any]]:
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
            summary, _ = analyze_fixture(item, enabled_groups)
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


def build_cart(
    ranking: pd.DataFrame,
    target_odds: float,
    max_picks: int,
    minimum_tier: str,
    assumed_odds: float,
    selected_leagues: list[str],
    max_one_per_league: bool,
    max_same_market: int,
) -> tuple[pd.DataFrame, float]:
    if ranking.empty:
        return pd.DataFrame(), 1.0

    tier_order = {"S++": 3, "S+": 2, "A++": 1, "NO BET": 0}

    valid = ranking[
        ranking["Tier"].map(tier_order).fillna(0) >= tier_order[minimum_tier]
    ].copy()

    if selected_leagues:
        valid = valid[valid["Liga"].isin(selected_leagues)]

    valid = valid.sort_values(
        ["JOYA Score", "Muestra"],
        ascending=[False, False],
    )

    picks = []
    used_fixtures = set()
    used_leagues = set()
    market_counts: dict[str, int] = defaultdict(int)
    combined = 1.0

    for _, row in valid.iterrows():
        if row["fixture_id"] in used_fixtures:
            continue

        if max_one_per_league and row["Liga"] in used_leagues:
            continue

        if market_counts[row["Pick"]] >= max_same_market:
            continue

        picks.append(row)
        used_fixtures.add(row["fixture_id"])
        used_leagues.add(row["Liga"])
        market_counts[row["Pick"]] += 1
        combined *= assumed_odds

        if combined >= target_odds or len(picks) >= max_picks:
            break

    if not picks:
        return pd.DataFrame(), 1.0

    return pd.DataFrame(picks), round(combined, 2)


def next_goal_live(item: dict[str, Any]) -> dict[str, Any]:
    fixture = item.get("fixture", {}) or {}
    fixture_id = int(fixture["id"])
    teams = item.get("teams", {}) or {}
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}
    home_id, away_id = home.get("id"), away.get("id")

    stats = api_list("fixtures/statistics", {"fixture": fixture_id})
    events = api_list("fixtures/events", {"fixture": fixture_id})

    home_pressure = 0.0
    away_pressure = 0.0

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

    red_home = 0
    red_away = 0

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
        return {
            "pick": "NO DATA",
            "home": 0.0,
            "away": 0.0,
            "tier": "NO BET",
        }

    home_pct = round(100 * home_pressure / total, 1)
    away_pct = round(100 - home_pct, 1)
    difference = abs(home_pct - away_pct)

    if difference < 10:
        pick = "Sin ventaja clara"
        tier_value = "NO BET"
    elif home_pct > away_pct:
        pick = f"Próximo gol: {home.get('name', 'Local')}"
        tier_value = "S+" if difference >= 25 else "A++"
    else:
        pick = f"Próximo gol: {away.get('name', 'Visitante')}"
        tier_value = "S+" if difference >= 25 else "A++"

    return {
        "pick": pick,
        "home": home_pct,
        "away": away_pct,
        "tier": tier_value,
    }


st.title("💎 JOYA 21 AI")
st.caption("Dashboard único · Scanner · Mercados · Cartillas · Próximo gol")

if not api_key():
    st.error("Falta APISPORTS_KEY en Streamlit Secrets.")
    st.stop()

try:
    status_payload = api_get("status", {}).get("response", {})
    requests_data = (
        status_payload.get("requests", {})
        if isinstance(status_payload, dict)
        else {}
    )
    st.sidebar.success("API-Football conectada")
    st.sidebar.caption(
        f"Solicitudes hoy: {requests_data.get('current', '—')} / "
        f"{requests_data.get('limit_day', '—')}"
    )
except Exception as exc:
    st.sidebar.error(f"Error de conexión: {exc}")
    st.stop()

selected_date = st.sidebar.date_input(
    "Fecha",
    value=date.today(),
    min_value=date.today() - timedelta(days=7),
    max_value=date.today() + timedelta(days=30),
)

exclude_youth = st.sidebar.checkbox(
    "Excluir juveniles y reservas",
    value=True,
)

exclude_friendlies = st.sidebar.checkbox(
    "Excluir amistosos",
    value=False,
)

max_per_league = st.sidebar.select_slider(
    "Máximo de partidos por liga",
    options=[1, 2, 3, 4, 5],
    value=2,
)

st.sidebar.subheader("Mercados a analizar")

enabled_groups_list = st.sidebar.multiselect(
    "Selecciona categorías",
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

fixtures = api_list(
    "fixtures",
    {
        "date": selected_date.isoformat(),
        "timezone": TZ,
    },
)

prepared = prepare_fixtures(
    fixtures,
    exclude_youth=exclude_youth,
    exclude_friendlies=exclude_friendlies,
)

catalog = fixture_catalog(prepared)

if "ranking_joya21" not in st.session_state:
    st.session_state.ranking_joya21 = pd.DataFrame()

if "single_markets_joya21" not in st.session_state:
    st.session_state.single_markets_joya21 = pd.DataFrame()

if "single_summary_joya21" not in st.session_state:
    st.session_state.single_summary_joya21 = None

c1, c2, c3 = st.columns(3)

c1.metric("Partidos disponibles", len(catalog))
c2.metric(
    "Ligas disponibles",
    catalog["Liga"].nunique() if not catalog.empty else 0,
)
c3.metric("Categorías activas", len(enabled_groups))

st.subheader("🌍 Ligas disponibles")

selected_countries = st.multiselect(
    "Filtrar países",
    options=sorted(catalog["País"].unique().tolist()) if not catalog.empty else [],
    placeholder="Vacío = todos",
)

visible_catalog = catalog.copy()

if selected_countries:
    visible_catalog = visible_catalog[
        visible_catalog["País"].isin(selected_countries)
    ]

for (country, league), group in visible_catalog.groupby(
    ["País", "Liga"],
    sort=True,
):
    with st.expander(
        f"{country} · {league} · {len(group)} partidos"
    ):
        st.dataframe(
            group[["Hora", "Local", "Visitante"]],
            use_container_width=True,
            hide_index=True,
        )

st.divider()

st.subheader("🔥 Analizar todo")

if st.button(
    "🧠 EJECUTAR JOYA AI",
    type="primary",
    use_container_width=True,
):
    if not enabled_groups:
        st.error("Selecciona al menos una categoría de mercados.")
    else:
        progress = st.progress(0)
        progress_text = st.empty()

        fixtures_to_scan = prepared

        if selected_countries:
            allowed_ids = set(visible_catalog["fixture_id"].tolist())
            fixtures_to_scan = [
                item
                for item in prepared
                if (item.get("fixture", {}) or {}).get("id") in allowed_ids
            ]

        def update_progress(
            current: int,
            total: int,
            league_name: str,
        ) -> None:
            progress.progress(current / total if total else 1)
            progress_text.caption(
                f"Analizando {current} de {total} · {league_name}"
            )

        with st.spinner("Escaneando partidos y mercados…"):
            st.session_state.ranking_joya21 = scan_all_by_league(
                fixtures=fixtures_to_scan,
                max_matches_per_league=int(max_per_league),
                enabled_groups=enabled_groups,
                progress_callback=update_progress,
            )

        progress.empty()
        progress_text.empty()

ranking = st.session_state.ranking_joya21

if not ranking.empty:
    st.subheader("🏆 Top picks del día")

    top_count = st.slider(
        "Cantidad de picks a mostrar",
        min_value=5,
        max_value=min(50, len(ranking)),
        value=min(20, len(ranking)),
    )

    top_ranking = ranking.head(top_count)

    st.dataframe(
        top_ranking[
            [
                "País",
                "Liga",
                "Local",
                "Visitante",
                "Grupo",
                "Pick",
                "JOYA Score",
                "Tier",
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

    for (country, league), group in ranking.groupby(
        ["País", "Liga"],
        sort=True,
    ):
        with st.expander(
            f"{country} · {league} · {len(group)} candidatos · "
            f"mejor {group['JOYA Score'].max():.1f}"
        ):
            st.dataframe(
                group[
                    [
                        "Local",
                        "Visitante",
                        "Grupo",
                        "Pick",
                        "JOYA Score",
                        "Tier",
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
else:
    st.info("Pulsa EJECUTAR JOYA AI para generar el ranking.")

st.divider()

st.subheader("📊 Analizar un partido")

match_labels = {}

for index, item in enumerate(prepared):
    league = item.get("league", {}) or {}
    teams = item.get("teams", {}) or {}
    home = (teams.get("home", {}) or {}).get("name", "Local")
    away = (teams.get("away", {}) or {}).get("name", "Visitante")

    match_labels[
        f"{league.get('country', '')} · "
        f"{league.get('name', '')} · "
        f"{home} vs {away}"
    ] = index

if match_labels:
    selected_match_label = st.selectbox(
        "Selecciona partido",
        list(match_labels.keys()),
    )

    selected_match = prepared[
        match_labels[selected_match_label]
    ]

    if st.button(
        "🔎 ANALIZAR PARTIDO",
        use_container_width=True,
    ):
        with st.spinner("Analizando todos los mercados seleccionados…"):
            summary, markets = analyze_fixture(
                selected_match,
                enabled_groups,
            )

        st.session_state.single_summary_joya21 = summary
        st.session_state.single_markets_joya21 = markets

    summary = st.session_state.single_summary_joya21
    markets = st.session_state.single_markets_joya21

    if not markets.empty:
        if summary:
            a, b, c = st.columns(3)
            a.metric("Mejor mercado", summary["Pick"])
            b.metric("JOYA Score", summary["JOYA Score"])
            c.metric("Tier", summary["Tier"])

        st.dataframe(
            markets,
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("No hay partidos disponibles para analizar.")

st.divider()

st.subheader("🚀 Crear cartilla")

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

target_odds = a.selectbox(
    "Cuota objetivo",
    [2.0, 3.0, 4.0, 5.0],
    index=1,
)

max_picks = b.selectbox(
    "Máximo de picks",
    [2, 3, 4, 5, 6],
    index=3,
)

minimum_tier = c.selectbox(
    "Tier mínimo",
    ["S++", "S+", "A++"],
    index=1,
)

assumed_odds = d.number_input(
    "Cuota media estimada",
    min_value=1.05,
    max_value=2.00,
    value=1.30,
    step=0.05,
)

max_one_per_league = st.checkbox(
    "Máximo un pick por liga",
    value=True,
)

max_same_market = st.selectbox(
    "Máximo de veces que puede repetirse el mismo mercado",
    [1, 2, 3],
    index=1,
)

if st.button(
    "📋 CREAR CARTILLA",
    use_container_width=True,
):
    cart, combined = build_cart(
        ranking=ranking,
        target_odds=float(target_odds),
        max_picks=int(max_picks),
        minimum_tier=str(minimum_tier),
        assumed_odds=float(assumed_odds),
        selected_leagues=selected_leagues,
        max_one_per_league=max_one_per_league,
        max_same_market=int(max_same_market),
    )

    if cart.empty:
        st.warning("No hay suficientes selecciones para crear la cartilla.")
    else:
        if combined < target_odds:
            st.warning(
                f"Cuota estimada {combined:.2f}. "
                "JOYA no forzó picks para alcanzar el objetivo."
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

st.divider()

st.subheader("🔴 Próximo gol en vivo")

live_matches = []

for item in prepared:
    status = ((item.get("fixture", {}) or {}).get("status", {}) or {}).get("short")

    if status in {"1H", "HT", "2H", "ET", "BT", "P"}:
        live_matches.append(item)

if not live_matches:
    st.info("No hay partidos en vivo con cobertura activa.")
else:
    live_labels = {}

    for index, item in enumerate(live_matches):
        fixture = item.get("fixture", {}) or {}
        league = item.get("league", {}) or {}
        teams = item.get("teams", {}) or {}
        home = (teams.get("home", {}) or {}).get("name", "Local")
        away = (teams.get("away", {}) or {}).get("name", "Visitante")
        elapsed = (fixture.get("status", {}) or {}).get("elapsed")

        live_labels[
            f"{league.get('name', '')} · "
            f"{home} vs {away} · {elapsed or '—'}'"
        ] = index

    selected_live_label = st.selectbox(
        "Selecciona partido en vivo",
        list(live_labels.keys()),
    )

    selected_live = live_matches[
        live_labels[selected_live_label]
    ]

    if st.button(
        "⚡ CALCULAR PRÓXIMO GOL",
        use_container_width=True,
    ):
        with st.spinner("Consultando presión y eventos en vivo…"):
            result = next_goal_live(selected_live)

        teams = selected_live.get("teams", {}) or {}
        home_name = (teams.get("home", {}) or {}).get("name", "Local")
        away_name = (teams.get("away", {}) or {}).get("name", "Visitante")

        st.subheader(result["pick"])

        x, y, z = st.columns(3)
        x.metric(home_name, f"{result['home']}%")
        y.metric(away_name, f"{result['away']}%")
        z.metric("Tier interno", result["tier"])

st.caption(
    "JOYA 21 AI integra scanner, ligas, mercados, minuto, primer gol, "
    "constructor de cartillas y próximo gol dentro de un único flujo."
)
