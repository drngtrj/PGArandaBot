import os
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)

# Variables de entorno
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_API_KEY = os.environ.get("HF_API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

HF_API_KEY = os.environ.get("HF_API_KEY")
# Modelo de resumen (puedes cambiarlo si quieres otro)
HF_MODEL = "facebook/bart-large-cnn"


def resumir_texto(texto):
    API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": texto,
        "parameters": {
            "max_length": 130,
            "min_length": 30,
            "do_sample": False
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        result = response.json()

        if isinstance(result, list):
            return result[0]["summary_text"]
        else:
            return f"Error IA: {result}"

    except Exception as e:
        return f"Error técnico: {str(e)}"


# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Mándame un texto largo y te lo resumo al tiro 🔥"
    )


# Responder a mensajes normales
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto = update.message.text

    if len(texto) < 50:
        await update.message.reply_text("Eso está muy corto pa resumir 😅")
        return

    await update.message.reply_text("Dame un segundo que estoy pensando... 🧠")

    resumen = resumir_texto(texto)

    await update.message.reply_text(resumen)


# Crear app
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

# Ejecutar webhook (Railway)
app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
    webhook_url=WEBHOOK_URL
)

