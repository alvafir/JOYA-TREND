from datetime import date,timedelta
import streamlit as st
from config.settings import MARKET_GROUPS
def render_sidebar():
 return {"date":st.sidebar.date_input("Fecha",value=date.today(),min_value=date.today()-timedelta(days=7),max_value=date.today()+timedelta(days=30)),"exclude_youth":st.sidebar.checkbox("Excluir juveniles y reservas",True),"exclude_friendlies":st.sidebar.checkbox("Excluir amistosos",False),"max_per_league":int(st.sidebar.select_slider("Máximo de partidos por liga",options=[1,2,3,4,5],value=2)),"selected_groups":st.sidebar.multiselect("Mercados activos",options=list(MARKET_GROUPS.keys()),default=list(MARKET_GROUPS.keys()))}
