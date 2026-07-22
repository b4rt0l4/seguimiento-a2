from datetime import date

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.db import registrar_examen, obtener_personas, ensure_schema

app = FastAPI(title="Seguimiento A2")

templates = Jinja2Templates(directory="src/web/templates")


@app.on_event("startup")
def startup():
    ensure_schema()


def _render(request: Request, message=None):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "personas": obtener_personas(),
            "hoy": date.today().isoformat(),
            "message": message,
        },
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return _render(request)


@app.post("/registrar")
async def registrar(
    request: Request,
    persona_id: int = Form(...),
    fecha: str = Form(...),
    num_examenes: int = Form(...),
    num_aprobados: int = Form(...),
):
    try:
        fecha_parsed = date.fromisoformat(fecha)
    except ValueError:
        return _render(request, {"type": "error", "text": "Fecha invalida."})

    if fecha_parsed > date.today():
        return _render(request, {"type": "error", "text": "La fecha no puede ser posterior a hoy."})

    if num_examenes < 1:
        return _render(request, {"type": "error", "text": "El numero de examenes debe ser mayor que cero."})

    if num_aprobados < 0 or num_aprobados > num_examenes:
        return _render(request, {"type": "error", "text": f"Los aprobados deben estar entre 0 y {num_examenes}."})

    registrar_examen(persona_id, fecha_parsed, num_examenes, num_aprobados)

    personas = obtener_personas()
    nombre = next((p["nombre"] for p in personas if p["id"] == persona_id), "?")
    return _render(request, {
        "type": "success",
        "text": f"Registrado: {nombre} — {num_examenes} examen(es), {num_aprobados} aprobado(s) el {fecha}",
    })
