from __future__ import annotations

from math import prod
import pandas as pd

from modules.correlation_engine import cart_correlation, market_family


def build_smart_cart(
    all_markets: pd.DataFrame,
    min_confidence: float = 85.0,
    allowed_tiers: tuple[str, ...] = ("S++", "S+", "A++"),
    max_picks: int = 4,
    max_per_league: int = 1,
    max_per_country: int = 1,
    max_same_market: int = 1,
    max_same_family: int = 2,
    avoid_same_fixture: bool = True,
    manual_odds: dict[tuple[int, str], float] | None = None,
    target_odds: float | None = None,
) -> tuple[pd.DataFrame, dict]:
    if all_markets.empty:
        return pd.DataFrame(), {"reason": "No existen mercados analizados."}

    candidates = all_markets[
        (all_markets["Confianza JOYA"] >= min_confidence)
        & (all_markets["Tier"].isin(allowed_tiers))
        & (all_markets["Riesgo"].isin(["Bajo", "Medio"]))
    ].copy()

    if candidates.empty:
        return pd.DataFrame(), {"reason": "Ningún mercado cumple los filtros elegidos."}

    candidates["Familia"] = candidates.apply(
        lambda row: market_family(str(row["Grupo"]), str(row["Mercado"])), axis=1
    )
    candidates = candidates.sort_values(
        ["Confianza JOYA", "Muestra", "Probabilidad %"],
        ascending=[False, False, False],
    )

    selected: list[dict] = []
    league_counts: dict[tuple[str, str], int] = {}
    country_counts: dict[str, int] = {}
    market_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    fixture_ids: set[int] = set()

    for _, row in candidates.iterrows():
        item = row.to_dict()
        fixture_id = int(item["fixture_id"])
        league_key = (str(item["País"]), str(item["Liga"]))
        country = str(item["País"])
        market = str(item["Mercado"])
        family = str(item["Familia"])

        if avoid_same_fixture and fixture_id in fixture_ids:
            continue
        if league_counts.get(league_key, 0) >= max_per_league:
            continue
        if country_counts.get(country, 0) >= max_per_country:
            continue
        if market_counts.get(market, 0) >= max_same_market:
            continue
        if family_counts.get(family, 0) >= max_same_family:
            continue

        if manual_odds:
            item["Cuota"] = float(manual_odds.get((fixture_id, market), 0.0))
        else:
            item["Cuota"] = 0.0

        selected.append(item)
        fixture_ids.add(fixture_id)
        league_counts[league_key] = league_counts.get(league_key, 0) + 1
        country_counts[country] = country_counts.get(country, 0) + 1
        market_counts[market] = market_counts.get(market, 0) + 1
        family_counts[family] = family_counts.get(family, 0) + 1

        valid_odds = [x["Cuota"] for x in selected if x["Cuota"] and x["Cuota"] > 1]
        combined_odds = prod(valid_odds) if len(valid_odds) == len(selected) and selected else 0.0

        if target_odds and combined_odds >= target_odds:
            break
        if len(selected) >= max_picks:
            break

    cart = pd.DataFrame(selected)
    if cart.empty:
        return cart, {"reason": "No fue posible formar una cartilla con estas restricciones."}

    overall_correlation, warnings = cart_correlation(selected)
    valid_odds = [float(x.get("Cuota", 0)) for x in selected]
    combined_odds = prod(valid_odds) if valid_odds and all(x > 1 for x in valid_odds) else None

    confidence_product = prod(float(x["Probabilidad %"]) / 100 for x in selected)
    combined_probability = round(confidence_product * 100, 2)

    return cart, {
        "reason": "Cartilla construida correctamente.",
        "correlation": overall_correlation,
        "warnings": warnings,
        "combined_odds": round(combined_odds, 2) if combined_odds else None,
        "combined_probability": combined_probability,
        "average_confidence": round(sum(float(x["Confianza JOYA"]) for x in selected) / len(selected), 1),
    }
