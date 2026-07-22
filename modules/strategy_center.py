from __future__ import annotations
import pandas as pd
from config.settings import DREAM_MARKETS, SAFE_ALTERNATIVES


def dream_candidates(all_markets, min_confidence=79, min_sample=6):
    if all_markets.empty:
        return pd.DataFrame()
    df=all_markets[
        all_markets["Mercado"].isin(DREAM_MARKETS)
        & (all_markets["Confianza JOYA"]>=min_confidence)
        & (all_markets["Muestra"]>=min_sample)
        & all_markets["Calidad"].isin(["A+","A","B+"])
    ].copy()
    if df.empty:return df
    risk_penalty=df["Riesgo"].map({"Bajo":0,"Medio":3,"Alto":8}).fillna(8)
    df["Potencial soñadora"]=(df["Confianza JOYA"]+df["Probabilidad %"]*0.15-risk_penalty).round(1)
    return df.sort_values(["Potencial soñadora","Confianza JOYA","Muestra"],ascending=[False,False,False])


def build_dream_card(candidates,picks=3):
    if candidates.empty:return pd.DataFrame()
    selected=[];matches=set();leagues=set()
    for _,row in candidates.iterrows():
        league=(row["País"],row["Liga"])
        if row["fixture_id"] in matches or league in leagues:continue
        selected.append(row);matches.add(row["fixture_id"]);leagues.add(league)
        if len(selected)>=picks:break
    return pd.DataFrame(selected)


def joya_of_day(all_markets):
    if all_markets.empty:return pd.DataFrame()
    df=all_markets[(all_markets["Tier"].isin(["S++","S+"]))&(all_markets["Riesgo"]=="Bajo")&(all_markets["Muestra"]>=8)]
    return df.sort_values(["Confianza JOYA","Muestra"],ascending=[False,False]).head(1)


def bleeding_core(all_markets,max_picks=8):
    if all_markets.empty:return pd.DataFrame()
    df=all_markets[(all_markets["Tier"].isin(["S++","S+","A++"]))&(all_markets["Riesgo"].isin(["Bajo","Medio"]))].sort_values(["Confianza JOYA","Muestra"],ascending=[False,False])
    selected=[];matches=set()
    for _,row in df.iterrows():
        if row["fixture_id"] in matches:continue
        selected.append(row);matches.add(row["fixture_id"])
        if len(selected)>=max_picks:break
    return pd.DataFrame(selected)


def ladder(all_markets):
    if all_markets.empty:return {"Nivel 1 · Base":pd.DataFrame(),"Nivel 2 · Intermedio":pd.DataFrame(),"Nivel 3 · Soñador":pd.DataFrame()}
    df=all_markets[(all_markets["Tier"].isin(["S++","S+","A++"]))&(all_markets["Riesgo"].isin(["Bajo","Medio"]))].sort_values(["Confianza JOYA","Muestra"],ascending=[False,False])
    def choose(n):
        chosen=[];matches=set();leagues=set()
        for _,row in df.iterrows():
            key=(row["País"],row["Liga"])
            if row["fixture_id"] in matches or key in leagues:continue
            chosen.append(row);matches.add(row["fixture_id"]);leagues.add(key)
            if len(chosen)>=n:break
        return pd.DataFrame(chosen)
    return {"Nivel 1 · Base":choose(2),"Nivel 2 · Intermedio":choose(3),"Nivel 3 · Soñador":choose(4)}


def safe_alternative(market):return SAFE_ALTERNATIVES.get(market,"Usar la alternativa conservadora mejor puntuada")


def trap_reasons(row):
    reasons=[]
    if row["Muestra"]<6:reasons.append("Muestra pequeña")
    if row["Consistencia"]=="Baja":reasons.append("Tendencias local/visitante divididas")
    if row["Riesgo"]=="Alto":reasons.append("Riesgo alto")
    if abs(row["Local casa %"]-row["Visitante fuera %"])>=25:reasons.append("Señales muy desiguales")
    if row["Probabilidad %"]>=88 and row["Confianza JOYA"]<82:reasons.append("Porcentaje bruto alto, pero confianza calibrada baja")
    if row["Mercado"] in {"Gana local","Gana visitante"} and row["Confianza JOYA"]<82:reasons.append("Ganador simple sin ventaja suficiente")
    return reasons
