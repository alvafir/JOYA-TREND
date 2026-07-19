from __future__ import annotations

import math
import pandas as pd


def build_cart(
    ranking: pd.DataFrame,
    target_odds: float,
    max_picks: int,
    minimum_tier: str,
    assumed_odds: float,
) -> tuple[pd.DataFrame, float]:
    """
    Primera versión: usa una cuota manual promedio por selección.
    La integración de cuotas reales Betano llegará en la siguiente versión.
    """
    if ranking.empty:
        return pd.DataFrame(), 1.0

    tier_order = {"S++": 3, "S+": 2, "A++": 1, "NO BET": 0}
    minimum_value = tier_order[minimum_tier]

    valid = ranking[
        ranking["Tier"].map(tier_order).fillna(0) >= minimum_value
    ].copy()

    picks = []
    combined = 1.0
    used_fixtures = set()

    for _, row in valid.iterrows():
        fixture_id = row["fixture_id"]
        if fixture_id in used_fixtures:
            continue

        picks.append(row)
        used_fixtures.add(fixture_id)
        combined *= assumed_odds

        if combined >= target_odds or len(picks) >= max_picks:
            break

    if not picks:
        return pd.DataFrame(), 1.0

    return pd.DataFrame(picks), round(combined, 2)
