# Seguimiento A2

## Descripcion del proyecto

Aplicacion para llevar el seguimiento del numero de examenes del carnet de moto A2 realizados por un grupo de personas, y de la "pregunta del dia" (acierto/fallo diario). Los datos se visualizan en un Grafana Cloud publico y gratuito.

## Decisiones tomadas

### Tecnologia
- **Lenguaje**: Python
- **Visualizacion**: Grafana Cloud (free tier)
- **Almacenamiento**: PostgreSQL (Supabase free tier)
- **Hosting web form**: Render (free tier) — URL publica automatica
- **Hosting bot Telegram**: Raspberry Pi (polling, siempre encendido)
- **Libreria bot**: python-telegram-bot 21.x
- **Framework web**: FastAPI (uvicorn como servidor ASGI)
- **Driver DB**: psycopg2

### Entrada de datos (triple via)
1. **Telegram Bot**: entrada rapida desde movil (ej: `/examen Juan 2 1`)
2. **Web form simple**: formulario accesible desde navegador con campos persona, fecha, num_examenes, num_aprobados
3. **API REST**: endpoint `POST /api/pregunta` para sistema externo (pregunta del dia)

### Modelo de datos
Tres tablas en PostgreSQL:

**persona**: lista de personas con flags de participacion
```sql
id SERIAL PRIMARY KEY, nombre VARCHAR(100) UNIQUE NOT NULL,
puede_examenes BOOLEAN NOT NULL DEFAULT false,
puede_pregunta BOOLEAN NOT NULL DEFAULT false
```

**examenes**: registro de examenes por persona y dia
```sql
id SERIAL PRIMARY KEY, persona_id INTEGER REFERENCES persona(id), fecha DATE,
num_examenes INTEGER CHECK (> 0), num_aprobados INTEGER CHECK (>= 0 AND <= num_examenes)
```

**pregunta_dia**: registro de pregunta del dia por persona y fecha
```sql
id SERIAL PRIMARY KEY, persona_id INTEGER REFERENCES persona(id),
fecha DATE NOT NULL, acertada BOOLEAN NOT NULL
```

- La lista de personas se gestiona en la tabla `persona` (no hardcodeada en codigo).
- Cada persona tiene flags `puede_examenes` y `puede_pregunta` (default false). Los conjuntos pueden ser distintos.
- El formulario web muestra solo personas con `puede_examenes = true`.
- El bot de Telegram solo permite registrar examenes de personas con `puede_examenes = true`.
- La API de pregunta del dia solo acepta personas con `puede_pregunta = true`.
- Validaciones (en backend y en BD): fecha no futura, examenes > 0, 0 <= aprobados <= examenes.

### API para sistema externo
- Endpoint: `POST /api/pregunta`
- Autenticacion: `Authorization: Bearer <API_KEY>`
- Body JSON: `{ "persona": "nombre", "fecha": "YYYY-MM-DD", "acertada": true/false }`
- Variable de entorno `API_KEY` en `.env`

### Graficas en Grafana
#### Examenes (8 paneles)
1. **Examenes por dia**: barras por persona y fecha (Bar chart, generate_series)
2. **Examenes acumulado**: linea continua por persona (Time series, Connect null values: Always)
3. **Aprobados por dia**: barras por persona y fecha (Bar chart, generate_series)
4. **Aprobados acumulado**: linea continua por persona
5. **Suspensos por dia**: calculado como num_examenes - num_aprobados (Bar chart, generate_series)
6. **Suspensos acumulado**: linea continua por persona
7. **Ratio aprobados por dia (%)**: porcentaje diario por persona
8. **Ratio aprobados acumulado (%)**: evolucion del porcentaje global por persona

#### Pregunta del dia (4 paneles)
9. **Aciertos por dia**: barras con aciertos/fallos por persona y fecha
10. **Aciertos acumulado**: linea continua con total de aciertos por persona
11. **Ratio aciertos por dia (%)**: porcentaje de acierto diario por persona
12. **Ratio aciertos acumulado (%)**: evolucion del porcentaje global por persona

Nota sobre paneles con barras: para que respeten el rango de tiempo del dashboard, usar visualizacion Time series con estilo Bars (no Bar chart).
Para que las lineas no tengan saltos en dias sin datos: Connect null values = Always.
Para paneles con barras desglosadas por persona: usar query con columnas separadas por persona en vez de AS metric.

### Dashboard publico
- El dashboard se comparte con link publico desde Grafana Cloud
- Se habilita el time range picker para que los visitantes puedan filtrar por fechas
- Rango por defecto: 7 dias

## Arquitectura

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Telegram Bot │────>│                 │────>│   PostgreSQL     │
└─────────────┘     │  Python backend │     │   (Supabase)     │
┌─────────────┐     │  (FastAPI)      │     └────────┬─────────┘
│  Web Form   │────>│                 │              │
└─────────────┘     │                 │              │ lee datos
┌─────────────┐     │                 │     ┌────────▼─────────┐
│Sistema ext. │────>│  POST /api/     │     │  Grafana Cloud   │
│(pregunta)   │     │  pregunta       │     │  (dashboards)    │
└─────────────┘     └─────────────────┘     └──────────────────┘
```

## Estado actual
- [x] Crear cuenta en Supabase (PostgreSQL free tier)
- [x] Crear cuenta en Grafana Cloud (free tier)
- [x] Estructura del proyecto Python
- [x] Bot de Telegram (codigo)
- [x] Web form (codigo)
- [x] Conectar Grafana a PostgreSQL
- [x] Crear dashboards en Grafana (8 paneles examenes)
- [x] Despliegue web en Render
- [x] Despliegue bot en Raspberry Pi
- [x] API pregunta del dia (codigo)
- [ ] Crear paneles Grafana para pregunta del dia (4 paneles)
- [ ] Configurar API_KEY en Render y Raspberry Pi

## Estructura de carpetas
```
seguimiento-a2/
├── CLAUDE.md
├── .gitignore
├── .env.example
├── requirements.txt
├── docs/
│   └── setup.md           ← guia de registro y despliegue
└── src/
    ├── config.py          ← configuracion compartida (env vars)
    ├── db.py              ← acceso a PostgreSQL (esquema + queries)
    ├── bot/
    │   └── main.py        ← bot Telegram (polling)
    └── web/
        ├── app.py         ← FastAPI app (formulario + API pregunta)
        └── templates/
            └── index.html ← formulario
```

## Notas
- El proyecto debe ser sencillo y publico.
- El fichero CLAUDE.md sirve como contexto para cualquier LLM que continue el trabajo.
- Ante cambios de requisitos, actualizar este fichero primero.
- Importante: usar siempre la URL del connection pooler de Supabase (pooler.supabase.com:6543), no la conexion directa (db.xxx.supabase.co:5432). La directa no es accesible desde servicios externos como Render o Grafana Cloud.
