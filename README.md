# JOYA X ENTERPRISE — Sprint 1

Incluye arquitectura modular, indicador visible de conexión API-Football, Market Matrix, Ranking Global, Ranking por Liga y base SQLite inicial para JOYA Brain.

## Subir a GitHub
Sube todo respetando exactamente los nombres. El archivo principal de Streamlit es `app.py`.

## Streamlit Secrets
```toml
APISPORTS_KEY = "TU_CLAVE_API_FOOTBALL"
```

SQLite en Streamlit Cloud no es persistente tras reinicios; una fase posterior migrará JOYA Brain a PostgreSQL.
