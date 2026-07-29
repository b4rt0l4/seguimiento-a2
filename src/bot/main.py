import asyncio
from datetime import date

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.config import TELEGRAM_BOT_TOKEN
from src.db import TipoPersona, registrar_examen, buscar_persona_por_nombre, obtener_personas, ensure_schema


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "Bot de seguimiento A2.\n\n"
        "Comandos:\n"
        "/examen <nombre> <realizados> <aprobados> — Registrar examenes de hoy\n"
        "/examen <nombre> <realizados> <aprobados> <YYYY-MM-DD> — En una fecha\n"
        "/personas — Ver personas disponibles\n"
        "/grafana — Ver dashboard con graficas\n"
        "/formulario — Abrir formulario web\n"
        "/ayuda — Mostrar este mensaje"
    )


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def examen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    args = context.args
    if not args or len(args) < 3:
        await update.message.reply_text(
            "Uso: /examen <nombre> <realizados> <aprobados> [fecha YYYY-MM-DD]"
        )
        return

    nombre = args[0]
    persona = buscar_persona_por_nombre(nombre, TipoPersona.EXAMENES)
    if not persona:
        personas = obtener_personas(TipoPersona.EXAMENES)
        nombres = ", ".join(p["nombre"] for p in personas)
        await update.message.reply_text(
            f"Persona '{nombre}' no encontrada.\nPersonas disponibles: {nombres}"
        )
        return

    try:
        num_examenes = int(args[1])
        num_aprobados = int(args[2])
    except ValueError:
        await update.message.reply_text("Los examenes deben ser numeros enteros.")
        return

    if num_examenes < 1:
        await update.message.reply_text("Los examenes realizados deben ser mayor que cero.")
        return

    if num_aprobados < 0 or num_aprobados > num_examenes:
        await update.message.reply_text(f"Los aprobados deben estar entre 0 y {num_examenes}.")
        return

    fecha = date.today()
    if len(args) >= 4:
        try:
            fecha = date.fromisoformat(args[3])
        except ValueError:
            await update.message.reply_text("Formato de fecha invalido. Usa YYYY-MM-DD.")
            return

    if fecha > date.today():
        await update.message.reply_text("La fecha no puede ser posterior a hoy.")
        return

    registrar_examen(persona["id"], fecha, num_examenes, num_aprobados)
    await update.message.reply_text(
        f"Registrado: {persona['nombre']} — {num_examenes} examen(es), {num_aprobados} aprobado(s) el {fecha.isoformat()}"
    )


async def personas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    lista = obtener_personas(TipoPersona.EXAMENES)
    nombres = "\n".join(f"- {p['nombre']}" for p in lista)
    await update.message.reply_text(f"Personas que pueden registrar examenes:\n{nombres}")


async def grafana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "https://ardentjunco2055.grafana.net/public-dashboards/a422b02d9fd5446b8c312001b179737b"
    )


async def formulario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "https://seguimiento-a2.onrender.com"
    )


def main():
    ensure_schema()
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("examen", examen))
    app.add_handler(CommandHandler("personas", personas))
    app.add_handler(CommandHandler("grafana", grafana))
    app.add_handler(CommandHandler("formulario", formulario))
    app.run_polling()


if __name__ == "__main__":
    main()
