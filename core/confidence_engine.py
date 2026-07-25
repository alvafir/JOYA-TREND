from config.settings import MARKET_PENALTIES
def calibrate_probability(raw,sample,market):
    w=min(1.0,sample/10); v=70+(raw-70)*(0.58+0.24*w)+min(3,max(0,sample-5)*.45)-MARKET_PENALTIES.get(market,0)
    return round(max(0,min(99,v)),1)
def data_quality(n): return "A+" if n>=10 else "A" if n>=8 else "B+" if n>=6 else "B" if n>=5 else "Insuficiente"
def risk_level(c,n): return "Alto" if n<5 else "Bajo" if c>=92 and n>=8 else "Medio" if c>=84 and n>=6 else "Alto"
def tier(c,n): return "NO BET" if n<5 else "S++" if c>=95 else "S+" if c>=90 else "A++" if c>=85 else "A+" if c>=80 else "NO BET"
def consistency(h,a):
    g=abs(h-a); return "Muy alta" if g<=8 else "Alta" if g<=15 else "Media" if g<=25 else "Baja"
