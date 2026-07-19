from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from api.football import response_list
from config.settings import EXCLUDED_KEYWORDS, RECENT_MATCHES
from engine.markets import evaluate_markets
from engine.metrics import team_metrics


def is_excluded(league_name: str) -> bool:
    value = league_name.lower()
    return any(keyword in value for keyword in EXCLUDED_KEYWORDS)


def scan_fixture(item: dict[str, Any]) -> dict[str, Any] | None:
    fixture = item.get("fixture", {}) or {}
    league = item.get("league", {}) or {}
    teams = item.get("teams", {}) or {}
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}

    home_id = home.get("id")
    away_id = away.get("id")
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
        "Pick": best["Mercado Betano"],
        "JOYA Score": float(best["Score"]),
        "Tier": str(best["Tier"]),
        "Muestra": int(best["Muestra"]),
    }


def scan_day(
    fixtures: list[dict[str, Any]],
    limit: int,
    exclude_volatile: bool,
    progress_callback: Callable[[int, int], None] | None = None,
) -> pd.DataFrame:
    selected = []
    for item in fixtures:
        league_name = ((item.get("league", {}) or {}).get("name") or "")
        if exclude_volatile and is_excluded(league_name):
            continue
        selected.append(item)
        if len(selected) >= limit:
            break

    results = []
    total = len(selected)
    for index, item in enumerate(selected, start=1):
        try:
            result = scan_fixture(item)
            if result:
                results.append(result)
        except Exception:
            pass

        if progress_callback:
            progress_callback(index, total)

    if not results:
        return pd.DataFrame()

    return pd.DataFrame(results).sort_values(
        ["JOYA Score", "Muestra"],
        ascending=[False, False],
    )
