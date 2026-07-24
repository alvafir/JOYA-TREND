from api.football_api import get_fixture_events
from core.probability_engine import event_minute,is_finished
def calculate_minute_metrics(fixtures,team_id,max_games):
    valid=[]
    for x in fixtures:
        if (x.get("fixture",{}) or {}).get("id") and is_finished(x): valid.append(x)
        if len(valid)>=max_games: break
    ks=["no_goal_10","goal_before_70","first_half_goal","team_goal_before_70","opponent_goal_before_70","team_scores_first","opponent_scores_first"]; c={k:0 for k in ks}; n=0
    for x in valid:
        ev=get_fixture_events(int((x.get("fixture",{}) or {}).get("id"))); goals=[]
        for e in ev:
            if e.get("type")!="Goal" or e.get("detail")=="Missed Penalty": continue
            m=event_minute(e); tid=(e.get("team",{}) or {}).get("id")
            if m is not None: goals.append((m,tid))
        goals.sort(); first=goals[0] if goals else None; n+=1
        c["no_goal_10"]+=first is None or first[0]>10;c["goal_before_70"]+=first is not None and first[0]<=70;c["first_half_goal"]+=any(m<=45 for m,_ in goals);c["team_goal_before_70"]+=any(m<=70 and t==team_id for m,t in goals);c["opponent_goal_before_70"]+=any(m<=70 and t!=team_id for m,t in goals)
        if first:c["team_scores_first"]+=first[1]==team_id;c["opponent_scores_first"]+=first[1]!=team_id
    if not n:return {"event_sample":0}
    r={"event_sample":n};r.update({k:round(100*v/n,1) for k,v in c.items()});return r
