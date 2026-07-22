from collections import defaultdict
import pandas as pd
from engines.market_engine import analyze_all_markets
def scan_fixtures(fixtures,max_per_league,selected_groups,progress_callback):
 g=defaultdict(list)
 for x in fixtures:
  l=x.get("league",{}) or {};g[(l.get("country") or "Sin país",l.get("name") or "Sin liga")].append(x)
 q=[]
 for k in sorted(g):q.extend(g[k][:max_per_league])
 s=[];tables={};total=len(q)
 for i,x in enumerate(q,1):
  try:
   sm,t=analyze_all_markets(x,selected_groups);fid=int((x.get("fixture",{}) or {}).get("id"));
   if sm:s.append(sm)
   if not t.empty:tables[fid]=t
  except Exception:pass
  progress_callback(i,total,((x.get("league",{}) or {}).get("name") or "Sin liga"))
 r=pd.DataFrame(s)
 if not r.empty:r=r.sort_values(["Confianza","Muestra"],ascending=[False,False])
 return r,tables
