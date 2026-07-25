from __future__ import annotations

from collections import defaultdict

import pandas as pd

from engines.market_engine import analyze_all_markets


def scan_fixtures(
    fixtures,
    max_per_league,
    selected_groups,
    progress_callback,
):
    grouped = defaultdict(list)

    for fixture in fixtures:
        league = fixture.get("league", {}) or {}
        key = (
            league.get("country") or "Sin país",
            league.get("name") or "Sin liga",
        )
        grouped[key].append(fixture)

    queue = []

    for key in sorted(grouped):
        league_matches = grouped[key]

        if max_per_league >= 999:
            queue.extend(league_matches)
        else:
            queue.extend(league_matches[:max_per_league])

    summaries = []
    tables = {}
    total = len(queue)

    for index, fixture in enumerate(queue, start=1):
        league_name = (
            (fixture.get("league", {}) or {}).get("name")
            or "Sin liga"
        )

        try:
            summary, table = analyze_all_markets(
                fixture,
                selected_groups,
            )

            fixture_id = int(
                (fixture.get("fixture", {}) or {}).get("id")
            )

            if summary:
                summaries.append(summary)

            if table is not None and not table.empty:
                tables[fixture_id] = table

        except Exception:
            pass

        progress_callback(
            index,
            total,
            league_name,
        )

    ranking = pd.DataFrame(summaries)

    if not ranking.empty:
        ranking = ranking.sort_values(
            ["Confianza", "Muestra"],
            ascending=[False, False],
        )

    return ranking, tables
