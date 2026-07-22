# Guia de registro y despliegue

## 1. PostgreSQL (Supabase — free tier)

### Registro
1. Ir a https://supabase.com y crear cuenta (GitHub login recomendado)
2. Crear un nuevo proyecto (elegir region cercana, ej: eu-central-1)
3. Esperar a que el proyecto se provisione (~2 min)

### Obtener credenciales
1. Ir a **Project Settings > Database**
2. En la seccion "Connection string" copiar la URI de conexion (modo "URI")
   - Formato: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`
3. Guardar como `DATABASE_URL` en el fichero `.env`

### Nota
La tabla `examenes` se crea automaticamente al arrancar la app (tanto el bot como la web ejecutan `ensure_schema()` al inicio).

---

## 2. Grafana Cloud (free tier)

### Registro
1. Ir a https://grafana.com/auth/sign-up/create-user y crear cuenta gratuita
2. Se crea automaticamente una instancia de Grafana Cloud

### Conectar PostgreSQL como data source
1. En Grafana, ir a **Connections > Data Sources > Add data source**
2. Seleccionar **PostgreSQL**
3. Rellenar con los datos de Supabase:
   - Host: `aws-0-[region].pooler.supabase.com:6543`
   - Database: `postgres`
   - User: `postgres.[ref]`
   - Password: la del proyecto
   - TLS/SSL Mode: `require`
4. Click **Save & Test**

### Crear dashboards
1. Ir a **Dashboards > New Dashboard**

2. **Panel 1 — Examenes por dia**:
   - Add visualization, seleccionar datasource PostgreSQL
   - Query:
     ```sql
     SELECT e.fecha AS time, p.nombre AS metric, SUM(e.num_examenes) AS examenes
     FROM examenes e JOIN persona p ON e.persona_id = p.id
     GROUP BY e.fecha, p.nombre
     ORDER BY e.fecha
     ```
   - Visualization: Bar chart o Time series
   - Agrupar por: persona

3. **Panel 2 — Examenes acumulado total**:
   - Query:
     ```sql
     SELECT e.fecha AS time, p.nombre AS metric,
       SUM(SUM(e.num_examenes)) OVER (PARTITION BY p.nombre ORDER BY e.fecha) AS acumulado
     FROM examenes e JOIN persona p ON e.persona_id = p.id
     GROUP BY e.fecha, p.nombre
     ORDER BY e.fecha
     ```
   - Visualization: Time series, Connect null values: Always

4. **Panel 3 — Aprobados por dia**:
   - Query:
     ```sql
     SELECT e.fecha AS time, p.nombre AS metric, SUM(e.num_aprobados) AS aprobados
     FROM examenes e JOIN persona p ON e.persona_id = p.id
     GROUP BY e.fecha, p.nombre
     ORDER BY e.fecha
     ```
   - Visualization: Time series, Connect null values: Always

5. **Panel 4 — Aprobados acumulado total**:
   - Query:
     ```sql
     SELECT e.fecha AS time, p.nombre AS metric,
       SUM(SUM(e.num_aprobados)) OVER (PARTITION BY p.nombre ORDER BY e.fecha) AS acumulado
     FROM examenes e JOIN persona p ON e.persona_id = p.id
     GROUP BY e.fecha, p.nombre
     ORDER BY e.fecha
     ```
   - Visualization: Time series, Connect null values: Always

6. **Panel 5 — Suspensos por dia**:
   - Query:
     ```sql
     SELECT e.fecha AS time, p.nombre AS metric, SUM(e.num_examenes - e.num_aprobados) AS suspensos
     FROM examenes e JOIN persona p ON e.persona_id = p.id
     GROUP BY e.fecha, p.nombre
     ORDER BY e.fecha
     ```
   - Visualization: Time series, Connect null values: Always

7. **Panel 6 — Suspensos acumulado total**:
   - Query:
     ```sql
     SELECT e.fecha AS time, p.nombre AS metric,
       SUM(SUM(e.num_examenes - e.num_aprobados)) OVER (PARTITION BY p.nombre ORDER BY e.fecha) AS acumulado
     FROM examenes e JOIN persona p ON e.persona_id = p.id
     GROUP BY e.fecha, p.nombre
     ORDER BY e.fecha
     ```
   - Visualization: Time series, Connect null values: Always

8. **Panel 7 — Ratio aprobados por dia (%)**:
   - Query:
     ```sql
     SELECT e.fecha AS time, p.nombre AS metric,
       ROUND(SUM(e.num_aprobados)::numeric / SUM(e.num_examenes) * 100, 1) AS ratio
     FROM examenes e JOIN persona p ON e.persona_id = p.id
     GROUP BY e.fecha, p.nombre
     ORDER BY e.fecha
     ```
   - Visualization: Time series, Connect null values: Always
   - Standard options > Unit: Percent (0-100)

9. **Panel 8 — Ratio aprobados acumulado (%)**:
   - Query:
     ```sql
     SELECT fecha AS time, metric,
       ROUND(SUM(aprobados) OVER w::numeric / SUM(examenes) OVER w * 100, 1) AS ratio
     FROM (
       SELECT e.fecha, p.nombre AS metric,
         SUM(e.num_aprobados) AS aprobados,
         SUM(e.num_examenes) AS examenes
       FROM examenes e JOIN persona p ON e.persona_id = p.id
       GROUP BY e.fecha, p.nombre
     ) sub
     WINDOW w AS (PARTITION BY metric ORDER BY fecha)
     ORDER BY fecha
     ```
   - Visualization: Time series, Connect null values: Always
   - Standard options > Unit: Percent (0-100)

10. **Compartir dashboard publicamente**:
   - Dashboard settings > **Make public** (disponible en Grafana Cloud free)
   - Copiar el link publico

---

## 3. Telegram Bot

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
   nano .env  # rellenar valores reales
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

---

## 4. Web Form (Render)

### Registro
1. Ir a https://render.com y crear cuenta (GitHub login recomendado)
2. Conectar tu repositorio de GitHub/GitLab

### Desplegar
1. Crear un nuevo **Web Service**
2. Seleccionar el repositorio
3. Configurar:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.web.app:app --host 0.0.0.0 --port $PORT`
   - **Instance type**: Free
4. Anadir variables de entorno en la seccion **Environment**:
   - `DATABASE_URL`
   - `TELEGRAM_BOT_TOKEN` (no necesario para la web, pero no molesta)
5. Deploy — Render asigna una URL publica automaticamente

### Nota sobre el free tier de Render
- El servicio se "duerme" tras 15 min sin trafico
- La primera peticion tras dormir tarda ~30s (cold start)
- Para este caso de uso es aceptable

---

## Resumen de URLs y accesos

| Servicio | URL | Notas |
|----------|-----|-------|
| Grafana | (tu instancia en grafana.com) | Dashboard publico via Share link |
| Web Form | https://tu-app.onrender.com | Formulario de registro |
| Telegram Bot | @tu_bot_username | Comando /examen |
| Supabase | (panel del proyecto) | Base de datos PostgreSQL |
