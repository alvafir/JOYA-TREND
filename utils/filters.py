from config.settings import EXCLUDED_YOUTH_TERMS,FRIENDLY_TERMS
def contains_any(text,terms):
    t=text.lower();return any(x in t for x in terms)
def prepare_fixtures(fixtures,exclude_youth,exclude_friendlies):
    out=[]
    for x in fixtures:
        name=((x.get("league",{}) or {}).get("name") or "")
        if exclude_youth and contains_any(name,EXCLUDED_YOUTH_TERMS):continue
        if exclude_friendlies and contains_any(name,FRIENDLY_TERMS):continue
        out.append(x)
    return sorted(out,key=lambda x:(((x.get("league",{}) or {}).get("country") or ""),((x.get("league",{}) or {}).get("name") or ""),((x.get("fixture",{}) or {}).get("date") or "")))
