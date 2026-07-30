from datetime import date, datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Form, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.config import API_KEY
from src.db import (
    TipoPersona,
    buscar_persona_por_nombre,
    ensure_schema,
    obtener_personas,
    registrar_examen,
    registrar_pregunta,
)

app = FastAPI(title="Seguimiento A2")

templates = Jinja2Templates(directory="src/web/templates")


@app.on_event("startup")
def startup():
    ensure_schema()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, msg: str = "", msg_type: str = ""):
    message = None
    if msg:
        message = {"type": msg_type or "success", "text": msg}
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "personas": obtener_personas(TipoPersona.EXAMENES),
            "hoy": datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat(),
            "message": message,
        },
    )


@app.post("/registrar")
async def registrar(
    persona_id: int = Form(...),
    fecha: str = Form(...),
    num_examenes: int = Form(...),
    num_aprobados: int = Form(...),
):
    try:
        fecha_parsed = date.fromisoformat(fecha)
    except ValueError:
        return RedirectResponse(f"/?msg={quote('Fecha invalida.')}&msg_type=error", status_code=303)

    if fecha_parsed > datetime.now(ZoneInfo("Europe/Madrid")).date():
        return RedirectResponse(f"/?msg={quote('La fecha no puede ser posterior a hoy.')}&msg_type=error", status_code=303)

    if num_examenes < 1:
        return RedirectResponse(f"/?msg={quote('El numero de examenes debe ser mayor que cero.')}&msg_type=error", status_code=303)

    if num_aprobados < 0 or num_aprobados > num_examenes:
        return RedirectResponse(f"/?msg={quote(f'Los aprobados deben estar entre 0 y {num_examenes}.')}&msg_type=error", status_code=303)

    registrar_examen(persona_id, fecha_parsed, num_examenes, num_aprobados)

    personas = obtener_personas(TipoPersona.EXAMENES)
    nombre = next((p["nombre"] for p in personas if p["id"] == persona_id), "?")
    msg = f"Registrado: {nombre} — {num_examenes} examen(es), {num_aprobados} aprobado(s) el {fecha}"
    return RedirectResponse(f"/?msg={quote(msg)}&msg_type=success", status_code=303)


@app.post("/api/pregunta")
async def api_pregunta(request: Request, authorization: str = Header(None)):
    if not API_KEY:
        return JSONResponse({"error": "API no configurada"}, status_code=500)

    if not authorization or authorization != f"Bearer {API_KEY}":
        return JSONResponse({"error": "No autorizado"}, status_code=401)

    body = await request.json()

    nombre = body.get("persona")
    fecha_str = body.get("fecha")
    acertada = body.get("acertada")

    if not nombre or fecha_str is None or acertada is None:
        return JSONResponse({"error": "Campos requeridos: persona, fecha, acertada"}, status_code=400)

    persona = buscar_persona_por_nombre(nombre, TipoPersona.PREGUNTA)
    if not persona:
        return JSONResponse({"error": f"Persona '{nombre}' no encontrada o no participa en pregunta del dia"}, status_code=404)

    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        return JSONResponse({"error": f"{fecha_str} no es un formato de fecha válido. Usa YYYY-MM-DD"}, status_code=400)

    if fecha > datetime.now(ZoneInfo("Europe/Madrid")).date():
        return JSONResponse({"error": "La fecha no puede ser posterior a hoy"}, status_code=400)

    if not isinstance(acertada, bool):
        return JSONResponse({"error": "El campo acertada debe ser true o false"}, status_code=400)

    registrar_pregunta(persona["id"], fecha, acertada)

    return JSONResponse({
        "ok": True,
        "mensaje": f"{persona['nombre']} — {'acertada' if acertada else 'fallada'} el {fecha.isoformat()}",
    })
