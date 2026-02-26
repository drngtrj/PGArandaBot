import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from openai import OpenAI

TELEGRAM_TOKEN = "8666433188:AAFyo56YJPNngSk0phnYqv-meTjLXUCGB00"
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





