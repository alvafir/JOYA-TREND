# JOYA X ENTERPRISE 4.0.1 — RANKING HOTFIX

# JOYA X ENTERPRISE 4.0 — PHASE 1

# JOYA X ENTERPRISE v2 — ADAPTIVE ANALYSIS ENGINE

# JOYA X ENTERPRISE v1.1.1 — PROJECTION IMPORT HOTFIX

# JOYA X ENTERPRISE v1.1 — PROJECTION CENTER

# JOYA X ENTERPRISE v1.0.3 — FULL LEAGUE SCAN

# JOYA X ENTERPRISE v1.0.2 SETTINGS HOTFIX

# JOYA X ENTERPRISE v1.0.1 HOTFIX

# JOYA X ENTERPRISE v1.0 — Stable

Versión consolidada y compatible de JOYA X Enterprise.

## Incluye

- Conexión visible con API-Football.
- Intelligence Center por partido.
- Matriz completa de mercados activos.
- Probabilidad, confianza JOYA, Tier, riesgo, calidad y muestra.
- Índice de fragilidad y Score de decisión.
- BET, BET CON PRECAUCIÓN y NO BET.
- JOYA Explain.
- Heatmap y diversidad de familias.
- Dos picks finales por partido y una alternativa.
- Comparador de mercados.
- Joya del día.
- Soñadora del día.
- Núcleo sangrado.
- Escalera.
- Detector de trampas.
- Ranking global y por liga.
- Base SQLite inicial para historial.

## Instalación limpia recomendada

1. Borra del repositorio los archivos y carpetas de versiones anteriores.
2. Sube **todo el contenido** de este ZIP a la raíz del repositorio.
3. Conserva exactamente los nombres en inglés y en minúsculas.
4. El archivo principal de Streamlit es `app.py`.
5. En Streamlit Secrets agrega:

```toml
APISPORTS_KEY = "TU_CLAVE_API_FOOTBALL"
```

## Estructura obligatoria

```text
app.py
requirements.txt
api/
config/
core/
database/
engines/
history/
modules/
ui/
utils/
```

No mezcles esta versión con archivos de Sprints anteriores, ya que eso puede producir errores de importación.

## Nota

Las clasificaciones estadísticas no garantizan resultados. Los mercados sin cobertura o muestra suficiente deben quedar como NO BET.


## Instalación limpia obligatoria

1. Elimina del repositorio todos los archivos y carpetas de la versión anterior.
2. Sube el contenido completo de este ZIP.
3. Comprueba que `modules/strategy_center.py` esté presente.
4. En Streamlit Cloud pulsa **Reboot app**.
5. Si sigue mostrando una versión antigua, usa **Clear cache** y vuelve a reiniciar.

Este Hotfix también contiene un respaldo dentro de `app.py`, por lo que la aplicación
puede iniciar aunque Streamlit esté leyendo temporalmente un `strategy_center.py` antiguo.


## Corrección incluida

Esta versión corrige el error:

```text
KeyError: dream_min_confidence
```

La barra lateral ahora devuelve siempre:

- `dream_min_confidence`
- `dream_min_sample`
- `dream_picks`

Además, `app.py` incorpora valores de respaldo para impedir que la aplicación
se caiga aunque Streamlit conserve temporalmente archivos antiguos en caché.

## Instalación limpia

1. Borra el contenido anterior del repositorio.
2. Sube todo el contenido de este ZIP.
3. Confirma que `ui/sidebar.py` sea el archivo nuevo.
4. En Streamlit Cloud pulsa **Reboot app**.
5. Si aparece el error anterior, usa **Clear cache** y vuelve a reiniciar.


## Cobertura por liga

- **Rápida:** hasta 3 partidos por liga.
- **Amplia:** hasta 10 partidos por liga.
- **Completa:** todos los partidos disponibles de cada liga.

Para una jornada MLS con 15 partidos, selecciona **Cobertura completa**. Así,
los 15 encuentros entrarán al análisis y podrán aparecer en Intelligence Center,
Ranking global, Joya del día, Soñadora, Núcleo y otros módulos.

La cobertura completa utiliza más solicitudes de API-Football, especialmente
cuando están activos los mercados de minutos.


## Nuevos módulos

### Goal Range Engine

- Goles esperados totales.
- Goles esperados por equipo.
- Rango principal.
- Rangos de goles estilo Betano:
  - 0–2
  - 0–3
  - 0–4
  - 1–2
  - 1–3
  - 1–4
  - 1–5
  - 2–4
  - 2–5
  - 2–6
  - 3–4
  - 3–5
  - 3–6
  - 5–6
- Marcadores compatibles.

### BTTS primer tiempo

- Ambos marcan 1T — Sí.
- Ambos marcan 1T — No.
- Con penalización especial de fragilidad.

### Proyecciones avanzadas

Cuando API-Football tiene cobertura, JOYA proyecta:

- córners totales y por equipo;
- tarjetas amarillas y rojas;
- remates totales;
- tiros al arco;
- faltas;
- offsides;
- atajadas;
- saques de banda;
- saques de meta.

Cada categoría muestra:

- proyección total;
- rango;
- proyección local;
- proyección visitante;
- línea sugerida;
- probabilidad;
- confianza JOYA;
- muestra;
- BET / BET CON PRECAUCIÓN / NO BET.

### Árbitro

Se muestra el árbitro informado por API-Football. Esta versión no inventa un
ajuste tarjetero cuando no existe una base histórica suficiente del árbitro.

## Consumo de API

Las proyecciones avanzadas consultan estadísticas históricas de partidos.
Con cobertura completa y muchas ligas, el consumo puede ser elevado. La barra
lateral permite usar entre 2 y 5 partidos históricos por equipo.


## Corrección incluida

Corrige el error de inicio producido por:

```text
ImportError en engines/projection_engine.py
from api.football_api import get_fixture_statistics
```

`projection_engine.py` ahora utiliza una importación compatible. Si el repositorio
conserva temporalmente un `api/football_api.py` antiguo, consulta
`fixtures/statistics` mediante `api_list` y la aplicación puede iniciar.

## Instalación limpia

1. Elimina la versión anterior del repositorio.
2. Sube todo el contenido de este ZIP.
3. Comprueba que existan:
   - `api/football_api.py`
   - `engines/projection_engine.py`
4. En Streamlit Cloud usa **Clear cache**.
5. Pulsa **Reboot app**.


## Novedades

### Escaneo ligero

Carga primero:

- goles;
- local/visitante;
- BTTS;
- primer tiempo;
- minutos;
- rangos de goles;
- proyección central;
- fragilidad;
- BET / NO BET.

### Análisis PRO bajo demanda

Solo al pulsar el botón de un partido:

- córners;
- tarjetas;
- árbitro;
- remates;
- tiros al arco;
- faltas;
- offsides;
- atajadas;
- saques de banda;
- saques de meta.

### Prioridad automática

- Nivel 1 · Interés alto.
- Nivel 2 · Interés medio.
- Nivel 3 · Interés bajo.
- NO BET.

### Modos

- Rápido.
- Equilibrado.
- Profundo.
- Solo resumen.
- Top 5 partidos.
- Top 10 partidos.
- Todos.

## Recomendación para MLS

Usa cobertura completa, modo Rápido y Top 5 o Top 10. Después ejecuta
Análisis PRO únicamente en los partidos que realmente quieras revisar.


Incluye Data Lake, Job Manager, lotes de 10 y reutilización de resultados en todas las pestañas.


## Corrección

Soluciona el error:

```text
KeyError: ['Confianza', 'Muestra']
```

La aplicación valida el ranking antes de ordenarlo, ignora análisis antiguos
incompatibles y permite limpiarlos desde Job Manager.

## Instalación

1. Reemplaza completamente la versión anterior.
2. Usa Clear cache y Reboot app.
3. Abre Job Manager.
4. Pulsa `Limpiar análisis antiguos incompatibles`.
5. Crea un trabajo nuevo y ejecuta el primer lote.
