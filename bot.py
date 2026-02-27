import os
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ===== CONFIG =====
HF_API_KEY = os.environ.get("HF_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

if not HF_API_KEY or not TELEGRAM_TOKEN:
    raise RuntimeError("Faltan variables de entorno")

HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

event_data = {}

# ===== LLAMADA IA =====
def analizar_con_ia(texto):
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
Analiza el siguiente contenido y crea un evento.

Devuelve SOLO un JSON válido con esta estructura:
{{
  "evento": "nombre_corto_sin_espacios_raros",
  "resumen": "descripcion_breve"
}}

Contenido:
{texto}
"""

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 200,
            "temperature": 0.3
        }
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)

    if response.status_code != 200:
        return None

    result = response.json()

    try:
        texto_generado = result[0]["generated_text"]
        inicio = texto_generado.find("{")
        fin = texto_generado.rfind("}") + 1
        json_str = texto_generado[inicio:fin]
        return json.loads(json_str)
    except:
        return None

# ===== HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Envíame texto o imagen.\n"
        "La IA creará automáticamente el evento.\n\n"
        "Usa /evento para ver los eventos generados."
    )

async def evento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not event_data:
        await update.message.reply_text("No hay eventos guardados.")
        return

    keyboard = [
        [InlineKeyboardButton(ev, callback_data=f"ver|{ev}")]
        for ev in event_data.keys()
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Selecciona un evento:",
        reply_markup=reply_markup
    )

async def evento_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    evento_nombre = query.data.split("|")[1]

    datos = event_data.get(evento_nombre)

    if not datos:
        await query.message.reply_text("Este evento no tiene datos.")
        return

    mensaje = f"📌 Evento: {evento_nombre}\n\n"

    for i, item in enumerate(datos, 1):
        mensaje += f"{i}. {item}\n\n"

    await query.message.reply_text(mensaje)

async def procesar_contenido(update: Update, texto_para_ia):
    resultado = analizar_con_ia(texto_para_ia)

    if not resultado:
        await update.message.reply_text("No se pudo procesar con IA.")
        return

    evento_nombre = resultado["evento"].lower().strip()
    resumen = resultado["resumen"]

    if evento_nombre not in event_data:
        event_data[evento_nombre] = []

    event_data[evento_nombre].append(resumen)

    await update.message.reply_text(
        f"Evento creado por IA: {evento_nombre}\n"
        f"Resumen: {resumen}"
    )

async def texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contenido = update.message.text
    await procesar_contenido(update, contenido)

async def imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Analizando imagen con IA...")

    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()

    # Convertimos imagen a texto base64 para mandarla a IA
    import base64
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")

    texto_para_ia = f"Imagen en base64:\n{img_b64}"

    await procesar_contenido(update, texto_para_ia)

# ===== MAIN =====

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("evento", evento))
app.add_handler(CallbackQueryHandler(evento_callback, pattern="^ver\\|"))
app.add_handler(MessageHandler(filters.PHOTO, imagen))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), texto))

print("Bot listo 🚀")
app.run_polling()
