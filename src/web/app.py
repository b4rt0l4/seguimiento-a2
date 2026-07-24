from datetime import date
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.db import registrar_examen, obtener_personas, ensure_schema

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
            "personas": obtener_personas(),
            "hoy": date.today().isoformat(),
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

    if fecha_parsed > date.today():
        return RedirectResponse(f"/?msg={quote('La fecha no puede ser posterior a hoy.')}&msg_type=error", status_code=303)

    if num_examenes < 1:
        return RedirectResponse(f"/?msg={quote('El numero de examenes debe ser mayor que cero.')}&msg_type=error", status_code=303)

    if num_aprobados < 0 or num_aprobados > num_examenes:
        return RedirectResponse(f"/?msg={quote(f'Los aprobados deben estar entre 0 y {num_examenes}.')}&msg_type=error", status_code=303)

    registrar_examen(persona_id, fecha_parsed, num_examenes, num_aprobados)

    personas = obtener_personas()
    nombre = next((p["nombre"] for p in personas if p["id"] == persona_id), "?")
    msg = f"Registrado: {nombre} — {num_examenes} examen(es), {num_aprobados} aprobado(s) el {fecha}"
    return RedirectResponse(f"/?msg={quote(msg)}&msg_type=success", status_code=303)
