# Guia de registro y despliegue

Este documento explica como registrarse en cada servicio, configurar las credenciales y desplegar los componentes de la aplicacion desde cero.

---

## 1. PostgreSQL (Supabase — free tier)

### Registro
1. Ir a https://supabase.com y crear cuenta (GitHub login recomendado)
2. Crear un nuevo proyecto (elegir region cercana, ej: eu-central-1)
3. Esperar a que el proyecto se provisione (~2 min)

### Obtener credenciales
1. En el dashboard de Supabase, click en el boton **"Connect"** (arriba a la derecha)
2. Seleccionar modo **Session** (connection pooler)
3. Copiar la URI de conexion. Tendra este formato:
   ```
   postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
4. Guardar como `DATABASE_URL` en el fichero `.env`

### Importante
- Usar siempre la URL del **connection pooler** (`pooler.supabase.com:6543`), NO la conexion directa (`db.xxx.supabase.co:5432`). La directa no es accesible desde Render ni Grafana Cloud.
- Las tablas (`persona`, `examenes` y `pregunta_dia`) se crean automaticamente al arrancar la app.
- Las personas iniciales (Rafa y Sergio) se insertan automaticamente con `puede_examenes = true` y `puede_pregunta = true`.
- Cada persona tiene flags `puede_examenes` y `puede_pregunta` (default false) que controlan en que funcionalidades participa.

---

## 2. Web Form (Render — free tier)

### Registro
1. Ir a https://render.com y crear cuenta (GitHub login recomendado)
2. Conectar tu repositorio de GitHub (puede ser privado)

### Desplegar
1. Crear un nuevo **Web Service**
2. Seleccionar el repositorio
3. Configurar:
   - **Name**: el nombre que quieras (sera parte de la URL)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.web.app:app --host 0.0.0.0 --port $PORT`
   - **Instance type**: Free
4. Anadir variables de entorno en **Environment**:
   - `DATABASE_URL` → la URI del pooler de Supabase
   - `API_KEY` → clave secreta para la API de pregunta del dia (generar con `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
5. Deploy — Render asigna una URL publica automaticamente (ej: `https://tu-nombre.onrender.com`)

### Nota sobre el free tier
- El servicio se "duerme" tras 15 min sin trafico
- La primera peticion tras dormir tarda ~30s (cold start)
- `$PORT` lo inyecta Render automaticamente, no hay que configurarlo

### Formulario
- Dropdown no editable con las personas de la tabla `persona`
- Campos: persona, fecha, examenes realizados, examenes aprobados
- Validaciones: fecha no futura, examenes > 0, aprobados entre 0 y examenes

---

## 3. Grafana Cloud (free tier)

### Registro
1. Ir a https://grafana.com/auth/sign-up/create-user y crear cuenta gratuita
2. Se crea automaticamente una instancia de Grafana Cloud

### Conectar PostgreSQL como data source
1. En Grafana, ir a **Connections > Data Sources > Add data source**
2. Seleccionar **PostgreSQL**
3. Rellenar con los datos del pooler de Supabase:
   - Host: `aws-0-[region].pooler.supabase.com:6543`
   - Database: `postgres`
   - User: `postgres.[ref]`
   - Password: la del proyecto
   - TLS/SSL Mode: `require`
4. Click **Save & Test** — debe decir "Database Connection OK"

### Crear dashboards

Ir a **Dashboards > New Dashboard**. Para cada panel: Add visualization, seleccionar datasource PostgreSQL, cambiar a modo **Code** y pegar la query.

Nota sobre paneles con barras: usar **Bar chart** con Format: **Time series**, Stacking: **Normal**. Para que muestren todas las fechas del rango (incluso sin datos), las queries usan `generate_series` + `CROSS JOIN persona` + `LEFT JOIN` con `COALESCE(..., 0)`. El formato Time series hace que Grafana use la columna `metric` para nombrar las series en la leyenda. En todos los paneles activar **Show values**: **Always** para mostrar los valores sin necesidad de hover.

#### Panel 1 — Examenes por dia (aprobados + suspensos)
```sql
SELECT d.fecha::date AS time,
  p.nombre || ' - Aprobados' AS metric,
  COALESCE(SUM(e.num_aprobados), 0) AS valor
FROM generate_series(
  $__timeFrom()::date, $__timeTo()::date, '1 day'::interval
) AS d(fecha)
CROSS JOIN persona p
LEFT JOIN examenes e ON e.fecha = d.fecha AND e.persona_id = p.id
WHERE p.puede_examenes = true
GROUP BY d.fecha, p.nombre

UNION ALL

SELECT d.fecha::date AS time,
  p.nombre || ' - Suspensos' AS metric,
  COALESCE(SUM(e.num_examenes - e.num_aprobados), 0) AS valor
FROM generate_series(
  $__timeFrom()::date, $__timeTo()::date, '1 day'::interval
) AS d(fecha)
CROSS JOIN persona p
LEFT JOIN examenes e ON e.fecha = d.fecha AND e.persona_id = p.id
WHERE p.puede_examenes = true
GROUP BY d.fecha, p.nombre

ORDER BY time
```
- Visualization: **Bar chart**, Format: **Time series**, Stacking: **Normal**

#### Panel 2 — Examenes acumulado (aprobados + suspensos)
```sql
SELECT e.fecha AS time, p.nombre || ' - Aprobados' AS metric,
  SUM(SUM(e.num_aprobados)) OVER (PARTITION BY p.nombre ORDER BY e.fecha) AS acumulado
FROM examenes e JOIN persona p ON e.persona_id = p.id
WHERE p.puede_examenes = true
GROUP BY e.fecha, p.nombre

UNION ALL

SELECT e.fecha AS time, p.nombre || ' - Suspensos' AS metric,
  SUM(SUM(e.num_examenes - e.num_aprobados)) OVER (PARTITION BY p.nombre ORDER BY e.fecha) AS acumulado
FROM examenes e JOIN persona p ON e.persona_id = p.id
WHERE p.puede_examenes = true
GROUP BY e.fecha, p.nombre

ORDER BY time
```
- Visualization: **Time series**, Connect null values: **Always**, Stacking: **Off**

#### Panel 3 — Ratio aprobados por dia (%)
```sql
SELECT e.fecha AS time, p.nombre AS metric,
  ROUND(SUM(e.num_aprobados)::numeric / SUM(e.num_examenes) * 100, 1) AS ratio
FROM examenes e JOIN persona p ON e.persona_id = p.id
WHERE p.puede_examenes = true AND $__timeFilter(e.fecha)
GROUP BY e.fecha, p.nombre
ORDER BY e.fecha
```
- Visualization: **Time series**, Connect null values: **Always**
- Standard options > Unit: **Misc > Percent (0-100)**

#### Panel 4 — Ratio aprobados acumulado (%)
```sql
SELECT fecha AS time, metric,
  ROUND(SUM(aprobados) OVER w::numeric / SUM(examenes) OVER w * 100, 1) AS ratio
FROM (
  SELECT e.fecha, p.nombre AS metric,
    SUM(e.num_aprobados) AS aprobados,
    SUM(e.num_examenes) AS examenes
  FROM examenes e JOIN persona p ON e.persona_id = p.id
  WHERE p.puede_examenes = true
  GROUP BY e.fecha, p.nombre
) sub
WINDOW w AS (PARTITION BY metric ORDER BY fecha)
ORDER BY fecha
```
- Visualization: **Time series**, Connect null values: **Always**
- Standard options > Unit: **Misc > Percent (0-100)**

#### Panel 5 — Acertadas por dia
```sql
SELECT d.fecha::date AS time, p.nombre AS metric,
  COALESCE(SUM(CASE WHEN q.acertada THEN 1 ELSE 0 END), 0) AS acertadas
FROM generate_series(
  $__timeFrom()::date, $__timeTo()::date, '1 day'::interval
) AS d(fecha)
CROSS JOIN persona p
LEFT JOIN pregunta_dia q ON q.fecha = d.fecha AND q.persona_id = p.id
WHERE p.puede_pregunta = true
GROUP BY d.fecha, p.nombre
ORDER BY d.fecha
```
- Visualization: **Bar chart**, Format: **Time series**, Stacking: **Normal**
- Standard options > Decimals: **0**

#### Panel 6 — Acertadas acumulado
```sql
SELECT q.fecha AS time, p.nombre AS metric,
  SUM(SUM(CASE WHEN q.acertada THEN 1 ELSE 0 END)) OVER (PARTITION BY p.nombre ORDER BY q.fecha) AS acumulado
FROM pregunta_dia q JOIN persona p ON q.persona_id = p.id
GROUP BY q.fecha, p.nombre
ORDER BY q.fecha
```
- Visualization: **Time series**, Connect null values: **Always**
- Standard options > Decimals: **0**

#### Panel 7 — Falladas por dia
```sql
SELECT d.fecha::date AS time, p.nombre AS metric,
  COALESCE(SUM(CASE WHEN q.acertada = false THEN 1 ELSE 0 END), 0) AS falladas
FROM generate_series(
  $__timeFrom()::date, $__timeTo()::date, '1 day'::interval
) AS d(fecha)
CROSS JOIN persona p
LEFT JOIN pregunta_dia q ON q.fecha = d.fecha AND q.persona_id = p.id
WHERE p.puede_pregunta = true
GROUP BY d.fecha, p.nombre
ORDER BY d.fecha
```
- Visualization: **Bar chart**, Format: **Time series**, Stacking: **Normal**
- Standard options > Decimals: **0**

#### Panel 8 — Falladas acumulado
```sql
SELECT q.fecha AS time, p.nombre AS metric,
  SUM(SUM(CASE WHEN q.acertada = false THEN 1 ELSE 0 END)) OVER (PARTITION BY p.nombre ORDER BY q.fecha) AS acumulado
FROM pregunta_dia q JOIN persona p ON q.persona_id = p.id
GROUP BY q.fecha, p.nombre
ORDER BY q.fecha
```
- Visualization: **Time series**, Connect null values: **Always**
- Standard options > Decimals: **0**

### Configurar dashboard
- Rango de tiempo por defecto: seleccionar **Last 7 days** y al guardar marcar **"Save current time range as dashboard default"**
- Compartir: Dashboard settings > **Make public** > habilitar **Time range picker enabled** para que los visitantes puedan filtrar por fechas
- Copiar el link publico

---

## 4. API pregunta del dia

### Endpoint
```
POST /api/pregunta
```

### Autenticacion
Header `Authorization: Bearer <API_KEY>`. La API_KEY se configura como variable de entorno.

### Body (JSON)
```json
{
  "persona": "Rafa",
  "fecha": "2026-07-29",
  "acertada": true
}
```

### Validaciones
- La persona debe existir y tener `puede_pregunta = true`
- La fecha no puede ser posterior a hoy
- `acertada` debe ser `true` o `false`

### Ejemplo con curl
```bash
curl -X POST https://seguimiento-a2.onrender.com/api/pregunta \
  -H "Authorization: Bearer TU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"persona": "Rafa", "fecha": "2026-07-29", "acertada": true}'
```

### Respuestas
- `200`: `{"ok": true, "mensaje": "Rafa — acertada el 2026-07-29"}`
- `401`: API key invalida o ausente
- `400`: campos faltantes, fecha invalida o futura
- `404`: persona no encontrada o sin permiso de pregunta

---

## 5. Telegram Bot

### Crear el bot
1. Abrir Telegram y buscar @BotFather
2. Enviar `/newbot`
3. Seguir instrucciones: nombre del bot y username (ej: `seguimiento_a2_bot`)
4. BotFather devuelve el **token** — guardarlo en `.env` como `TELEGRAM_BOT_TOKEN`

### Desplegar en Raspberry Pi
1. Clonar el repositorio en la Raspberry Pi:
   ```bash
   git clone <url-del-repo> ~/seguimiento-a2
   cd ~/seguimiento-a2
   ```

2. Crear entorno virtual e instalar dependencias:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Crear fichero `.env` con las credenciales:
   ```bash
   cp .env.example .env
   nano .env  # rellenar DATABASE_URL y TELEGRAM_BOT_TOKEN
   ```

4. Probar que funciona:
   ```bash
   python -m src.bot.main
   ```

5. Configurar como servicio systemd para que arranque automaticamente:
   ```bash
   sudo nano /etc/systemd/system/seguimiento-a2-bot.service
   ```

   Contenido del fichero:
   ```ini
   [Unit]
   Description=Seguimiento A2 Telegram Bot
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/seguimiento-a2
   Environment=PATH=/home/pi/seguimiento-a2/.venv/bin
   EnvironmentFile=/home/pi/seguimiento-a2/.env
   ExecStart=/home/pi/seguimiento-a2/.venv/bin/python -m src.bot.main
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

6. Activar y arrancar:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable seguimiento-a2-bot
   sudo systemctl start seguimiento-a2-bot
   ```

7. Ver logs:
   ```bash
   journalctl -u seguimiento-a2-bot -f
   ```

### Comandos del bot
- `/start` o `/ayuda` — muestra ayuda con los comandos disponibles
- `/examen <nombre> <realizados> <aprobados>` — registra examenes de hoy
- `/examen <nombre> <realizados> <aprobados> <YYYY-MM-DD>` — registra en una fecha concreta
- `/personas` — ver personas que pueden registrar examenes
- `/grafana` — devuelve el link al dashboard publico con las graficas
- `/formulario` — devuelve el link al formulario web de entrada de datos
- Validaciones: persona debe existir en la tabla con `puede_examenes = true`, fecha no futura, examenes > 0, aprobados entre 0 y examenes

---

## 6. Desarrollo local

### Configuracion
```bash
git clone <url-del-repo>
cd seguimiento-a2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con las credenciales reales (URL pooler de Supabase + token bot + API key)
```

### Arrancar la web en local
```bash
uvicorn src.web.app:app --port 5000
```
Abrir http://localhost:5000

### Arrancar el bot en local
```bash
python -m src.bot.main
```

---

## Resumen de servicios

| Servicio | URL / Acceso | Notas |
|----------|-------------|-------|
| Supabase | Panel del proyecto en supabase.com | PostgreSQL — usar siempre URL del pooler |
| Render | https://tu-nombre.onrender.com | Formulario web — cold start ~30s |
| Grafana | tu-instancia.grafana.net | Dashboard publico con link compartido |
| Telegram Bot | @tu_bot_username | Desplegado en Raspberry Pi |
