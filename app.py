import pandas as pd
import streamlit as st
from api.football_api import api_list,get_api_key,test_connection
from config.settings import DEFAULT_TIMEZONE
from database.database import initialize_database
from history.joya_brain import save_analysis_rows
from modules.league_analyzer import build_league_ranking
from modules.market_matrix import get_group_table
from modules.scanner import scan_fixtures
from ui.sidebar import render_sidebar
from utils.filters import prepare_fixtures
st.set_page_config(page_title="JOYA X Enterprise",page_icon="💎",layout="wide");initialize_database();st.title("💎 JOYA X ENTERPRISE");st.caption("Sprint 1 · Core Engine · Market Matrix · League Analyzer · Global Ranking")
if not get_api_key():st.error("Falta APISPORTS_KEY en Streamlit Secrets.");st.stop()
connected,msg=test_connection()
if connected:st.success(f"🟢 Conectado con API-Football · {msg}")
else:st.error(f"🔴 Sin conexión con API-Football · {msg}");st.stop()
s=render_sidebar();fixtures=api_list("fixtures",{"date":s["date"].isoformat(),"timezone":DEFAULT_TIMEZONE});prepared=prepare_fixtures(fixtures,s["exclude_youth"],s["exclude_friendlies"]);st.session_state.setdefault("ranking",pd.DataFrame());st.session_state.setdefault("tables",{})
c1,c2,c3,c4=st.columns(4);c1.metric("Partidos disponibles",len(prepared));c2.metric("Ligas disponibles",len({(((x.get("league",{}) or {}).get("country") or ""),((x.get("league",{}) or {}).get("name") or "")) for x in prepared}));c3.metric("Grupos activos",len(s["selected_groups"]));c4.metric("API-Football","Conectada")
if st.button("🔥 EJECUTAR SPRINT 1",type="primary",use_container_width=True):
 p=st.progress(0);txt=st.empty()
 def upd(i,total,league):p.progress(i/total if total else 1);txt.caption(f"Analizando {i} de {total} · {league}")
 r,t=scan_fixtures(prepared,s["max_per_league"],set(s["selected_groups"]),upd);st.session_state.ranking=r;st.session_state.tables=t
 for _,sm in r.iterrows():save_analysis_rows(sm.to_dict(),t.get(int(sm["fixture_id"]),pd.DataFrame()))
 p.empty();txt.empty();st.success("Sprint 1 completado y guardado en JOYA Brain.")
r=st.session_state.ranking;t=st.session_state.tables
if r.empty:st.info("Pulsa EJECUTAR SPRINT 1 para iniciar.");st.stop()
tabs=st.tabs(["🏆 Ranking global","🌍 Ranking por liga","📊 Market Matrix"])
with tabs[0]:st.dataframe(r[["País","Liga","Local","Visitante","Mejor pick","Confianza","Tier","Riesgo","Calidad","Muestra"]].head(100),use_container_width=True,hide_index=True)
with tabs[1]:st.dataframe(build_league_ranking(r),use_container_width=True,hide_index=True)
with tabs[2]:
 for (country,league),lg in r.groupby(["País","Liga"],sort=True):
  b=lg.sort_values(["Confianza","Muestra"],ascending=[False,False]).iloc[0]
  with st.expander(f"{country} · {league} · Mejor: {b['Mejor pick']} ({b['Confianza']:.1f})"):
   st.success(f"🏆 {b['Local']} vs {b['Visitante']} · {b['Mejor pick']} · {b['Confianza']:.1f} · {b['Tier']}")
   for _,m in lg.iterrows():
    table=t.get(int(m["fixture_id"]),pd.DataFrame());st.markdown(f"### {m['Local']} vs {m['Visitante']}")
    for group in s["selected_groups"]:
     gt=get_group_table(table,group)
     if not gt.empty:st.markdown(f"**{group}**");st.dataframe(gt,use_container_width=True,hide_index=True)
    st.divider()
st.caption("Tendencias históricas calibradas; no garantizan resultados.")
