# JOYA 20 ELITE v0.5 — GOAL ENGINE

Incluye:

- local jugando en casa;
- visitante jugando fuera;
- eventos históricos por minuto;
- ningún gol antes del minuto 10;
- gol antes del minuto 70;
- gol en la primera parte;
- doble condición 0–10 + antes del 70;
- local o visitante marca antes del 70;
- local o visitante marca primero;
- módulo de próximo gol en vivo usando estadísticas del partido.

## Instalación

Reemplaza:

- app.py
- requirements.txt
- README.md

Mantén:

```toml
APISPORTS_KEY = "TU_CLAVE"
```

## Consumo

El análisis por minutos consulta eventos históricos. Por seguridad, esta versión
trabaja partido por partido. El scanner masivo se añadirá después con caché persistente.
