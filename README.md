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
