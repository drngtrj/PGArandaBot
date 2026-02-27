import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)
from PIL import Image
import io
import requests

# --- CONFIG ---
HF_API_KEY = os.environ.get("HF_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Solo si usas webhook

# Almacenamiento en memoria (puede pasar a DB si quieres)
event_data = {}  # {'Evento 1': [imagenes y datos], 'Evento 2': [...]}

# --- FUNCIONES DE IA ---
def process_image(image_bytes):
    """Envía la imagen a Hugging Face y devuelve el resultado"""
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    files = {"file": image_bytes}
    response = requests.post(
        "https://router.huggingface.co/models/google/vit-base-patch16-224",
        headers=headers,
        files=files,
        timeout=30
    )
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola! Envíame imágenes para procesarlas y almacena los datos por evento.\n"
        "Usa /evento para crear un nuevo evento o seleccionar uno existente."
    )

async def evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menú de eventos existentes o permite crear uno nuevo"""
    keyboard = [
        [InlineKeyboardButton(ev, callback_data=ev)] for ev in event_data
    ]
    keyboard.append([InlineKeyboardButton("Crear nuevo evento", callback_data="NUEVO_EVENTO")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona un evento:", reply_markup=reply_markup)

async def evento_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "NUEVO_EVENTO":
        await query.message.reply_text("Escribe el nombre del nuevo evento:")
        context.user_data["esperando_evento"] = True
    else:
        context.user_data["evento_actual"] = query.data
        await query.message.reply_text(f"Seleccionaste el evento: {query.data}")

async def mensaje_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe texto para crear evento si estamos en modo 'esperando_evento'"""
    if context.user_data.get("esperando_evento"):
        nombre_evento = update.message.text.strip()
        if nombre_evento not in event_data:
            event_data[nombre_evento] = []
        context.user_data["evento_actual"] = nombre_evento
        context.user_data["esperando_evento"] = False
        await update.message.reply_text(f"Evento '{nombre_evento}' creado y seleccionado!")
    else:
        await update.message.reply_text("Envíame una imagen para procesarla.")

async def imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa la imagen y la guarda en el evento seleccionado"""
    evento_actual = context.user_data.get("evento_actual")
    if not evento_actual:
        await update.message.reply_text("Primero selecciona o crea un evento con /evento")
        return

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    resultado = process_image(io.BytesIO(photo_bytes))
    
    # Guardamos la info en el evento
    event_data[evento_actual].append({"imagen": photo_bytes, "resultado": resultado})
    
    await update.message.reply_text(f"Imagen procesada y guardada en evento '{evento_actual}'!\nResultado IA: {resultado}")

async def listar_eventos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista los eventos y cuántas imágenes tienen"""
    if not event_data:
        await update.message.reply_text("No hay eventos aún.")
        return
    msg = "Eventos actuales:\n"
    for ev, items in event_data.items():
        msg += f"- {ev}: {len(items)} imagen(es)\n"
    await update.message.reply_text(msg)

# --- MAIN ---
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("evento", evento))
app.add_handler(CommandHandler("listar", listar_eventos))
app.add_handler(CallbackQueryHandler(evento_callback))
app.add_handler(MessageHandler(filters.PHOTO, imagen))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), mensaje_texto))

# Corremos el bot (polling)
print("Bot listo")
app.run_polling()

