import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)

# ===== CONFIG =====
HF_API_KEY = os.environ.get("HF_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

if not HF_API_KEY or not TELEGRAM_TOKEN:
    raise RuntimeError("Faltan variables de entorno HF_API_KEY o TELEGRAM_TOKEN")

# Modelo que SÍ funciona con imágenes
HF_MODEL = "google/vit-base-patch16-224"

event_data = {}

# ===== FUNCION IA CORREGIDA =====
def process_image(image_bytes):
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
        return response.json()
    else:
        return {"error": response.text}


# ===== HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola compa! Usa /evento para crear o seleccionar evento."
    )

async def evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(ev, callback_data=ev)] for ev in event_data
    ]
    keyboard.append([InlineKeyboardButton("Crear nuevo evento", callback_data="NEW")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona evento:", reply_markup=reply_markup)

async def evento_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "NEW":
        await query.message.reply_text("Escribe el nombre del evento:")
        context.user_data["creating_event"] = True
    else:
        context.user_data["evento_actual"] = query.data
        await query.message.reply_text(f"Evento seleccionado: {query.data}")

async def texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("creating_event"):
        nombre = update.message.text.strip()
        event_data[nombre] = []
        context.user_data["evento_actual"] = nombre
        context.user_data["creating_event"] = False
        await update.message.reply_text(f"Evento '{nombre}' creado!")
    else:
        await update.message.reply_text("Envíame una imagen mejor 😉")

async def imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    evento_actual = context.user_data.get("evento_actual")

    if not evento_actual:
        await update.message.reply_text("Primero crea o selecciona un evento con /evento")
        return

    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()

    resultado = process_image(image_bytes)

    event_data[evento_actual].append(resultado)

    await update.message.reply_text(
        f"Imagen procesada en evento '{evento_actual}'\n\nResultado IA:\n{resultado}"
    )

# ===== MAIN =====

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("evento", evento))
app.add_handler(CallbackQueryHandler(evento_callback))
app.add_handler(MessageHandler(filters.PHOTO, imagen))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), texto))

print("Bot listo 🚀")
app.run_polling()
