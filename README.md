# JOYA X ENTERPRISE — Sprint 2

Evolución directa del Sprint 1.

## Novedades

- Top 5 mercados por cada partido.
- Explicación automática y transparente de cada selección.
- Top 5 mercados por liga.
- Ranking global real con todos los mercados analizados.
- Medallas oro, plata y bronce para lectura rápida.
- Market Matrix completa conservada.
- Indicador visible de conexión con API-Football.
- Historial SQLite inicial para JOYA Brain.

## Instalación

Reemplaza el contenido del repositorio por todo lo incluido en este ZIP, respetando exactamente los nombres de carpetas y archivos.

En Streamlit Secrets:

```toml
APISPORTS_KEY = "TU_CLAVE_API_FOOTBALL"
```

Archivo principal:

```text
app.py
```

## Interpretación

- La copa dentro de un partido identifica el mercado con mayor Confianza JOYA de ese encuentro.
- El Top por liga compara todos los mercados de todos los partidos analizados en esa competición.
- El ranking global compara todos los mercados del día entre todas las ligas.
- NO BET significa que el mercado no superó los filtros mínimos de muestra y confianza.
