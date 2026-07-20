FINISHED={"FT","AET","PEN"}
def is_finished(x): return (((x.get("fixture",{}) or {}).get("status",{}) or {}).get("short") in FINISHED)
def select_venue_fixtures(fixtures,team_id,home,limit):
    out=[]
    for x in fixtures:
        if not is_finished(x): continue
        t=x.get("teams",{}) or {}; sid=((t.get("home",{}) or {}).get("id") if home else (t.get("away",{}) or {}).get("id"))
        if sid==team_id: out.append(x)
        if len(out)>=limit: break
    return out
def calculate_basic_metrics(fixtures,team_id):
    keys=["score","concede","over15","over25","under35","under45","btts","team_over15","first_half_over05","first_half_under25","win","draw","loss"]; c={k:0 for k in keys}; n=0
    for x in fixtures:
        if not is_finished(x): continue
        teams=x.get("teams",{}) or {}; goals=x.get("goals",{}) or {}; ht=((x.get("score",{}) or {}).get("halftime",{}) or {})
        gh,ga=goals.get("home"),goals.get("away")
        if gh is None or ga is None: continue
        home_id=(teams.get("home",{}) or {}).get("id"); gf,gc=(gh,ga) if home_id==team_id else (ga,gh); n+=1
        c["score"]+=gf>=1;c["concede"]+=gc>=1;c["over15"]+=gf+gc>=2;c["over25"]+=gf+gc>=3;c["under35"]+=gf+gc<=3;c["under45"]+=gf+gc<=4;c["btts"]+=gf>=1 and gc>=1;c["team_over15"]+=gf>=2
        hth,hta=ht.get("home"),ht.get("away")
        if hth is not None and hta is not None: c["first_half_over05"]+=hth+hta>=1;c["first_half_under25"]+=hth+hta<=2
        c["win"]+=gf>gc;c["draw"]+=gf==gc;c["loss"]+=gf<gc
    if not n:return {"sample":0}
    r={"sample":n}; r.update({k:round(100*v/n,1) for k,v in c.items()}); return r
def event_minute(e):
    t=e.get("time",{}) or {}; el=t.get("elapsed"); ex=t.get("extra") or 0
    return None if el is None else int(el)+int(ex)
