import os
import requests
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

HF_MODEL = "Salesforce/blip-image-captioning-large"

# Base en memoria
event_data = {}

# ===== NORMALIZAR EVENTO =====
def limpiar_evento(nombre):
    return nombre.strip().replace("\n", "").replace("\r", "").lower()

# ===== IA IMAGEN =====
def describir_imagen(image_bytes):
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/octet-stream"
    }

    response = requests.post(
        url,
        headers=headers,
        data=image_bytes,
        timeout=60
    )

    if response.status_code == 200:
        result = response.json()
        if isinstance(result, list) and "generated_text" in result[0]:
            return result[0]["generated_text"]
        return str(result)
    else:
        return f"Error IA: {response.text}"

# ===== DETECTAR EVENTO =====
def detectar_evento(texto):
    texto_lower = texto.lower()

    if "evento:" in texto_lower:
        parte = texto_lower.split("evento:")[1]
        nombre = parte.split("\n")[0]
        return limpiar_evento(nombre)

    if "#" in texto_lower:
        parte = texto_lower.split("#")[1]
        nombre = parte.split()[0]
        return limpiar_evento(nombre)

    return "general"

# ===== HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Envíame texto o imagen.\n"
        "Incluye el evento así:\n"
        "Evento: Boda\n"
        "o\n"
        "#Cumpleaños\n\n"
        "Usa /evento para ver los eventos guardados."
    )

# 🔹 COMANDO /evento
async def evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not event_data:
        await update.message.reply_text("No hay eventos creados aún.")
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

# 🔹 CALLBACK BOTÓN
async def evento_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if not data.startswith("ver|"):
        return

    evento_nombre = data.split("|")[1]

    datos = event_data.get(evento_nombre)

    if not datos:
        await query.message.reply_text(
            f"No hay datos guardados en '{evento_nombre}'."
        )
        return

    mensaje = f"📌 Evento: {evento_nombre}\n\n"

    for i, item in enumerate(datos, 1):
        mensaje += f"{i}. {item}\n\n"

    await query.message.reply_text(mensaje)

# 🔹 TEXTO
async def texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contenido = update.message.text
    evento_nombre = detectar_evento(contenido)

    if evento_nombre not in event_data:
        event_data[evento_nombre] = []

    event_data[evento_nombre].append(contenido)

    await update.message.reply_text(
        f"Guardado en evento '{evento_nombre}'."
    )

# 🔹 IMAGEN
async def imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Analizando imagen...")

    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()

    descripcion = describir_imagen(image_bytes)

    evento_nombre = detectar_evento(descripcion)

    if evento_nombre not in event_data:
        event_data[evento_nombre] = []

    event_data[evento_nombre].append(descripcion)

    await update.message.reply_text(
        f"IA detectó:\n{descripcion}\n\n"
        f"Guardado en evento '{evento_nombre}'."
    )

# ===== MAIN =====

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("evento", evento))
app.add_handler(CallbackQueryHandler(evento_callback, pattern="^ver\\|"))
app.add_handler(MessageHandler(filters.PHOTO, imagen))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), texto))

print("Bot listo 🚀")
app.run_polling()
