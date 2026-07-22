from core.confidence_engine import *
def build_market_result(group,market,raw,sample,h,a):
    c=calibrate_probability(raw,sample,market)
    return {"Grupo":group,"Mercado":market,"Local casa %":round(h,1),"Visitante fuera %":round(a,1),"Probabilidad %":round(raw,1),"Confianza JOYA":c,"Tier":tier(c,sample),"Riesgo":risk_level(c,sample),"Calidad":data_quality(sample),"Consistencia":consistency(h,a),"Muestra":sample}
