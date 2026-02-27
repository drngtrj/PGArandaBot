import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from PIL import Image
import pytesseract
import requests
from io import BytesIO

# Diccionario para guardar eventos
eventos = {}

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Ver eventos", callback_data="ver_eventos")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "¡Hola! Puedes enviarme texto o imágenes de eventos y los guardo.\n"
        "Usa el menú para ver tus eventos.",
        reply_markup=reply_markup
    )

# Comando para ver los eventos directamente
async def ver_eventos_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if eventos:
        lista = "\n".join(eventos.keys())
        await update.message.reply_text(f"Eventos guardados:\n{lista}")
    else:
        await update.message.reply_text("No hay eventos guardados aún ❌")

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

# Función para guardar texto
async def nuevo_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if not texto.strip():
        return
    nombre_evento = f"Evento {len(eventos)+1}"
    eventos[nombre_evento] = texto
    await update.message.reply_text(f"Guardé tu evento '{nombre_evento}' ✅")

# Función para procesar imagen
async def imagen_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = BytesIO()
    await photo_file.download(out=photo_bytes)
    photo_bytes.seek(0)

    try:
        img = Image.open(photo_bytes)
        texto = pytesseract.image_to_string(img)
        if texto.strip():
            nombre_evento = f"Evento {len(eventos)+1}"
            eventos[nombre_evento] = texto
            await update.message.reply_text(f"Guardé tu evento de la imagen '{nombre_evento}' ✅")
        else:
            await update.message.reply_text("No pude extraer texto de la imagen 😕")
    except Exception as e:
        await update.message.reply_text(f"Error procesando la imagen: {e}")

# Main
async def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("Debes configurar BOT_TOKEN en las variables de entorno")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ver_eventos", ver_eventos_comando))
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_evento))
    app.add_handler(MessageHandler(filters.PHOTO, imagen_evento))

    print("Bot listo")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
