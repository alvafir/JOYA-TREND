from __future__ import annotations
import pandas as pd


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
    minimum_value = tier_order[minimum_tier]

    valid = ranking[
        ranking["Tier"].map(tier_order).fillna(0) >= minimum_value
    ].copy()

    if selected_leagues:
        valid = valid[valid["Liga"].isin(selected_leagues)]

    valid = valid.sort_values(["JOYA Score", "Muestra"], ascending=[False, False])

    picks, used_fixtures, used_leagues = [], set(), set()
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
