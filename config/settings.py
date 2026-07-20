API_BASE="https://v3.football.api-sports.io"
DEFAULT_TIMEZONE="America/Santiago"
RECENT_GENERAL=10
RECENT_VENUE=8
EVENT_SAMPLE=6
EXCLUDED_YOUTH_TERMS={"u17","u18","u19","u20","u21","u22","u23","youth","juvenil","reserve","reserves"}
FRIENDLY_TERMS={"friendly","friendlies","amistoso","amistosos"}
MARKET_GROUPS={
"Goles del partido":["Más de 1.5 goles","Más de 2.5 goles","Menos de 3.5 goles","Menos de 4.5 goles"],
"Goles por equipo":["Local marca +0.5","Visitante marca +0.5","Local marca +1.5","Visitante marca +1.5"],
"BTTS":["Ambos anotan - Sí","Ambos anotan - No"],
"Primer tiempo":["1T +0.5 goles","1T -2.5 goles"],
"Doble oportunidad":["1X","X2","12"],
"Minutos":["Sin gol antes del 10","Gol antes del 70","Sin gol 0-10 + gol antes del 70","Local marca antes del 70","Visitante marca antes del 70"],
"Primer gol":["Local marca primero","Visitante marca primero"]}
MARKET_PENALTIES={"Menos de 4.5 goles":8.0,"Menos de 3.5 goles":3.5,"Más de 1.5 goles":1.5,"1X":3.5,"X2":3.5,"12":4.5,"Local marca +0.5":1.0,"Visitante marca +0.5":1.0,"Sin gol antes del 10":2.0,"Gol antes del 70":2.0,"Local marca primero":2.0,"Visitante marca primero":2.0}
