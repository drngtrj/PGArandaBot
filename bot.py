import os
import logging
import aiohttp
from PIL import Image
from io import BytesIO
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# --- Configuración ---
HF_API_KEY = os.environ.get("HF_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # si usas webhook

if not HF_API_KEY or not TELEGRAM_TOKEN:
    raise RuntimeError("Debes configurar HF_API_KEY y TELEGRAM_TOKEN en variables de entorno")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Base de datos en memoria ---
eventos = {}  # formato: {"nombre_evento": {"datos": [...] } }

# --- Función para llamar a Hugging Face ---
async def procesar_ia(prompt=None, image_bytes=None):
    url = "https://router.huggingface.co/models/gpt-4o-mini"  # modelo de ejemplo
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {}
    if prompt:
        payload["inputs"] = prompt
    elif image_bytes:
        payload["inputs"] = image_bytes  # depende del modelo, aquí ejemplo simplificado

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=60) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get("generated_text", "No se generó respuesta")
            else:
                return f"Error IA: {await resp.text()}"

# --- Handlers de comandos ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    botones = [
        [InlineKeyboardButton("Crear evento", callback_data="evento_crear")],
        [InlineKeyboardButton("Listar eventos", callback_data="evento_listar")],
        [InlineKeyboardButton("Borrar evento", callback_data="evento_borrar")]
    ]
    markup = InlineKeyboardMarkup(botones)
    await update.message.reply_text("Bienvenido al bot! Elige una opción:", reply_markup=markup)

async def eventos_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "evento_crear":
        await query.message.reply_text("Envíame el nombre del evento:")
        context.user_data["modo_evento"] = "crear"
    elif query.data == "evento_listar":
        if eventos:
            lista = "\n".join(eventos.keys())
            await query.message.reply_text(f"Eventos guardados:\n{lista}")
        else:
            await query.message.reply_text("No hay eventos guardados.")
    elif query.data == "evento_borrar":
        if eventos:
            botones = [[InlineKeyboardButton(name, callback_data=f"borrar_{name}")] for name in eventos.keys()]
            markup = InlineKeyboardMarkup(botones)
            await query.message.reply_text("Elige evento a borrar:", reply_markup=markup)
        else:
            await query.message.reply_text("No hay eventos para borrar.")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    modo = context.user_data.get("modo_evento")
    if modo == "crear":
        eventos[user_text] = {"datos": []}
        await update.message.reply_text(f"Evento '{user_text}' creado!")
        context.user_data["modo_evento"] = None
    else:
        respuesta = await procesar_ia(prompt=user_text)
        await update.message.reply_text(f"IA dice: {respuesta}")

async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = BytesIO()
    await photo_file.download_to_memory(out=photo_bytes)
    photo_bytes.seek(0)
    respuesta = await procesar_ia(image_bytes=photo_bytes.read())
    await update.message.reply_text(f"IA dice: {respuesta}")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("borrar_"):
        nombre = data.replace("borrar_", "")
        if nombre in eventos:
            del eventos[nombre]
            await query.message.reply_text(f"Evento '{nombre}' borrado!")
        else:
            await query.message.reply_text("Evento no encontrado.")

# --- Main ---
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Comandos básicos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(eventos_menu))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern=r"borrar_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, image_handler))

    # Opcional: setear menú de comandos en Telegram
    await app.bot.set_my_commands([
        BotCommand("start", "Inicia el bot"),
    ])

    # Run
    if WEBHOOK_URL:
        await app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8000)),
            webhook_url=WEBHOOK_URL
        )
    else:
        await app.run_polling()

import asyncio
asyncio.run(main())
