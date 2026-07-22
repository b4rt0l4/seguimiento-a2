# Seguimiento A2

## Descripcion del proyecto

Aplicacion para llevar el seguimiento del numero de examenes del carnet de moto A2 realizados por un grupo de personas. Los datos se visualizan en un Kibana publico y gratuito.

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

### Entrada de datos (doble via)
1. **Telegram Bot**: entrada rapida desde movil (ej: `/examen Juan 2`)
2. **Web form simple**: formulario accesible desde navegador con campos persona, fecha, num_examenes

### Modelo de datos
Dos tablas en PostgreSQL:

**persona**: lista fija de personas (actualmente Rafa y Sergio)
```sql
id SERIAL PRIMARY KEY, nombre VARCHAR(100) UNIQUE NOT NULL
```

**examenes**: registro de examenes por persona y dia
```sql
id SERIAL PRIMARY KEY, persona_id INTEGER REFERENCES persona(id), fecha DATE,
num_examenes INTEGER CHECK (> 0), num_aprobados INTEGER CHECK (>= 0 AND <= num_examenes)
```

- La lista de personas se gestiona en la tabla `persona` (no hardcodeada en codigo).
- El formulario web muestra un dropdown no editable con las personas de la tabla.
- Validaciones (en backend y en BD): fecha no futura, examenes > 0, 0 <= aprobados <= examenes.

### Graficas en Kibana
1. **Examenes por dia**: numero de examenes realizados cada dia (por persona)
2. **Acumulado total**: suma acumulada de examenes por persona a lo largo del tiempo

## Arquitectura

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Telegram Bot │────>│                 │────>│   PostgreSQL     │
└─────────────┘     │  Python backend │     │   (Supabase)     │
┌─────────────┐     │                 │     └────────┬─────────┘
│  Web Form   │────>│                 │              │
└─────────────┘     └─────────────────┘              │ lee datos
                                            ┌────────▼─────────┐
                                            │  Grafana Cloud   │
                                            │  (dashboards)    │
                                            └──────────────────┘
```

## Estado actual
- [ ] Crear cuenta en Supabase (PostgreSQL free tier)
- [ ] Crear cuenta en Grafana Cloud (free tier)
- [x] Estructura del proyecto Python
- [x] Bot de Telegram (codigo)
- [x] Web form (codigo)
- [ ] Conectar Grafana a PostgreSQL
- [ ] Crear dashboards en Grafana
- [ ] Despliegue bot en Raspberry Pi
- [ ] Despliegue web en Render

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
    ├─��� config.py          ← configuracion compartida (env vars)
    ├── db.py              ← acceso a PostgreSQL (esquema + queries)
    ├── bot/
    │   └── main.py        ← bot Telegram (polling)
    └── web/
        ├── app.py         ← Flask app
        └── templates/
            └── index.html ← formulario
```

## Notas
- El proyecto debe ser sencillo y publico.
- El fichero CLAUDE.md sirve como contexto para cualquier LLM que continue el trabajo.
- Ante cambios de requisitos, actualizar este fichero primero.
