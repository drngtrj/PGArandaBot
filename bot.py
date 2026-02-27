import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Tokens y claves
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
HF_API_KEY = os.environ["HF_API_KEY"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

# Cliente OpenAI / Hugging Face
client = OpenAI(api_key=HF_API_KEY)

# Función que resume mensajes
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text

    # Llamada a la API para resumir
    respuesta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Resumir y responder de forma clara y breve."},
            {"role": "user", "content": texto_usuario}
        ]
    )

    # Enviar respuesta resumida
    await update.message.reply_text(respuesta.choices[0].message.content)

# Crear la app de Telegram
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

# Ejecutar webhook
app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
    webhook_url=WEBHOOK_URL
)


