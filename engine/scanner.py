from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable
import pandas as pd

from api.football import response_list
from config.settings import EXCLUDED_KEYWORDS, VOLATILE_KEYWORDS, RECENT_MATCHES
from engine.markets import evaluate_markets
from engine.metrics import team_metrics


def league_key(item: dict[str, Any]) -> tuple[str, str, int]:
    league = item.get("league", {}) or {}
    return (
        league.get("country") or "Sin país",
        league.get("name") or "Sin liga",
        int(league.get("id") or 0),
    )


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

    # Ordena por país, liga y horario para que ninguna liga quede escondida
    return sorted(
        selected,
        key=lambda x: (
            league_key(x)[0],
            league_key(x)[1],
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
            "league_id": league.get("id"),
            "Local": (teams.get("home", {}) or {}).get("name") or "Local",
            "Visitante": (teams.get("away", {}) or {}).get("name") or "Visitante",
            "Hora API": fixture.get("date") or "—",
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
        "league_id": league.get("id"),
        "País": league.get("country") or "Sin país",
        "Liga": league.get("name") or "Sin liga",
        "Local": home.get("name") or "Local",
        "Visitante": away.get("name") or "Visitante",
        "Pick": best["Mercado Betano"],
        "JOYA Score": float(best["Score"]),
        "Tier": str(best["Tier"]),
        "Muestra": int(best["Muestra"]),
    }


def scan_all_by_league(
    fixtures: list[dict[str, Any]],
    max_matches_per_league: int,
    exclude_youth_reserves: bool,
    exclude_friendlies: bool,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> pd.DataFrame:
    prepared = prepare_fixtures(
        fixtures,
        exclude_youth_reserves=exclude_youth_reserves,
        exclude_friendlies=exclude_friendlies,
    )

    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for item in prepared:
        grouped[league_key(item)].append(item)

    # Escanea todas las ligas, pero limita partidos por liga para repartir la cobertura.
    queue = []
    for key in sorted(grouped):
        queue.extend(grouped[key][:max_matches_per_league])

    results = []
    total = len(queue)

    for index, item in enumerate(queue, start=1):
        league_name = league_key(item)[1]
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
