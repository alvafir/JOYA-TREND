import pandas as pd
def build_league_ranking(r):
 if r.empty:return pd.DataFrame()
 out=[]
 for (c,l),g in r.groupby(["País","Liga"],sort=True):
  b=g.sort_values(["Confianza","Muestra"],ascending=[False,False]).iloc[0];out.append({"País":c,"Liga":l,"Partido":f"{b['Local']} vs {b['Visitante']}","Mejor pick":b["Mejor pick"],"Confianza":b["Confianza"],"Tier":b["Tier"],"Riesgo":b["Riesgo"],"Calidad":b["Calidad"],"Muestra":b["Muestra"]})
 return pd.DataFrame(out).sort_values(["Confianza","Muestra"],ascending=[False,False])
