DISPLAY_COLUMNS=["Mercado","Local casa %","Visitante fuera %","Probabilidad %","Confianza JOYA","Tier","Riesgo","Calidad","Consistencia","Muestra"]
def get_group_table(t,g):return t[t["Grupo"]==g][DISPLAY_COLUMNS].copy() if not t.empty else t
