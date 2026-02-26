import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from openai import OpenAI

TELEGRAM_TOKEN = os.getenv("8666433188:AAFyo56YJPNngSk0phnYqv-meTjLXUCGB00")
OPENAI_API_KEY = "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"

print("TOKEN:", TELEGRAM_TOKEN)
print("API KEY:", OPENAI_API_KEY)

client = OpenAI(api_key=OPENAI_API_KEY)

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("API KEY:", OPENAI_API_KEY)
    texto_usuario = update.message.text

    respuesta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Responde de forma clara y breve."},
            {"role": "user", "content": texto_usuario}
        ]
    )

    await update.message.reply_text(respuesta.choices[0].message.content)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))


app.run_polling()


