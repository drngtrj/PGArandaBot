import os
import requests
import json
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ===== CONFIG =====
HF_API_KEY = os.environ.get("HF_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

if not HF_API_KEY or not TELEGRAM_TOKEN:
    raise RuntimeError("Faltan variables de entorno")

VISION_MODEL = "Salesforce/blip-image-captioning-large"
TEXT_MODEL = "google/flan-t5-large"

event_data = {}

# ===== DESCRIBIR IMAGEN =====
def describir_imagen(image_bytes):
    url = f"https://api-inference.huggingface.co/models/{VISION_MODEL}"
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/octet-stream"
    }

    r = requests.post(url, headers=headers, data=image_bytes, timeout=60)

    if r.status_code == 200:
        result = r.json()
        if isinstance(result, list):
            return result[0]["generated_text"]
    return ""

# ===== CREAR EVENTO CON IA =====
def crear_evento_con_ia(texto):
    url = f"https://api-inference.huggingface.co/models/{TEXT_MODEL}"

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
Analiza el siguiente contenido y genera un nombre corto de evento
y un resumen breve.

Devuelve SOLO un JSON válido así:
{{
"evento": "nombre_evento",
"resumen": "descripcion"
}}

Contenido:
{texto}
"""

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 200
        }
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)

    if r.status_code != 200:
        print("Error IA:", r.text)
        return None

    try:
        result = r.json()[0]["generated_text"]

        inicio = result.find("{")
        fin = result.rfind("}") + 1
        json_str = result[inicio:fin]

        return json.loads(json_str)
    except Exception as e:
        print("Error parseando:", e)
        return None

# ===== HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Envíame texto o imagen.\n"
        "La IA creará automáticamente el evento.\n\n"
        "Usa /evento para ver eventos guardados."
    )

async def evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not event_data:
        await update.message.reply_text("No hay eventos guardados.")
        return

    keyboard = [
        [InlineKeyboardButton(ev, callback_data=f"ver|{ev}")]
        for ev in event_data.keys()
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Selecciona un evento:",
        reply_markup=reply_markup
    )

async def evento_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    evento_nombre = query.data.split("|")[1]

    datos = event_data.get(evento_nombre)

    if not datos:
        await query.message.reply_text("Evento sin datos.")
        return

    mensaje = f"📌 Evento: {evento_nombre}\n\n"

    for i, item in enumerate(datos, 1):
        mensaje += f"{i}. {item}\n\n"

    await query.message.reply_text(mensaje)

async def procesar(update: Update, texto_base):
    resultado = crear_evento_con_ia(texto_base)

    if not resultado:
        await update.message.reply_text("La IA no respondió correctamente.")
        return

    evento_nombre = resultado["evento"].lower().strip()
    resumen = resultado["resumen"]

    if evento_nombre not in event_data:
        event_data[evento_nombre] = []

    event_data[evento_nombre].append(resumen)

    await update.message.reply_text(
        f"Evento creado: {evento_nombre}\n"
        f"Resumen: {resumen}"
    )

async def texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await procesar(update, update.message.text)

async def imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Analizando imagen...")

    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()

    descripcion = describir_imagen(image_bytes)

    if not descripcion:
        await update.message.reply_text("No se pudo describir la imagen.")
        return

    await procesar(update, descripcion)

# ===== MAIN =====

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("evento", evento))
app.add_handler(CallbackQueryHandler(evento_callback, pattern="^ver\\|"))
app.add_handler(MessageHandler(filters.PHOTO, imagen))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), texto))

print("Bot listo 🚀")
app.run_polling()
