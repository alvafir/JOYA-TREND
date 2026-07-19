# JOYA 21 AI v1

Interfaz unificada con:

- Scanner de todas las ligas.
- Filtros por país.
- Mercados seleccionables.
- Ranking global.
- Resultados por liga.
- Análisis de un partido.
- Constructor de cartillas.
- Minutos y primer gol.
- Próximo gol en vivo.

## Instalación

Reemplaza únicamente:

- app.py
- requirements.txt
- README.md

Mantén en Streamlit Secrets:

```toml
APISPORTS_KEY = "TU_CLAVE"
```

## Nota

Los módulos de Minutos y Primer gol consumen más solicitudes porque revisan
eventos históricos. El scanner limita partidos por liga para controlar el uso.
