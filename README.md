# JOYA X ENTERPRISE — Sprint 6
## Intelligence Center

Archivo listo para Streamlit, construido sobre Sprint 4.

### Incluye

- Match Report completo por partido.
- Matriz de todos los mercados activos.
- Probabilidad histórica.
- Confianza JOYA.
- Fragilidad del mercado.
- Score de decisión.
- BET / BET CON PRECAUCIÓN / NO BET.
- Calidad de datos.
- Consistencia.
- Tamaño de muestra.
- JOYA Explain con explicación automática.
- Heatmap por familias de mercado.
- Índice de diversidad de mercados.
- Dos picks finales por partido.
- Una alternativa.
- Comparador de mercados.
- Ranking global ajustado por fragilidad.
- Joya del día.
- Soñadora.
- Núcleo sangrado.
- Escalera.
- Detector de trampas.

### Cambio clave

Mercados como `Sin gol antes del 10` reciben una penalización de fragilidad.
Un porcentaje alto ya no basta para convertirse automáticamente en el pick principal.

### Instalación

Sube todo el contenido del ZIP a GitHub conservando exactamente los nombres.

Archivo principal:

```text
app.py
```

Streamlit Secrets:

```toml
APISPORTS_KEY = "TU_CLAVE_API_FOOTBALL"
```

### Nota

Tarjetas, córners, remates, tiros al arco, offsides y atajadas solo deben
mostrar porcentajes cuando la API tenga cobertura y una muestra suficiente.
No se deben inventar estadísticas cuando no exista información válida.
