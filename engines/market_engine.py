from api.football_api import get_team_fixtures
from config.settings import EVENT_SAMPLE,RECENT_GENERAL,RECENT_VENUE
from core.probability_engine import calculate_basic_metrics,select_venue_fixtures
from core.score_engine import build_market_result
from engines.goal_engine import calculate_minute_metrics
import pandas as pd
def avg(a,b):return round((a+b)/2,1)
def analyze_all_markets(fixture,groups):
 f=fixture.get("fixture",{}) or {};l=fixture.get("league",{}) or {};t=fixture.get("teams",{}) or {};h=t.get("home",{}) or {};a=t.get("away",{}) or {};hid=h.get("id");aid=a.get("id")
 if not hid or not aid:return None,pd.DataFrame()
 ha=get_team_fixtures(int(hid));aa=get_team_fixtures(int(aid));hb=select_venue_fixtures(ha,int(hid),True,RECENT_VENUE) or ha[:RECENT_GENERAL];ab=select_venue_fixtures(aa,int(aid),False,RECENT_VENUE) or aa[:RECENT_GENERAL];hm=calculate_basic_metrics(hb,int(hid));am=calculate_basic_metrics(ab,int(aid));sample=min(int(hm.get("sample",0)),int(am.get("sample",0)));rows=[]
 def add(g,m,r,x,y,s=sample):rows.append(build_market_result(g,m,r,s,x,y))
 if "Goles del partido" in groups:
  for m,k in [("Más de 1.5 goles","over15"),("Más de 2.5 goles","over25"),("Menos de 3.5 goles","under35"),("Menos de 4.5 goles","under45")]:add("Goles del partido",m,avg(hm.get(k,0),am.get(k,0)),hm.get(k,0),am.get(k,0))
 if "Goles por equipo" in groups:
  add("Goles por equipo","Local marca +0.5",avg(hm.get("score",0),am.get("concede",0)),hm.get("score",0),am.get("concede",0));add("Goles por equipo","Visitante marca +0.5",avg(am.get("score",0),hm.get("concede",0)),hm.get("concede",0),am.get("score",0));add("Goles por equipo","Local marca +1.5",avg(hm.get("team_over15",0),am.get("concede",0)),hm.get("team_over15",0),am.get("concede",0));add("Goles por equipo","Visitante marca +1.5",avg(am.get("team_over15",0),hm.get("concede",0)),hm.get("concede",0),am.get("team_over15",0))
 if "BTTS" in groups:
  add("BTTS","Ambos anotan - Sí",avg(hm.get("btts",0),am.get("btts",0)),hm.get("btts",0),am.get("btts",0));add("BTTS","Ambos anotan - No",avg(100-hm.get("btts",0),100-am.get("btts",0)),100-hm.get("btts",0),100-am.get("btts",0))
 if "Primer tiempo" in groups:
  add("Primer tiempo","1T +0.5 goles",avg(hm.get("first_half_over05",0),am.get("first_half_over05",0)),hm.get("first_half_over05",0),am.get("first_half_over05",0));add("Primer tiempo","1T -2.5 goles",avg(hm.get("first_half_under25",0),am.get("first_half_under25",0)),hm.get("first_half_under25",0),am.get("first_half_under25",0))
 if "Doble oportunidad" in groups:
  add("Doble oportunidad","1X",avg(100-hm.get("loss",0),am.get("loss",0)),100-hm.get("loss",0),am.get("loss",0));add("Doble oportunidad","X2",avg(hm.get("loss",0),100-am.get("loss",0)),hm.get("loss",0),100-am.get("loss",0));add("Doble oportunidad","12",avg(100-hm.get("draw",0),100-am.get("draw",0)),100-hm.get("draw",0),100-am.get("draw",0))
 if "Ganadores" in groups:
  add("Ganadores","Gana local",avg(hm.get("win",0),am.get("loss",0)),hm.get("win",0),am.get("loss",0));add("Ganadores","Gana visitante",avg(am.get("win",0),hm.get("loss",0)),hm.get("loss",0),am.get("win",0))
 if "Minutos" in groups or "Primer gol" in groups:
  x=calculate_minute_metrics(hb,int(hid),EVENT_SAMPLE);y=calculate_minute_metrics(ab,int(aid),EVENT_SAMPLE);es=min(int(x.get("event_sample",0)),int(y.get("event_sample",0)))
  if es>=5:
   no10=avg(x["no_goal_10"],y["no_goal_10"]);b70=avg(x["goal_before_70"],y["goal_before_70"])
   if "Minutos" in groups:
    add("Minutos","Sin gol antes del 10",no10,x["no_goal_10"],y["no_goal_10"],es);add("Minutos","Gol antes del 70",b70,x["goal_before_70"],y["goal_before_70"],es);add("Minutos","Sin gol 0-10 + gol antes del 70",round(no10*b70/100,1),x["no_goal_10"],y["goal_before_70"],es);add("Minutos","Local marca antes del 70",avg(x["team_goal_before_70"],y["opponent_goal_before_70"]),x["team_goal_before_70"],y["opponent_goal_before_70"],es);add("Minutos","Visitante marca antes del 70",avg(y["team_goal_before_70"],x["opponent_goal_before_70"]),x["opponent_goal_before_70"],y["team_goal_before_70"],es)
   if "Primer gol" in groups:
    add("Primer gol","Local marca primero",avg(x["team_scores_first"],y["opponent_scores_first"]),x["team_scores_first"],y["opponent_scores_first"],es);add("Primer gol","Visitante marca primero",avg(y["team_scores_first"],x["opponent_scores_first"]),x["opponent_scores_first"],y["team_scores_first"],es)
 table=pd.DataFrame(rows)
 if table.empty:return None,table
 table=table.sort_values(["Grupo","Confianza JOYA","Muestra"],ascending=[True,False,False]);valid=table[table["Tier"]!="NO BET"]
 if valid.empty:return None,table
 best=valid.sort_values(["Confianza JOYA","Muestra"],ascending=[False,False]).iloc[0]
 return {"fixture_id":f.get("id"),"País":l.get("country") or "Sin país","Liga":l.get("name") or "Sin liga","Local":h.get("name") or "Local","Visitante":a.get("name") or "Visitante","Mejor grupo":best["Grupo"],"Mejor pick":best["Mercado"],"Confianza":float(best["Confianza JOYA"]),"Tier":str(best["Tier"]),"Riesgo":str(best["Riesgo"]),"Calidad":str(best["Calidad"]),"Muestra":int(best["Muestra"])},table
