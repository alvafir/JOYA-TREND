from database.database import get_connection
def save_analysis_rows(summary,table):
    if table.empty:return
    rows=[(summary.get("fixture_id"),summary.get("País"),summary.get("Liga"),summary.get("Local"),summary.get("Visitante"),r.get("Grupo"),r.get("Mercado"),float(r.get("Probabilidad %",0)),float(r.get("Confianza JOYA",0)),r.get("Tier"),r.get("Riesgo"),int(r.get("Muestra",0))) for _,r in table.iterrows()]
    with get_connection() as c:
        c.executemany("INSERT INTO analyses(fixture_id,country,league,home_team,away_team,market_group,market,probability,confidence,tier,risk,sample_size) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",rows);c.commit()
