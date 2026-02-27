import os
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ===== CONFIG =====
HF_API_KEY = os.environ.get("HF_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

if not HF_API_KEY or not TELEGRAM_TOKEN:
    raise RuntimeError("Faltan variables de entorno")

HF_MODEL = "Salesforce/blip-image-captioning-large"

event_data = {}

# ===== IA PARA IMAGEN =====
def describir_imagen(image_bytes):
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/octet-stream"
    }

    response = requests.post(
        url,
        headers=headers,
        data=image_bytes,
        timeout=60
    )

    if response.status_code == 200:
        result = response.json()
        if isinstance(result, list) and "generated_text" in result[0]:
            return result[0]["generated_text"]
        return str(result)
    else:
        return f"Error IA: {response.text}"


# ===== DETECTAR EVENTO DESDE TEXTO =====
def detectar_evento(texto):
    """
    Busca algo como:
    Evento: Cumpleaños
    evento=Reunión
    #Boda
    """
    texto = texto.lower()

    if "evento:" in texto:
        return texto.split("evento:")[1].strip().split()[0]

    if "evento=" in texto:
        return texto.split("evento=")[1].strip().split()[0]

    if "#" in texto:
        return texto.split("#")[1].strip().split()[0]

    return "general"


# ===== HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Mándame una imagen o texto.\n"
        "Incluye el evento así:\n"
        "Evento: Boda\n"
        "o\n"
        "#Cumpleaños"
    )


async def texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contenido = update.message.text
    evento = detectar_evento(contenido)

    if evento not in event_data:
        event_data[evento] = []

    event_data[evento].append(contenido)

    await update.message.reply_text(
        f"Texto guardado en evento '{evento}' correctamente."
    )


async def imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Analizando imagen...")

    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()

    descripcion = describir_imagen(image_bytes)

    evento = detectar_evento(descripcion)

    if evento not in event_data:
        event_data[evento] = []

    event_data[evento].append(descripcion)

    await update.message.reply_text(
        f"IA detectó:\n{descripcion}\n\n"
        f"Guardado en evento '{evento}'."
    )


async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not event_data:
        await update.message.reply_text("No hay eventos aún.")
        return

    mensaje = ""

    for ev, datos in event_data.items():
        mensaje += f"\n📌 Evento: {ev}\n"
        for i, item in enumerate(datos, 1):
            mensaje += f"{i}. {item}\n"

    await update.message.reply_text(mensaje)


# ===== MAIN =====

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ver", ver))
app.add_handler(MessageHandler(filters.PHOTO, imagen))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), texto))

print("Bot listo 🚀")
app.run_polling()
