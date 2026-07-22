from __future__ import annotations

import pandas as pd


def build_all_market_ranking(
    match_ranking: pd.DataFrame,
    market_tables: dict[int, pd.DataFrame],
) -> pd.DataFrame:
    """Create a true global ranking containing every analyzed market."""
    rows: list[dict] = []

    if match_ranking.empty:
        return pd.DataFrame()

    metadata = match_ranking.set_index("fixture_id").to_dict("index")

    for fixture_id, table in market_tables.items():
        match = metadata.get(fixture_id)
        if not match or table.empty:
            continue

        for _, market in table.iterrows():
            rows.append({
                "fixture_id": fixture_id,
                "País": match.get("País"),
                "Liga": match.get("Liga"),
                "Partido": f"{match.get('Local')} vs {match.get('Visitante')}",
                "Local": match.get("Local"),
                "Visitante": match.get("Visitante"),
                "Grupo": market.get("Grupo"),
                "Mercado": market.get("Mercado"),
                "Probabilidad %": float(market.get("Probabilidad %", 0)),
                "Confianza JOYA": float(market.get("Confianza JOYA", 0)),
                "Tier": market.get("Tier"),
                "Riesgo": market.get("Riesgo"),
                "Calidad": market.get("Calidad"),
                "Consistencia": market.get("Consistencia"),
                "Muestra": int(market.get("Muestra", 0)),
                "Local casa %": float(market.get("Local casa %", 0)),
                "Visitante fuera %": float(market.get("Visitante fuera %", 0)),
            })

    ranking = pd.DataFrame(rows)
    if ranking.empty:
        return ranking

    return ranking.sort_values(
        ["Confianza JOYA", "Muestra", "Probabilidad %"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def top_markets_by_match(
    all_markets: pd.DataFrame,
    fixture_id: int,
    limit: int = 5,
) -> pd.DataFrame:
    if all_markets.empty:
        return pd.DataFrame()

    result = all_markets[
        (all_markets["fixture_id"] == fixture_id)
        & (all_markets["Tier"] != "NO BET")
    ].copy()

    return result.head(limit)


def top_markets_by_league(
    all_markets: pd.DataFrame,
    country: str,
    league: str,
    limit: int = 5,
) -> pd.DataFrame:
    if all_markets.empty:
        return pd.DataFrame()

    result = all_markets[
        (all_markets["País"] == country)
        & (all_markets["Liga"] == league)
        & (all_markets["Tier"] != "NO BET")
    ].copy()

    return result.head(limit)
