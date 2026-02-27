import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    CallbackQueryHandler, filters
)
import httpx

# --- CONFIG ---
HF_API_KEY = "TU_HF_API_KEY"
TELEGRAM_TOKEN = "TU_TELEGRAM_TOKEN"

# Diccionario para almacenar eventos
eventos = {}  # { "Nombre Evento": "Resumen IA" }

# --- FUNCIONES IA ---
async def procesar_texto_ia(texto: str) -> str:
    """Procesa texto con HuggingFace y devuelve resumen"""
    url = "https://api-inference.huggingface.co/models/google/flan-t5-small"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {
        "inputs": f"Resume este texto en pocas palabras: {texto}",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            resultado = r.json()
            # HuggingFace devuelve lista con 'generated_text'
            if isinstance(resultado, list) and "generated_text" in resultado[0]:
                return resultado[0]["generated_text"]
            else:
                return "No se pudo resumir el texto con IA."
    except Exception as e:
        return f"No se pudo procesar con IA: {e}"

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola! Envía un texto describiendo un evento y la IA lo guardará."
    )

async def nuevo_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Crea un nuevo evento desde el texto del usuario"""
    if not context.args:
        await update.message.reply_text("Usa /nuevoevento NOMBRE_DEL_EVENTO")
        return

    nombre_evento = " ".join(context.args)
    await update.message.reply_text(f"Envíame la descripción del evento '{nombre_evento}'")

    # Guardamos temporalmente el nombre del evento en context.user_data
    context.user_data["nombre_evento"] = nombre_evento

async def texto_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el texto enviado por el usuario como descripción del evento"""
    if "nombre_evento" not in context.user_data:
        await update.message.reply_text("Primero indica el nombre del evento con /nuevoevento")
        return

    nombre = context.user_data.pop("nombre_evento")
    texto = update.message.text

    resumen = await procesar_texto_ia(texto)
    eventos[nombre] = resumen

    await update.message.reply_text(
        f"Evento '{nombre}' guardado con resumen:\n{resumen}"
    )

async def listar_eventos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra botones con todos los eventos"""
    if not eventos:
        await update.message.reply_text("No hay eventos guardados.")
        return

    botones = [
        [InlineKeyboardButton(nombre, callback_data=nombre)]
        for nombre in eventos.keys()
    ]
    await update.message.reply_text(
        "Selecciona un evento:",
        reply_markup=InlineKeyboardMarkup(botones)
    )

async def ver_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la info del evento seleccionado"""
    query = update.callback_query
    await query.answer()
    nombre = query.data
    info = eventos.get(nombre, "No hay información para este evento.")
    await query.edit_message_text(f"Evento: {nombre}\nResumen: {info}")

# --- MAIN ---
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nuevoevento", nuevo_evento))
    app.add_handler(CommandHandler("evento", listar_eventos))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto_evento))
    app.add_handler(CallbackQueryHandler(ver_evento))

    print("Bot listo")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
