import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- CONFIG ---
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
HF_MODEL = "philschmid/bart-large-cnn-samsum"
API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# Diccionario para almacenar eventos y datos
eventos = {}  # { "NombreEvento": {datos} }

# --- FUNCIONES ---
def extraer_datos(texto: str):
    payload = {"inputs": texto}
    try:
        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()[0]["summary_text"]  # O ajusta según el modelo que uses
    except Exception as e:
        return f"Error IA: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Manda los datos del evento y lo guardaré 📝")

async def nuevo_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    resumen = extraer_datos(texto)
    
    # Guardamos en diccionario
    nombre_evento = f"Evento{len(eventos)+1}"
    eventos[nombre_evento] = {
        "original": texto,
        "resumen": resumen
    }
    
    await update.message.reply_text(f"Datos guardados para {nombre_evento} ✅\nResumen: {resumen}")

    # Mostramos menú
    botones = [[InlineKeyboardButton(ev, callback_data=ev)] for ev in eventos]
    keyboard = InlineKeyboardMarkup(botones)
    await update.message.reply_text("Elige un evento para ver los datos:", reply_markup=keyboard)

async def menu_evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    evento = query.data
    datos = eventos.get(evento, {})
    if datos:
        await query.edit_message_text(
            f"Datos de {evento}:\n\nOriginal: {datos['original']}\nResumen: {datos['resumen']}"
        )
    else:
        await query.edit_message_text("Evento no encontrado ❌")

# --- APP ---
app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, nuevo_evento))
app.add_handler(CallbackQueryHandler(menu_evento))

app.run_polling()
