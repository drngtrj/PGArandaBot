import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Variables de entorno (ponelas en Railway: Settings → Environment Variables)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_API_KEY = os.environ.get("HF_API_KEY")
HF_MODEL = "facebook/bart-large-cnn"  # modelo de resumen

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"


# Función para resumir texto usando Hugging Face
def resumir_texto(texto):
    payload = {"inputs": texto}
    response = requests.post(HF_API_URL, headers=HEADERS, json=payload)
    data = response.json()
    if "error" in data:
        return f"Error al resumir: {data['error']}"
    return data[0]["summary_text"]


# Función que responde a los mensajes en Telegram
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text
    resumen = resumir_texto(texto_usuario)
    await update.message.reply_text(resumen)


# Configuración de la app con Webhook (para Railway)
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

# Usar Webhook en vez de polling
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # tu URL de Railway, ej: https://miapp.up.railway.app

# Arranca el webhook
app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
    webhook_url=WEBHOOK_URL
)
