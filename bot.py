import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from PIL import Image
import pytesseract
from io import BytesIO

# Variables de entorno
HF_API_KEY = os.environ.get("HF_API_KEY")           # Tu Hugging Face API Key
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")   # Tu token de Telegram
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")         # Tu URL pública HTTPS para webhook

# Diccionario para guardar eventos
eventos = {}

# Etapas del conversation handler
NOMBRE_EVENTO = 1

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Ver eventos", callback_data="ver_eventos")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "¡Hola! Puedes crear eventos y enviar texto o imágenes.\n"
        "Usa /nuevoevento para crear un evento con nombre.",
        reply_markup=reply_markup
    )

# Iniciar nuevo evento
async def nuevo_evento_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escribe el nombre de tu nuevo evento:")
    return NOMBRE_EVENTO

# Guardar el nombre y pedir contenido
async def nuevo_evento_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text.strip()
    if not nombre:
        await update.message.reply_text("El nombre no puede estar vacío, intenta de nuevo:")
        return NOMBRE_EVENTO

    context.user_data['nombre_evento'] = nombre
    await update.message.reply_text(
        f"Perfecto, tu evento se llamará '{nombre}'.\n"
        "Ahora envía texto o una imagen para guardar los datos."
    )
    return ConversationHandler.END

# Callback del menú
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "ver_eventos":
        if eventos:
            keyboard = [
                [InlineKeyboardButton(name, callback_data=f"evento_{name}")]
                for name in eventos
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Elige un evento:", reply_markup=reply_markup)
        else:
            await query.edit_message_text("No hay eventos guardados aún ❌")
    elif query.data.startswith("evento_"):
        nombre_evento = query.data.split("_", 1)[1]
        datos = eventos.get(nombre_evento, "No hay datos")
        await query.edit_message_text(f"Evento: {nombre_evento}\nDatos:\n{datos}")

# Guardar texto en evento
async def guardar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre_evento = context.user_data.get('nombre_evento')
    if not nombre_evento:
        await update.message.reply_text(
            "Primero usa /nuevoevento para crear un evento y darle un nombre."
        )
        return

    eventos[nombre_evento] = update.message.text
    await update.message.reply_text(f"Guardé el texto en el evento '{nombre_evento}' ✅")
    context.user_data.pop('nombre_evento')

# Guardar imagen en evento
async def guardar_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre_evento = context.user_data.get('nombre_evento')
    if not nombre_evento:
        await update.message.reply_text(
            "Primero usa /nuevoevento para crear un evento y darle un nombre."
        )
        return

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = BytesIO()
    await photo_file.download(out=photo_bytes)
    photo_bytes.seek(0)

    try:
        img = Image.open(photo_bytes)
        texto = pytesseract.image_to_string(img)
        if texto.strip():
            eventos[nombre_evento] = texto
            await update.message.reply_text(f"Guardé el evento '{nombre_evento}' de la imagen ✅")
        else:
            await update.message.reply_text("No pude extraer texto de la imagen 😕")
    except Exception as e:
        await update.message.reply_text(f"Error procesando la imagen: {e}")

    context.user_data.pop('nombre_evento')

# Main
async def main():
    if not TELEGRAM_TOKEN:
        print("Debes configurar TELEGRAM_TOKEN en las variables de entorno")
        return
    if not HF_API_KEY:
        print("Debes configurar HF_API_KEY en las variables de entorno")
        return
    if not WEBHOOK_URL:
        print("Debes configurar WEBHOOK_URL en las variables de entorno")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Conversation handler para crear evento con nombre
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('nuevoevento', nuevo_evento_start)],
        states={
            NOMBRE_EVENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_evento_nombre)]
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_texto))
    app.add_handler(MessageHandler(filters.PHOTO, guardar_imagen))

    print("Bot listo")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
